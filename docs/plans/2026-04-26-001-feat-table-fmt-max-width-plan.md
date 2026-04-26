---
title: "feat: Add --max-width flag to table_fmt"
type: feat
status: active
date: 2026-04-26
origin: docs/brainstorms/2026-04-26-table-fmt-max-width-requirements.md
---

# feat: Add --max-width flag to table_fmt

## Overview

Add a `--max-width N` CLI flag to `table_fmt.py` that caps every column's
formatted width at N characters by truncating cells whose original content is
longer than N and ending them with a literal `...`. Without the flag, output is
byte-for-byte identical to today's behavior.

The work is two cohesive changes: a CLI surface migration to `argparse` (so
`--max-width` can be parsed and validated before any input is read) and a
truncation pass inside `format_table()` (so existing column-width and alignment
logic is preserved unchanged for columns that already fit).

## Problem Frame

`format_table()` pads every column to the width of its widest cell. One
oversized cell — a URL, a stack trace, a paragraph — explodes the table
horizontally and breaks readability in narrower viewers. Users want a width
ceiling without losing the formatter's alignment guarantees. Truncation, with
an explicit `...` marker, is the chosen mechanism (no wrapping). See origin:
`docs/brainstorms/2026-04-26-table-fmt-max-width-requirements.md`.

## Requirements Trace

- **R1.** `--max-width N` truncates any column whose widest cell exceeds N;
  columns that already fit are emitted unchanged.
- **R2.** A truncated cell is exactly N characters wide: `N - 3` characters of
  the original content followed by `...`.
- **R3.** Without `--max-width`, output is byte-for-byte identical to the
  pre-flag implementation. Existing tests must pass unchanged.
- **R4.** `--max-width` accepts a positive integer `≥ 4`. Non-integer, zero,
  negative, or `1–3` values are rejected with a clear stderr message and
  non-zero exit. Validation happens before stdin is read.
- **R5.** `--help` documents `--max-width N`, including the minimum value of
  4 and the meaning of N (total cell width including the `...` marker).
- **R6.** Truncation applies uniformly to every row, including the header.
  The separator row is regenerated against the (possibly narrower) widths and
  continues to honor existing alignment hints.
- **R7.** Tests cover: basic truncation, mixed (some columns truncated, some
  not), already-short input (no-op), and rejection of `--max-width` values
  `0`, `3`, and `foo`.

## Scope Boundaries

- No multi-line wrapping. Truncation is the only width-reduction behavior.
- No Unicode-aware width handling. Each character counts as width 1.
- No per-column override syntax (e.g., `--max-width col1=10,col2=20`).
- No changes to `parse_table()`. Truncation lives in `format_table()` only.
- No changes to `countdown.sh`, `dashboard.html`, or any file other than
  `table_fmt.py` and `test_table_fmt.py`.
- No `--json` interaction logic — `--json` mode does not exist on this branch
  (see origin §D3). Test for that combination is omitted with a brief
  comment until/unless `--json` lands.

## Context & Research

### Relevant Code and Patterns

- `table_fmt.py` — `format_table(rows, alignments=None)` is the only function
  affected. Existing logic computes `col_widths` with a `max(width, 3)`
  minimum, then formats each row via `pad_cell` and emits a separator via
  `separator_cell`. Truncation must hook in before width computation so the
  rest of the function sees already-narrowed cells.
- `table_fmt.py:127` — `main()` currently reads stdin directly with no flags.
  This is where `argparse` is introduced.
- `test_table_fmt.py` — existing tests import `format_table` and `parse_table`
  in-process and group cases by behavior into `unittest.TestCase` classes
  (`ParseAlignmentTests`, `FormatSeparatorTests`, `FormatRowPaddingTests`,
  `RoundTripTests`). New tests follow the same shape.

### Institutional Learnings

- `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
  — the most recent change to this module. Two patterns to mirror:
  1. **Round-trip / idempotency tests for any formatter change.** Format →
     parse → format must be a fixed point. Apply this to truncation: feeding
     truncated output back through the formatter with the same `--max-width`
     should yield identical output.
  2. **Optional metadata threaded through the function signature with a
     conservative default.** Mirror the `alignments=None` precedent: add
     `max_width=None`, default behaves exactly as today. A shorter list of
     "things callers may pass" stays tolerated.

### Repo Conventions Confirmed

- Python 3 stdlib only — no `pyproject.toml`, no CI workflow, no pytest, no
  type checker config. `argparse` is fresh to the repo (no other CLIs).
- Test runner: `unittest` (`python -m unittest test_table_fmt.py`).
- Existing stderr style on error: `print("Error: ...", file=sys.stderr)`
  followed by `sys.exit(1)` (`table_fmt.py:128`). Match this tone for the
  argparse validator's error message wording so the surface stays consistent.
- `docs/plans/` does not exist on this branch; this plan creates it.

### External References

None required. `argparse` is well-established stdlib; the truncation logic is
a few lines of slicing. External research adds no value here.

## Key Technical Decisions

- **Truncation runs as a pre-pass on rows, before column-width computation.**
  Each column is examined: if its widest cell exceeds N, every cell longer
  than N in that column is rewritten as `cell[:N-3] + "..."`. Cells in that
  column already ≤ N are left alone. Columns whose widest cell already fits
  are not touched. After the pre-pass, the existing width and padding logic
  works unchanged. Rationale: keeps `format_table` readable, avoids a
  second code path, and the `max(width, 3)` clamp at `table_fmt.py:89`
  remains correct since N ≥ 4.
- **`max_width=None` is the new default parameter on `format_table()`.**
  Keeps every existing call site (tests + `main()`) working. Mirrors the
  earlier `alignments=None` precedent.
- **`argparse` validator is a small function, not a `lambda`.** Validates
  "positive integer ≥ 4" and raises `argparse.ArgumentTypeError` with a
  message that stays close to the existing `Error: ...` stderr style. Tests
  can patch `sys.argv` and assert `SystemExit` with the validator's
  message on stderr. Validation runs before stdin is read because argparse
  parses arguments first.
- **Header row is truncated like data rows.** Carried forward from origin §D1.
  Skipping the header would break the column-width contract — `--max-width N`
  must mean "no cell exceeds N," and an exempt header row produces a
  misaligned table. The `...` marker keeps the truncation honest.
- **Separator row is regenerated, not truncated.** The existing
  `separator_cell` logic emits `---`, `:--`, `--:`, or `:-:` to the column's
  current width. After truncation that width is N, so the separator stays
  honest with no special-case code.
- **Idempotency under repeated `--max-width N`.** Once a cell is truncated to
  exactly N chars (with trailing `...`), feeding the output back through the
  same flag must yield identical bytes. The pre-pass naturally satisfies
  this: the column's widest cell is now exactly N, so no further truncation
  fires.

## Open Questions

### Resolved During Planning

- **Where does truncation hook in?** As a pre-pass on `rows` before column
  widths are computed. (Origin's "Deferred to Planning" question.) Rationale
  in the Key Technical Decisions section.
- **Empty-cell columns?** If a column has no rows (only the header) the
  natural max is the header length; same logic applies. No special case.
- **Unicode width?** Out of scope per origin. Each char counts as 1 via
  `len()`, matching the rest of `format_table`.

### Deferred to Implementation

- Final wording of the argparse error message for `--max-width 3` /
  `--max-width foo`. Keep it close to the existing `Error: ...` style; exact
  text is fine to settle in code.
- Whether to add a docstring example to `format_table` showing the new
  `max_width=` argument. Probably yes; finalize when the function is edited.
- Whether to add a CLI-level integration test (subprocess-based) in addition
  to in-process `main()` tests. The repo's existing tests are all in-process,
  so the default is to stay in-process unless a behavior is unreachable that
  way.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for
> review, not implementation specification. The implementing agent should
> treat it as context, not code to reproduce.*

**CLI surface (in `main()`):**

```text
parser = argparse.ArgumentParser(description=...)
parser.add_argument("--max-width", type=<positive_int_ge_4>, default=None,
                    help="Cap each column's width at N characters; ...")
args = parser.parse_args()

text = sys.stdin.read()
rows, alignments = parse_table(text)
if not rows: error + exit 1
sys.stdout.write(format_table(rows, alignments, max_width=args.max_width))
```

**Truncation pre-pass (inside `format_table`, only when `max_width` is set):**

```text
For each column index c in 0 .. num_cols - 1:
    natural_max = max(len(row[c]) for row in normalised)
    if natural_max <= max_width:
        continue  # column already fits; leave it alone
    for r in 0 .. len(normalised) - 1:
        cell = normalised[r][c]
        if len(cell) > max_width:
            normalised[r][c] = cell[: max_width - 3] + "..."
# fall through to existing col_widths / pad_cell / separator_cell logic
```

The pre-pass mutates the local `normalised` list (already a copy made by the
existing function); the rest of `format_table` is unchanged.

## Implementation Units

- [ ] **Unit 1: Migrate `main()` to argparse and add validated `--max-width`**

**Goal:** Introduce `argparse` in `main()` and declare `--max-width N` with a
validator that rejects non-integer / `< 4` values before stdin is read. No
truncation behavior yet — the value is parsed and ignored. Existing
no-flag invocations remain byte-for-byte identical.

**Requirements:** R3, R4, R5

**Dependencies:** None.

**Files:**
- Modify: `table_fmt.py`
- Test: `test_table_fmt.py`

**Approach:**
- Add `import argparse` at the top of `table_fmt.py`.
- Define a small module-level validator (e.g., `_positive_int_at_least_4`)
  that takes a string and returns an int, raising
  `argparse.ArgumentTypeError` with a clear message for non-int / `< 4`
  values. Keep the message style close to the existing `Error: ...` stderr
  surface so the tool feels consistent.
- In `main()`, build an `ArgumentParser`, add `--max-width` with
  `type=<validator>`, `default=None`, and a `help=` string that names the
  minimum value of 4 and explains that N includes the `...` marker (R5).
- Replace the bare stdin read with `args = parser.parse_args()` followed by
  the existing stdin read and `parse_table` / `format_table` flow. Pass
  `max_width=args.max_width` through to `format_table` *now* (preserving the
  parameter for Unit 2) — `format_table` will accept and ignore it in this
  unit.
- Confirm that running `python table_fmt.py` with no flags produces identical
  bytes to before. The existing `unittest` suite must pass without
  modification.

**Patterns to follow:**
- Existing stderr style: `print("Error: ...", file=sys.stderr); sys.exit(1)`
  at `table_fmt.py:128`. Argparse handles its own exit-code-2 path on
  validation errors; do not double-handle.
- The `alignments=None` precedent: optional parameter, conservative default.

**Test scenarios:**
- `--max-width foo` → `SystemExit` with non-zero code; stderr mentions the
  flag and the integer requirement.
- `--max-width 0`, `--max-width -1`, `--max-width 3` → all rejected before
  stdin is read; non-zero exit; stderr names the minimum value of 4.
- `--max-width 4` → accepts and proceeds (no truncation visible yet because
  Unit 1 doesn't implement it; smoke test only).
- Default invocation (no `--max-width`) → byte-for-byte equal to a fixed
  pre-flag fixture string. Use the existing `RoundTripTests` fixtures as
  the comparison input.
- `--help` output contains the string `--max-width` and mentions the
  minimum value of 4.

**Verification:**
- Existing `unittest` suite passes unchanged.
- New CLI validation tests pass.
- Manually confirmed (or asserted): byte-for-byte parity for the no-flag
  path on at least one representative table.

---

- [ ] **Unit 2: Truncate columns inside `format_table()` and wire the flag through**

**Goal:** Add `max_width=None` to `format_table()`. When set, run the
column-by-column truncation pre-pass described in High-Level Technical
Design. Wire `args.max_width` from `main()` into the call (already done in
Unit 1; here it becomes load-bearing). Cover R1, R2, R6, R7.

**Requirements:** R1, R2, R6, R7

**Dependencies:** Unit 1 (argparse plumbing must accept the value).

**Files:**
- Modify: `table_fmt.py` (`format_table` only)
- Test: `test_table_fmt.py`

**Approach:**
- Extend `format_table(rows, alignments=None)` →
  `format_table(rows, alignments=None, max_width=None)`.
- After the existing `normalised` rebuild but before the `col_widths`
  computation, run the per-column truncation pass when `max_width is not
  None`. Mutate `normalised` in place (it is already a freshly built list).
- Leave the rest of `format_table` (col_widths, pad_cell, separator_cell)
  unchanged. The `max(width, 3)` clamp stays valid because N ≥ 4 by
  validation.
- Update the `format_table` docstring with one short sentence describing
  `max_width` and noting that columns already within N are unaffected.

**Technical design:** *(directional only)*

```text
if max_width is not None:
    for col in range(num_cols):
        widest = max(len(normalised[r][col]) for r in range(len(normalised)))
        if widest <= max_width:
            continue
        for r in range(len(normalised)):
            cell = normalised[r][col]
            if len(cell) > max_width:
                normalised[r][col] = cell[: max_width - 3] + "..."
```

**Patterns to follow:**
- Optional metadata threaded through with a default that preserves prior
  behavior — the same shape as `alignments=None`.
- Round-trip / idempotency tests, mirroring
  `test_mixed_alignments_round_trip` in `test_table_fmt.py:94`.

**Test scenarios** *(in `test_table_fmt.py`, new `MaxWidthTests` class)*:
- **Basic truncation:** A two-column table where the second column has a
  20-char cell, `format_table(rows, max_width=10)` → that cell becomes
  exactly 10 chars ending in `...`; column width is exactly 10. The first
  column (cells already ≤ 10) is untouched.
- **Mixed truncation:** Three columns, only the middle one exceeds N. The
  outer two are byte-for-byte identical to the no-flag output for those
  columns; only the middle column is narrowed.
- **Already-short input:** All cells ≤ N. Output is byte-for-byte identical
  to `format_table(rows)` (the no-`max_width` path) — proves R1's
  "columns that already fit are emitted unchanged" guarantee at the
  function level.
- **Header is truncated:** A long header value gets truncated to N (with
  `...`) just like a data cell. The separator row regenerates against the
  narrowed width and stays valid.
- **Alignment honored after truncation:** A right-aligned column whose
  widest cell triggers truncation produces cells of width N, right-padded
  via `rjust` (i.e., no extra padding because every cell is already exactly
  N or shorter than N and right-justified to N).
- **Idempotency:** `format_table(rows, alignments, max_width=10)` →
  `parse_table(...)` → `format_table(rows2, alignments2, max_width=10)`
  produces identical bytes.
- **CLI end-to-end:** `main()` invocation with patched `sys.argv =
  ["table_fmt.py", "--max-width", "10"]` and a stdin that contains a
  too-wide table → captured stdout matches the expected truncated table.
- **Skipped:** `--max-width` × `--json` interaction. `--json` does not
  exist on this branch (see origin §D3); add a one-line comment in the
  test file pointing at the brainstorm doc and skip the test until/unless
  `--json` lands.

**Verification:**
- All new `MaxWidthTests` pass.
- Existing test suite continues to pass (R3 byte-for-byte parity).
- A manual spot-check: feed a known wide table through
  `python table_fmt.py --max-width 20 < fixture` and confirm every column
  is ≤ 20 chars and truncated cells end with `...`.

## System-Wide Impact

- **Interaction graph:** `main()` is the only caller of `format_table` in
  production code. Tests call `format_table` directly. No other modules
  depend on this surface. Adding `max_width=None` as a trailing keyword
  argument is non-breaking for both call sites.
- **Error propagation:** Validation errors flow through argparse's standard
  exit-code-2 path with a stderr message, before stdin is read. The
  existing "no valid markdown table found" stderr + exit-1 path is
  preserved unchanged.
- **State lifecycle risks:** None. The function is pure; the CLI is one-shot.
- **API surface parity:** `parse_table` is intentionally untouched (per
  scope). The new `max_width=` parameter on `format_table` is additive
  and optional; downstream callers (none today) are unaffected.
- **Integration coverage:** The CLI end-to-end test in Unit 2 (with patched
  `sys.argv`) plus the function-level tests together cover the user-facing
  behavior. No subprocess test is required given the repo's in-process
  conventions.

## Risks & Dependencies

- **Argparse-induced behavior drift on the default path.** Risk: argparse
  could change exit codes or stderr formatting in surprising ways. Mitigated
  by a no-flag byte-for-byte parity test against a known fixture (Unit 1's
  test list).
- **Off-by-one in truncation length.** R2 requires cells of length *exactly*
  N: `N - 3` content chars + 3 ellipsis chars. Mitigated by an explicit
  length assertion in the basic-truncation test (`assertEqual(len(cell), N)`)
  alongside the value assertion.
- **Idempotency regression.** Mitigated by the round-trip test that mirrors
  the existing `test_mixed_alignments_round_trip` shape.
- **Header-truncation surprise.** Some users may expect headers to stay
  intact. Mitigated by the explicit decision in origin §D1 (uniform
  truncation produces an honest, aligned table) and by `--help` text that
  names the behavior of N as "every cell, including headers."

## Documentation / Operational Notes

- `--help` output gains the `--max-width N` line (covered by R5 / Unit 1's
  test).
- No changes to `README.md`, `CHANGELOG.md`, or any external docs are
  required by the requirements doc; the work-phase or follow-up may add a
  one-line `CHANGELOG.md` entry (out of scope here).
- No rollout, monitoring, or migration concerns — local CLI tool only.

## Sources & References

- **Origin document:** `docs/brainstorms/2026-04-26-table-fmt-max-width-requirements.md`
- Related code: `table_fmt.py`, `test_table_fmt.py`
- Related learnings: `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
- Related issues / commits: GitHub issue #111; brainstorm commit `d8c9e43`.
