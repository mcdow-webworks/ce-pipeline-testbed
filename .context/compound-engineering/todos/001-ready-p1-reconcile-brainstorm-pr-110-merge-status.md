---
status: ready
priority: p1
issue_id: "001"
tags: [docs, ce-review-residual, issue-114, brainstorm-correctness]
dependencies: []
---

# Reconcile brainstorm's PR #110 merge claim with plan and git state

## Problem Statement

The brainstorm at `docs/brainstorms/2026-04-26-format-json-ragged-row-policy-requirements.md`
asserts PR #110 has merged. The plan at
`docs/plans/2026-04-26-001-fix-format-json-ragged-row-enforcement-plan.md`
declares `status: blocked` because PR #110 has *not* merged. Direct
inspection of git state confirms the plan is right and the brainstorm is
wrong.

This makes the two pipeline artifacts internally inconsistent on day
zero. A reader who consults the brainstorm first forms a false picture
of the dependency state; a reader who consults the plan first sees the
correct state. The plan's `status: blocked` flag and Work Phase Outcome
section already correctly halt forward progress, so the workflow is not
at risk — but the brainstorm needs to be brought into agreement.

## Findings

Sourced from ce-review autofix run `issue-114-autofix-20260426`,
findings F1 (correctness, P1, conf 0.97) and F2 (correctness, P2, conf
0.95).

- **Brainstorm line 11:** `format_json(rows, alignments)` in
  `table_fmt.py` (added by PR #110, **merged 2026-04-26**)
- **Brainstorm lines 104-106:** "Assumes PR #110 ... is in the base when
  this work lands. **PR #110 is already merged on GitHub (`d4e064cb`).**"
- **Plan frontmatter line 8:**
  `blocked_on: PR #110 (commit cecc635 — feat(table_fmt): add --json output mode) not yet merged to master`
- **Plan Work Phase Outcome lines 408-414:** master HEAD (`d02bb44`):
  no `format_json`. `origin/master` HEAD (`d02bb44`): no `format_json`.
  The feature commit `cecc635` lives on `claude/issue-109` and has not
  been merged to master.
- **Git verification:** `git rev-parse d4e064cb` resolves to a merge
  commit ("Merge pull request #110 from mcdow-webworks/claude/issue-109")
  but it is unreachable from any current ref — a dangling object.
  `git log --all` does not contain it. The brainstorm's traceability
  link points to nothing reviewable.
- **Commit-hash mismatch:** brainstorm cites `d4e064cb`; plan cites
  `cecc635`. Both refer to PR #110, but to different artifacts (a merge
  commit that is not in any branch vs. the feature commit on
  `claude/issue-109`). Pick one consistently.

## Proposed Solutions

### Option 1: Edit brainstorm to match plan (recommended)

**Approach:** Update the brainstorm's Problem Frame and
Dependencies/Assumptions sections to match the plan's verified state.
Replace the "merged 2026-04-26" and "already merged on GitHub
(`d4e064cb`)" assertions with language that aligns with the plan:
the feature is *expected* to land via PR #110 (commit `cecc635` on
`claude/issue-109`), and the fix's work phase will not run until that
commit is reachable from `claude/issue-114`'s base.

**Pros:**
- Brings the brainstorm into agreement with the plan and git reality
- Removes the dangling-SHA citation
- Single editing pass, low risk

**Cons:**
- Rewrites a brainstorm after-the-fact, which violates the "brainstorms
  are point-in-time artifacts" convention. Acceptable here because the
  point-in-time claim was factually wrong on the day it was written.

**Effort:** 15-30 minutes
**Risk:** Low

---

### Option 2: Append a correction note to the brainstorm

**Approach:** Leave the original assertions but append a new section
("Correction (2026-04-26)") that calls out the contradiction and points
the reader at the plan's Work Phase Outcome as authoritative.

**Pros:**
- Preserves the "point-in-time artifact" convention
- Audit-trail is intact

**Cons:**
- Two assertions live side-by-side in the same file, which a reader
  must reconcile manually
- Still leaves the dangling SHA citation in place

**Effort:** 10 minutes
**Risk:** Low

---

### Option 3: Leave the brainstorm alone and rely on the plan

**Approach:** Do nothing to the brainstorm; trust readers to consult
the plan first.

**Pros:**
- Zero churn

**Cons:**
- Real-world readers (engineer-auto's downstream phases, future humans)
  may consult the brainstorm in isolation and act on the false claim
- The dangling SHA stays in the doc forever

## Recommended Action

Option 1: edit the brainstorm to match the plan and remove the dangling
SHA citation. Do this as part of the work that unblocks `claude/issue-114`
(after PR #110 lands and the branch is rebased) — at that point the
brainstorm is being re-derived against the new base anyway, and a
factually correct version costs almost nothing extra.

If the unblock takes longer than expected and the brainstorm is consulted
before then, fall back to Option 2 (append a correction note) to prevent
misleading downstream readers.

## Technical Details

**Affected files:**
- `docs/brainstorms/2026-04-26-format-json-ragged-row-policy-requirements.md` —
  edit Problem Frame (lines 8-22) and Dependencies/Assumptions (lines 102-107)
- `docs/plans/2026-04-26-001-fix-format-json-ragged-row-enforcement-plan.md` —
  no edits needed; already correct

**Verification commands:**
- `git rev-parse d4e064cb` — confirms the SHA exists in odb
- `git log --all --oneline | grep d4e064` — confirms it is unreachable
- `git show origin/master:table_fmt.py | grep -c format_json` — confirms
  master has no `format_json`

## Resources

- ce-review run artifact:
  `.context/compound-engineering/ce-review/issue-114-autofix-20260426/run.md`
- Brainstorm:
  `docs/brainstorms/2026-04-26-format-json-ragged-row-policy-requirements.md`
- Plan:
  `docs/plans/2026-04-26-001-fix-format-json-ragged-row-enforcement-plan.md`
- Issue: #114
- Originating PR: #110 (state: not yet merged to master, per git)

## Acceptance Criteria

- [ ] Brainstorm no longer asserts PR #110 has merged
- [ ] Brainstorm no longer cites the dangling SHA `d4e064cb` (or, if
      kept, qualifies it as the unmerged feature/merge SHA on the
      `claude/issue-109` PR branch)
- [ ] Brainstorm and plan agree on the merge state of PR #110
- [ ] If commit hashes are cited, both docs cite the same one (preferred:
      `cecc635`, the feature commit on `claude/issue-109`)
- [ ] No regression to other sections of the brainstorm

## Work Log

### 2026-04-26 — Identified during ce-review autofix

**By:** Claude Code (ce-review autofix run `issue-114-autofix-20260426`)

**Actions:**
- Reviewers correctness (conf 0.97) and maintainability (conf 0.85)
  independently flagged the brainstorm-vs-plan contradiction
- Verified against git: `format_json` is absent from master, `d4e064cb`
  is unreachable from any ref
- Routed as `manual` — content correction to a pipeline-artifact doc,
  not a `safe_auto` candidate
- Recorded as residual actionable work in the run artifact

**Learnings:**
- Engineer-auto's brainstorm phase wrote a confident claim about
  external state ("PR #110 is already merged on GitHub") that did not
  hold up to git verification. Future runs of the brainstorm skill on
  branches whose dependency PRs are still open should either fetch
  authoritative state at write-time or hedge the claim. Candidate input
  for `/ce-compound` once #114 fully unblocks.

## Notes

- This todo intentionally bundles F1 (the merge claim) and F2 (the
  dangling SHA) since they live in the same brainstorm section and the
  same edit resolves both.
- Do not act on this todo before PR #110 merges and `claude/issue-114`
  rebases — there is no rush, and the rebase may itself trigger a
  brainstorm re-derivation that handles this naturally.
