#!/usr/bin/env python3
"""Markdown table formatter — reads sloppy tables from stdin, outputs aligned columns."""

import sys


def parse_table(text):
    """Parse a markdown table string into a list of rows (each row is a list of cell strings).

    Strips leading/trailing whitespace from each cell. Skips the separator row
    (the row containing only dashes, pipes, and colons).
    """
    rows = []
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
            continue
        rows.append([c.strip() for c in cells])
    return rows


def format_table(rows):
    """Return a formatted markdown table string with columns padded to equal width.

    The first row is treated as the header. A separator row of dashes is inserted
    after the header. All columns are padded to the width of the longest cell
    in that column (minimum width 3).
    """
    if not rows:
        return ""

    # Normalise column count to the maximum across all rows
    num_cols = max(len(row) for row in rows)
    normalised = [row + [""] * (num_cols - len(row)) for row in rows]

    # Compute column widths (minimum 3 for separator aesthetics)
    col_widths = []
    for col in range(num_cols):
        width = max((len(normalised[r][col]) for r in range(len(normalised))), default=3)
        col_widths.append(max(width, 3))

    def format_row(cells):
        padded = [cells[i].ljust(col_widths[i]) for i in range(num_cols)]
        return "| " + " | ".join(padded) + " |"

    lines = [format_row(normalised[0])]
    # Separator row
    sep_cells = ["-" * col_widths[i] for i in range(num_cols)]
    lines.append("| " + " | ".join(sep_cells) + " |")
    # Data rows
    for row in normalised[1:]:
        lines.append(format_row(row))

    return "\n".join(lines) + "\n"


def main():
    """Read a markdown table from stdin, format it, and print to stdout."""
    text = sys.stdin.read()
    rows = parse_table(text)
    if not rows:
        print("Error: no valid markdown table found in input", file=sys.stderr)
        sys.exit(1)
    sys.stdout.write(format_table(rows))


if __name__ == "__main__":
    main()
