# ce-review autofix run

- **Run id**: 20260425-210217-strip-padding-autofix
- **Mode**: autofix
- **Branch**: claude/issue-96
- **Base**: master (merge-base d02bb44)
- **Issue**: #96 — `--strip-padding` CLI flag for `table_fmt.py`

## Intent

Add a `--strip-padding` CLI flag that emits markdown table data rows without surrounding whitespace inside cells (`|a|b|` instead of `| a | b |`). The separator row stays padded so the output remains valid markdown. Default behavior is byte-identical to prior output.

## Reviewers spawned

- correctness (always)
- testing (always)
- maintainability (always)
- agent-native-reviewer (always)
- learnings-researcher (always)
- api-contract — new public CLI flag + new keyword on `format_table`
- kieran-python — Python source change with new behavior mode

Skipped: security, performance, data-migrations, reliability, dhh-rails, kieran-rails, kieran-typescript, julik-frontend-races, schema-drift-detector, deployment-verification-agent (no diff signal).

## Synthesized findings

After confidence gating (>= 0.60) and dedup (`maintainability` and `kieran-python` agreed on the line 109 finding):

| # | Severity | File:line | Title | Confidence | Reviewers | Route |
|---|----------|-----------|-------|------------|-----------|-------|
| 1 | P2 | test_table_fmt.py:94 | No CLI-level test for `--strip-padding` argparse wiring | 0.90 | testing | manual / downstream-resolver |
| 2 | P2 | test_table_fmt.py:94 | No round-trip test for `--strip-padding` through `parse_table` | 0.85 | testing, learnings, api-contract | safe_auto / review-fixer |
| 3 | P2 | test_table_fmt.py:116 | Default-byte-identity not verified across alignment modes | 0.80 | testing | safe_auto / review-fixer |
| 4 | P3 | test_table_fmt.py:94 | Empty rows / header-only edge cases under strip_padding untested | 0.70 | testing | safe_auto / review-fixer |
| 5 | P3 | test_table_fmt.py:94 | Ragged-row / empty-cell strip_padding emission untested | 0.65 | testing, maintainability, kieran-python | safe_auto / review-fixer |
| 6 | P3 | table_fmt.py:109 | strip_padding branch indexes by `range(num_cols)` where slice reads cleaner | 0.78 | maintainability, kieran-python | safe_auto / review-fixer |
| 7 | P3 | table_fmt.py:124 | Separator-row format inline-duplicates padded `format_row` branch | 0.66 | maintainability | manual / downstream-resolver |
| 8 | P3 | table_fmt.py:92 | `col_widths` computed unconditionally even when `strip_padding=True` | 0.60 | maintainability | advisory |

No findings below the 0.60 threshold were suppressed. No findings flagged as `pre_existing`.

## Applied fixes (round 1, 1 round used of `max_rounds: 2`)

- **table_fmt.py:109** — replaced `cells[i] for i in range(num_cols)` with `cells[:num_cols]` in the `strip_padding` short-circuit. `normalised` already pads each row to `num_cols` (line 89), so the slice is equivalent and matches the abstraction level of the surrounding code.
- **test_table_fmt.py** — added 5 new test cases inside `StripPaddingTests`:
  - `test_default_matches_explicit_false_across_alignment_modes` — covers finding #3 with parameterised `subTest` over `None`, `[]`, all-`None`, mixed alignments, and `["right", None, "left"]`.
  - `test_empty_rows_returns_empty_string_under_strip_padding` — covers part of finding #4 (empty input).
  - `test_header_only_table_under_strip_padding` — covers part of finding #4 (no body rows).
  - `test_ragged_row_emits_empty_trailing_cells_under_strip_padding` — covers finding #5.
  - `test_round_trip_through_parse_table_under_strip_padding` — covers finding #2; asserts `parse_table` recovers rows + alignments and that re-formatting under the same flag is a fixed point.

Verification: `python -m unittest test_table_fmt.py -v` → 22/22 pass (17 prior + 5 new). Re-review round 1 produced no new findings on the changed scope, so the bounded loop closed at round 1 of 2.

## Residual actionable work (handed off to downstream-resolver)

- **`add-cli-wiring-test-for-strip-padding.md`** (P2) — no `subprocess` or `main()`-level test exercises the argparse wiring. A typo in the flag name, action, or `args.strip_padding` attribute-name would not be caught by the function-keyword tests.
- **`extract-padded-row-helper-in-table-fmt.md`** (P3) — `table_fmt.py:124` inline-duplicates the padded branch of `format_row`. Future readers changing the padded format would have to remember to update both sites. Manual change because it crosses a function boundary and could surface in callers.

## Advisory (not converted to todos)

- **`col_widths` unconditional compute (#8, P3)** — when `strip_padding=True`, `col_widths` is still consumed by `separator_cell` for the (intentionally padded) separator row, so it is not dead. No refactor recommended.
- **Agent-native: README + CHANGELOG silent on `--strip-padding`** — documentation hygiene rather than a code defect. Out of scope for autofix; surfacing for human follow-up if the project tracks user-facing flags in `README.md` / `CHANGELOG.md`.

## Past solutions surfaced

`docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md` — directly relevant. The recommendation to add round-trip fixed-point tests reinforced finding #2 and informed the new `test_round_trip_through_parse_table_under_strip_padding` test.

## Coverage notes

- Suppressed below-threshold: 0
- Reviewers timed out / failed: 0
- Pre-existing findings: 0
- Intent uncertainty: none — issue body and brainstorm doc were unambiguous.

## Verdict

Ready with fixes. No P0/P1 issues. P2/P3 safe_auto items applied; two manual residuals handed off as todos for downstream resolution.
