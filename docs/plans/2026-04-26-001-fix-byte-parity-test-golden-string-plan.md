---
title: "fix: Replace byte-parity test tautology with hardcoded golden string"
type: fix
status: active
date: 2026-04-26
origin: docs/brainstorms/2026-04-26-byte-parity-test-golden-string-requirements.md
---

# fix: Replace byte-parity test tautology with hardcoded golden string

## Overview

`test_no_flag_path_byte_for_byte_parity` in `test_table_fmt.py` (added by PR #110, lives on `origin/dev-worker`) currently computes its expected value by calling the very `format_table` function it is supposed to be checking. Both sides of the assertion regress in lockstep, so a defect introduced into `format_table` would not be caught — the test reduces to `assertTrue(True)`.

Replace the recomputed expected with a literal byte string captured from the pre-flag binary's behavior, and add a one-line comment explaining *why* it is hardcoded so a future "DRY this up" refactor does not silently re-introduce the regression.

## Problem Frame

Carried forward from the origin document.

PR #110 (`--json` mode) added a parity test intended to satisfy R3 of the `--json` requirements: *"the no-flag invocation is byte-for-byte identical to the pre-flag implementation"*. The implementation diverged from intent: instead of asserting against a frozen oracle (the pre-flag output captured as a literal), it asserts against the live `format_table` output. CE-review rollup #113 flagged this as a P2 finding.

```python
# origin/dev-worker:test_table_fmt.py:313 — current state
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

(See origin: `docs/brainstorms/2026-04-26-byte-parity-test-golden-string-requirements.md`.)

## Requirements Trace

- **R1** — Expected value is a literal string, not a `format_table(...)` call. Advanced by Unit 2.
- **R2** — Literal is exactly `'| Name  | Age | City |\n| :---- | --: | :--: |\n| Alice |  30 | NYC  |\n'` (verified pre-flag output for the existing fixture). Advanced by Unit 2.
- **R3** — A one-line comment explains why the literal is hardcoded. Advanced by Unit 2.
- **R4** — Fixture (`Name | Age | City` with `left | right | center` alignments) preserved unchanged so all three alignment paths and the min-width-3 floor for `Age` continue to be exercised. Advanced by Unit 2.
- **R5** — No production code changes. Enforced by scope of Unit 2 (test file only).
- **R6** — All existing tests on the fix's base branch continue to pass. Verified at the end of Unit 2.

## Scope Boundaries

Carried forward from origin:

- **Out of scope:** the sibling P2 finding about `format_json` silently truncating ragged rows — separate issue, separate decision.
- **Out of scope:** broadening parity to multiple fixtures, snapshot files, or a parametrized suite. One representative fixture is enough to break a real regression.
- **Out of scope:** any changes to `table_fmt.py`, the `--json` mode, the `--max-width` mode, or other tests in the file.
- **Out of scope:** moving the fixture to a shared constant — inlining keeps the test self-contained and the byte-comparison obvious.

## Context & Research

### Relevant Code and Patterns

- `test_table_fmt.py` on `origin/dev-worker` — target file. The test under repair is `CLIArgparseTests.test_no_flag_path_byte_for_byte_parity` at line 313.
- `_run_main(argv, stdin_text)` helper (lines 283–308) — used as-is; no change needed. It returns `(exit_code, stdout, stderr)`.
- `RoundTripTests` elsewhere in the same file — uses the same fixture pattern and is what the comment on the failing test originally referenced. Useful as a reference for the kind of fixture that exercises the same paths.
- `table_fmt.py:format_table` on `master` (the pre-flag version) — produces the literal in R2 for the chosen fixture. This is the implicit "golden" oracle. The current branch is on pre-flag `master`, so spot-checking the literal locally is trivial.

### Institutional Learnings

- `docs/solutions/best-practices/` and adjacent — reviewed; no prior entry on parity-test-design specifically. This plan's eventual `ce:compound` follow-up may be worth one paragraph (deferred, not in scope here).
- Sibling fixes #109 and #111 followed the same pattern — branched from `master`, PR'd into `dev-worker`. This plan repeats that base-branch choice deliberately (see Key Technical Decisions).

### External References

None required. The fix is a one-method test edit using `unittest` patterns that already exist in the file and a literal verified by inspection. (See origin §Dependencies/Assumptions: literal verified on the current pre-flag working tree.)

## Key Technical Decisions

- **Hardcoded literal beats recomputed expected.** A parity test's value comes from being an *independent* oracle. Computing the expected value via the same code path under test is `assertTrue(True)` in disguise. (Origin §Key Decisions.)
- **Inline the literal in the test method, not a module-level constant.** Keeps the byte-comparison obvious to a reader and the test self-contained. (Origin §Out of scope.)
- **One-line comment justifying the literal is mandatory, not optional.** Without it, "DRY this up" is the obvious refactor and would silently re-introduce the regression that #113 caught. (Origin §Key Decisions; matches global CLAUDE.md guidance: comments are warranted when removing them would surprise a future reader.)
- **Base branch: `dev-worker`, not `master`.** The test under repair does not exist on `master` — it was added by PR #110 which merged into `dev-worker`. PR target must be `dev-worker`. The working branch (`claude/issue-115`) is currently based on `master` and must be rebased onto `origin/dev-worker` before any edit, otherwise the file the plan edits does not exist in the working tree. Resolves the origin's only deferred-to-planning question.
- **Single fixture, no parametrized expansion.** The bug is assertion strength, not coverage breadth. YAGNI on multi-fixture sweeps; file a follow-up if breadth becomes desirable.

## Open Questions

### Resolved During Planning

- **Q (carried from origin):** PR base — `dev-worker` or `master`? **Resolution:** `dev-worker`. The test under repair only exists there; PRs #110 and #112 have not been merged back to `master`. Sibling issues #109 and #111 used the same pattern.
- **Q:** Should the test be moved into a shared helper or fixture file? **Resolution:** No. Inlining keeps the byte comparison reviewer-obvious. Origin §Out of scope.
- **Q:** Should we capture multiple golden strings (different alignment combos, ragged rows, empty input)? **Resolution:** No, in this PR. The chosen fixture exercises all three alignment paths plus the min-width-3 floor. Coverage breadth is a separate follow-up if desired.

### Deferred to Implementation

- None. All planning-time questions resolved.

## Implementation Units

- [ ] **Unit 1: Rebase working branch onto `origin/dev-worker`**

**Goal:** Make the file under repair (`test_table_fmt.py` containing `test_no_flag_path_byte_for_byte_parity`) present in the working tree so Unit 2 can edit it. Choose the eventual PR base explicitly.

**Requirements:** Enabling step for R1, R6.

**Dependencies:** None.

**Files:** None edited; this is a git-state operation.

**Approach:**
- Fetch `origin/dev-worker` and rebase the current `claude/issue-115` branch onto it.
- The only commit on `claude/issue-115` not already on master is the brainstorm doc (`3e1dbd9 docs(brainstorm): requirements for byte-parity test golden string (#115)`), which touches only `docs/brainstorms/`. No conflicts expected against `dev-worker` (which has not touched that directory).
- After rebase, confirm `test_table_fmt.py` contains `test_no_flag_path_byte_for_byte_parity` at the expected location before proceeding to Unit 2.

**Patterns to follow:**
- Sibling issues #109 and #111 followed the same base-branch posture (branch off master, PR into `dev-worker`). This unit makes that posture explicit.

**Verification:**
- `git log --oneline origin/dev-worker..HEAD` shows only the brainstorm commit (and, after Unit 2, the test edit).
- `grep -n "test_no_flag_path_byte_for_byte_parity" test_table_fmt.py` returns a hit.

---

- [ ] **Unit 2: Replace tautology with hardcoded golden expected string**

**Goal:** Edit `CLIArgparseTests.test_no_flag_path_byte_for_byte_parity` so the expected value is the literal pre-flag output instead of a live `format_table(...)` call, and document why with a single comment.

**Requirements:** R1, R2, R3, R4, R5, R6.

**Dependencies:** Unit 1 complete.

**Files:**
- Modify: `test_table_fmt.py` — single test method, ~10 lines of body.
- Test: `test_table_fmt.py` — same file; the test *is* the test.

**Approach:**
- Keep the fixture `text` literal unchanged (R4).
- Remove the `parse_table(text)` and `format_table(rows, alignments)` calls (R1, R3-success-criteria).
- Replace `expected` with the R2 literal:
  - `'| Name  | Age | City |\n| :---- | --: | :--: |\n| Alice |  30 | NYC  |\n'`
- Keep the existing `_run_main(["table_fmt.py"], text)` invocation and the three assertions (`code == 0`, `out == expected`, `err == ""`).
- Add one comment line directly above `expected` explaining why the value is hardcoded — for example, that recomputing it via `format_table` would make the test a tautology that regresses in lockstep with the function under test.
- Update or remove the existing `# R3:` comment so it no longer claims the test "matches in-process format_table output" (which was the bug). Replace with a comment that reflects the new oracle stance: parity against the *pre-flag* binary's output for this fixture.

**Execution note:** Pure test edit. Run the existing test suite locally after the change to confirm R6.

**Patterns to follow:**
- Existing assertions and `_run_main` usage in `CLIArgparseTests` (e.g., `test_max_width_truncates_via_cli`) — keep the same shape.
- Comment style: one short line, focused on the *why*, matching the existing per-test comment placement in this file.

**Test scenarios:**
- **Happy path:** Test passes when run against the current `format_table` in `dev-worker`. Asserts `code == 0`, `out == <R2 literal>`, `err == ""`.
- **Mutation sanity (manual, before declaring done):** Temporarily flip a width or alignment in `format_table` (e.g., change the min-width floor from 3 to 4, or swap `ljust` and `rjust` for one alignment branch) and confirm the test fails with a clear byte-diff message. Revert.
- **Negative regression check:** No other test in the file references the now-changed line numbers in a brittle way. Quick `grep` for the test method name confirms it is not referenced elsewhere.

**Verification:**
- `python -m unittest test_table_fmt.py -v` (or the project's standard runner if one is established on `dev-worker`) passes — the target test included.
- The test method body no longer contains the names `parse_table` or `format_table`.
- A reviewer reading the test can see, without scrolling, both the input fixture and the literal expected output, with a comment explaining why the literal is not derived.

## System-Wide Impact

- **Interaction graph:** None. Test-only change confined to one method in `test_table_fmt.py`. No production code path or import surface affected.
- **Error propagation:** N/A.
- **State lifecycle risks:** None.
- **API surface parity:** None. The public `format_table` / `parse_table` API is unchanged.
- **Integration coverage:** The change strengthens, rather than weakens, integration coverage — the `--no-flag` CLI path now has a real (independent) byte-parity oracle.

## Risks & Dependencies

- **Risk: literal drifts.** If `format_table`'s formatting is intentionally changed in a future PR, this literal must be updated in lockstep — and its comment will tell that future PR's author exactly why they need to think about it. Mitigation: the explanatory comment (R3).
- **Risk: rebase conflict on the brainstorm commit.** Very low — `dev-worker` has not touched `docs/brainstorms/`. If a conflict appears, resolve in favor of the brainstorm content (it is purely additive in its own directory).
- **Dependency: PR #110 lives on `dev-worker`.** Confirmed via `gh pr` lookup and direct `git show origin/dev-worker:test_table_fmt.py`. Re-confirm at the start of Unit 1 in case of upstream merges.

## Documentation / Operational Notes

- No user-facing documentation impact (test-only change).
- Worth a small `ce:compound` follow-up entry in `docs/solutions/best-practices/` after merge: "byte-parity tests need a frozen oracle; recomputing expected via the function under test is a silent tautology." Not in scope for this PR; flag for the post-merge phase.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-26-byte-parity-test-golden-string-requirements.md](../brainstorms/2026-04-26-byte-parity-test-golden-string-requirements.md)
- **Source rollup:** #113 (CE-review autofix harvest)
- **Originating PR:** #110 (`feat(table_fmt): add --json output mode`)
- **Sibling issues for base-branch posture:** #109, #111
- **Code under repair:** `origin/dev-worker:test_table_fmt.py` — `CLIArgparseTests.test_no_flag_path_byte_for_byte_parity`
- **Pre-flag oracle:** `master:table_fmt.py:format_table` (the version that produced the R2 literal)
