---
title: Strip-padding CLI flag for table_fmt without breaking the separator row
date: 2026-04-25
category: best-practices
module: table_fmt
problem_type: best_practice
component: tooling
symptoms:
  - Downstream CSV converters and plain-text consumers received padded markdown cells (`| a | b |`) and had to strip whitespace post-hoc
  - No CLI flag existed to opt into a compact `|a|b|` cell style
  - Adding such a flag risked corrupting the separator row, which depends on whitespace to remain valid markdown (`|---|` is borderline-ambiguous in some parsers)
root_cause: missing_tooling
resolution_type: tooling_addition
severity: low
tags:
  - markdown
  - table
  - cli
  - argparse
  - formatting
  - downstream-tooling
---

# Strip-padding CLI flag for table_fmt without breaking the separator row

## Problem

`table_fmt.py` only emitted padded cells (`| a | b |`) to keep columns aligned. Downstream consumers — CSV converters, naive plain-text parsers — needed the compact form (`|a|b|`) and were having to strip whitespace themselves. We needed a `--strip-padding` flag that emits compact cells without breaking the separator row, since markdown's parseability depends on the separator keeping its standard padded shape.

## Symptoms

- Downstream tools consuming `table_fmt`'s output had to post-process every cell to remove padding
- No way to opt in to compact cells from the CLI
- A naive "strip everywhere" implementation would emit `|---|` for the separator, which some markdown parsers tolerate but others reject as not-a-table

## What Didn't Work

Three approaches were considered during the brainstorm phase and rejected before any code was written:

- **Strip whitespace inside `parse_table`.** This would conflate parse and emit responsibilities and would break the existing alignment-padded round trip for callers that don't pass the flag. The flag belongs at the emit boundary, not the parse boundary.
- **Add a separate `format_table_compact` function.** Doubles the API surface and forces every caller to choose at import time. A keyword toggle on the existing function keeps one entry point and lets the CLI flip the bit at runtime.
- **Strip the separator row too.** Tempting for symmetry, but `|---|` (no spaces) is borderline-ambiguous as markdown. Keeping the separator row in its standard padded form preserves valid-markdown output regardless of which mode the data rows use.

## Solution

Add a `strip_padding=False` keyword to `format_table` and branch at the smallest possible emit point — the inner `format_row` helper — so the default code path is byte-identical to the prior implementation. Wire the flag through `argparse` as `--strip-padding`.

**Emit-time branch in `format_table` (table_fmt.py:107-111):**

```python
def format_row(cells):
    if strip_padding:
        return "|" + "|".join(cells[:num_cols]) + "|"
    padded = [pad_cell(cells[i], col_widths[i], align_for(i)) for i in range(num_cols)]
    return "| " + " | ".join(padded) + " |"
```

The separator row is built outside `format_row`, so it is naturally exempt — no special-case logic needed:

```python
lines = [format_row(normalised[0])]
sep_cells = [separator_cell(col_widths[i], align_for(i)) for i in range(num_cols)]
lines.append("| " + " | ".join(sep_cells) + " |")
for row in normalised[1:]:
    lines.append(format_row(row))
```

**CLI wiring (table_fmt.py:136-144, 151):**

```python
parser.add_argument(
    "--strip-padding",
    action="store_true",
    help=(
        "Emit data rows without surrounding whitespace inside cells "
        "(|a|b| instead of | a | b |). The separator row is left "
        "unchanged so the output remains valid markdown."
    ),
)
# ...
sys.stdout.write(format_table(rows, alignments, strip_padding=args.strip_padding))
```

**With the flag:**

```
|a|b|
| --- | --- |
|x|y|
```

**Without the flag (unchanged from prior behavior):**

```
| a | b |
| --- | --- |
| x | y |
```

## Why This Works

The format function already had a single per-row emit path (`format_row`). Branching at that point — rather than restructuring the function, adding a parallel "compact" function, or pushing the toggle into `parse_table` — keeps the change additive: every existing caller's output is byte-identical because the new branch is only entered when `strip_padding=True`. The separator row is constructed in a separate pipeline (`sep_cells` joined explicitly), so it stays padded "for free" without any special-case guard. This is the smallest viable surface: one keyword, one branch, one CLI flag.

## Prevention

Patterns worth replicating when adding any optional output mode to a formatter:

- **Default-false keyword preserves byte-identity.** A new mode must default to off and produce output identical to the prior version. Lock this in with an explicit test like `format(rows) == format(rows, new_flag=False)`. Include alignment / option permutations in a parameterized check so a future refactor cannot quietly drift the default:

  ```python
  def test_default_matches_explicit_false_across_alignment_modes(self):
      rows = [["Name", "Age", "City"], ["Alice", "30", "NYC"]]
      for alignments in (None, [], [None, None, None],
                         ["left", "right", "center"], ["right", None, "left"]):
          with self.subTest(alignments=alignments):
              self.assertEqual(
                  format_table(rows, alignments),
                  format_table(rows, alignments, strip_padding=False),
              )
  ```

- **Branch at the smallest emit point.** Restructuring the whole function around a flag inflates the diff, weakens the byte-identity guarantee, and makes future modes harder to add. Locate the one place the bytes diverge and put the branch there.

- **Exempt structural rows from any "strip" or "minimize" transform.** In a markdown table, the separator row carries the contract that "this is a table" and encodes alignment. Keep it in its padded form so the output stays valid markdown regardless of which mode the data rows use. The test that locks this in:

  ```python
  def test_separator_row_unchanged_under_strip_padding(self):
      rows = [["a", "b"], ["x", "y"]]
      out_stripped = format_table(rows, strip_padding=True)
      out_padded = format_table(rows, strip_padding=False)
      self.assertEqual(out_stripped.splitlines()[1], out_padded.splitlines()[1])
  ```

- **Round-trip tests should cross feature toggles.** If `format → parse → format` is a fixed point in the default mode, it must be a fixed point in every new mode too. Otherwise the new mode is silently lossy:

  ```python
  def test_round_trip_through_parse_table_under_strip_padding(self):
      rows = [["Name", "Age", "City"], ["Alice", "30", "NYC"]]
      alignments = ["left", "right", "center"]
      formatted = format_table(rows, alignments, strip_padding=True)
      rows2, alignments2 = parse_table(formatted)
      self.assertEqual(rows2, rows)
      self.assertEqual(alignments2, alignments)
      self.assertEqual(format_table(rows2, alignments2, strip_padding=True), formatted)
  ```

- **Cover the awkward shapes once the toggle exists.** Empty input, header-only, and ragged rows often expose a flag's edge behavior. Three short tests (`test_empty_rows_returns_empty_string_under_strip_padding`, `test_header_only_table_under_strip_padding`, `test_ragged_row_emits_empty_trailing_cells_under_strip_padding`) catch regressions cheaply.

- **Slice over index-build.** The autofix pass simplified `[cells[i] for i in range(num_cols)]` to `cells[:num_cols]` on the strip-padding branch — same semantics, fewer moving parts. Worth the habit when the surrounding code uses `range(num_cols)` only as an iteration vehicle.

## Related Issues

- GitHub issue #96 — Add `--strip-padding` CLI flag for downstream tooling
- Companion learning: `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md` (issue #92) — same `table_fmt` module, complementary scope: alignment hints flow from parse to format, while strip-padding is an emit-only toggle. Together they establish that the parse stage owns alignment metadata and the emit stage owns presentation modes
- Origin docs: `docs/brainstorms/2026-04-25-strip-padding-cli-flag-requirements.md`, `docs/plans/2026-04-25-001-feat-strip-padding-cli-flag-plan.md`
- Commits: `a40294e` (feature + tests + brainstorm), `eb55d9e` (plan), `9ed0ffe` (ce-review autofix)
