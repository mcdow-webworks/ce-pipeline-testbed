---
status: ready
priority: p3
issue_id: "002"
tags: [maintainability, refactor, table_fmt]
dependencies: []
---

# Extract a padded-row helper in `table_fmt.py` to remove inline duplication

## Problem Statement

`table_fmt.py:124` emits the separator row with a hand-rolled `"| " + " | ".join(sep_cells) + " |"` that exactly duplicates the padded branch of `format_row` on `table_fmt.py:111`. The duplication is the mechanism by which the separator row stays padded under `--strip-padding`, but the contract is implicit. A future reader changing the padded form (e.g., switching to a different join character or adding outer trim behavior) would have to remember to update both sites.

## Findings

- `table_fmt.py:107-111` — `format_row` returns `"| " + " | ".join(padded) + " |"` in the non-stripped branch.
- `table_fmt.py:122-124` — separator emission inline-duplicates that join expression.
- The separator is intentionally always padded (so the markdown output remains valid even under `strip_padding=True`). This is a design decision worth making explicit, not a bug.

## Proposed Solutions

### Option 1: Extract a small `_join_padded(cells)` helper

**Approach:** Define a one-liner closure or module-level helper:

```python
def _join_padded(cells):
    return "| " + " | ".join(cells) + " |"
```

Use it in both the padded branch of `format_row` and the separator emission. The strip-padding branch keeps its own minimal join.

**Pros:**
- Single source of truth for the padded format.
- The separator's choice to remain padded becomes an explicit "use the padded helper" call.
- Minimal change; no behavior delta.

**Cons:**
- Adds a tiny indirection for what is currently obvious inline code.
- Helper is used in only two spots, so the abstraction is modest.

**Effort:** 15 minutes.

**Risk:** Low. Existing tests cover both call sites.

### Option 2: Route the separator through `format_row` with a `force_pad=True` flag

**Approach:** Extend `format_row` to take a parameter that overrides `strip_padding` for a single call, then call `format_row(sep_cells, force_pad=True)` on line 124.

**Pros:**
- Reuses the full `format_row` machinery.
- Makes "the separator ignores strip_padding" a single boolean at the call site.

**Cons:**
- Mixes data-row formatting with separator formatting; `format_row` would now be doing two distinct jobs.
- The padded branch already goes through `pad_cell` which is irrelevant for separator cells (their widths come from `separator_cell`, not `pad_cell`).
- Adds a parameter that only one caller ever sets.

**Effort:** 30 minutes.

**Risk:** Low-Medium. More invasive; risk of confusing future readers.

### Option 3: Add an inline comment on line 124 only

**Approach:** Leave the duplication, add a one-line comment explaining the intent.

**Pros:**
- Cheapest; no code change.
- Documents the design decision at the call site.

**Cons:**
- Comment can rot; the structural duplication remains.
- Doesn't actually remove the maintainability hazard.

**Effort:** 5 minutes.

**Risk:** Low.

## Recommended Action

Adopt **Option 1**. The helper is two lines, the abstraction is honest (a padded markdown row is a thing), and it removes the implicit coupling between the two sites. Update existing `FormatRowPaddingTests` and `FormatSeparatorTests` only if needed for clarity — behavior is unchanged so all tests should pass without modification.

## Technical Details

**Affected files:**
- `table_fmt.py:107-128` — `format_row`, separator emission inside `format_table`.

**Related components:** none.

**Database changes:** none.

## Resources

- **PR:** Closes #96
- **ce-review run artifact:** `.context/compound-engineering/ce-review/20260425-210217-strip-padding-autofix/run.md`
- **Related finding:** ce-review maintainability reviewer, finding #2 (P3, conf 0.66)

## Acceptance Criteria

- [ ] A single helper produces the padded `"| ... | ... |"` form; it is called from both the padded branch of `format_row` and the separator emission.
- [ ] All existing tests (22 cases) still pass with no modification needed.
- [ ] Behavior is byte-identical for both `strip_padding=True` and `strip_padding=False`.

## Work Log

### 2026-04-25 - Surfaced by ce-review autofix

**By:** ce-review autofix run (run id `20260425-210217-strip-padding-autofix`)

**Actions:**
- Synthesized as P3 finding from `maintainability` reviewer at confidence 0.66.
- Routed to `downstream-resolver` because extracting a helper crosses a function boundary and is judgment-laden enough to deserve human review rather than autofix.
- Filed as `ready` since synthesis already triaged the work.

**Learnings:**
- The separator-row's "always padded, even under strip_padding" decision is a real design intent worth surfacing; a helper makes that intent visible at the call site.
