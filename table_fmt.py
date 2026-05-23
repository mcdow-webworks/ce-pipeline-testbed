#!/usr/bin/env python3
"""Markdown table formatter — reads sloppy tables from stdin, outputs aligned columns."""

import argparse
import json
import re
import sys


_YAML_NEEDS_QUOTE_START = frozenset(':!@%&*?|>\'"#-{[`')
_YAML_BOOL_NULL = frozenset([
    'true', 'false', 'null', '~', 'yes', 'no', 'on', 'off',
    # YAML 1.1 special float forms that Python's float() does not parse
    '.inf', '+.inf', '-.inf', '.nan', '+.nan', '-.nan',
])
# YAML 1.1 bare-zero octals (e.g. 077 → 63). Python 3 rejects int('077', 0),
# so the numeric guard below does not catch them; a dedicated regex is required.
_YAML_BARE_OCTAL = re.compile(r'^0[0-7]+$')


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


def _is_empty_row(cells):
    """Return True when every cell in the row is empty or whitespace-only.

    Whitespace is defined by Python's default ``str.strip()``, which strips
    characters where ``str.isspace()`` is True. That covers ASCII whitespace,
    non-breaking space (U+00A0), and full-width space (U+3000). Zero-width
    characters such as U+200B do not count as whitespace and a row of them is
    treated as non-empty. This matches the trimming convention already used
    by ``parse_table``.
    """
    return all(not cell.strip() for cell in cells)


def _strip_empty_rows(rows):
    """Return ``rows`` with all-empty data rows removed; the header is preserved.

    ``rows[0]`` is treated as the header (matching ``format_table``'s
    convention) and is never stripped, even when every cell is empty — the
    operator may intentionally be building a header-only table for downstream
    consumers. The markdown separator row is consumed by ``parse_table`` and
    never appears in ``rows``, so it cannot be stripped.

    Applied before ``format_table``'s column-count normalization so the
    predicate sees the cells the user actually wrote, not padding we added.
    """
    if not rows:
        return rows
    header, *data = rows
    return [header] + [row for row in data if not _is_empty_row(row)]


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
    if not rows:
        raise ValueError(
            "--json requires a non-empty rows list (no header row)"
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


def _yaml_scalar(value):
    """Return a YAML-safe plain or single-quoted scalar for a string value.

    Single-quotes are used when the value is empty, starts with a
    YAML-special character, matches a boolean/null keyword, contains
    inline-comment or mapping-indicator sequences, or would be parsed as a
    number by a YAML parser.  Single quotes inside the value are doubled
    (the standard YAML escape for single-quoted scalars).
    """
    if not value:
        return "''"
    needs_quote = (
        value[0] in _YAML_NEEDS_QUOTE_START
        or value.lower() in _YAML_BOOL_NULL
        or ": " in value
        or value.endswith(":")
        or " #" in value
        or value != value.strip()
    )
    if not needs_quote:
        # YAML 1.1 bare-zero octals (077, 010…). Python 3 rejects int('077',0)
        # so they would escape the numeric guard below without this explicit check.
        if _YAML_BARE_OCTAL.match(value):
            needs_quote = True
        else:
            try:
                # base=0 catches 0x.../0o.../0b... prefixes that YAML 1.1 parsers
                # interpret as integers (e.g. 0xff → 255)
                int(value, 0)
                needs_quote = True
            except ValueError:
                try:
                    float(value)
                    needs_quote = True
                except ValueError:
                    pass
    if needs_quote:
        return "'" + value.replace("'", "''") + "'"
    return value


def format_yaml(rows, alignments):
    """Return a YAML document of row objects keyed by the header row.

    The first row is the header; remaining rows are emitted as a block-style
    YAML list of mappings (one key per line). Header-only or empty-data input
    emits ``'[]\\n'``. Requires a separator row (``alignments`` non-empty) to
    identify the header row; raises ``ValueError`` when missing or when header
    column names are not unique.
    """
    if not alignments:
        raise ValueError(
            "--yaml requires a header row (no separator row found in input)"
        )
    if not rows:
        raise ValueError(
            "--yaml requires a non-empty rows list (no header row)"
        )

    header = rows[0]
    seen = set()
    for name in header:
        if name in seen:
            raise ValueError(
                f"--yaml requires unique header column names; duplicate header: '{name}'"
            )
        seen.add(name)

    data_rows = rows[1:]
    if not data_rows:
        return "[]\n"

    lines = []
    for row in data_rows:
        for i, key in enumerate(header):
            cell = row[i] if i < len(row) else ""
            prefix = "- " if i == 0 else "  "
            lines.append(f"{prefix}{_yaml_scalar(key)}: {_yaml_scalar(cell)}")

    return "\n".join(lines) + "\n"


def main(argv=None):
    """Read a markdown table from stdin, format it, and print to stdout.

    Default mode emits a re-aligned markdown table. With ``--json`` or
    ``--yaml``, emits structured data keyed by the header row instead.
    ``--json`` and ``--yaml`` are mutually exclusive.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Format markdown tables from stdin. Default output is a re-aligned "
            "markdown table. Use --json or --yaml to emit structured data instead."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit parsed table as a JSON array of row objects keyed by header",
    )
    parser.add_argument(
        "--yaml",
        action="store_true",
        help="emit parsed table as a YAML list of row mappings keyed by header",
    )
    parser.add_argument(
        "--strip-empty-rows",
        action="store_true",
        help="drop data rows whose cells are all empty or whitespace-only "
        "before rendering. The header row is preserved even when every "
        "cell is empty.",
    )
    args = parser.parse_args(argv)

    if args.json and args.yaml:
        print("Error: --json and --yaml are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    text = sys.stdin.read()
    rows, alignments = parse_table(text)
    if not rows:
        print("Error: no valid markdown table found in input", file=sys.stderr)
        sys.exit(1)

    if args.strip_empty_rows:
        rows = _strip_empty_rows(rows)

    if args.json:
        try:
            output = format_json(rows, alignments)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        sys.stdout.write(output)
        return

    if args.yaml:
        try:
            output = format_yaml(rows, alignments)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        sys.stdout.write(output)
        return

    sys.stdout.write(format_table(rows, alignments))


if __name__ == "__main__":
    main()
