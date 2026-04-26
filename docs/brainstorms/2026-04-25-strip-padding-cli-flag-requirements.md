---
date: 2026-04-25
topic: strip-padding-cli-flag
---

# Add `--strip-padding` CLI flag to `table_fmt.py`

## Problem Frame

`table_fmt.py` always pads data-row cells with surrounding whitespace for visual
alignment (`| a | b |`). Some downstream consumers — CSV converters, plain-text
post-processors, naive splitters — prefer cells without the alignment padding.
Today these consumers have to run a separate strip pass; we want a single
opt-in flag at format time.

## Requirements

- R1. `table_fmt.py` accepts a `--strip-padding` argparse flag. When present,
  data rows (header + body) are emitted with no whitespace between the pipes
  and the cell content, e.g. `|a|b|` instead of `| a | b |`.
- R2. The separator row is emitted unchanged when `--strip-padding` is set —
  same dash count, same colon markers, same surrounding spaces (`| --- | --- |`,
  `| :-- | --: |`, etc.) — so the output remains valid markdown that re-parses
  to the same logical table.
- R3. Default behavior (flag absent) is byte-identical to current output. No
  existing test changes required.
- R4. `python table_fmt.py --help` lists `--strip-padding` with a short
  description.

## Success Criteria

- With flag on input `| a | b |\n| --- | --- |\n| x | y |\n`: data rows
  collapse to `|a|b|` and `|x|y|`; separator row stays `| --- | --- |`.
- Without flag: output is identical to the pre-change implementation
  (verified by all existing tests passing unmodified).
- New tests cover: stripped data rows, separator unchanged across flag states,
  alignment colons preserved on separator under stripping, default false
  matches explicit false.

## Scope Boundaries

- Out of scope: stripping whitespace *inside* a cell (e.g., `"hello world"` is
  not modified; only the padding between pipes and content is removed).
- Out of scope: a separate flag to also collapse the separator row. The issue
  explicitly keeps the separator intact for markdown round-trip safety.
- Out of scope: changing `parse_table` behavior. Strip-padding is an emit-only
  choice; parsing already strips cells.
- Out of scope: short flag alias (e.g., `-s`). Adds carrying cost (collision
  surface) without enough demand signal.

## Key Decisions

- **Flag affects `format_table`, not `parse_table`.** Why: parsing already
  strips cells; the asymmetry only exists at emit time. Threading a
  `strip_padding` keyword arg through `format_table` keeps the change local
  and keeps `parse_table` untouched.
- **Separator row keeps its existing form when stripping.** Why: the issue's
  acceptance is explicit ("separator unchanged"). Collapsing the separator
  would also lose the alignment colons' meaningful spacing and would risk
  ambiguity with header-less tables under some markdown parsers.
- **No padding ⇒ no alignment.** Why: alignment is implemented as ljust/rjust/
  center inside cell padding. With padding stripped, alignment becomes a
  no-op for data rows. The separator still carries the alignment hint via
  colons, so re-parsing recovers it.

## Dependencies / Assumptions

- Only `main()` and `test_table_fmt.py` consume `format_table` (verified via
  repo scan). Adding an optional keyword argument is a non-breaking change.

## Outstanding Questions

### Resolve Before Planning
(none)

### Deferred to Planning
(none)

## Next Steps

→ `/ce:plan` for structured implementation planning, or proceed directly
   to `/ce:work` since scope is lightweight and acceptance criteria are
   already concrete.
