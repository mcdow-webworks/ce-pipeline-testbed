#!/usr/bin/env python3
"""Markdown table formatter — reads sloppy tables from stdin, outputs aligned columns."""

import sys


def _parse_alignment(cell):
    """Return 'left', 'right', 'center', or None from a separator cell.

    Returns ``None`` (not ``'left'``) when the cell has no colons, so
    ``format_table`` can emit a plain ``---`` separator and preserve the
    input's bare-dash style across a round trip.
    """
    if not cell:
        return None
    starts = cell.startswith(":")
    ends = cell.endswith(":")
    if starts and ends:
        return "center"
    if ends:
        return "right"
    if starts:
        return "left"
    return None


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


def parse_table(text):
    """Parse a markdown table string into ``(rows, alignments)``.

    ``rows`` is a list of rows (each a list of stripped cell strings).
    ``alignments`` is a list of ``'left'``, ``'right'``, ``'center'``, or ``None``
    per column, read from the separator row. Empty list when no separator row
    is present. Only the first separator row contributes alignment; any
    additional separator-like rows are still skipped.
    """
    rows = []
    alignments = []
    separator_seen = False
    for line in text.strip().splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # Split on pipes (treating \| as a literal pipe), drop the empty
        # first/last elements from leading/trailing |.
        cells = _split_cells(stripped)
        if cells and cells[0].strip() == "":
            cells = cells[1:]
        if cells and cells[-1].strip() == "":
            cells = cells[:-1]
        if not cells:
            continue
        # Check if this is a separator row (all cells are just dashes/colons)
        if all(c.strip().replace("-", "").replace(":", "") == "" for c in cells):
            if not separator_seen:
                alignments = [_parse_alignment(c.strip()) for c in cells]
                separator_seen = True
            continue
        rows.append([c.strip() for c in cells])
    return rows, alignments


def format_table(rows, alignments=None):
    """Return a formatted markdown table string with columns padded to equal width.

    The first row is treated as the header. A separator row is inserted after the
    header; its cells carry colon markers that reflect ``alignments`` when
    provided. Columns are padded to the width of the longest cell (minimum 3).

    ``alignments`` is an optional list of ``'left'``, ``'right'``, ``'center'``,
    or ``None`` per column. ``None`` (and any missing entries) defaults to
    left-padding with a plain dash separator, matching prior behavior. An
    ``alignments`` list shorter than the number of columns is allowed; missing
    trailing entries fall back to the ``None`` default. Extra entries beyond
    the column count are ignored.
    """
    if not rows:
        return ""

    if alignments is None:
        alignments = []

    # Normalise column count to the maximum across all rows
    num_cols = max(len(row) for row in rows)
    normalised = [row + [""] * (num_cols - len(row)) for row in rows]

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

    def align_for(i):
        return alignments[i] if i < len(alignments) else None

    def pad_cell(text, width, align):
        if align == "right":
            return text.rjust(width)
        if align == "center":
            return text.center(width)
        return text.ljust(width)

    def format_row(cells):
        padded = [pad_cell(cells[i], col_widths[i], align_for(i)) for i in range(num_cols)]
        return "| " + " | ".join(padded) + " |"

    def separator_cell(width, align):
        if align == "center":
            return ":" + "-" * (width - 2) + ":"
        if align == "right":
            return "-" * (width - 1) + ":"
        if align == "left":
            return ":" + "-" * (width - 1)
        return "-" * width

    lines = [format_row(encoded[0])]
    sep_cells = [separator_cell(col_widths[i], align_for(i)) for i in range(num_cols)]
    lines.append("| " + " | ".join(sep_cells) + " |")
    for row in encoded[1:]:
        lines.append(format_row(row))

    return "\n".join(lines) + "\n"


def main():
    """Read a markdown table from stdin, format it, and print to stdout."""
    text = sys.stdin.read()
    rows, alignments = parse_table(text)
    if not rows:
        print("Error: no valid markdown table found in input", file=sys.stderr)
        sys.exit(1)
    sys.stdout.write(format_table(rows, alignments))


if __name__ == "__main__":
    main()
