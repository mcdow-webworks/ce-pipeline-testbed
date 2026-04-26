#!/usr/bin/env python3
"""Markdown table formatter — reads sloppy tables from stdin, outputs aligned columns."""

import argparse
import json
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

    # Compute column widths (minimum 3 for separator aesthetics)
    col_widths = []
    for col in range(num_cols):
        width = max((len(normalised[r][col]) for r in range(len(normalised))), default=3)
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


def format_json(rows, alignments):
    """Return a JSON string of row objects keyed by the header row.

    The first row is the header; remaining rows are emitted as objects mapping
    each header cell text to the corresponding cell text. All values are
    strings — no type coercion. Output is pretty-printed with ``indent=2`` and
    terminated with a single trailing newline; non-ASCII cell text is preserved
    literally rather than escaped. Per-column ``alignments`` metadata has no
    JSON representation and is intentionally dropped from the output, but the
    list itself is consulted to detect whether the parser saw a separator row.

    Preconditions: ``rows`` is non-empty (caller should have already errored on
    no-table input). Raises ``ValueError`` when ``alignments`` is empty (no
    separator row, so the header is unidentified) or when ``rows[0]`` contains
    duplicate cell text (header keys would collide).
    """
    if not alignments:
        raise ValueError(
            "--json requires a header row (no separator row found in input)"
        )

    header = rows[0]
    seen = set()
    for name in header:
        if name in seen:
            raise ValueError(
                f"--json requires unique header column names; duplicate header: '{name}'"
            )
        seen.add(name)

    payload = [dict(zip(header, row)) for row in rows[1:]]
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main(argv=None):
    """Read a markdown table from stdin, format it, and print to stdout.

    Default mode emits a re-aligned markdown table (byte-for-byte identical to
    the pre-flag implementation). With ``--json``, emits a JSON array of row
    objects keyed by the header row instead.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Format markdown tables from stdin. Without --json, output a "
            "re-aligned markdown table. With --json, output an array of row "
            "objects keyed by header."
        )
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit parsed table as JSON instead of markdown",
    )
    args = parser.parse_args(argv)

    text = sys.stdin.read()
    rows, alignments = parse_table(text)
    if not rows:
        print("Error: no valid markdown table found in input", file=sys.stderr)
        sys.exit(1)

    if args.json:
        try:
            output = format_json(rows, alignments)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        sys.stdout.write(output)
        return

    sys.stdout.write(format_table(rows, alignments))


if __name__ == "__main__":
    main()
