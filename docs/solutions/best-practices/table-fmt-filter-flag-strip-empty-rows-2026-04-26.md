---
title: "table_fmt: design pattern for filter-style preprocessing CLI flags"
date: 2026-04-26
category: best-practices
module: table_fmt
problem_type: best_practice
component: tooling
severity: low
applies_when:
  - Adding a flag that removes or transforms rows before rendering
  - Adding any preprocessing step to table_fmt's format pipeline
  - Implementing filter predicates that need to be testable in isolation
tags:
  - cli
  - table
  - filtering
  - markdown
  - formatter
  - predicate
  - empty-rows
---

# table_fmt: design pattern for filter-style preprocessing CLI flags

## Context

`table_fmt.py` reformats markdown tables but previously kept blank rows — rows
where every cell is empty or whitespace-only — producing visually awkward gaps
in cleaned-up tables. Adding a `--strip-empty-rows` flag exposed a set of
design decisions that apply to any filter-style preprocessing flag on a
formatter CLI.

The four decisions made here (predicate helper, strip-before-normalization,
format-path-only, unconditional header preservation) form a reusable template
for future flags of the same shape.

## Guidance

**1. Isolate filter logic in a private predicate helper.**

```python
def _is_empty_row(cells):
    """Return True when every cell is empty or whitespace-only."""
    return all(not cell.strip() for cell in cells)
```

- Keeps the filtering rule independently testable without invoking the CLI.
- `_is_empty_row([])` returns `True` (vacuous truth from `all()`). Pin this
  contract with an explicit test so it cannot silently change:

```python
def test_empty_cell_list_vacuous_truth(self):
    self.assertTrue(_is_empty_row([]))
```

**2. Apply filtering before column-count normalization.**

`format_table()` pads short rows to the max column count. A 2-cell row in a
5-column table has 2 cells — not 5 — when the predicate runs, so non-empty
short rows are never incorrectly classified as empty due to padding.

```python
def _strip_empty_rows(rows):
    if not rows:
        return rows
    header, *data = rows
    return [header] + [row for row in data if not _is_empty_row(row)]
```

Wire it between `parse_table` and `format_table` in `main()`:

```python
rows, alignments = parse_table(text)
if args.strip_empty_rows:
    rows = _strip_empty_rows(rows)
sys.stdout.write(format_table(rows, alignments))
```

**3. Filter in the format path only; leave `parse_table` unchanged.**

`parse_table` is a general-purpose parser used by tests and downstream consumers
that may want to inspect empty rows. Keeping stripping in the format path means
callers that use `parse_table` directly continue to see the full row set.

**4. Unconditionally preserve the header row.**

Even when every header cell is empty the operator may be intentionally building
a header-only table for downstream consumers. Never pass the header through the
predicate:

```python
header, *data = rows
return [header] + [row for row in data if not _is_empty_row(row)]
```

The markdown separator row is already consumed by `parse_table` and never
appears in `rows`, so it cannot be stripped.

**5. Use `str.strip()` for the whitespace definition.**

`str.strip()` trims any character where `str.isspace()` is True, including
ASCII space/tab, non-breaking space (U+00A0), and full-width space (U+3000).
This matches the trimming convention already used by `parse_table`, so the
"empty" definition is consistent across parsing and filtering. Zero-width
characters such as U+200B do not count — a row of them is treated as non-empty,
which is the conservative choice.

## Why This Matters

- **Predicate isolation** makes the core filtering rule trivially testable and
  prevents regressions when the whitespace definition or logic is revisited.
- **Strip-before-normalization** avoids a subtle bug: if padding ran first, a
  legitimately short but non-empty row could end up classified as all-empty
  after its padded cells are inspected.
- **Format-path-only** preserves the parse layer as a stable contract for code
  that calls `parse_table` directly.
- **Unconditional header preservation** sidesteps an edge case that is easy to
  overlook — an operator building a header-only table would have their data
  silently destroyed otherwise.

## When to Apply

- Adding any flag that drops rows matching a predicate (e.g., `--strip-duplicate-rows`,
  `--max-rows N`).
- Adding any flag that transforms rows before rendering (e.g., `--sort-by-col`,
  `--truncate-cells`).
- The same predicate-helper + strip-before-normalization pattern applies
  whenever the filter semantics should be based on the author's original cell
  content, not on the formatter's padded output.

## Examples

**Before `--strip-empty-rows`** — blank rows are kept:

```
| Name  | Value |
| ----- | ----- |
| foo   | 1     |
|       |       |
| bar   | 2     |
|       |       |
```

**After `--strip-empty-rows`** — clean output:

```
| Name | Value |
| ---- | ----- |
| foo  | 1     |
| bar  | 2     |
```

**Test classes added** (`test_table_fmt.py`):

- `IsEmptyRowTests` — unit tests for `_is_empty_row` including vacuous-truth
  contract for empty list.
- `StripEmptyRowsTests` — unit tests for `_strip_empty_rows` including header
  preservation.
- `FormatTableUnchangedWithoutFlagTests` — byte-for-byte parity without flag.
- `StripEmptyRowsCliTests` — CLI tests via `subprocess.run`, including the case
  where all data rows are stripped (asserts exit 0 and 2-line output).

## Related

- `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md` — prior `table_fmt.py` fix; established the conventions (private helpers, docstrings, round-trip tests) that this feature follows.
- GitHub issue #130 — `--strip-empty-rows` flag implementation.
