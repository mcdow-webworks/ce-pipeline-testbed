---
date: 2026-04-25
topic: handle-escaped-pipes-in-table-cells
---

# Handle escaped pipes (\|) in markdown table cells

## Problem Frame

`table_fmt.py` splits each table row on every `|` character. Cells that contain
the markdown literal-pipe escape `\|` are silently broken into two cells, so any
user table holding a literal pipe in a cell is corrupted on format. This is the
same class of "structural row carries metadata that the parser drops" mistake
addressed for column alignment in issue #92, applied now to cell-splitting.

## Requirements

- R1. `parse_table` treats `\|` inside a row as a literal pipe belonging to the
  current cell, not as a cell separator. Parsed cell contents have `\|`
  unescaped to `|` so downstream consumers see the logical content.
- R2. `format_table` re-escapes literal `|` characters in cell contents as `\|`
  when emitting markdown, so the output is valid markdown that re-parses to the
  same logical cells (preserves the round-trip fixed point established by
  existing tests).
- R3. Column-width calculation in `format_table` uses the encoded (post-escape)
  cell length, so the rendered markdown source stays visually aligned even when
  a cell contains a literal pipe.
- R4. Existing parse/format/round-trip behavior is unchanged for any cell that
  contains no escaped pipes — including tables with leading/trailing pipes,
  separator rows, alignment hints, and bare-dash separators.

## Success Criteria

- Parsing `| a \| b |` produces a single cell whose content is `a | b`.
- Formatting a table whose cell content is `a | b` produces source containing
  `a \| b`, with column widths that account for the two-character encoding.
- Round-trip is a fixed point: parse → format → parse → format yields identical
  output for tables containing escaped pipes.
- All existing tests in `test_table_fmt.py` pass without modification.
- New tests cover: parse of `\|` in a cell, format-time escaping of literal `|`,
  round-trip stability for an escaped-pipe table.

## Scope Boundaries

- Out of scope: general markdown backslash-escape handling (`\*`, `\_`, `\#`,
  etc.). Only `\|` is interpreted; other backslash sequences pass through cell
  content verbatim. A table formatter is not a markdown renderer.
- Out of scope: alternative pipe-escaping conventions (HTML entities like
  `&#124;`, Unicode lookalikes, fenced inline code spans).
- Out of scope: changing the public return shape of `parse_table` or
  `format_table`. The fix is contained to splitting/escaping logic.

## Key Decisions

- **Splitter treats every `\X` as a 2-character unit, but only `\|` unescapes
  to `|` in cell content.** Why: this correctly handles `\\|` (an escaped
  backslash followed by a real separator) without expanding scope to full
  markdown unescaping. A naive `re.split(r"(?<!\\)\|", ...)` gets `\\|` wrong;
  a tiny character-by-character scan is just as short and right.
- **`format_table` escapes only `|`, not `\` itself.** Why: cell contents in
  `rows` may legitimately contain literal backslashes (paths, regex, code
  fragments). Only `|` is structurally significant to the table grammar and
  needs to be escaped on emit. Escaping `\` would silently rewrite user data.
- **Width is computed from the encoded form.** Why: the markdown source has to
  line up visually; using the unescaped length would produce misaligned pipes
  whenever a cell contains a literal `|`. Doing this once, in `format_table`,
  keeps the change local.

## Dependencies / Assumptions

- Self-contained change. No external callers beyond `main()` in this file and
  `test_table_fmt.py` consume `parse_table` / `format_table` (verified via repo
  scan). No public API shape change is required.

## Outstanding Questions

### Resolve Before Planning
(none)

### Deferred to Planning
(none)

## Next Steps

→ `/ce:plan` for structured implementation planning.
