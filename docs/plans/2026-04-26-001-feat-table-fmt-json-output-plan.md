---
title: "feat: Add --json output mode to table_fmt.py"
type: feat
status: active
date: 2026-04-26
origin: docs/brainstorms/2026-04-26-table-fmt-json-output-requirements.md
---

# feat: Add --json output mode to table_fmt.py

## Overview

Add an opt-in `--json` flag to `table_fmt.py` that emits the parsed table as a JSON array of row objects keyed by header text, instead of the formatted markdown table. Default (no-flag) behavior remains byte-for-byte identical to today.

## Problem Frame

`table_fmt.py` currently does one thing: read a sloppy markdown table from stdin, write a re-formatted markdown table to stdout. Downstream consumers (scripts, dashboards, other tools in this repo) that want structured access to the cells must re-parse the formatter's output, which is wasteful and brittle. A `--json` mode lets callers reuse the existing parser and get a structured representation in a single step. (see origin: `docs/brainstorms/2026-04-26-table-fmt-json-output-requirements.md`)

## Requirements Trace

- **R1.** `--json` writes JSON to stdout; absent `--json`, current markdown round-trip behavior is preserved byte-for-byte.
- **R2.** JSON shape is an array of row objects, keyed by header-row cell text; all cell values are strings (no type coercion).
- **R3.** JSON is pretty-printed with `indent=2` and terminated with a single trailing newline.
- **R4.** `--help` documents the new `--json` flag.
- **R5.** Implementation reuses existing `parse_table()` — no parallel parser.
- **R6.** Tests cover: basic happy path, table with alignments (alignment metadata dropped), single-column table, and table with empty cells.
- **R7.** Malformed input fails fast with non-zero exit and stderr message — matches existing `main()` pattern. Never silently emit `[]` for non-table input.

## Scope Boundaries

- No type coercion (numbers/booleans/nulls stay as strings).
- No streaming output for large tables.
- No reverse `--from-json` mode.
- No file-path argument — stdin only.
- No edits to `countdown.sh`, `dashboard.html`, or any unrelated file.

## Context & Research

### Relevant Code and Patterns

- `table_fmt.py:27` — `parse_table(text)` returns `(rows, alignments)`. When a separator row is seen, `rows[0]` is the header and `alignments` is a per-column list. When no separator is seen, `alignments == []` and the header is unidentified — the JSON shape `{header: value}` is undefined in that case.
- `table_fmt.py:61` — `format_table(rows, alignments=None)` — the existing companion to a new `format_json` helper. Same `(rows, alignments)` argument shape keeps the API parallel.
- `table_fmt.py:123` — `main()` sets the precedent for malformed-input handling: `print("Error: ...", file=sys.stderr)` followed by `sys.exit(1)`. New error paths must follow this pattern.
- `test_table_fmt.py` — tests are organized into `unittest.TestCase` classes by concern (`ParseAlignmentTests`, `FormatSeparatorTests`, `FormatRowPaddingTests`, `RoundTripTests`). New JSON tests should follow this convention with a dedicated class (e.g., `FormatJsonTests`, `MainCliTests`).

### Institutional Learnings

- `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md` — alignment-hint discovery established the `parse_table` → `(rows, alignments)` contract. JSON output deliberately drops the alignment list because per-column alignment has no JSON representation in this contract (R2). Round-trip / fixed-point thinking from that solution does not apply here: JSON is a one-way emission, not a round-trip target.
- The same solutions doc reinforces "before broadening a function's signature, grep every call site." `parse_table` already has the right signature; we are adding a new sibling formatter, not modifying parser shape.

### External References

None gathered. Stdlib `argparse` and `json` are well-established and the codebase has no equivalent local pattern to mirror — this is the script's first CLI flag and first JSON emission. Decisions in the origin doc (argparse, error-on-ambiguity) already align with stdlib idioms.

## Key Technical Decisions

- **Argparse over manual `argv` inspection.** Stdlib, gives `--help`, unknown-flag rejection, and a stable extension surface for free; cost is trivial. (see origin)
- **Error on no-header-row (`alignments == []`).** Without a separator we cannot identify which row is the header, so the `{header: value}` shape is undefined. Falling back silently changes the contract; erroring matches R7 and existing `main()` precedent. (see origin)
- **Error on duplicate header keys, naming the duplicate.** Last-wins/first-wins silently lose data; numeric-suffixing produces keys the caller did not write. Erroring keeps the JSON shape unambiguous. (see origin)
- **New `format_json(rows, alignments)` helper, parallel to `format_table`.** Keeps `main()` thin, enables direct unit testing of JSON shape and error paths without spawning a subprocess, and mirrors the existing `format_table` API shape so future readers see the symmetry. (resolves origin "Deferred to Planning" item #2.)
- **Error message wording reuses the existing `Error: ...` prefix and `sys.exit(1)` exit code.** Concrete strings:
  - `Error: --json requires a header row (no separator row found in input)`
  - `Error: --json requires unique header column names; duplicate header: '<name>'`
  Consistency with the existing "Error: no valid markdown table found in input" message; exit 1 matches R7. (resolves origin "Deferred to Planning" item #1.)
- **Use `json.dumps(payload, indent=2, ensure_ascii=False)` plus a trailing `\n` written separately.** `indent=2` satisfies R3; `ensure_ascii=False` preserves non-ASCII cell text rather than escaping it (markdown tables routinely contain UTF-8). Single trailing newline aligns with the existing `format_table` output convention.

## Open Questions

### Resolved During Planning

- **Helper vs inline JSON emission?** → Helper (`format_json`). Testability + API symmetry with `format_table`.
- **Error wording and exit code?** → Reuse `Error: ...` prefix + `sys.exit(1)`. See decisions above.
- **Header row with a single empty cell — allowed key `""`?** → Allowed. The origin doc explicitly states a single empty header is valid; multiple empty headers fall under the duplicate-header rule and error out.
- **Should `format_json` accept the alignments list it does not use?** → Yes. The signal "is `alignments` empty?" is the only reliable way to know whether the parser identified a header row. Accepting the list keeps the API parallel to `format_table` and avoids passing a separate boolean.

### Deferred to Implementation

- Whether to factor the duplicate-detection scan into its own private helper (`_check_unique_headers`) or keep it inline in `format_json`. Decide based on how the body reads after writing it; either is acceptable.
- Whether the argparse `description=` string should mention specific examples or stay terse. Decide once `--help` output is visible.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
stdin ──► parse_table(text) ──► (rows, alignments)
                                     │
                                     ├─ alignments == []  ──► stderr "Error: --json requires a header row…", exit 1
                                     │
                                     ├─ duplicate in rows[0]  ──► stderr "Error: --json requires unique header column names…", exit 1
                                     │
                                     └─ ok ──► format_json(rows, alignments)
                                                   │
                                                   │  header = rows[0]
                                                   │  payload = [ dict(zip(header, row)) for row in rows[1:] ]
                                                   │  text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
                                                   │
                                                   ▼
                                               stdout

main():
    parse argv with argparse → args.json bool
    read stdin
    rows, alignments = parse_table(text)
    if not rows:  → existing "no valid markdown table" error path (unchanged)
    if args.json: → format_json branch
    else:         → format_table branch (current default, unchanged)
```

Argparse contract:

```
usage: table_fmt.py [-h] [--json]

Format markdown tables from stdin. Without --json, output a re-aligned
markdown table. With --json, output an array of row objects keyed by header.

options:
  -h, --help  show this help message and exit
  --json      emit parsed table as JSON instead of markdown
```

## Implementation Units

- [ ] **Unit 1: Add `format_json(rows, alignments)` helper**

**Goal:** Add a new module-level function that converts parsed table data to a JSON string matching R2/R3, with header-row and duplicate-header validation that raises a typed error rather than calling `sys.exit` directly.

**Requirements:** R2, R3, R5, R7

**Dependencies:** None (uses existing `parse_table` output contract).

**Files:**
- Modify: `table_fmt.py`
- Test: `test_table_fmt.py`

**Approach:**
- Add `format_json(rows, alignments)` near `format_table`, before `main()`.
- Validation order:
  1. If `not rows` → raise `ValueError("no valid markdown table found in input")`. (Or let `main()` continue to handle this — see note below.)
  2. If `alignments == []` (no separator row seen) → raise `ValueError("--json requires a header row (no separator row found in input)")`.
  3. If `rows[0]` contains duplicate values → raise `ValueError("--json requires unique header column names; duplicate header: '<name>'")` naming the first duplicate seen.
- Build `payload = [dict(zip(header, row)) for row in rows[1:]]`. Use `dict(zip(...))` so a row shorter than the header naturally truncates and a row longer than the header naturally drops trailing extras — both edge cases are out of scope for explicit handling and the zip behavior is the simplest defensible default.
- Return `json.dumps(payload, indent=2, ensure_ascii=False) + "\n"`.
- Note on validation #1: the existing `main()` already errors on `not rows` before either branch; keeping that single check in `main()` is simplest. `format_json` then assumes `rows` is non-empty as a precondition. Implementer can choose either layout; document the choice in a one-line comment if defensive validation is added inside `format_json`.

**Patterns to follow:**
- `format_table` in `table_fmt.py:61` — same `(rows, alignments)` argument shape, same module-level placement, same single-string return.
- Existing docstring style — one-line summary, then a short paragraph explaining behavior.

**Test scenarios:**
- Basic happy path: 2-column, 2-row table → array of 2 dicts with header keys, string values.
- Alignment metadata dropped: feed in `(rows, ["left", "right", "center"])` → output JSON has no alignment info; rows are still keyed by header.
- Single-column table: header `["X"]`, rows `[["X"], ["a"], ["b"]]` → `[{"X": "a"}, {"X": "b"}]`.
- Empty cells preserved as `""`: row `["Alice", ""]` → `{"Name": "Alice", "Age": ""}`.
- Pretty-print contract: returned string matches `json.dumps(..., indent=2)` output and ends with exactly one `\n`.
- Error: `alignments == []` → raises `ValueError` whose message starts with the no-header phrasing.
- Error: duplicate header (`["Name", "Name"]`) → raises `ValueError` whose message names `'Name'`.
- Edge: non-ASCII cell text (e.g., `"Café"`) round-trips literally, not as `é`.

**Verification:**
- All seven test scenarios above pass.
- `format_json` does not touch `sys.exit`, `sys.stderr`, or `sys.stdout` directly — error reporting is the caller's responsibility.

---

- [ ] **Unit 2: Wire argparse and `--json` flag into `main()`**

**Goal:** Replace the bare `sys.stdin.read()` entry point with an argparse-backed `main()` that reads the same stdin, dispatches to `format_table` (default) or `format_json` (with `--json`), and translates `format_json`'s `ValueError` into the existing `Error: ...` / exit-1 pattern.

**Requirements:** R1, R4, R7

**Dependencies:** Unit 1 (the helper exists).

**Files:**
- Modify: `table_fmt.py`
- Test: `test_table_fmt.py`

**Approach:**
- Add `import argparse` and `import json` at the top of the module.
- In `main()`:
  - Build an `ArgumentParser` with a short `description` describing both modes; add `--json` as a `store_true` flag with a one-line `help=` per R4.
  - Parse `sys.argv[1:]` (let argparse handle `--help` and unknown flags — exit code is its concern).
  - Read stdin (unchanged).
  - Call `parse_table(text)` (unchanged).
  - If `not rows` → existing error path (unchanged).
  - If `args.json`: call `format_json(rows, alignments)`, catch `ValueError`, print `f"Error: {exc}"` to stderr and `sys.exit(1)`. On success, write returned string to `sys.stdout`.
  - Else: call `format_table(rows, alignments)` and write — identical to current behavior.
- Critical: when `--json` is absent, the code path through `main()` must produce output identical to today's. Verify with a byte-equality regression test.

**Patterns to follow:**
- Existing `main()` error reporting — `print("Error: ...", file=sys.stderr)` + `sys.exit(1)`.
- Stdlib argparse idioms (`add_argument("--json", action="store_true", help="...")`).

**Test scenarios:**
- Default mode unchanged: feed a known input through `main()` (via `subprocess`/runpy or by capturing stdout), assert the output equals what `format_table` produces — i.e., byte-for-byte identical to pre-change behavior.
- `--json` mode happy path: same input plus `--json` produces JSON matching `format_json` output.
- `--help` exits 0 and prints text containing `--json` and a description of the flag.
- Unknown flag (e.g., `--xml`) exits non-zero (argparse default).
- Malformed input (no `|`-bearing lines) with `--json` produces the existing `Error: no valid markdown table found in input` message and exit 1 (no JSON, no `[]`).
- No-header-row input (table with no separator row) with `--json` produces the new "Error: --json requires a header row…" message and exit 1.
- Duplicate-header input with `--json` produces the new "Error: --json requires unique header column names…" message and exit 1.
- No-header-row input *without* `--json` continues to work as today (existing tests still pass).

**Verification:**
- `python table_fmt.py --help` shows `--json`.
- `python table_fmt.py < fixture.md` output matches the pre-change golden output for every existing fixture.
- `python table_fmt.py --json < fixture.md` produces valid JSON parseable by `json.loads`.
- All existing tests in `test_table_fmt.py` continue to pass without modification.

---

- [ ] **Unit 3: Test coverage for JSON mode and CLI dispatch**

**Goal:** Lock in R6 coverage and protect R1 (default-mode parity) with explicit regression tests.

**Requirements:** R1, R4, R6, R7

**Dependencies:** Units 1 and 2 (functions and CLI exist).

**Files:**
- Test: `test_table_fmt.py`

**Approach:**
- Add a `FormatJsonTests(unittest.TestCase)` class for direct `format_json(rows, alignments)` tests — covers Unit 1's seven scenarios above. Use `json.loads` on the returned string in addition to checking the raw text shape, so both the contract and the actual structure are asserted.
- Add a `MainCliTests(unittest.TestCase)` class that exercises `main()` end-to-end. Prefer in-process invocation (monkey-patching `sys.stdin`/`sys.stdout`/`sys.argv` and calling `table_fmt.main()`) over `subprocess` to keep tests fast and avoid Windows path quoting issues — the codebase is small and this is a one-file CLI.
  - Use `unittest.mock.patch` and `io.StringIO` for stdin/stdout capture.
  - Use `self.assertRaises(SystemExit)` with `cm.exception.code` checks for `--help` (code 0) and error paths (code 1 or 2 per argparse semantics).
- Default-mode parity test: pick one of the existing `RoundTripTests` fixtures, run it through `main()` without `--json`, and assert the captured stdout equals what `format_table(parse_table(input))` produces. This is the byte-for-byte regression guard for R1.

**Patterns to follow:**
- Existing `unittest.TestCase` style in `test_table_fmt.py`.
- Class-per-concern grouping (e.g., `ParseAlignmentTests`, `FormatSeparatorTests`).
- Plain `assertEqual` for exact strings; use `json.loads` only when comparing structures.

**Test scenarios:**
*(Aggregated from Units 1 and 2 — do not duplicate the unit-level scenarios; this unit tracks that they actually land in `test_table_fmt.py`.)*
- Happy path JSON output for a 2-column table (R6).
- Aligned-table JSON output drops alignment metadata (R6).
- Single-column table JSON output (R6).
- Empty-cells JSON output preserves `""` values (R6).
- `--help` mentions `--json` (R4).
- Default mode produces byte-equivalent markdown to the pre-change implementation (R1).
- All three error paths print the documented message and exit 1 (R7): no-table, no-header, duplicate-header.

**Verification:**
- `python -m unittest test_table_fmt` exits 0.
- Coverage of `format_json` and the new `main()` argparse branch is exercised by at least the seven scenarios above.

## System-Wide Impact

- **Interaction graph:** No external callers. `table_fmt.py` is a leaf script invoked from the CLI / pipes; adding `--json` is purely additive. The pre-existing `parse_table` and `format_table` call sites (limited to `main()` and `test_table_fmt.py`, per the prior solutions doc) are unchanged.
- **Error propagation:** `format_json` raises `ValueError` for plan-defined error states; `main()` is the single boundary that translates these to `Error: ...` + exit 1. Keeps user-visible behavior consistent with the existing "Error: no valid markdown table found in input" path.
- **State lifecycle risks:** None. The script is stateless and process-scoped.
- **API surface parity:** `format_json` mirrors `format_table` — same `(rows, alignments)` shape, same module-level placement, same return type. Future maintainers should be able to add additional output formats by following the same pattern.
- **Integration coverage:** Default-mode byte-parity test (in Unit 3) is the cross-layer guard ensuring no `main()` refactor accidentally changes today's output.

## Risks & Dependencies

- **Risk: Default-mode regression.** Refactoring `main()` to add argparse could subtly alter stdout (e.g., trailing whitespace, exit code on edge cases). **Mitigation:** Unit 3's byte-equality regression test using an existing fixture; keep `format_table(...)` call signature and `sys.stdout.write(...)` invocation untouched for the default branch.
- **Risk: Over-validation in `format_json`.** Re-checking conditions `main()` already enforces (e.g., `not rows`) creates duplicated logic. **Mitigation:** Document the precondition contract in the helper's docstring; keep the `not rows` check in `main()` and the `--json`-specific checks (`alignments == []`, duplicate headers) in `format_json` since they are tied to the JSON shape, not the markdown shape.
- **Risk: argparse exit-code semantics.** argparse uses exit code 2 for unknown flags by default, which differs from the script's existing exit code 1 for malformed input. **Mitigation:** Accept this — exit code 2 is the standard CLI convention for argument errors, exit code 1 stays for input-content errors. Document the distinction in test assertions only if it surprises a reviewer.
- **Dependency:** None outside the Python stdlib (`argparse`, `json`, `sys`). Compatible with the script's existing `#!/usr/bin/env python3` shebang.

## Documentation / Operational Notes

- `--help` output is the user-visible documentation (R4). No README update is in scope.
- After this PR lands, consider a follow-up `docs/solutions/best-practices/` entry capturing the "add a sibling formatter rather than modifying the existing one" pattern — useful precedent if a third output mode is ever proposed. Defer to post-merge.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-26-table-fmt-json-output-requirements.md](../brainstorms/2026-04-26-table-fmt-json-output-requirements.md)
- Related code: `table_fmt.py:27` (`parse_table`), `table_fmt.py:61` (`format_table`), `table_fmt.py:123` (`main`)
- Related tests: `test_table_fmt.py`
- Related learnings: `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
- Related issues: #109 (this work), #92 (prior alignment work that established the `(rows, alignments)` contract)
