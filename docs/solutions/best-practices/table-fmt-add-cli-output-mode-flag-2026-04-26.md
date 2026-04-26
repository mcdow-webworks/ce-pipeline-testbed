---
title: Adding a new output-mode flag to a stdin CLI without regressing the default
date: 2026-04-26
category: best-practices
module: table_fmt
problem_type: best_practice
component: tooling
symptoms:
  - downstream consumers re-parse formatter stdout to get structured cell data
  - no convention for layering a second output mode onto a stdin-only CLI script
  - risk of subtly changing default-mode bytes when adding argparse and a new flag
  - tautological byte-parity test (compares output against itself) provides no real regression guard
  - no documented boundary for where ValueError vs sys.exit responsibility lives
root_cause: missing_workflow_step
resolution_type: workflow_improvement
severity: medium
tags:
  - table-fmt
  - cli
  - argparse
  - json-output
  - formatter-pattern
  - regression-testing
  - stdin-tools
  - python
---

# Adding a new output-mode flag to a stdin CLI without regressing the default

## Problem

How do you add a new output mode (e.g. `--json`) to a stdin-driven CLI without breaking the existing default-mode behavior, and what testing/structure conventions keep the addition safe? `table_fmt.py` shipped as a single-purpose markdown reformatter; downstream callers wanted structured access to parsed cells, but any refactor of `main()` to add a flag risks silently regressing the byte-for-byte default output that pipelines depend on.

## Symptoms

The pre-conditions and at-risk behaviors a careless implementation would have produced:

- Default markdown output regressing byte-for-byte — silent breakage of any script piping `table_fmt.py < x.md > x.md`.
- Inconsistent error reporting across argparse failures (unknown flag) and content failures (no header, dup header, no table) — users get cryptic stack traces instead of `Error: ...` lines.
- Parallel parser drift if `--json` had introduced a second `parse_*` function instead of reusing `parse_table` — alignment-aware parsing in one mode, naive split in the other.
- Ragged-row data loss in JSON because `parse_table` does not normalize column counts; `dict(zip(header, row))` truncates silently when a row is short or long (`table_fmt.py:155`), while `format_table` happens to pad ragged rows (`table_fmt.py:84-85`). Asymmetry is invisible until someone feeds a malformed table.
- Self-referential regression test of the form `expected = format_table(rows, alignments); main(...) == expected` — passes by construction even if both sides regress in lockstep (deferred P2 from review).

## What Didn't Work

- **Manual `sys.argv` inspection.** Rejected for argparse: `--help` is free, unknown-flag rejection is free, exit code 2 on argument errors is the coreutils convention.
- **Inline JSON emission inside `main()`.** Rejected for a `format_json(rows, alignments)` helper — mirrors `format_table`, keeps error paths importable and unit-testable without a subprocess.
- **Calling `sys.exit` or writing to `sys.stderr` from `format_json` directly.** Rejected: pure helpers raise `ValueError`; `main()` is the only place that translates exceptions to stderr+exit. Keeps the helper reusable from other entry points (tests, future tools).
- **Self-referential byte-parity test.** The shape `expected = format_table(rows, alignments); assert main_stdout == expected` shipped at `test_table_fmt.py:216-229` and was flagged in review as tautological — `main()` itself calls `format_table(rows, alignments)`, so both sides regress together and the test still passes. The correct shape is a hardcoded golden string captured before the new flag landed (the residual fix is documented in the run artifact for issue #109; not yet applied at time of writing).

## Solution

Four structural moves, all visible in the shipped `table_fmt.py`:

**1. argparse wiring with a terse description (`table_fmt.py:166-178`):**

```python
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
```

**2. `format_json(rows, alignments)` raising `ValueError` for both error states (`table_fmt.py:125-156`):**

```python
def format_json(rows, alignments):
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
```

**3. Exit-code dispatch in `main()` (`table_fmt.py:180-195`).** Content errors print `Error: <msg>` to stderr and exit 1; argparse errors exit 2 (built-in). The `not rows` check stays in `main()` (single source of truth), and `format_json`'s `ValueError`s are caught and translated:

```python
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
```

**4. Mirror-the-sibling signature.** Both `format_table(rows, alignments)` and `format_json(rows, alignments)` accept the same argument tuple even though JSON discards alignment metadata. The list is still consulted (`if not alignments:`) as the "did the parser see a header" signal — the alignment list doubles as a header-presence flag, avoiding a separate boolean parameter.

**5. R1 byte-parity guard — the durable shape.** Capture a golden string from running the binary *before* the change, paste the literal output into the test:

```python
def test_default_mode_byte_for_byte_parity(self):
    original = (
        "| Name | Age | City |\n"
        "| :--- | ---: | :---: |\n"
        "| Alice | 30 | NYC |\n"
    )
    GOLDEN = (  # captured from `python table_fmt.py < fixture.md` before --json
        "| Name  | Age | City |\n"
        "| :---- | --: | :--: |\n"
        "| Alice |  30 | NYC  |\n"
    )
    stdout, stderr, code = self._run_main([], original)
    self.assertEqual(code, 0)
    self.assertEqual(stderr, "")
    self.assertEqual(stdout, GOLDEN)
```

## Why This Works

The exit-code split (1 for content errors, 2 for argparse errors) matches user expectations from coreutils-style tools and surfaces "you typed the flag wrong" distinctly from "your input is malformed." Pure formatter functions raising `ValueError` keep error paths importable and unit-testable without a subprocess — `test_table_fmt.py:172-183` exercises the dup-header and no-header branches directly via `with self.assertRaises(ValueError)`, no IO mocking needed. argparse buys `--help` documentation, structured errors, and a stable extension surface for the next flag with no extra code.

Reusing `parse_table` (no parallel parser) keeps `format_table` and `format_json` consuming the same parser invariants — including the alignment metadata that JSON drops. The `(rows, alignments)` signature is now the established convention for table_fmt formatters, building on the contract introduced in [`table-fmt-respect-column-alignment-2026-04-24.md`](../logic-errors/table-fmt-respect-column-alignment-2026-04-24.md). Future modes (CSV, TSV, HTML) plug in trivially: write `format_csv(rows, alignments)`, add a flag in `main()`, done.

## Prevention

- **Don't write self-referential regression tests.** When adding a flag that should preserve a default code path, the regression guard MUST compare against a hardcoded golden string (or a stable fixture file on disk) — not a fresh call to the same function the production code uses. `expected = format_table(rows, alignments); assert main(...) == expected` is tautological because `main()` itself calls `format_table(rows, alignments)`. Both sides can regress together. Capture the golden by running the binary before the change, paste the literal output into the test.
- **Pure helpers raise; `main()` translates.** Any new formatter function should raise `ValueError` (or a domain-specific exception) for malformed input and never touch `sys.exit`, `sys.stderr`, or `sys.stdout` directly. Concentrates the stderr+exit policy in one place; lets the helper be reused from other entry points.
- **Use argparse for any new flag, not manual `sys.argv` inspection.** You get `--help` text, structured error messages, the standard exit-code-2-on-unknown-flag convention, and an extension surface for the next flag — all for free.
- **Watch for parser-formatter normalization asymmetry.** When `parse_table` doesn't normalize column counts, downstream formatters silently disagree about ragged rows: `format_table` pads them at `table_fmt.py:84-85` (`max(len(row) for row in rows)`); `format_json` truncates them via `zip()` at `table_fmt.py:155` (silently drops cells when row length doesn't match header). Pick one of three: (a) document the asymmetry in both docstrings, (b) add an explicit ragged-row check that raises in `format_json`, or (c) normalize in `parse_table`. Don't let `zip()` silently drop columns from one mode but not another. (This is one of the two P2s deferred from issue #109's review.)
- **Mirror sibling formatter signatures.** `format_X(rows, alignments)` is the convention; even when X discards alignments, accept the parameter so callers can swap modes without rewiring. In this codebase the alignment list also doubles as a "did the parser identify a header" signal — dropping the parameter would mean threading a separate boolean.

Sample test patterns to copy (from `test_table_fmt.py`):

```python
# Duplicate-header error path — direct ValueError, no IO mocking
def test_duplicate_header_raises_value_error_naming_duplicate(self):
    rows = [["Name", "Name"], ["a", "b"]]
    with self.assertRaises(ValueError) as cm:
        format_json(rows, [None, None])
    self.assertIn("duplicate header", str(cm.exception))
    self.assertIn("'Name'", str(cm.exception))

# Empty-array empty-table case — exact text shape, not just structural
def test_header_only_table_emits_empty_array(self):
    out = format_json([["Name", "Age"]], [None, None])
    self.assertEqual(json.loads(out), [])
    self.assertEqual(out, "[]\n")

# CLI dispatch via in-process stdin/stdout patching, no subprocess
def _run_main(self, argv, stdin_text):
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = 0
    with patch.object(table_fmt.sys, "stdin", io.StringIO(stdin_text)), \
         patch.object(table_fmt.sys, "stdout", stdout), \
         patch.object(table_fmt.sys, "stderr", stderr):
        try:
            table_fmt.main(argv)
        except SystemExit as exc:
            exit_code = 0 if exc.code is None else int(exc.code)
    return stdout.getvalue(), stderr.getvalue(), exit_code
```

## Related Issues

- GitHub issue #109 — Add a `--json` output mode to `table_fmt.py`
- GitHub issue #92 — Respect markdown column-alignment syntax in the separator row (parent of the `(rows, alignments)` convention this doc extends)
- Sibling output-mode work without solution docs: #96 (`--strip-padding`), #107 (`--tick-format` for `countdown.sh`)
- Prior learning: [`docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`](../logic-errors/table-fmt-respect-column-alignment-2026-04-24.md)
- Commits: `5a7ccfa` (plan), `cecc635` (feat), `3f36438` (test gaps from review)
- Run artifact: `.context/compound-engineering/ce-review/issue-109-autofix-20260426/run.md`
