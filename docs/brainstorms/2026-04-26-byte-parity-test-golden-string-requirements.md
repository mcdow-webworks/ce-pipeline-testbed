---
date: 2026-04-26
topic: byte-parity-test-golden-string
---

# Byte-parity test for `table_fmt --json` default path needs an independent oracle

## Problem Frame

PR #110 added `--json` to `table_fmt.py` and a test asserting that the no-flag invocation is byte-for-byte identical to the pre-flag behavior. The test as written computes its expected value at runtime by calling the very function it is checking:

```python
# test_table_fmt.py (origin/dev-worker, line 313, in CLIArgparseTests):
def test_no_flag_path_byte_for_byte_parity(self):
    text = (
        "| Name | Age | City |\n"
        "| :--- | ---: | :---: |\n"
        "| Alice | 30 | NYC |\n"
    )
    rows, alignments = parse_table(text)
    expected = format_table(rows, alignments)   # ← tautology
    code, out, err = _run_main(["table_fmt.py"], text)
    self.assertEqual(out, expected)
```

`main()` calls `format_table(rows, alignments)` with the same `rows`/`alignments`. Both sides regress in lockstep, so a defect introduced into `format_table` itself would not be caught. R3 of the `--json` requirements (`docs/brainstorms/2026-04-26-table-fmt-json-output-requirements.md`) called for byte-for-byte parity *with the pre-flag implementation* — a frozen oracle, not a self-comparison.

Source: harvested finding from CE-review rollup #113 (originating PR #110), severity P2.

## Requirements

- **R1.** The no-flag CLI parity test asserts against a literal expected string captured from the pre-flag binary's behavior, not against a recomputed `format_table(...)` call.
- **R2.** The literal is `'| Name  | Age | City |\n| :---- | --: | :--: |\n| Alice |  30 | NYC  |\n'` — the exact output produced by `format_table` on the existing fixture **before** the `--json` (PR #110) and `--max-width` (PR #112) changes landed. Verified on this branch (which is still on pre-flag `master`) by running the helper directly: same bytes.
- **R3.** A one-line comment explains *why* the expected value is hardcoded — without context, a future reviewer would refactor it back to the computed form and silently re-introduce the lockstep regression.
- **R4.** The fixture (`Name | Age | City` with `left | right | center` alignments) is preserved unchanged, so the test continues to exercise all three alignment paths (`left`, `right`, `center`) and the minimum-width-3 floor for the `Age` column.
- **R5.** No production code changes. Pure test-design fix.
- **R6.** All existing tests on the fix's base branch (the branch carrying PR #110's changes) continue to pass.

## Success Criteria

- The amended test passes when run against the current `format_table`.
- The test would fail if `format_table` were mutated to emit even one differing byte (verified mentally by inspection — and worth running locally as a quick sanity mutation, e.g., flipping `min(width, 3)` to `min(width, 4)`).
- The test no longer references `format_table` or `parse_table` in its expected-value derivation.

## Scope Boundaries

- **Out of scope:** the sibling P2 finding about `format_json` silently truncating ragged rows via unchecked `zip()` — that is a separate behavioral decision (error / pad / document) tracked in PR #110's rollup and warrants its own issue.
- **Out of scope:** broadening the parity coverage to multiple fixtures, snapshot files, or a parametrized suite. One representative fixture matched the original test's intent and is enough to break a real regression.
- **Out of scope:** any changes to `table_fmt.py`, the `--json` mode, the `--max-width` mode, or other tests in the file.
- **Out of scope:** moving the fixture to a shared constant. Inlining keeps the test self-contained and the byte-comparison obvious to a reader.

## Key Decisions

- **Hardcoded golden string over recomputed expected.** Rationale: a parity test's value comes from being an *independent* oracle. Computing the expected via the same code path under test reduces it to `assertTrue(True)`.
- **Single fixture, not a parametrized table of fixtures.** Rationale: the original test used one fixture; the bug is the assertion strength, not the coverage breadth. YAGNI on multi-fixture sweeps; if breadth is wanted later, file a follow-up.
- **Comment justifying the literal.** Rationale: per `CLAUDE.md`, comments are warranted when removing them would surprise a future reader. This is exactly that case — without the comment, "DRY this up" is the obvious refactor and would silently re-introduce the regression that PR #113 caught.
- **Branch the fix lives on, not master.** Rationale: PR #110 merged into `dev-worker`, not `master` (verified via `gh pr list`). The current `claude/issue-115` branch is from `master` and does not yet contain the test being fixed. Planning/work needs to either (a) target `dev-worker` directly or (b) wait for `dev-worker` → `master` integration. Same pattern as siblings issues #109 and #111.

## Dependencies / Assumptions

- The base branch for the eventual PR carries PR #110's `test_no_flag_path_byte_for_byte_parity` test. (Confirmed present on `origin/dev-worker:test_table_fmt.py:313`.)
- The pre-flag `format_table` output for the chosen fixture is stable. Confirmed by running it on the current (pre-flag) `master` working tree — output matches R2's literal exactly.

## Outstanding Questions

### Resolve Before Planning

(none)

### Deferred to Planning

- [Affects R1, R6][Technical] Confirm the eventual PR base (`dev-worker` vs `master`) and rebase the working branch onto it before editing — the test under repair does not exist on `master`. Mechanical, but planning should pick the base explicitly rather than assume.

## Next Steps

→ `/ce:plan` for structured implementation planning
