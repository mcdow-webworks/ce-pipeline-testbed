---
title: "fix: format_json — raise ValueError on ragged rows"
type: fix
status: blocked
date: 2026-04-26
origin: docs/brainstorms/2026-04-26-format-json-ragged-row-policy-requirements.md
issue: 114
blocked_on: PR #110 (commit cecc635 — feat(table_fmt): add --json output mode) not yet merged to master
---

# fix: `format_json` — raise `ValueError` on ragged rows

## Overview

Add a precondition check to `format_json` in `table_fmt.py` that raises
`ValueError` when any data row's column count differs from the header row's
column count. This closes a P2 silent-data-loss bug introduced by PR #110:
`dict(zip(header, row))` truncates short or long rows without warning, and
JSON consumers cannot detect the truncation visually.

The fix is the third sibling of the existing strict guards in `format_json`
(no-header, duplicate-header) and uses the same shape:
`raise ValueError("--json requires …; …")` so `main()`'s existing
`except ValueError as exc` translation continues to be the single boundary
that emits `Error: …` + exit 1.

## Problem Frame

`format_json(rows, alignments)` builds JSON with
`payload = [dict(zip(header, row)) for row in rows[1:]]`. Python's `zip`
silently stops at the shorter iterable, so:

- A short row (fewer cells than the header) drops trailing header keys from
  the emitted object — quiet data loss.
- A long row (more cells than the header) drops the trailing extra cells —
  quiet data loss.

Either form produces structurally valid JSON that downstream consumers will
treat as authoritative, with no error and no exit code change. The markdown
path (`format_table`) hides the same input shape behind padding, so the
asymmetry stays invisible until JSON consumers act on truncated rows.

Three reviewers (correctness, testing, kieran-python) flagged this as P2 in
the ce-review of PR #110 and recommended Option A (strict `ValueError`),
which is symmetrical with the existing duplicate-header guard.

## Requirements Trace

- R1. `format_json` raises `ValueError` on row/header column-count mismatch
  before any output is produced (no partial JSON).
- R2. Error message identifies the offending row by index and reports both
  column counts. Message follows the existing `--json requires …; …`
  phrasing pattern used by the duplicate-header guard so `main()`
  translates it consistently to `Error: …` on stderr.
- R3. `main()` continues to translate the new `ValueError` into `Error:
  <msg>` + exit 1 via its existing `--json` branch handler. No new exit
  code, no new stream, no special formatting.
- R4. Rectangular input is byte-for-byte unchanged. The change is purely
  additive — a new failure path on inputs that were already silently broken.

## Scope Boundaries

- Out of scope: changing `format_table`'s ragged-row padding behavior.
  Markdown is visual; padding is the established, intentional contract.
- Out of scope: changing `parse_table` to normalize or reject ragged input.
  Other callers depend on the raw cell list.
- Out of scope: a `--json --lenient` (or similar) opt-in to the old
  truncation behavior. YAGNI — no current consumer asks for it, and
  default-strict is the whole point of the fix.
- Out of scope: deduplication or normalization beyond column count
  (Unicode NFC/NFD header collapse, empty-string headers). Recorded as
  separate residual risks in the source ce-review.
- Out of scope: replacing `zip(...)` with `zip(..., strict=True)`. The repo
  declares no minimum Python version; `strict=` is 3.10+. Use an explicit
  `len(row) != len(header)` check that works under any plausible 3.x floor.

## Context & Research

### Relevant Code and Patterns

- `table_fmt.py` — `format_json(rows, alignments)`. The current shape (per
  the merged --json feature, commit `cecc635` on `claude/issue-109`):
  - Lines ~125-156: function body, including the no-header guard, the
    duplicate-header guard, and the `payload = [dict(zip(header, row)) …]`
    line that needs the new precondition check inserted before it.
  - Docstring already has a `Preconditions:` section listing the existing
    error states. The new state goes there.
- `table_fmt.py` — `main()`'s `--json` branch. Already wraps the
  `format_json(...)` call in `try/except ValueError` and emits
  `print(f"Error: {exc}", file=sys.stderr); sys.exit(1)`. No changes
  needed; the new `ValueError` flows through the same path.
- `test_table_fmt.py` — `FormatJsonTests` class. Existing
  `test_no_header_row_raises_value_error` and
  `test_duplicate_header_raises_value_error_naming_duplicate` use
  `assertRaises(ValueError)` plus `assertIn(...)` substring matches on
  the message. The new ragged-row tests should follow the same shape.
- `test_table_fmt.py` — `MainCliTests` class. Existing
  `test_no_header_row_with_json_flag_errors` and
  `test_duplicate_header_with_json_flag_errors` use the in-process
  `_run_main` helper to assert exit code 1 + stderr substring. The new
  CLI-level test should mirror this.

### Institutional Learnings

- `docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md`
  explicitly calls out this exact bug under "Symptoms": *"Ragged-row data
  loss in JSON because `parse_table` does not normalize column counts;
  `dict(zip(header, row))` truncates silently when a row is short or long
  (`table_fmt.py:155`)…"* The same doc captures the convention this fix
  must preserve: *"pure helpers raise `ValueError`; `main()` is the only
  place that translates exceptions to stderr+exit."*

### External References

External research skipped. The codebase has a strong, recently-shipped
local pattern for this exact situation (the duplicate-header guard added
in PR #110), the institutional learning already documents the convention,
and the brainstorm's Option A is aligned with both. Adding external
best-practices here would not change the design.

## Key Technical Decisions

- **Strict `ValueError`, not normalize-or-document (Option A).** Carries
  forward from origin: symmetrical with the duplicate-header guard, keeps
  the helper's strict tone, prevents silent data loss in the structural
  output mode where consumers cannot detect truncation visually. Chosen
  over Option B (normalize-pad like `format_table`) because the JSON
  consumer's contract is "exactly the input rows, structurally", not "the
  input rectangularized for visual presentation". Chosen over Option C
  (docstring-only) because no docstring change prevents the data loss for
  callers who never read it (see origin).
- **First-mismatch reporting, not aggregated.** Match the existing
  duplicate-header guard, which raises on the first duplicate found. A CLI
  expects users to fix the input and re-run; an aggregated report adds
  machinery for negligible UX gain.
- **1-indexed row numbering in the error message.** User-facing
  convention; matches what users see when scrolling their input file
  (first data row = "row 1", not "row 0"). The header row is implicit, not
  numbered, since the error message already references it by name
  ("header"). No in-repo precedent to override this default — the existing
  duplicate-header guard names the cell value, not its index, so there is
  no row-numbering convention to mirror or contradict.
- **Insertion point: after the duplicate-header guard, before the
  `dict(zip(...))` payload comprehension.** The check is a precondition
  on the comprehension's input; it belongs immediately upstream so the
  "no partial output" guarantee is structural rather than incidental.
  Ordering after the duplicate-header guard means the user sees
  duplicate-header errors first if both apply, which is the order the
  existing function already establishes.
- **No `zip(..., strict=True)`.** Carried forward from origin: repo
  declares no Python floor; explicit `len(row) != len(header)` works
  everywhere. The check is also clearer at the call site than a
  `try/except ValueError` wrapper around `strict=True`.
- **Test-first execution posture.** This is new domain behavior, not a
  refactor. Writing the failing test first proves the bug is real on the
  current codebase, exercises the chosen error-message wording, and
  confirms the `main()` translation path before the fix is in place.

## Open Questions

### Resolved During Planning

- *Exact error-message wording* (deferred from origin): Use
  `f"--json requires every data row to have the same column count as the header; row {row_num} has {len(row)} cells but header has {len(header)}"`.
  Matches the `--json requires …; …` phrasing of the duplicate-header
  guard so `main()`'s `Error: {exc}` formatting reads consistently.
- *1-index vs 0-index row number* (deferred from origin): 1-indexed.
  See Key Technical Decisions for rationale.
- *Test-assertion style — exact-string vs substring* (deferred from
  origin): Substring match via `assertIn(...)`, following the
  duplicate-header test precedent in `FormatJsonTests`. Asserting on the
  exact string would couple the test to phrasing details and produce
  needless churn on future wording polish.

### Deferred to Implementation

- Final test method names. Cosmetic; pick names that mirror the
  existing `test_no_header_row_raises_value_error` and
  `test_duplicate_header_raises_value_error_naming_duplicate` shape.
- Exact line numbers within `format_json` after insertion. Will depend
  on the file state at implementation time and any unrelated drift.

## Implementation Units

- [ ] **Unit 1: Add ragged-row precondition check to `format_json` and cover with `FormatJsonTests`**

**Goal:** `format_json` raises `ValueError` on row/header column-count
mismatch before building the payload. Function-level test coverage proves
the new error path on short rows, long rows, and that rectangular input is
unaffected.

**Requirements:** R1, R2, R4

**Dependencies:** PR #110 (`feat(table_fmt): add --json output mode`) must
be in the base. The brainstorm records this assumption; the merged commit
is `cecc635` on `claude/issue-109`. If `format_json` is not present in
`table_fmt.py` when implementation starts, surface the discrepancy and
stop — this fix has nothing to operate on otherwise.

**Files:**
- Modify: `table_fmt.py` — add the precondition loop inside `format_json`
  and extend the docstring's `Preconditions:` section to list the new
  raise condition.
- Modify: `test_table_fmt.py` — add tests to the existing
  `FormatJsonTests` class.

**Approach:**
- Insert the new check after the existing duplicate-header `for name in
  header` loop and before the `payload = [dict(zip(header, row)) …]`
  comprehension.
- Iterate `enumerate(rows[1:], start=1)` so the row number in the error
  message is 1-indexed against the data rows (header is not counted).
- On the first row whose `len(row) != len(header)`, raise
  `ValueError(f"--json requires every data row to have the same column count as the header; row {row_num} has {len(row)} cells but header has {len(header)}")`.
- Update the docstring's `Preconditions:` paragraph to add: *"Raises
  `ValueError` when any data row's column count differs from the header
  row's column count."*

**Execution note:** Test-first. Add the failing tests in this unit before
the source change so the chosen error-message phrasing is exercised by a
real assertion before it is committed.

**Patterns to follow:**
- The existing duplicate-header guard in `format_json` for raise-shape
  and message phrasing.
- The existing `test_duplicate_header_raises_value_error_naming_duplicate`
  for `assertRaises(ValueError)` + `assertIn(...)` test shape.
- The existing `test_basic_happy_path` for the shape of the rectangular
  regression test.

**Test scenarios:**
- Short data row raises `ValueError` whose message contains
  `"every data row to have the same column count"`, `"row 1"`,
  the row's actual column count, and the header's column count. Input:
  `rows = [["A", "B", "C"], ["x", "y"]]`, `alignments = [None, None, None]`.
- Long data row raises `ValueError` with the same phrase and a row
  identifier matching whichever data row is long. Input:
  `rows = [["A", "B"], ["x", "y", "z"]]`, `alignments = [None, None]`.
- First-mismatch reporting: when multiple rows are ragged, the error
  identifies the *first* offender (row 1), not a later one. Input:
  `rows = [["A", "B"], ["x", "y", "z"], ["p", "q"]]`,
  `alignments = [None, None]` — error must reference row 1, not row 2.
- Rectangular input is unchanged: existing `test_basic_happy_path`,
  `test_alignment_metadata_dropped`, `test_single_column_table`,
  `test_empty_cells_preserved_as_empty_string`, and
  `test_pretty_printed_with_indent_2_and_trailing_newline` continue to
  pass with the same expected output (regression coverage).
- The `ValueError` raises *before* any payload is built (no partial JSON
  written): implicit in raising rather than printing, but worth a
  comment in the test docstring so future readers do not assume the
  helper does any best-effort emission.

**Verification:**
- `python -m unittest test_table_fmt` exits 0.
- The three existing duplicate-header / no-header tests still pass
  unchanged.
- Visual inspection of `format_json`'s docstring shows the new
  `Preconditions:` line.
- The rectangular happy-path tests' expected JSON strings are
  byte-for-byte identical to the pre-fix versions (R4).

- [ ] **Unit 2: Add CLI integration coverage for the ragged-row exit path**

**Goal:** Confirm end-to-end that ragged input under `--json` produces
exit 1 with `Error: …` on stderr and no stdout, exercising the
`main()` translation path that the bug-fixed helper relies on.

**Requirements:** R3

**Dependencies:** Unit 1.

**Files:**
- Modify: `test_table_fmt.py` — add tests to the existing `MainCliTests`
  class.

**Approach:**
- Use the existing in-process `_run_main(argv, stdin_text)` helper to
  drive `main(["--json"], <ragged-input-table>)`.
- Assert exit code 1, empty stdout, and an `assertIn(...)` substring
  match against the same `"every data row to have the same column count"`
  phrase and `"Error:"` prefix.
- Cover both shapes (short row and long row) since they exercise the
  same code path but are separately observable failure modes from a
  user perspective.

**Patterns to follow:**
- `test_duplicate_header_with_json_flag_errors` for the assertion
  triplet (`code == 1`, `stdout == ""`, `assertIn` on stderr).
- `test_no_header_row_with_json_flag_errors` for the markdown-table
  literal stdin shape.

**Test scenarios:**
- `--json` with a markdown table whose first data row is short: exit
  code 1, empty stdout, stderr contains `"Error:"` and
  `"every data row to have the same column count"`.
- `--json` with a markdown table whose first data row is long: exit
  code 1, empty stdout, stderr contains the same substrings.
- Default mode (no `--json`) with the same ragged inputs continues to
  succeed (regression check that the strictness is JSON-mode-only —
  R4-adjacent: `format_table` still pads, exit code 0).

**Verification:**
- `python -m unittest test_table_fmt` exits 0.
- The two new tests are visible under `MainCliTests` in the test
  output.
- The existing `test_default_mode_byte_for_byte_parity_with_format_table`
  and the rest of `MainCliTests` continue to pass unchanged.

## System-Wide Impact

- **Interaction graph:** Single call site in `main()` (the `--json`
  branch). The existing `try/except ValueError as exc` wrapper already
  catches the new exception type — no new translation glue needed. No
  other module imports `format_json`.
- **Error propagation:** New `ValueError` flows through the same path as
  the existing no-header and duplicate-header errors: helper raises,
  `main()` catches in the `--json` branch, prints `Error: <msg>` to
  stderr, calls `sys.exit(1)`. Exception class and exit code are
  unchanged from the existing pattern.
- **State lifecycle risks:** None. `format_json` is a pure function with
  no I/O. The check is pre-payload, so no partial JSON is ever emitted.
  `main()` does not write to stdout before catching the exception.
- **API surface parity:** `format_table` continues to pad ragged rows.
  This asymmetry is intentional and documented: markdown is visual
  (padding is helpful), JSON is structural (truncation is data loss).
  No other interface (no library API, no second CLI) needs the same
  change.
- **Integration coverage:** Unit 2 covers the helper-to-CLI handoff
  end-to-end, which unit-only tests on `format_json` cannot prove.

## Risks & Dependencies

- **Risk: pre-existing rectangular tests are accidentally non-rectangular.**
  Low. The shipped `FormatJsonTests` cases (`test_basic_happy_path`,
  `test_single_column_table`, etc.) all use rectangular fixtures. If any
  did not, this fix would surface it as a test failure — which is the
  correct outcome and worth fixing in the same change. The implementer
  should re-read those tests before adding new ones to confirm.
- **Risk: someone is depending on the silent-truncation behavior.**
  Negligible. The behavior is undocumented quiet data loss; there is no
  call site, no flag, and no test exercising it intentionally. The
  brainstorm's scope boundary explicitly closes the door on a `--lenient`
  opt-in.
- **Dependency: PR #110 (the `--json` feature) is present in the base.**
  Carried forward from origin. The current `claude/issue-114` branch
  does not yet contain `format_json` in its working tree (it branched
  from a pre-#110 base). If implementation starts before PR #110 is
  merged into this branch's base, the implementer should surface the
  discrepancy rather than re-implement `format_json`.

## Documentation / Operational Notes

- After the fix lands and ce-review runs clean, capture a one-page
  learning under `docs/solutions/logic-errors/` describing the
  `zip(short, long)` silent-truncation pattern and the
  raise-`ValueError`-from-pure-helper convention. The existing
  best-practices doc at
  `docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md`
  already mentions this bug under Symptoms; the new doc should
  cross-link from it and update it to reflect that the symptom is now
  fixed. (The compound-engineering refresh workflow handles this; the
  fix PR itself does not need to write the learning.)
- No CHANGELOG entry needed beyond what the merged PR's title and
  description provide — this is a bug fix to a recently-shipped flag,
  not a user-facing surface change.

## Sources & References

- **Origin document:**
  [docs/brainstorms/2026-04-26-format-json-ragged-row-policy-requirements.md](../brainstorms/2026-04-26-format-json-ragged-row-policy-requirements.md)
- Related code:
  - `table_fmt.py` — `format_json(rows, alignments)` (the function to
    modify); the existing duplicate-header guard inside it (the pattern
    to mirror); `main()`'s `--json` branch (the unchanged translation
    boundary).
  - `test_table_fmt.py` — `FormatJsonTests` class (function-level test
    pattern); `MainCliTests` class (CLI-level test pattern).
- Related PRs/issues:
  - Issue #114 — this fix.
  - Issue #113 — the rollup that harvested this finding.
  - PR #110 — the originating PR that introduced the unchecked `zip()`
    in `format_json` (issue #109's --json output mode).
- Related institutional learning:
  - `docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md`
    — already documents the bug under Symptoms and the
    pure-helper-raises-`ValueError` convention this fix preserves.
- Source artifact referenced by the issue body
  (`.context/compound-engineering/ce-review/issue-109-autofix-20260426/run.md`)
  is **not present in this branch's `.context/` tree**. The relevant
  reviewer guidance is preserved in the brainstorm's "Notes from review"
  carry-forward, so the missing artifact does not block planning.

## Work Phase Outcome (2026-04-26)

**Status: blocked — dependency PR #110 not yet on this branch's base.**

`/ce:work` ran on `claude/issue-114` and stopped before code changes per the
plan's explicit dependency clause ("If `format_json` is not present in
`table_fmt.py` when implementation starts, surface the discrepancy and stop
— this fix has nothing to operate on otherwise").

### What was checked

- `claude/issue-114` HEAD (`bccbffe`): `table_fmt.py` does **not** contain
  `format_json`. Only `parse_table`, `format_table`, and `main()` are
  present.
- `master` HEAD (`d02bb44`): same — no `format_json`.
- `origin/master` HEAD (`d02bb44`): same — no `format_json`.
- The `format_json` feature commit (`cecc635 feat(table_fmt): add --json
  output mode (#109)`) lives on `claude/issue-109` (and `origin/claude/issue-109`)
  and has not yet been merged to master.
- The merge-base of `claude/issue-114` against `master` is `d02bb44` (a
  pre-`format_json` commit), confirming this branch was cut before the
  `--json` feature landed.

### Why no code change was made

The plan's Risks & Dependencies section already anticipated this exact
state: *"If implementation starts before PR #110 is merged into this
branch's base, the implementer should surface the discrepancy rather than
re-implement `format_json`."* Implementing the ragged-row guard against a
fabricated `format_json` would re-implement PR #110 inside this PR's diff,
which would (a) duplicate the feature when both PRs eventually merge to
master and (b) couple this fix's review to the still-open `--json` feature
review.

### Recommended next step

Re-run `/ce:work` on `claude/issue-114` after the base resolves. Either:

1. PR #110 (issue #109) merges to master and `claude/issue-114` is rebased
   onto the new master tip, so `format_json` is present in the working
   tree, **or**
2. The pipeline merges `claude/issue-109` into `claude/issue-114`'s base
   explicitly before the work phase runs.

The plan, brainstorm, and pre-verified references in this branch remain
valid as-is — only the base needs to advance. The Implementation Units
checkboxes are left unchecked to reflect that no code work was performed.
