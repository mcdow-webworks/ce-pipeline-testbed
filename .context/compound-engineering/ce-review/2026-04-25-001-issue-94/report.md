# ce-review autofix run — claude/issue-94

- **Run ID:** 2026-04-25-001-issue-94
- **Mode:** autofix
- **Branch:** claude/issue-94
- **Base SHA:** d02bb44 (origin/master)
- **HEAD SHA:** 8527cac (pre-fix)
- **Date:** 2026-04-25

## Scope

Issue #94: handle escaped pipes (`\|`) in markdown table cells. Diff covers
`table_fmt.py` (parse + format) and `test_table_fmt.py` (added 11 tests).

## Intent

Replace `parse_table`'s `stripped.split("|")` with a char-by-char `_split_cells`
helper that treats each `\X` as a 2-char unit (only `\|` unescapes). Update
`format_table` to encode `|` → `\|` once into a parallel `encoded` view and
drive both column widths and emitted rows from it. `\` is intentionally NOT
re-escaped, by design (preserves cells whose content really is a single `\`,
e.g. paths/regex/code). Public signatures unchanged. Existing 12 tests pass
byte-identically.

## Reviewer Team (6)

- correctness (always-on)
- testing (always-on)
- maintainability (always-on)
- agent-native-reviewer (always-on)
- learnings-researcher (always-on)
- kieran-python (Python parser/formatter changes warrant the lens)

Skipped: security, performance, api-contract, data-migrations, reliability,
all rails/ts/frontend-races personas — none applicable to a small CLI text
transform with no auth, I/O, or framework surface.

## Findings (synthesized, post-dedup, post-confidence-gate ≥ 0.60)

### P2 — `safe_auto`: 0 / `gated_auto`: 0 / `manual`: 1 / `advisory`: 0

**F-1 — Cells whose logical content contains literal `\|` do not round-trip
through `format_table` → `parse_table`** (correctness, conf 0.92)

- **File / Line:** `table_fmt.py:130` (the `cell.replace("|", "\\|")` step)
- **Owner:** human · **requires_verification:** true
- **Description:** `format_table` only encodes `|` → `\|`, but `_split_cells`
  consumes any `\X` as a 2-char unit. So a cell whose logical content is
  `a \| b` (6 chars) format-encodes to `a \\| b` (7 chars: backslash backslash
  pipe), and `_split_cells` reads the leading `\\` as a pass-through unit and
  the bare `|` as a real cell separator — splitting the cell in two on the
  round trip.
- **Synthesis decision:** This is a *documented* design tradeoff, not a hidden
  bug. The plan and brainstorm explicitly chose not to re-escape `\` to keep
  cells like `C:\path` and regex literals readable. The inline comment at
  `table_fmt.py:127-129` calls this out. The issue #94 acceptance criteria
  ("a cell containing `a \| b` round-trips as a single cell with contents
  `a | b`") is met as written. The `a \| b` ↔ `a | b` symmetry holds; the
  edge case the reviewer found is `a \\| b` (literal backslash-pipe), which
  is outside the issue's scope.
- **Action:** No autofix. Owner `human`. Per autofix policy
  ("Do not create todos for `owner: human`"), no downstream todo created.
  Surfaced here for human review on the PR.

### P3 — `safe_auto`: 3 / `advisory`: 3 (incl. pre-existing)

**F-2 — No fixed-point test for cells containing literal `\|` content**
(correctness + testing, conf 0.85, advisory, owner: human)

- Pairs with F-1. Adding this test today would fail because of F-1.
- No autofix. Will be valuable to add once F-1 is decided.

**F-3 — No test for cell content equal to exactly `'|'`** (testing, conf 0.85,
safe_auto → review-fixer)

- Most-reduced form of the regression. Will pin existing correct behavior.

**F-4 — No test for multiple `\|` sequences in a single cell** (testing,
conf 0.80, safe_auto → review-fixer)

- Verifies the inductive case for the char-by-char splitter.

**F-5 — No test combining alignment hints with escaped-pipe body cells**
(testing + learnings-researcher, conf 0.65, safe_auto → review-fixer)

- The learnings-researcher specifically called this out, citing the round-trip
  pattern from the issue #92 fix in the same module.

**F-6 — `default=3` on `max()` in `format_table` is unreachable** (maintainability,
conf 0.78, **pre-existing**)

- Dead code predates this PR (was on `normalised` before, now on `encoded`).
  Excluded from autofix scope.

**F-7 — `encoded` parallel structure in `format_table` could fold padding into
the encoding comprehension** (maintainability, conf 0.62, advisory)

- Borderline confidence. Stylistic. No action.

## Applied Fixes (round 1)

Three new passing tests added to `test_table_fmt.py`:

1. `SplitCellsTests::test_multiple_escaped_pipes_in_one_cell` (resolves F-4).
2. `EscapedPipeTests::test_pipe_only_cell_round_trips` (resolves F-3).
3. `EscapedPipeTests::test_format_with_right_alignment_and_escaped_pipe`
   (resolves F-5).

All three pin existing correct behavior; none expose new bugs. Suite went
from 23 → 26 passing, no regressions.

## Residual Actionable Work

None routed to downstream-resolver. F-1 and F-2 are owner: `human` and tied
to the design decision documented in the plan; no todos created per autofix
policy.

## Advisory Outputs

- F-1 / F-2: documented design tradeoff. PR reviewer should decide whether
  the existing limitation (no round-trip safety for cells containing literal
  `\|`) is acceptable or warrants a follow-up issue.
- F-7: stylistic, no action.

## Past Solutions / Known Patterns

- `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
  — direct predecessor (issue #92) on the same module. Reusable lessons:
  round-trip / fixed-point tests are the canonical safety net for this
  formatter, alignment + escape interaction is a known interaction surface.
  PR is consistent with that pattern.

## Agent-Native

CLI is stdin/stdout — no UI gate, automatically agent-accessible. Empty
findings.

## Coverage

- Suppressed (< 0.60 confidence): 0
- Reviewers run: 6 / 6 (all returned valid output)
- Pre-existing findings separated: 1 (F-6)
- Intent uncertainty: none

## Verdict

**Ready with optional follow-up.** Issue #94 acceptance criteria are met.
Three additional pinning tests added by autofix. F-1 (round-trip asymmetry
for cells with literal `\|` content) is a known, documented design tradeoff
and is out of scope for the issue; flagged here for the PR reviewer's
awareness, not as a blocker.
