---
date: 2026-04-26
topic: table-fmt-max-width
---

# table_fmt `--max-width` flag

## Problem Frame

`table_fmt.py` currently pads every column to the width of its widest cell. A
single long cell (a URL, a description paragraph, a stack-trace fragment) blows
the whole table out horizontally and breaks readability in any viewer narrower
than that cell. Users want a way to cap column width without losing the
formatter's column-alignment guarantees.

This is purely a presentation concern for markdown output. `parse_table()` is
unchanged; only `format_table()` learns to truncate.

## Requirements

- **R1.** `python table_fmt.py --max-width N` truncates any column whose
  widest cell exceeds N characters. Columns whose widest cell already fits
  are emitted byte-for-byte as today.
- **R2.** A truncated cell is exactly N characters wide: `N - 3` characters
  of the original content followed by the literal three-character ASCII
  ellipsis `...`.
- **R3.** Without `--max-width`, output is byte-for-byte identical to the
  pre-flag implementation. Adding the flag must not regress existing tests.
- **R4.** `--max-width` accepts a positive integer ≥ 4. Non-integer values,
  zero, negatives, and 1–3 are rejected with a clear stderr message and a
  non-zero exit code. Validation happens before any input is read.
- **R5.** `--help` documents the flag, including the minimum value of 4 and
  the meaning of N (total cell width including the `...` marker).
- **R6.** Truncation applies uniformly to every row, including the header
  row. The separator row is regenerated against the (possibly narrower)
  column widths and continues to honor alignment hints.
- **R7.** Tests in `test_table_fmt.py` cover: basic truncation, mixed
  (some columns truncated, others not), already-short input (no truncation
  occurs), and rejection of invalid `--max-width` values (`0`, `3`, `foo`).

## Success Criteria

- A wide table fed through `--max-width 20` produces an output where every
  column is at most 20 characters wide, with `...` marking truncated cells.
- The existing test suite passes unchanged.
- `--help` output mentions `--max-width N` with the minimum-value constraint.
- Without the flag, `git diff` against pre-change output for the existing
  test fixtures is empty.

## Scope Boundaries

- No multi-line wrapping. Truncation is the only width-reduction behavior.
- No Unicode-aware width handling. Each character counts as width 1.
  (Existing `format_table` already uses `len()` everywhere.)
- No per-column width override syntax (e.g., `--max-width col1=10,col2=20`).
- No changes to `countdown.sh`, `dashboard.html`, or any file other than
  `table_fmt.py` and `test_table_fmt.py`.
- No changes to `parse_table()`. Truncation lives in `format_table()` only.

## Key Decisions

- **D1. Header row is truncated like data rows.** Skipping the header would
  break the column-width contract — `--max-width 20` must mean "no cell
  exceeds 20 chars," and a header row exempt from that rule produces a
  misaligned table where headers overhang their separators. The `...`
  marker makes the truncation honest, and users who choose a tight cap
  have implicitly accepted the readability tradeoff.

- **D2. `N ≤ 3` is rejected, not silently clamped.** The flag's contract is
  "exactly N characters, ending with `...`." That contract is mathematically
  impossible for N ≤ 3. Silent clamping (e.g., to 4) violates the user's
  stated intent; dot-filling produces meaningless output; rendering an
  empty cell hides data. Rejecting at argparse time (with a clear stderr
  message) is the same principle the issue already applies to
  `--max-width foo`. Minimum allowed value: **4**.

- **D3. `--max-width` does not affect `--json` output.** `--max-width` is a
  markdown-formatting concern — column padding only matters for the visual
  table. JSON output is data for downstream consumers; truncating string
  values would silently corrupt that data. When both flags are passed, the
  script emits a single-line stderr warning
  (`warning: --max-width is ignored when --json is set`) and produces
  unmodified JSON. Warning rather than silent-ignore catches user mistakes
  without breaking automation. **Note:** `--json` mode (PR #109) does not
  exist on this branch's base (`master` at d02bb44). The conflict-handling
  logic is only authored if the work phase merges or rebases #109 in;
  otherwise, the test for `--max-width` × `--json` interaction is omitted
  with a brief comment explaining why.

## Dependencies / Assumptions

- The implementation introduces `argparse`. The current `main()` reads
  stdin directly; argparse-driven dispatch is a small refactor but worth
  doing now since R4 requires real CLI validation rather than `sys.argv`
  poking.
- The existing minimum column width of 3 (for separator aesthetics) stays
  in effect for un-truncated columns; truncated columns honor `--max-width`
  exactly, which is always ≥ 4 per D2 and therefore also ≥ 3.

## Outstanding Questions

### Resolve Before Planning

(none — all product decisions are resolved)

### Deferred to Planning

- [Affects R3][Technical] Where in `format_table()` should truncation hook
  in — after column-width computation (modify `col_widths` and rewrite
  cells in place) or as a pre-pass on `rows` before width computation?
  Either works; planning should pick whichever keeps the function
  readable.
- [Affects D3][Technical] If/when `--json` is in scope on this branch,
  does the warning go through `argparse`'s error machinery or a plain
  `print(..., file=sys.stderr)`? Plain print is simpler since the
  combination is allowed, just degraded.

## Next Steps

→ `/ce:plan` for structured implementation planning
