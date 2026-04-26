---
title: table_fmt splits cells on every `|`, corrupting cells that contain an escaped pipe
date: 2026-04-25
category: logic-errors
module: table_fmt
problem_type: logic_error
component: tooling
symptoms:
  - A cell containing `\|` is silently broken into two cells on parse
  - Round-tripping a table whose cell content includes a literal pipe corrupts the table
  - No error raised — cell content is silently split and column count expands
related_components:
  - testing_framework
root_cause: logic_error
resolution_type: code_fix
severity: low
tags:
  - markdown
  - table
  - escape
  - pipe
  - cli
  - formatting
  - round-trip
---

# table_fmt splits cells on every `|`, corrupting cells that contain an escaped pipe

## Problem

`table_fmt.py` parsed each table row with `stripped.split("|")`, so a cell whose content contained the markdown literal-pipe escape `\|` was silently broken into two cells. The bug widened the row's column count and produced an unrelated, mis-aligned table after a single format pass.

## Symptoms

- A row like `| Alice | a \| b |` parsed as three data cells (`Alice`, `a \`, `b`) instead of two (`Alice`, `a | b`)
- Format → parse → format was not a fixed point for any table containing `\|` in cell content
- No error raised — the formatter happily padded the corrupted columns and emitted what looked like a valid table

## What Didn't Work

- **Regex-based split with a "not preceded by backslash" lookbehind** (`re.split(r"(?<!\\)\|", row)`). It looks right at first glance but mishandles `\\|` — escaped backslash immediately before a real separator — by treating the second `\` as escaping the `|`. Any cell whose author meant "literal `\` at end of cell" would be wrongly merged with the next cell.
- **Escape-only-on-format with naive split-on-format**. Re-escaping `|` to `\|` in `format_table` while leaving `parse_table` unchanged would fix the visual symptom for the immediate write-and-re-read cycle but still corrupt any input that already contained `\|`. The fix has to start at parse-time.
- **Re-escaping `\` itself on format**. Tempting for symmetry, but corrupts cells whose logical content really is a single `\` (paths, regex fragments, code snippets). Only `|` is structurally significant to the table grammar, so only `|` is encoded on emit.

## Solution

Two changes in `table_fmt.py` and a battery of tests in `test_table_fmt.py`. Public signatures of `parse_table` and `format_table` are unchanged.

**New private helper — escape-aware row splitter:**

```python
def _split_cells(row):
    r"""Split a row string on bare ``|``, treating ``\|`` as a literal pipe.

    Walks the string character by character so each ``\X`` is consumed as a
    two-character unit: ``\|`` unescapes to ``|`` inside the current cell,
    every other ``\X`` passes through verbatim, and a lone trailing ``\``
    stays in the current cell. A bare ``|`` flushes the current cell.

    Returns the same outer shape ``str.split("|")`` did, including the empty
    leading and trailing entries produced by ``| ... |`` borders, so callers
    don't need to change their trim logic.

    Implementation note: do not "simplify" this with ``re.split(r"(?<!\\)\|",
    ...)`` — that pattern misclassifies ``\\|`` (escaped backslash followed
    by a real separator) by treating the second ``\`` as escaping the ``|``.
    """
    cells = []
    buf = []
    i = 0
    n = len(row)
    while i < n:
        ch = row[i]
        if ch == "\\" and i + 1 < n:
            nxt = row[i + 1]
            if nxt == "|":
                buf.append("|")
            else:
                buf.append(ch)
                buf.append(nxt)
            i += 2
        elif ch == "|":
            cells.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(ch)
            i += 1
    cells.append("".join(buf))
    return cells
```

**`parse_table` — single-line wiring change:**

```python
# Split on pipes (treating \| as a literal pipe), drop the empty
# first/last elements from leading/trailing |.
cells = _split_cells(stripped)
```

The leading/trailing empty-cell trim and the separator-row detection downstream of the split are unchanged — `_split_cells` returns the same outer shape `str.split("|")` did.

**`format_table` — encode `|` once, drive both width and emit from the encoded view:**

```python
# Encode literal pipes in cell content (| -> \|). Only `|` is structurally
# significant to the table grammar; `\` is intentionally not re-escaped so
# cells whose content really is a single `\` (paths, regex, code) survive.
encoded = [[cell.replace("|", "\\|") for cell in row] for row in normalised]

# Compute column widths from the encoded form so visual alignment holds
# when a cell contains a literal `|` (encoded form is one char longer).
col_widths = []
for col in range(num_cols):
    width = max((len(encoded[r][col]) for r in range(len(encoded))), default=3)
    col_widths.append(max(width, 3))
```

`format_row` is then driven from `encoded` instead of `normalised`. The bordering `| ` and ` | ` produced by `format_row` are never rewritten — only cell *contents* are encoded.

## Why This Works

The table grammar's only structural delimiter is `|`. Markdown's literal-pipe escape is `\|`. So `|` and `\|` are two different tokens, and the parser has to distinguish them token-by-token — `str.split("|")` cannot, because the only signal that `|` is escaped is the character before it, which `split` does not see. The char-by-char splitter consumes any `\X` as a two-character unit, which is what makes it robust on the adversarial `\\|` case (escaped backslash followed by a real separator): the first `\\` is consumed as a 2-char unit and the next `|` is recognized as a real delimiter. A lookbehind regex makes the wrong call there.

On emit, only `|` is encoded. Re-escaping `\` would silently rewrite cell content for any user whose data legitimately contains a backslash, breaking R4 (no regression for non-`\|` tables). And the encoded view is what drives column-width math — using the logical (decoded) length would misalign every column whose data cells contained a literal `|`, since the encoded form is always at least one character longer per `|`.

The result is a parse → format → parse → format fixed point: each cell's logical content is the same after every round trip, and the rendered byte-for-byte output is identical from the second format onward.

## Prevention

- **When splitting on a structural delimiter, check whether it can be escaped first.** This is the cell-split twin of the alignment-row lesson from #92: structural punctuation often carries adjacent metadata (alignment hints, escape sequences) that a naive `split` discards. If your input language has any backslash-escape convention at all, `str.split` is almost certainly wrong — even when the immediate test inputs don't exercise it.
- **Round-trip fixed-point tests catch this entire class of regression.** A test that does `parse → format → parse → format` and asserts the second format equals the first is the strongest single test you can add to a formatter. It would have caught the original bug on the first table containing `\|`. `test_table_fmt.py::EscapedPipeTests::test_round_trip_fixed_point_with_escaped_pipe` enforces this for the escaped-pipe case.
- **Don't reach for `(?<!\\)\|`.** It is the obvious-looking regex for "pipe not preceded by backslash" and it is wrong on `\\|`. The `_split_cells` docstring calls this out at the top so the next contributor sees the trap before re-implementing it. If you must use a regex, the safe pattern is to consume `\X` greedily as a two-char unit (e.g., `re.findall(r"\\.|[^|]|\|", row)` driven through a small state machine) — but the char-by-char loop is shorter and clearer.
- **Encode for emit only what is structurally significant.** A formatter is not a markdown renderer. Other escape sequences (`\*`, `\_`, `\#`) belong to inline markdown spans, not to the table grammar — leave them alone. Only `|` is meaningful at the table layer, so only `|` is encoded on emit and only `\|` is decoded on parse.
- **Compute visual widths from the encoded form, not the logical form.** Any field that gets re-encoded between parse and emit (escape sequences, HTML entities, ANSI sequences) needs the same treatment. The width math runs after the encoding step, on the bytes that are about to hit the output, so the columns line up.

Test patterns worth replicating:

```python
# Splitter-level: pin the adversarial escape cases the regex would miss
def test_escaped_backslash_then_separator(self):
    # `| a \\| b |` — escaped backslash followed by a real separator.
    # The naive (?<!\\)\| regex misclassifies this case.
    self.assertEqual(_split_cells(r"| a \\| b |"), ["", r" a \\", " b ", ""])

def test_lone_trailing_backslash_stays_in_cell(self):
    # Trailing `\` with no following char must not read out of range.
    self.assertEqual(_split_cells("| foo \\"), ["", " foo \\"])

# Format-level: width is driven by the encoded length
def test_format_width_uses_encoded_form(self):
    out = format_table([["x"], ["a | b"]])
    lines = out.splitlines()
    self.assertEqual(lines[1], "| ------ |")  # 6 dashes, not 5
    self.assertEqual(lines[2], r"| a \| b |")

# Round-trip fixed point — the strongest single regression net
def test_round_trip_fixed_point_with_escaped_pipe(self):
    rows, aligns = parse_table(ORIGINAL_WITH_ESCAPED_PIPE)
    once = format_table(rows, aligns)
    rows2, aligns2 = parse_table(once)
    twice = format_table(rows2, aligns2)
    self.assertEqual(once, twice)
```

## Related Issues

- GitHub issue #94 — Handle escaped pipes (`\|`) in markdown table cells (this work)
- GitHub issue #92 — Respect markdown column-alignment syntax in the separator row (prior fix, same module, same class of "parser drops structural metadata" bug)
- Prior solution doc: `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
- Plan: `docs/plans/2026-04-25-001-fix-escaped-pipes-in-table-cells-plan.md`
- Commits: `8527cac` (fix), `7c2ad50` (ce-review autofix — pinning tests for `\|`-only cell, multi-`\|`-per-cell, alignment + `\|`)
