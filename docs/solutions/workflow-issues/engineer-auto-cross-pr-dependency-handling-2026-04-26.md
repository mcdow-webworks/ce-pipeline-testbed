---
title: Engineer-auto pipeline correctly defers a fix whose target function lives only on an unmerged sibling PR
date: 2026-04-26
category: workflow-issues
module: development_workflow
problem_type: workflow_issue
component: development_workflow
symptoms:
  - Work phase committed plan-status update with no source-code edits when target function was absent from working tree
  - Brainstorm asserted "PR #110 is already merged on GitHub" but the merge commit was not reachable from `origin/master`'s history
  - Plan quoted verbatim from a learnings doc at a path that does not exist anywhere in the worktree
  - Review phase flagged the brainstorm/git-state contradiction as P1 on a docs-only diff
  - Plan's Implementation Units checkboxes left unchecked, accurately reflecting that no code work was performed
root_cause: missing_workflow_step
resolution_type: workflow_improvement
severity: medium
related_components:
  - tooling
  - documentation
tags:
  - engineer-auto
  - cross-pr-dependency
  - plan-blocked
  - working-tree-verification
  - brainstorm-fact-check
  - dependency-stop-clause
---

# Engineer-auto pipeline correctly defers a fix whose target function lives only on an unmerged sibling PR

## Problem

A P2 fix queued against `claude/issue-114` could not be implemented because its
target function (`format_json` in `table_fmt.py`) was absent from the branch's
base — the function lives in PR #110 (`claude/issue-109`), which is recorded
as MERGED on GitHub but whose merge commit is not reachable from local
`origin/master`. Compounding the gap, the brainstorm asserted "PR #110 is
already merged on GitHub" without verifying reachability against the working
tree, and the plan quoted verbatim from a learnings doc at a path that does
not exist on disk.

## Symptoms

- `/ce:work` produced commit `7ef954b docs(plan): mark format_json ragged-row plan blocked on PR #110` containing only frontmatter + appended-section edits to the plan; zero changes to `table_fmt.py` or `test_table_fmt.py`.
- Working-tree inspection: `table_fmt.py` at HEAD (`bccbffe`), at `master`, and at `origin/master` (both `d02bb44`) contains only `parse_table`, `format_table`, and `main()` — no `format_json` symbol.
- `gh pr view 110 --json state,mergeCommit` returns `MERGED` with merge commit `d4e064cb31cbd80ed7b2c44a81132490687737e3`. `git cat-file -t d4e064c` resolves locally, but `git log origin/master --oneline | grep d4e064c` returns nothing — the merge commit exists in local objects but is not in `master`'s reachable history.
- Plan cites `docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md` and quotes a verbatim "Symptoms" passage from it; the file does not exist anywhere in `docs/solutions/`.
- Review phase flagged the brainstorm/git-state contradiction as P1 with confidence 0.97 / 0.85 on a docs-only diff.

## What Didn't Work

- **Trusting the brainstorm's "merged on GitHub" claim and proceeding to write code.** Rejected at the moment the implementer ran `grep -c format_json table_fmt.py` and got `0`. The PR-object's merge state on GitHub does not guarantee the merge commit is reachable from the working tree's base ref; in this case it isn't.
- **Merging `claude/issue-109` into `claude/issue-114`'s base before running the work phase.** Would produce a duplicated `format_json` introduction in this PR's diff once the upstream merge later flows into `master`, or a silent textual conflict that hides the bug-fix's actual contribution to history.
- **Re-implementing `format_json` inside this PR's diff alongside the new ragged-row guard.** Would couple the fix's review to the still-open `--json` feature review on PR #110: two reviewers debating the same function across two PRs, and the bug-fix PR no longer reviewable on its own merits.

## Solution

The work phase honored the plan's explicit dependency-stop clause and produced
documentation-only output:

1. **Plan frontmatter flipped from `active` to `blocked` with a `blocked_on:` field naming the dependency commit:**

   ```yaml
   # Before
   ---
   status: active
   ---
   ```

   ```yaml
   # After
   ---
   status: blocked
   blocked_on: PR #110 (commit cecc635 — feat(table_fmt): add --json output mode) not yet merged to master
   ---
   ```

2. **A `## Work Phase Outcome (2026-04-26)` section was appended to the plan** documenting the four trees that were checked (`claude/issue-114` HEAD, local `master`, `origin/master`, the merge-base), where the actual feature commit lives (`cecc635` on `claude/issue-109`), the rationale for not writing code, and the two acceptable next-step paths (rebase after #110 merges into `master`, or pre-merge `claude/issue-109` into the base).

3. **Implementation-unit checkboxes were left unchecked,** preserving the plan as a reusable artifact for the eventual rerun once the base advances.

4. **The dependency-stop clause that made the correct decision possible was already in the plan's Risks & Dependencies section,** carried forward from the brainstorm:

   > **Dependency: PR #110 (the `--json` feature) is present in the base.** The current `claude/issue-114` branch does not yet contain `format_json` in its working tree (it branched from a pre-#110 base). If implementation starts before PR #110 is merged into this branch's base, the implementer should surface the discrepancy rather than re-implement `format_json`.

   This clause names the specific symbol to look for, names the dependency PR, and prescribes the exact behavior on encountering the gap (surface, do not re-implement). Without it, the work phase would have had no documented authority to stop.

## Why This Works

The dependency-stop clause + plan-status flip keeps each open PR's diff scoped
to exactly its own change. If the work phase had re-implemented `format_json`,
both `claude/issue-114` and `claude/issue-109` would carry the function, and
whichever merged second would either produce a no-op merge commit (hiding the
bug-fix's actual contribution) or a textual conflict that the diff history no
longer explains. Flipping the plan to `status: blocked` with a machine-readable
`blocked_on:` field gives the engineer-auto pipeline a hard stop signal that
downstream phases (review, ce-compound, merge automation) can recognize, and
preserves the plan and brainstorm as valid artifacts to reuse on rerun.

The brainstorm's merge-status assertion failed in a more subtle way than a
typical "made-up SHA": PR #110 *is* in fact merged on GitHub at SHA `d4e064c`
(verifiable via `gh pr view 110 --json mergeCommit`), and the SHA exists in
local objects. But the merge commit is not reachable from `origin/master`'s
history — `master` is still at `d02bb44`. So the brainstorm's claim was true
about the PR object and false about what an implementer can actually use. The
load-bearing failure is asserting *reachability* without verifying against the
working tree's base ref. The plan compounded this with a fabricated verbatim
quote from a learnings doc at a path that does not exist on disk. The work
phase nevertheless landed correctly because it grounded its decision in the
working tree itself (`grep -c format_json table_fmt.py`) rather than in the
brainstorm's or plan's claims about the working tree.

## Prevention

- **Verify dependency reachability against the working tree's base ref, not against GitHub PR state.** When a brainstorm or plan asserts that a feature PR is "merged" or "available", the work phase must confirm the dependency symbol exists in the working tree before writing code. A one-liner like `grep -c '<symbol>' <file>` or `git log <base-ref> --oneline | grep '<feature-commit>'` is sufficient. PR-object merge state on GitHub does not imply reachability from the local base ref.

- **Brainstorm "Dependencies / Assumptions" sections must include the verification command + output, not a bare SHA citation.** A claim of the form "PR #N is merged at SHA X" must be accompanied by `git log <base-ref> --oneline | grep <feature-symbol>` output (or equivalent) showing the dependency is reachable from the branch's base. Bare SHA citations are insufficient even when the SHA is technically valid on GitHub.

- **Plans for fixes layered on a still-open or recently-merged feature PR must include an explicit Risks & Dependencies clause that (a) names the dependency commit by SHA, (b) names the specific symbol the implementer should grep for, and (c) instructs the implementer to surface the discrepancy and stop rather than re-implement.** This is the clause that made issue #114's correct decision structurally inevitable rather than dependent on implementer judgment.

- **Plans must not invent verbatim quotes from learnings docs at paths that have not been verified to exist.** The plan for issue #114 quoted from `docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md` — a path that does not exist on this branch. Before quoting, run a `Glob`/`ls` check on the asserted path. If the path is missing, either remove the citation or note it as "anticipated learning, not yet written".

- **Plan frontmatter should formally support a `blocked_on:` field, and the engineer-auto pipeline should treat `status: blocked` as a hard stop signal for downstream automation** (no auto-merge attempts, no PR auto-creation, no further work-phase invocations until status flips back). Without pipeline-level recognition, `status: blocked` is just documentation that a human or LLM might or might not honor.

- **The review phase should always cross-check brainstorm Dependencies claims against plan Risks & Dependencies claims and flag contradictions as P1 regardless of diff surface size.** Issue #114's review caught this with high confidence on a docs-only diff — exactly the kind of finding a less-careful review pass on a large code diff might let slip past.

## Related Issues

- Issue #114 — the deferred ragged-row fix that triggered this learning.
- Issue #113 — the rollup that harvested the finding into #114.
- Issue #109 / PR #110 — the originating `--json` feature whose unmerged-locally state caused the block.
- Plan: `docs/plans/2026-04-26-001-fix-format-json-ragged-row-enforcement-plan.md` — the centerpiece example of the dependency-stop clause + status-flip pattern.
- Brainstorm: `docs/brainstorms/2026-04-26-format-json-ragged-row-policy-requirements.md` — the artifact whose unverified merge-status claim is the cautionary example.
- Sibling engineer-auto workflow learning: `docs/solutions/workflow-issues/concurrent-pipeline-mention-handling-verification-2026-04-15.md` — captures a different failure mode (Phase 3 under-action on a directive); the present doc captures correct restraint when a dependency is absent.
- Same-module bug-fix prior art: `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`.
- ce-review autofix run that surfaced both prongs: `.context/compound-engineering/ce-review/issue-114-autofix-20260426/run.md`.
