#!/usr/bin/env python3
"""Markdown table formatter — reads sloppy tables from stdin, outputs aligned columns."""

import argparse
import sys


# Truncation marker and the smallest --max-width value that leaves room for
# at least one content character before the marker. _MIN_MAX_WIDTH derives
# from len(_ELLIPSIS) so the relationship is self-correcting if the marker
# ever changes (e.g. to a single-char Unicode ellipsis).
_ELLIPSIS = "..."
_MIN_MAX_WIDTH = len(_ELLIPSIS) + 1


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
        # Split on pipes, drop the empty first/last elements from leading/trailing |
        cells = stripped.split("|")
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


def format_table(rows, alignments=None, max_width=None):
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

    ``max_width`` is an optional positive integer (``>= _MIN_MAX_WIDTH``,
    currently 4). When set, any column whose widest cell exceeds it is
    truncated to exactly ``max_width`` characters: ``max_width - len(_ELLIPSIS)``
    characters of the original content followed by the literal ASCII ellipsis
    ``...``. Columns whose widest cell already fits are emitted unchanged.
    Header rows truncate the same as data rows so the column-width contract
    holds end-to-end.
    """
    if not rows:
        return ""

    if alignments is None:
        alignments = []

    # Normalise column count to the maximum across all rows
    num_cols = max(len(row) for row in rows)
    normalised = [row + [""] * (num_cols - len(row)) for row in rows]

    # Per-column truncation pre-pass. The CLI validator guarantees
    # max_width >= _MIN_MAX_WIDTH so cell[:keep] always leaves at least one
    # content character before the ellipsis. Columns whose widest cell
    # already fits inside max_width are skipped entirely so their bytes are
    # identical to the no-flag path.
    if max_width is not None:
        keep = max_width - len(_ELLIPSIS)
        for col in range(num_cols):
            widest = max(len(row[col]) for row in normalised)
            if widest <= max_width:
                continue
            for r, row in enumerate(normalised):
                cell = row[col]
                if len(cell) > max_width:
                    normalised[r][col] = cell[:keep] + _ELLIPSIS

    # Compute column widths (minimum 3 for separator aesthetics)
    col_widths = []
    for col in range(num_cols):
        width = max((len(row[col]) for row in normalised), default=3)
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

    lines = [format_row(normalised[0])]
    sep_cells = [separator_cell(col_widths[i], align_for(i)) for i in range(num_cols)]
    lines.append("| " + " | ".join(sep_cells) + " |")
    for row in normalised[1:]:
        lines.append(format_row(row))

    return "\n".join(lines) + "\n"


def _validate_max_width(value):
    """Argparse ``type=`` validator for ``--max-width``.

    Accepts only string forms of positive integers ``>= _MIN_MAX_WIDTH`` and
    returns the int. Raises ``argparse.ArgumentTypeError`` otherwise —
    argparse turns that into a stderr message + exit code 2 before stdin is
    read. The minimum is the smallest value where the contract "exactly N
    chars ending in '...'" leaves room for at least one content character.
    """
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--max-width must be an integer; got {value!r}"
        )
    if n < _MIN_MAX_WIDTH:
        raise argparse.ArgumentTypeError(
            f"--max-width must be a positive integer >= {_MIN_MAX_WIDTH}; got {n}"
        )
    return n


def main():
    """Read a markdown table from stdin, format it, and print to stdout."""
    parser = argparse.ArgumentParser(
        description=(
            "Format a markdown table read from stdin and write the aligned "
            "result to stdout."
        ),
    )
    parser.add_argument(
        "--max-width",
        type=_validate_max_width,
        default=None,
        metavar="N",
        help=(
            f"Cap each column's width at N characters (minimum {_MIN_MAX_WIDTH}). "
            f"Cells longer than N are truncated to (N-{len(_ELLIPSIS)}) characters "
            f"of original content followed by {_ELLIPSIS!r}, so the truncated "
            "cell's total width is exactly N. Header rows truncate the same as "
            "data rows. Without this flag, output is byte-for-byte identical to "
            "the pre-flag implementation."
        ),
    )
    args = parser.parse_args()

    text = sys.stdin.read()
    rows, alignments = parse_table(text)
    if not rows:
        print("Error: no valid markdown table found in input", file=sys.stderr)
        sys.exit(1)
    sys.stdout.write(format_table(rows, alignments, max_width=args.max_width))


if __name__ == "__main__":
    main()
