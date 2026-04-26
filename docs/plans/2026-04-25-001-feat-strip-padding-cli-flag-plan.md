---
title: "feat: Add --strip-padding CLI flag to table_fmt"
type: feat
status: active
date: 2026-04-25
origin: docs/brainstorms/2026-04-25-strip-padding-cli-flag-requirements.md
---

# feat: Add `--strip-padding` CLI flag to `table_fmt`

## Overview

Add an opt-in `--strip-padding` argparse flag to `table_fmt.py` that emits
data rows with no whitespace between pipes and cell content (`|a|b|`),
while leaving the separator row in its standard padded form so the output
remains valid markdown. Default behavior is byte-identical to today.

## Problem Frame

`table_fmt.py` always pads data-row cells for visual alignment
(`| a | b |`). Some downstream consumers — CSV converters, plain-text
post-processors, naive pipe-splitters — prefer unpadded cells and have to
run a separate strip pass today. A single emit-time flag eliminates that
extra pass without breaking the human-readable default
(see origin: `docs/brainstorms/2026-04-25-strip-padding-cli-flag-requirements.md`).

## Requirements Trace

- R1. `table_fmt.py` accepts a `--strip-padding` argparse flag; when
  present, header + body rows emit as `|cell|cell|` with no padding.
- R2. Separator row is emitted unchanged when `--strip-padding` is set —
  same dash count, same colon markers, same surrounding spaces — so the
  output remains valid markdown that re-parses to the same table.
- R3. Default behavior (flag absent) is byte-identical to current output;
  every existing test passes unmodified.
- R4. `python table_fmt.py --help` lists `--strip-padding` with a short
  description.

## Scope Boundaries

- Out of scope: stripping whitespace *inside* a cell (`"hello world"` is
  preserved verbatim — only padding between pipes and content is removed).
- Out of scope: a separate flag that also collapses the separator row.
- Out of scope: changing `parse_table` (parsing already strips cells).
- Out of scope: a short alias such as `-s`.

## Context & Research

### Relevant Code and Patterns

- `table_fmt.py` — single-file CLI tool. `format_table(rows, alignments)`
  is the only emit path; `main()` drives argparse and stdin I/O.
- `format_row(cells)` (closure inside `format_table`) is the precise seam
  where padding is currently applied via `pad_cell` + `" | ".join(...)`.
- `separator_cell(width, align)` builds the separator row independently
  of `format_row`, so the separator can keep its padded shape regardless
  of how data rows are emitted.
- `test_table_fmt.py` already groups tests by responsibility
  (`ParseAlignmentTests`, `FormatSeparatorTests`, `FormatRowPaddingTests`,
  `RoundTripTests`). New cases belong in a dedicated `StripPaddingTests`
  class to mirror that style.

### Institutional Learnings

- `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
  — alignment hints flow from the separator row through `parse_table`
  into `format_table`. The new flag must not regress that flow: the
  separator must still carry the colon markers under stripping, otherwise
  a strip → re-parse round trip would lose alignment.

### External References

- None gathered. The change is local, well-patterned in the existing
  module, and uses standard `argparse` only.

## Key Technical Decisions

- **Flag is wired into `format_table`, not `parse_table`.** Rationale:
  parsing already strips cells; the asymmetry only exists at emit time.
  A keyword argument keeps the seam minimal and leaves all parsing tests
  untouched.
- **Separator row is exempt from stripping.** Rationale: the issue
  explicitly requires the separator to round-trip; collapsing it would
  also bury the alignment colons inside narrow cells and risks ambiguity
  with header-less tables under some markdown parsers.
- **Padding strip implies alignment is a no-op for data rows.** Rationale:
  alignment is implemented via `ljust`/`rjust`/`center` on padded cells;
  with no padding there is nothing to justify. The separator still
  carries the alignment hint via colons, so re-parsing recovers it.
- **Default `strip_padding=False` keyword argument.** Rationale: existing
  callers (`main()` and `test_table_fmt.py`) need no change — confirmed
  by repo scan in the origin doc.

## Open Questions

### Resolved During Planning

- *Should the flag also affect the separator row?* No — origin acceptance
  criteria require the separator to remain unchanged.
- *Should a short alias (`-s`) be added?* No — origin scope explicitly
  excludes it.

### Deferred to Implementation

- None. Scope and acceptance criteria are concrete.

## Implementation Units

- [ ] **Unit 1: Add `strip_padding` keyword to `format_table`**

**Goal:** Teach `format_table` to emit data rows without surrounding
whitespace when `strip_padding=True`, while keeping the separator row
unchanged.

**Requirements:** R1, R2, R3

**Dependencies:** None

**Files:**
- Modify: `table_fmt.py`
- Test: `test_table_fmt.py`

**Approach:**
- Add `strip_padding: bool = False` keyword argument to `format_table`.
- Branch inside the `format_row` closure so that when `strip_padding` is
  true, the row is built as `"|" + "|".join(cells) + "|"` with no
  per-cell padding and no alignment-aware justification.
- Leave the separator row construction (`separator_cell` + the
  `"| " + " | ".join(sep_cells) + " |"` join) untouched so the colon
  markers and surrounding spaces are preserved.
- Update the `format_table` docstring to describe the new keyword and
  call out that the separator stays in its padded form.

**Patterns to follow:**
- The existing closure-based row builder in `format_table`; do not
  introduce a new top-level helper just for the stripped form.
- Existing test class layout in `test_table_fmt.py` — add a new
  `StripPaddingTests(unittest.TestCase)` class.

**Test scenarios:**
- Stripped data rows: `[["a","b"],["x","y"]]` with `strip_padding=True`
  emits `|a|b|` and `|x|y|`.
- Separator unchanged across flag states: separator line is identical
  for `strip_padding=True` and `strip_padding=False` on the same input.
- Alignment colons preserved on separator under stripping:
  `["left", "right", "center"]` still emits `| :-- | --: | :-: |`.
- Default-false matches explicit-false: `format_table(rows)` equals
  `format_table(rows, strip_padding=False)`.
- Inner cell whitespace preserved: `"hello world"` emits as
  `|hello world|` (only padding between pipes and content is removed).

**Verification:**
- `python -m unittest test_table_fmt.py` passes, including the new
  `StripPaddingTests` cases.
- All pre-existing tests pass without modification (R3 byte-identity).

- [ ] **Unit 2: Wire `--strip-padding` argparse flag through `main()`**

**Goal:** Expose the new behavior on the CLI and pipe the parsed flag
into `format_table`.

**Requirements:** R1, R4

**Dependencies:** Unit 1

**Files:**
- Modify: `table_fmt.py`

**Approach:**
- In `main()`, register `--strip-padding` as a `store_true` argument with
  a short help string that explains the effect and notes that the
  separator row is left unchanged.
- Pass `strip_padding=args.strip_padding` into the `format_table` call.
- No new test file is needed; the behavior is covered by Unit 1's
  function-level tests, and there is no existing CLI-level harness to
  extend (matches the current test layout).

**Patterns to follow:**
- The existing single-`add_argument` style in `main()`; keep the help
  string short, plain, and consistent with the module docstring.

**Test scenarios:**
- `python table_fmt.py --help` includes `--strip-padding` and its
  description (manual smoke check; no automated test).
- End-to-end stdin → stdout with the flag produces unpadded data rows
  and an unchanged separator (manual smoke check).

**Verification:**
- `--help` output lists the flag with a usable description.
- Running the script with `--strip-padding` against a sample table
  produces the expected unpadded output; running without it produces
  byte-identical output to the prior implementation.

## Risks & Dependencies

- **Round-trip risk.** Stripping the data rows but leaving the separator
  intact preserves markdown validity, but a downstream parser that
  treats the data row as authoritative (rather than the separator) for
  alignment could lose hints. Mitigation: the separator carries the
  alignment colons in both modes, and `parse_table` reads alignment
  exclusively from the separator.
- **Default-byte-identity regression risk.** Any change to the
  `format_row` closure could accidentally alter the padded path.
  Mitigation: keep the stripped branch isolated behind the flag and
  rely on the existing `FormatRowPaddingTests` and `RoundTripTests`
  passing unmodified.

## Documentation / Operational Notes

- Update only the `format_table` docstring and the argparse help text;
  no separate README or runbook exists for this single-file utility.
- After landing, consider adding a short solutions note under
  `docs/solutions/best-practices/` if any non-obvious tradeoff surfaces
  during execution; not required up front.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-25-strip-padding-cli-flag-requirements.md](../brainstorms/2026-04-25-strip-padding-cli-flag-requirements.md)
- Related code: `table_fmt.py` (`format_table`, `main`),
  `test_table_fmt.py` (`FormatSeparatorTests`, `FormatRowPaddingTests`,
  `RoundTripTests`)
- Related issues: #96
- Related learnings: `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
