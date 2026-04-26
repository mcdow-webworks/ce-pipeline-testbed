---
date: 2026-04-26
topic: table-fmt-json-output
---

# `table_fmt.py --json` Output Mode

## Problem Frame

`table_fmt.py` currently has one job: read a markdown table from stdin and write a re-formatted markdown table back to stdout. Downstream consumers that want structured access to the table cells (scripts, dashboards, other tools in this repo) have to re-parse the formatter's output, which is wasteful and brittle. A `--json` output mode lets callers reuse the existing parser and get a structured representation in one step, while keeping the default markdown round-trip behavior untouched.

Source: GitHub issue #109.

## Requirements

- **R1.** When invoked with `--json`, the script reads markdown from stdin and writes JSON to stdout. Without `--json`, current behavior is preserved byte-for-byte.
- **R2.** JSON output is an array of row objects. Each row object is keyed by the header row's cell text, with cell values as strings (no type coercion — numbers, booleans, nulls all stay as strings).
- **R3.** JSON output is pretty-printed with `indent=2` and terminates with a single trailing newline.
- **R4.** `--help` documents the new `--json` flag.
- **R5.** Implementation reuses the existing `parse_table()` function. No parallel parser.
- **R6.** Tests in `test_table_fmt.py` cover: basic happy path, table with alignments (alignment metadata is dropped in JSON output), single-column table, table with empty cells.
- **R7.** Malformed input (no recognizable table) fails fast with a non-zero exit and an error message on stderr — matches existing `main()` behavior. The script must not silently emit `[]` for non-table input.

## Success Criteria

- `python table_fmt.py --json < table.md` produces valid JSON matching the shape in R2 for any well-formed markdown table.
- `python table_fmt.py < table.md` (no flag) produces output identical to the pre-change implementation for every existing test fixture.
- `python table_fmt.py --help` lists `--json` and a one-line description.
- All new and existing tests pass.

## Scope Boundaries

- No type coercion (numbers/booleans/nulls stay as strings).
- No streaming output for large tables.
- No reverse `--from-json` mode.
- No file-path argument — stdin only.
- No edits to `countdown.sh`, `dashboard.html`, or any unrelated file.

## Key Decisions

- **No header row detected (separator row missing → `alignments == []`): error out with a non-zero exit.** Without a separator we cannot identify which row is the header, so the JSON shape (`{header_text: value}`) is undefined. Falling back to "array of arrays" or "empty array" silently changes the contract; erroring is consistent with R7 and with the existing `main()` precedent that already errors when no usable rows are found.
- **Duplicate header column names: error out with a non-zero exit, naming the duplicate.** Last-wins silently loses data and is invisible to the caller; first-wins has the same problem in reverse; numeric-suffixing produces surprising keys (`Name_1`, `Name_2`) the caller did not write. Erroring keeps the JSON shape unambiguous and surfaces the data-modeling problem at the source.
- **Argument parsing via `argparse`.** Stdlib, gives `--help` and unknown-flag rejection for free, and the cost (a few lines) is trivial against the value of getting R4 and basic flag hygiene without hand-rolling them.

## Dependencies / Assumptions

- The script's existing `parse_table()` already returns `(rows, alignments)` where `rows[0]` is the header when a separator row was seen. This contract is reused unchanged.
- Empty cells in non-header positions are valid JSON values (the empty string `""`). Empty cells in the header row collapse into a key of `""` — a single empty header is allowed; multiple empty headers fall under the duplicate-headers rule and error.

## Outstanding Questions

### Resolve Before Planning

(none — all blocking product decisions resolved above)

### Deferred to Planning

- [Affects R1, R7][Technical] Exact wording and exit code for the two new error paths (no-header-row, duplicate-headers). Reuse the existing `Error: ...` / `sys.exit(1)` pattern from `main()` for consistency unless planning surfaces a reason to differ.
- [Affects R6][Technical] Whether to add a separate `format_json()` helper or inline the JSON emission inside `main()`. Lean toward a small helper for testability, but defer the call until planning sees the surrounding code.

## Next Steps

→ `/ce:plan` for structured implementation planning
