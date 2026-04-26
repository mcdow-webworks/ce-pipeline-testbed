# ce-review run — issue #114 autofix

- Run ID: issue-114-autofix-20260426
- Branch: claude/issue-114
- Base: master (merge-base d02bb4428a9fdb7384c16db973a264bfaff50113)
- Mode: autofix
- Date: 2026-04-26

## Intent

Engineer-auto pipeline produced a brainstorm + plan for issue #114
(`format_json` ragged-row enforcement). The plan is `status: blocked`
because the target function `format_json` does not exist on this branch's
merge-base — PR #110 has not landed. No code changes are in this diff.
Reviewers evaluated the docs as docs: cross-reference correctness,
internal consistency, scope clarity, and accuracy of the blocked status.

## Scope

Files in scope (both new):

- `docs/brainstorms/2026-04-26-format-json-ragged-row-policy-requirements.md`
- `docs/plans/2026-04-26-001-fix-format-json-ragged-row-enforcement-plan.md`

Both files live in protected pipeline-artifact directories
(`docs/brainstorms/*`, `docs/plans/*.md`). Per skill rules, any finding
recommending deletion or gitignore for these paths is discarded during
synthesis.

## Review team

Always-on: correctness, testing, maintainability, agent-native,
learnings-researcher.

Conditional reviewers skipped: security, performance, api-contract,
data-migrations, reliability, dhh-rails, kieran-rails, kieran-python,
kieran-typescript, julik-frontend-races, schema-drift-detector,
deployment-verification-agent — none apply to a docs-only diff with no
code, no API surface, no migrations, and no stack-specific changes.

## Findings summary (after merge, dedup, 0.60 confidence gate)

- P0: 0
- P1: 1
- P2: 3
- P3: 1 actionable + 6 advisory testing scenario gaps
- Suppressed: 0

## Applied fixes (safe_auto → review-fixer)

**None.** All actionable findings are content corrections to
pipeline-artifact docs and were classified `manual` by every reviewer
that surfaced them. Synthesis preserved the conservative routing. The
plan's `status: blocked` flag and Work Phase Outcome already correctly
reflect that PR #110 is unmerged, so the blocked workflow is not at risk
from the brainstorm's stale claims — it just makes the brainstorm
internally inconsistent with its sibling plan.

## Residual actionable work (manual → downstream-resolver)

Durable todos created under `.context/compound-engineering/todos/`:

| # | Finding | Severity | Reviewers | Todo file |
|---|---|---|---|---|
| F1 | Brainstorm asserts PR #110 is merged ("merged 2026-04-26", "already merged on GitHub `d4e064cb`"); plan and git state contradict — plan declares `status: blocked`, master HEAD is `d02bb44` with no `format_json`, and `d4e064cb` is unreachable from any ref. Reconcile the brainstorm with the verified state in the plan's Work Phase Outcome. | P1 | correctness (0.97), maintainability (0.85) | `001-ready-p1-reconcile-brainstorm-pr-110-merge-status.md` |
| F2 | Brainstorm cites orphan SHA `d4e064cb` as the merge commit for PR #110. The SHA exists in the local odb but is unreachable from `master`, `origin/master`, `claude/issue-114`, or `claude/issue-109`. Resolved together with F1. | P2 | correctness (0.95) | folded into todo 001 |
| F3 | Plan's Institutional Learnings + Documentation Notes + Sources sections cite `docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md` and quote it verbatim. The file does not exist on this branch (only `docs/solutions/best-practices/project-status-dashboard-implementation-2026-04-06.md` is present). The verbatim quote is fabricated against a missing source. The genuine prior art is `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md` (per learnings-researcher). | P2 | maintainability (0.90), learnings-researcher (confirmed) | `002-ready-p2-fix-broken-learnings-doc-citation-in-plan.md` |
| F4 | Plan's Problem Frame, Scope Boundaries, Requirements Trace, and Key Technical Decisions duplicate brainstorm content near-verbatim. If the brainstorm is corrected (per F1/F2/F3) the plan's mirrored prose will not auto-update. Consider trimming the plan to a delta-only statement of what changed during planning and let the brainstorm carry the rest by reference. | P3 | maintainability (0.70) | not externalized — author judgment call, recorded here for future planning-skill prompt evolution |

These items will be naturally re-examined when PR #110 lands and
`/ce:work` re-runs on this branch — at that point the plan's blocked
state is unwound and the docs are re-derived against the new master
tip. Creating todos now ensures the discrepancies are not lost if the
re-derivation skips them.

## Advisory (testing scenario gaps in the plan)

These are anticipatory reviews of the *test plan inside the plan
document*, not real test code (none exists). They become live when the
plan is unblocked and Unit 1 / Unit 2 are implemented. Captured in the
run artifact for the implementer to consult; no todo is created because
they belong to whoever runs `/ce:work` after the blocker resolves.

| # | Finding | Severity |
|---|---|---|
| F5 | Plan's Unit 1 test scenarios omit empty-row case (`rows = [["A","B"], []]`) — boundary for `len(row) != len(header)` where row length is 0. | P3 |
| F6 | Plan omits single-column header with multi-cell ragged row (`rows = [["A"], ["x","y"]]`). | P3 |
| F7 | Unit 2 CLI scenarios always place the ragged row at row 1 — does not prove the "no partial JSON before raising" R1 invariant for cases where a rectangular row precedes the ragged one (`main()` could in principle flush partial output). | P2 |
| F8 | First-mismatch reporting test uses a fixture where row 1 is itself the first ragged row, so a buggy implementation that hardcoded `row 1` would still pass. Test should place the first offender at row 2 or later and assert `row 2` in the message. | P2 |
| F9 | All-rows-ragged-same-direction case missing — would prove the loop short-circuits on the first offender rather than scanning further. | P3 |
| F10 | Substring assertion `"every data row to have the same column count"` is repeated across four planned tests. Future polish that rewords this English phrase silently breaks all four. Anchor on shorter, lower-churn substrings (`"column count"`, `"row 1"`, numeric counts). | P3 |
| F11 | Default-mode regression scenario asserts only exit code 0; R4 calls for byte-for-byte equivalence to pre-fix markdown output. An exit-0 assertion would still pass if the markdown path silently regressed to a truncated table. Assert stdout content equality, not just exit code. | P3 |

## Pre-existing

None. Both files are new in this diff.

## Learnings & Past Solutions

Surfaced by `learnings-researcher`:

- **Real prior art (cite this, not the missing doc):**
  `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
  — same module (`table_fmt`), establishes the silent-data-loss
  prevention pattern this fix extends. Recommends parse-level,
  format-level, and round-trip tests — relevant guidance for the test
  scenarios above.
- **No prior precedent** in `docs/solutions/` for either the
  zip-short-iterable silent-truncation pattern or the "blocked plan
  awaiting dependency PR" engineer-auto state. Both are candidates for
  `/ce-compound` capture once PR #110 lands and #114 unblocks.
- **Confirmed dead citation:** the plan's reference to
  `docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md`
  resolves to no file in the current tree.

## Agent-native

PASS. The fix being planned (when it lands) is a Unix-style CLI helper
with stderr + exit-1 feedback — fully agent-native by convention. No
agent-mode-only paths are missed: agents and humans use the same
`format_json` -> `main()` boundary, and the planned error message is
structured enough (row index, row column count, header column count) for
agent consumption without a parallel structured-error stream. The plan
correctly does *not* propose a second `--errors-as-json` channel or a
distinct exit code.

## Verdict

**Ready with fixes (residual).** The branch is internally inconsistent
on the dependency state of PR #110 — the brainstorm claims merge, the
plan correctly does not. This is annoying but not blocking: the plan's
`status: blocked` and Work Phase Outcome are the authoritative
artifacts the next pipeline phase consults, and they correctly halt
forward progress until PR #110 lands. The residual todos capture the
content corrections so they are not lost when the branch unblocks.

No code or test code is in scope for autofix. No `safe_auto` fixes
applied.

## Next steps (out of band — autofix does not act on these)

1. PR #110 (`feat(table_fmt): add --json output mode (#109)`) merges to
   master, then `claude/issue-114` rebases onto the new master tip.
2. Re-run `/ce:work` on the rebased branch to actually implement Unit 1
   and Unit 2 from the plan.
3. Address the residual todos (F1–F3) as part of the same re-run, or
   earlier if the brainstorm/plan are consulted before the unblock.
4. The advisory testing gaps (F5–F11) feed into the next ce-review cycle
   that runs against real code.
