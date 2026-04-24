---
title: table_fmt silently discards markdown column-alignment hints
date: 2026-04-24
category: logic-errors
module: table_fmt
problem_type: logic_error
component: tooling
symptoms:
  - Output table left-justifies every column regardless of input hints
  - ":---", "---:", ":---:" markers in the separator row are erased on format
  - Piping a formatted table through the tool twice is not idempotent for aligned tables
root_cause: logic_error
resolution_type: code_fix
severity: low
tags:
  - markdown
  - table
  - alignment
  - cli
  - formatting
---

# table_fmt silently discards markdown column-alignment hints

## Problem

`table_fmt.py` always left-justified every column and emitted a plain `---` separator, ignoring the per-column alignment syntax defined by markdown (`:---` left, `---:` right, `:---:` center). Users who ran an aligned table through the formatter lost their alignment on the first pass.

## Symptoms

- A table with `| :--- | ---: | :---: |` as its separator row came back with `| --- | --- | --- |` and every cell left-padded
- Round-tripping `format -> parse -> format` was not a fixed point for aligned tables
- No error raised — the alignment information was silently dropped

## What Didn't Work

- The pre-existing `parse_table` skipped the separator row entirely, so the alignment hints never reached `format_table`. Any fix that only touched `format_table` would have nothing to align *to* — the hints had to be carried forward from parsing before the output stage could use them.

## Solution

Thread per-column alignment from `parse_table` through to `format_table`, add a small helper to read colon placement, and branch on alignment in both the separator-cell emitter and the data-cell padder.

**Signature change — `parse_table` now returns a tuple:**

```python
def parse_table(text):
    """Parse a markdown table string into (rows, alignments)."""
    rows = []
    alignments = []
    separator_seen = False
    for line in text.strip().splitlines():
        # ...
        if all(c.strip().replace("-", "").replace(":", "") == "" for c in cells):
            if not separator_seen:
                alignments = [_parse_alignment(c.strip()) for c in cells]
                separator_seen = True
            continue
        rows.append([c.strip() for c in cells])
    return rows, alignments
```

**New helper — reads colon placement:**

```python
def _parse_alignment(cell):
    """Return 'left', 'right', 'center', or None from a separator cell."""
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
```

`None` is kept distinct from `'left'` so a plain `---` input round-trips as `---`, not `:---`.

**`format_table` now accepts an optional alignments list and branches on it for both separator and data cells:**

```python
def pad_cell(text, width, align):
    if align == "right":
        return text.rjust(width)
    if align == "center":
        return text.center(width)
    return text.ljust(width)

def separator_cell(width, align):
    if align == "center":
        return ":" + "-" * (width - 2) + ":"
    if align == "right":
        return "-" * (width - 1) + ":"
    if align == "left":
        return ":" + "-" * (width - 1)
    return "-" * width
```

A shorter `alignments` list is tolerated — missing trailing entries fall back to `None` (plain dash, left-pad), preserving the prior behavior when callers pass no alignment at all.

## Why This Works

The separator row is the only place markdown encodes per-column alignment, so the parser is the single upstream source of truth. Previously, that signal was thrown away on line 52 of the old `parse_table` (the row was detected and skipped without inspection). By capturing the colon pattern at parse time and passing a parallel `alignments` list alongside `rows`, the format stage can make a per-column decision for both the separator marker and the data-cell justifier. Keeping `None` distinct from `'left'` avoids silently upgrading `---` inputs to `:---` outputs, which matters for idempotency: formatting twice produces identical output.

## Prevention

- **Round-trip tests for any formatter.** The regression would have been caught immediately by a test that parses, formats, parses again, and asserts the two parses agree. `test_table_fmt.py::RoundTripTests::test_mixed_alignments_round_trip` now enforces this.
- **When "skipping" a structural row in a parser, check whether it carries metadata first.** The separator row is a classic example — it looks like a delimiter but encodes alignment. A comment like `# Separator row — alignment hints read above` near any `continue` on structural rows makes the intent explicit.
- **Prefer `None` over a default string for "unspecified" in optional metadata.** It keeps defaults idempotent and makes "input said nothing" distinguishable from "input explicitly said the default".
- **When broadening a function's return shape (single value -> tuple), grep every call site before editing.** For this change: `grep -rn "parse_table(" .` confirmed only `main()` and the test file unpacked the return, so the tuple change was safe.

Test patterns worth replicating:

```python
# Parse-level coverage
def test_parses_mixed_alignments(self):
    rows, alignments = parse_table("| A | B | C |\n| :--- | ---: | :---: |\n| 1 | 2 | 3 |\n")
    self.assertEqual(alignments, ["left", "right", "center"])

# Format-level coverage
def test_right_aligned_cells_use_rjust(self):
    out = format_table([["Header"], ["x"]], ["right"])
    self.assertEqual(out.splitlines()[2], "|      x |")

# Round-trip (fixed point)
def test_mixed_alignments_round_trip(self):
    rows, aligns = parse_table(ORIGINAL)
    once = format_table(rows, aligns)
    rows2, aligns2 = parse_table(once)
    self.assertEqual(format_table(rows2, aligns2), once)
```

## Related Issues

- GitHub issue #92 — Respect markdown column-alignment syntax in the separator row
- Commits: `7443f54` (feat), `5605c07` (work-phase doc), `db88e9c` (ce-review autofix)
