---
status: ready
priority: p2
issue_id: "002"
tags: [docs, ce-review-residual, issue-114, plan-correctness, learnings]
dependencies: []
---

# Fix broken citation to non-existent learnings doc in plan

## Problem Statement

The plan at
`docs/plans/2026-04-26-001-fix-format-json-ragged-row-enforcement-plan.md`
cites `docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md`
in three places — Institutional Learnings, Documentation/Operational
Notes, and Sources & References — and includes a verbatim quote
attributed to it. The cited file does not exist in the repo. The
verbatim quote is therefore fabricated against a missing source.

The genuine prior art (per the ce-review learnings-researcher) is
`docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`,
which exists and covers the same module's silent-data-loss prevention
pattern.

## Findings

Sourced from ce-review autofix run `issue-114-autofix-20260426`,
finding F3 (maintainability, P2, conf 0.90; confirmed by
learnings-researcher).

- **Plan line 107-109 (Institutional Learnings):** *"docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md
  explicitly calls out this exact bug under "Symptoms": 'Ragged-row
  data loss in JSON because parse_table does not normalize column
  counts; dict(zip(header, row)) truncates silently when a row is short
  or long (table_fmt.py:155)…'"*
- **Plan ~line 358 (Documentation/Operational Notes):** *"The existing
  best-practices doc at
  docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md
  already mentions this bug under Symptoms…"*
- **Plan ~line 384 (Sources & References):** *"docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md
  — already documents the bug under Symptoms and the
  pure-helper-raises-ValueError convention this fix preserves."*
- **Filesystem reality:** `docs/solutions/best-practices/` contains
  exactly one file: `project-status-dashboard-implementation-2026-04-06.md`.
  No `2026-04-26` file exists anywhere under `docs/solutions/`.
- **Real prior art:**
  `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
  exists and is genuine prior art for the same module. It covers
  silent-data-loss prevention in `table_fmt` (alignment hints dropped on
  parse round-trip), recommends parse-level + format-level + round-trip
  tests, and warns about "skipping" structural rows without checking for
  metadata.

## Proposed Solutions

### Option 1: Replace dead citation with real prior art (recommended)

**Approach:** Edit the plan in three places (Institutional Learnings,
Documentation/Operational Notes, Sources & References) to:

1. Drop the verbatim quote attributed to the missing best-practices doc.
2. Replace citations to
   `docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md`
   with citations to
   `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`,
   summarizing the relevant guidance (silent-data-loss prevention,
   round-trip test pattern) in the plan's own words.
3. Update Documentation/Operational Notes to drop the cross-link
   instruction (no doc to cross-link to and update).

**Pros:**
- Plan cites a real document
- Removes fabricated verbatim quote
- Connects the fix to genuine prior institutional learning

**Cons:**
- Slightly more editing than just removing the citation
- The rewritten plan claims about prior art still need to be accurate
  to whatever the real doc actually says

**Effort:** 30-45 minutes
**Risk:** Low

---

### Option 2: Remove the dead citation and the verbatim quote without replacement

**Approach:** Strip all three references to
`table-fmt-add-cli-output-mode-flag-2026-04-26.md` from the plan, along
with the verbatim quote. Do not substitute the real prior-art doc.

**Pros:**
- Minimal editing
- Removes the false claim

**Cons:**
- Loses the institutional-learning anchor entirely
- Plan ends up weaker than it could be — the real prior art is
  genuinely relevant

**Effort:** 10-15 minutes
**Risk:** Low

---

### Option 3: Author the missing doc

**Approach:** Write
`docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md`
to match the verbatim quote in the plan, retroactively making the
citation valid.

**Pros:**
- The plan stays as-is
- A best-practices doc on this topic could be useful

**Cons:**
- Authoring a learnings doc to match a fabricated quote inverts the
  point of learnings docs (capturing what *actually* happened)
- The convention is: learnings docs are written via `/ce-compound`
  *after* a problem is solved, not pre-fabricated by a planning skill
- Probably not the intended workflow

**Effort:** 1-2 hours
**Risk:** Medium (sets a precedent of plan-driven backfilled learnings)

## Recommended Action

Option 1: replace the dead citation with the real prior-art doc and
drop the fabricated verbatim quote. Do this as part of the work that
unblocks `claude/issue-114` — the plan is being consulted by the work
phase anyway, and a corrected plan reduces friction for that phase.

If implementation does not start soon, do at minimum a partial Option 2
(strip the verbatim quote) to prevent the fabricated content from being
copy-pasted elsewhere.

## Technical Details

**Affected files:**
- `docs/plans/2026-04-26-001-fix-format-json-ragged-row-enforcement-plan.md` —
  edit Institutional Learnings (line 107-109),
  Documentation/Operational Notes (~line 358), Sources & References
  (~line 384).

**Verification commands:**
- `ls docs/solutions/best-practices/` — confirms the cited file is absent
- `ls docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md` —
  confirms the real prior-art file exists

## Resources

- ce-review run artifact:
  `.context/compound-engineering/ce-review/issue-114-autofix-20260426/run.md`
- Plan (file with the broken citation):
  `docs/plans/2026-04-26-001-fix-format-json-ragged-row-enforcement-plan.md`
- Real prior art:
  `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
- Issue: #114

## Acceptance Criteria

- [ ] Plan no longer cites
      `docs/solutions/best-practices/table-fmt-add-cli-output-mode-flag-2026-04-26.md`
- [ ] Verbatim quote attributed to the missing doc is removed
- [ ] If a substitute prior-art reference is included, it points to a
      real file (preferably
      `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`)
      and accurately summarizes that doc's guidance
- [ ] Plan's Documentation/Operational Notes section reflects the new
      reality (no cross-link instruction to the missing doc)

## Work Log

### 2026-04-26 — Identified during ce-review autofix

**By:** Claude Code (ce-review autofix run `issue-114-autofix-20260426`)

**Actions:**
- Maintainability reviewer (conf 0.90) flagged the dead citation
- Learnings-researcher independently confirmed the file is absent and
  surfaced the real prior-art doc
- Routed as `manual` — content correction to a pipeline-artifact doc,
  not a `safe_auto` candidate
- Recorded as residual actionable work in the run artifact

**Learnings:**
- A planning skill (`/ce:plan` or similar) appears to have generated a
  verbatim quote against a doc it expected to exist but did not.
  Defending against this in future runs would require the planning
  skill to verify cited learnings-doc paths exist before quoting them.
  Candidate input for `/ce-compound` once #114 fully unblocks.

## Notes

- The real prior-art doc
  (`logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`) is
  in a different `docs/solutions/` subdirectory (`logic-errors/`, not
  `best-practices/`). The plan's preference for a `best-practices/`
  citation may have driven the fabrication; the fix should not insist
  on the same subdirectory.
- Do not author the missing doc as a workaround (Option 3). Learnings
  docs are post-hoc artifacts of `/ce-compound`, not preconditions of
  planning.
