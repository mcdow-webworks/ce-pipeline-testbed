---
title: Adding a format-time CLI flag to table_fmt without regressing byte-for-byte output
date: 2026-04-26
category: best-practices
module: table_fmt
problem_type: best_practice
component: tooling
symptoms:
  - One oversized cell (URL, stack trace, paragraph) blows the whole table out horizontally
  - No way to cap column width without re-implementing the formatter
  - CLI lacked argparse plumbing so flags could not be validated before stdin was read
root_cause: missing_tooling
resolution_type: tooling_addition
severity: low
tags:
  - cli
  - argparse
  - table
  - truncation
  - backwards-compat
  - idempotency
---

# Adding a format-time CLI flag to table_fmt without regressing byte-for-byte output

## Problem

`table_fmt.py` padded every column to the width of its widest cell, so a single long cell (a URL, a stack-trace fragment, a paragraph) made the whole table unreadable in narrower viewers. Issue #111 asked for a `--max-width N` flag that caps each column at N chars by truncating with a literal `...` suffix, **without changing any byte of output when the flag is absent**. The challenge was less the truncation math than introducing a CLI flag and a new optional parameter through a tool that previously parsed `sys.argv` by hand and had no `argparse` machinery.

## Symptoms

- Tables with one long cell rendered hundreds of characters wide
- The CLI had no flags at all — adding one meant introducing argparse fresh
- Existing tests asserted byte-for-byte fixture parity, so any drift in the no-flag path would surface immediately

## What Didn't Work

- **Truncating during column-width computation** — the natural temptation is to truncate inline while computing `col_widths`. It mixes two concerns (width measurement and content rewriting) into one loop and forces the rest of `format_table` to know which cells were rewritten. A pre-pass on `normalised` rows is the simpler split: rewrite cells first, then let the existing width/padding/separator logic run unchanged.
- **A `lambda` for the argparse `type=` validator** — concise but produces a generic argparse error message that does not match the existing `Error: ...` stderr style, and gives the test suite nowhere to import the validator from for unit-level coverage. A named module-level function (`_validate_max_width`) is testable in isolation and lets the error wording stay consistent with the rest of the tool.
- **Hardcoding `4` as the minimum** — works, but the relationship "minimum = len(marker) + 1" is invisible to a future reader who changes `...` to a single-char Unicode ellipsis. Deriving `_MIN_MAX_WIDTH = len(_ELLIPSIS) + 1` keeps the constraint self-correcting.

## Solution

Two cohesive changes in one commit:

1. **Migrate `main()` to `argparse`** with a small named validator that rejects non-ints and `< 4` *before* stdin is read.
2. **Add a per-column truncation pre-pass** in `format_table()` behind a `max_width=None` default that preserves the existing call signature.

**Constants derived from the marker, not hardcoded:**

```python
_ELLIPSIS = "..."
_MIN_MAX_WIDTH = len(_ELLIPSIS) + 1   # smallest N that leaves >= 1 content char
```

**Argparse validator — named function, not lambda, raising `ArgumentTypeError` (argparse turns this into stderr + exit code 2):**

```python
def _validate_max_width(value):
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
```

**Pre-pass in `format_table()` — only runs when `max_width is not None`, skips columns that already fit so their bytes match the no-flag path exactly:**

```python
if max_width is not None:
    keep = max_width - len(_ELLIPSIS)
    for col in range(num_cols):
        widest = max(len(row[col]) for row in normalised)
        if widest <= max_width:
            continue   # column already fits; leave bytes untouched
        for r, row in enumerate(normalised):
            cell = row[col]
            if len(cell) > max_width:
                normalised[r][col] = cell[:keep] + _ELLIPSIS
```

**Signature change is additive:**

```python
# Before
def format_table(rows, alignments=None): ...

# After — old call sites unchanged because the new param is keyword-only-by-convention
def format_table(rows, alignments=None, max_width=None): ...
```

The pre-pass mutates the already-local `normalised` list, so the rest of `format_table` (col-width computation, `pad_cell`, `separator_cell`) runs unchanged. After truncation, the column's widest cell is exactly N, so the existing `max(width, 3)` clamp stays valid (N ≥ 4 by validation).

## Why This Works

- **Conservative default preserves byte-for-byte parity.** `max_width=None` is a hard guard: the entire pre-pass is skipped, and not just for the column-skip optimization. The existing fixture tests in `RoundTripTests` would catch any drift in the no-flag path immediately.
- **Per-column skip is more than an optimization — it is correctness.** When a column's widest cell is already ≤ N, the cells are emitted unchanged. This satisfies R1's "columns that already fit are emitted unchanged" guarantee at the byte level, not just the visual level. `test_already_short_input_is_byte_identical` and `test_mixed_only_oversized_column_changes` make this load-bearing.
- **Validation lives at the CLI boundary.** Because argparse parses arguments before the script reads stdin, an invalid `--max-width` aborts before any work is done. The validator is also unit-testable (`MaxWidthValidatorTests`) without spinning up a subprocess.
- **Idempotency is automatic, not asserted.** Once a cell is truncated to exactly N chars ending in `...`, the column's widest cell is N, the per-column skip fires on the next pass, and no further truncation can occur. The test (`test_idempotent_under_repeated_max_width`) verifies this for two and three passes — three-pass is deliberate, since alternating-output regressions can pass a two-pass check.
- **Strict `>` on the truncation gate is the fence.** A cell whose length equals N must be left alone; otherwise, repeated invocation could keep nibbling at it. `test_cell_of_exact_max_width_is_not_truncated` is an explicit boundary test that would catch a `>=` typo.

## Prevention

- **Mirror existing optional-parameter precedent rather than introducing a new convention.** This module already had `alignments=None` from issue #92 (see related-doc link below). Adding `max_width=None` follows the same shape: optional keyword, conservative default, behavior change only when caller opts in. The pattern is "extend by addition, never by mutation," which keeps every existing call site untouched and the diff small.

- **Derive related constants from each other instead of duplicating literals.**

  ```python
  _ELLIPSIS = "..."
  _MIN_MAX_WIDTH = len(_ELLIPSIS) + 1   # not a bare 4
  ```

  If the marker ever changes (e.g., to a single-char `…`), the minimum updates with it. Help text, error messages, and the validator all reference `_MIN_MAX_WIDTH` and `len(_ELLIPSIS)` directly so they cannot drift apart.

- **Reach for a named validator function, not a lambda, when the error wording matters.** Lambdas produce a generic argparse error and are not importable for unit tests. A named module-level function:
  - lets you keep the error-message style consistent with the rest of the tool (here: close to `Error: ...` stderr style),
  - is unit-testable without subprocess machinery (`MaxWidthValidatorTests` calls `_validate_max_width("foo")` directly and asserts on `ArgumentTypeError`),
  - serves as the single source of truth for "what counts as a valid `--max-width`."

- **Add a fence test for every strict-inequality branch in a content-rewriting path.** `>` versus `>=` is a one-character bug that boundary tests catch and example-driven tests miss. For this change:

  ```python
  def test_cell_of_exact_max_width_is_not_truncated(self):
      rows = [["H"], ["abcdefghij"]]   # data cell length == max_width
      out = format_table(rows, max_width=10)
      data_cell = out.splitlines()[2].split("|")[1].strip()
      self.assertEqual(data_cell, "abcdefghij")
      self.assertNotIn(_ELLIPSIS, data_cell)
  ```

- **Three-pass idempotency, not two.** Two-pass round-trip catches drift but not alternating regressions. The pattern from `RoundTripTests::test_mixed_alignments_round_trip` extends naturally to `test_idempotent_under_repeated_max_width` here:

  ```python
  rows, alignments = parse_table(original)
  once   = format_table(rows,  alignments,  max_width=15)
  rows2, alignments2 = parse_table(once)
  twice  = format_table(rows2, alignments2, max_width=15)
  self.assertEqual(once, twice)        # second pass is a fixed point
  rows3, alignments3 = parse_table(twice)
  thrice = format_table(rows3, alignments3, max_width=15)
  self.assertEqual(twice, thrice)      # third pass too — guards alternation
  ```

- **In-process CLI testing (patched `sys.argv`/`stdin`/`stdout`/`stderr`) beats subprocess testing for stdlib-only Python tools.** Subprocess tests pay startup cost and obscure tracebacks; the `_run_main` helper here runs `main()` in-process, captures all four streams, and returns `(exit_code, stdout, stderr)`. Document the one assumption it relies on (argparse resolves `sys.stderr` at write-time, not parser-construction-time) so a future Python upgrade does not silently break the captures.

- **Defer interactions with absent features rather than authoring untested logic.** The brainstorm specified `--max-width` × `--json` interaction (D3), but `--json` was not on this branch's base. The work-phase comment in `test_table_fmt.py` (with a pointer back to brainstorm §D3) is more honest than authoring a code path that nothing exercises:

  ```python
  # Note: --max-width × --json interaction is intentionally not tested here.
  # --json mode (PR #109) does not exist on this branch's base. See
  # docs/brainstorms/2026-04-26-table-fmt-max-width-requirements.md §D3.
  ```

## Related Issues

- GitHub issue #111 — Add a `--max-width N` flag to `table_fmt.py`
- Related learning: [`docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`](../logic-errors/table-fmt-respect-column-alignment-2026-04-24.md) — same module, established the `alignments=None` precedent that `max_width=None` mirrors. Round-trip / idempotency test pattern reused.
- Brainstorm: `docs/brainstorms/2026-04-26-table-fmt-max-width-requirements.md`
- Plan: `docs/plans/2026-04-26-001-feat-table-fmt-max-width-plan.md`
- Commits: `07959e8` (feat), `32b61b0` (ce-review autofix)
