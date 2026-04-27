---
title: "feat: Add --strip-empty-rows flag to table_fmt.py"
type: feat
status: active
date: 2026-04-26
---

# feat: Add --strip-empty-rows flag to table_fmt.py

## Overview

Adds a `--strip-empty-rows` CLI flag to `table_fmt.py` that removes data rows
where every cell is empty or whitespace-only before rendering. Header and
separator rows are never stripped. Without the flag, byte-for-byte behavior is
unchanged.

---

## Problem Frame

`format_table()` currently pads blank rows with spaces, producing visually
awkward gaps in cleaned-up tables. Operators need a way to drop these blank
data rows without touching the header or separator, and without changing
behavior for existing callers.

---

## Requirements Trace

- R1. `--strip-empty-rows` removes data rows whose cells are all empty or whitespace-only
- R2. Header row is never stripped, even when every cell is empty
- R3. Separator row is never stripped (structurally required by markdown table spec)
- R4. Without the flag, byte-for-byte behavior is unchanged
- R5. `--help` documents the new flag
- R6. Tests cover: all-empty cells, all-whitespace cells, mixed empty/non-empty cells, single empty cell, empty header preserved

---

## Scope Boundaries

- Removing duplicate rows is out of scope
- Sorting rows is out of scope
- Custom predicates for "empty" are out of scope
- No changes to `countdown.sh`, `dashboard.html`, or any file other than `table_fmt.py` and its tests

---

## Context & Research

### Relevant Code and Patterns

- `table_fmt.py` — `parse_table()` already strips per-cell whitespace using `str.strip()`; the new helper follows the same convention
- `table_fmt.py` — `format_table()` normalizes column count by padding short rows; the strip step runs before this normalization so rows are evaluated on user-written cells, not padding

### Institutional Learnings

- `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md` — prior fix to `table_fmt.py`; confirms the pattern of keeping `parse_table` and `format_table` as distinct stages and not mixing logic between them

---

## Key Technical Decisions

- **Whitespace definition**: Python's `str.strip()`, which strips all characters where `str.isspace()` is True, covering ASCII whitespace, non-breaking space (U+00A0), and full-width space (U+3000). Zero-width characters (e.g., U+200B) are not whitespace and a row of them is treated as non-empty. Matches the convention already used by `parse_table`.
- **Apply before normalization**: `_strip_empty_rows` runs on parsed rows before `format_table()` pads them to the max column count. A short row with 2 empty cells in a 3-column table is correctly stripped before normalization would add a third empty cell.
- **Format-only, not parse**: `parse_table()` is unchanged. `_strip_empty_rows` is applied in `main()` after parsing, so downstream library consumers still receive empty rows if they call `parse_table()` directly. Only the rendered output omits them.
- **Header preserved unconditionally**: `rows[0]` is the header by convention in `format_table`. It is never stripped, even if every cell is empty, because an operator may intentionally build a header-only table for downstream consumers.

---

## Open Questions

### Resolved During Planning

- **What counts as whitespace?**: Python `str.strip()` — covers ASCII and Unicode whitespace. Zero-width chars are not whitespace.
- **Apply before or after normalization?**: Before — predicate sees cells the user wrote, not padding.
- **Change `parse_table` or `format_table` path?**: Format path only (`main()` invokes `_strip_empty_rows` between `parse_table` and `format_table`). `parse_table` is unchanged.

---

## Implementation Units

- U1. **Add `_is_empty_row` predicate helper**

**Goal:** Expose a testable predicate that returns `True` when every cell in a row is empty or whitespace-only.

**Requirements:** R1, R6

**Dependencies:** None

**Files:**
- Modify: `table_fmt.py`
- Test: `test_table_fmt.py`

**Approach:**
- `_is_empty_row(cells: list[str]) -> bool`
- Uses `all(not cell.strip() for cell in cells)`
- Docstring explains whitespace definition (str.isspace coverage, zero-width chars excluded)

**Patterns to follow:**
- `parse_table` — uses `c.strip()` for per-cell trimming; new helper matches exactly

**Test scenarios:**
- Happy path: `["", "", ""]` → `True`
- Happy path: `["   ", "\t", " \t "]` → `True` (ASCII whitespace)
- Happy path: `[" ", "　"]` → `True` (Unicode whitespace)
- Edge case: `["​"]` → `False` (zero-width non-breaking space is not whitespace)
- Edge case: `["", "x", ""]` → `False` (one non-empty cell)
- Edge case: `[""]` → `True` (single empty cell)
- Edge case: `["x"]` → `False` (single non-empty cell)

**Verification:**
- All `IsEmptyRowTests` pass

---

- U2. **Add `_strip_empty_rows` helper and integrate into `main()`**

**Goal:** Provide a function that strips all-empty data rows while unconditionally preserving the header row, and wire the `--strip-empty-rows` CLI flag to invoke it.

**Requirements:** R1, R2, R3, R4, R5

**Dependencies:** U1

**Files:**
- Modify: `table_fmt.py`
- Test: `test_table_fmt.py`

**Approach:**
- `_strip_empty_rows(rows)` splits on `header, *data = rows`, returns `[header] + [row for row in data if not _is_empty_row(row)]`
- Separator row is consumed by `parse_table` and never present in `rows`, so it cannot be stripped
- `argparse` flag `--strip-empty-rows` with `action="store_true"`, help text documents behavior
- In `main()`: if `args.strip_empty_rows`, call `_strip_empty_rows(rows)` between `parse_table` and `format_table`
- `format_table()` itself is not modified — backward-compat is preserved at the library level

**Patterns to follow:**
- Existing `argparse` setup in `main()` for flag declaration style
- `format_table()` column-count normalization as the step this runs before

**Test scenarios:**
- Happy path: rows with all-empty data rows dropped, header kept (R1, R2)
- Happy path: rows with all-whitespace data rows dropped (R1)
- Edge case: rows where only some cells are empty — row kept (R1)
- Edge case: header row with all-empty cells — header preserved (R2)
- Edge case: header-only table (no data rows) — unchanged (R2)
- Edge case: short data row (fewer cells than header) with all-empty cells — stripped before normalization (R1)
- Edge case: empty input list — returns empty list
- CLI — `--strip-empty-rows` flag: blank data rows absent from output, header present (R1, R2)
- CLI — no flag: output identical to current behavior including blank rows (R4)
- CLI — `--help`: output contains `--strip-empty-rows` string (R5)
- Integration: `format_table` without flag still pads empty rows rather than dropping them (R4)

**Verification:**
- All `StripEmptyRowsTests`, `FormatTableUnchangedWithoutFlagTests`, and `StripEmptyRowsCliTests` pass
- `python table_fmt.py --help` output includes `--strip-empty-rows`
- Pipe a table with blank rows through both with and without the flag; confirm byte-for-byte parity for the no-flag case

---

## System-Wide Impact

- **Unchanged invariants:** `parse_table()` and `format_table()` signatures and behavior are unchanged. Existing callers that import these functions are unaffected.
- **API surface parity:** The new helpers (`_is_empty_row`, `_strip_empty_rows`) are module-level and importable; they are tested directly in `test_table_fmt.py`.
- **Error propagation:** No new error paths introduced. The flag is boolean; missing or extra whitespace in cells degrades gracefully via `str.strip()`.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| `str.strip()` behavior differs from what `parse_table` already does per cell | Both use the same `str.strip()` call — confirmed consistent |
| Column-count padding masks originally-empty short rows | Strip runs before `format_table` normalization — explicitly sequenced to avoid this |
| `format_table` behavior changes for empty-row callers | `format_table` is not modified; stripping is only in `main()` — library callers unaffected |

---

## Sources & References

- Related code: `table_fmt.py`, `test_table_fmt.py`
- Institutional learning: `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
