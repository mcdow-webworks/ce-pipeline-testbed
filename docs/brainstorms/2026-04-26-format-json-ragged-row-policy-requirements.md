---
date: 2026-04-26
topic: format-json-ragged-row-policy
---

# `format_json` ragged-row policy

## Problem Frame

`format_json(rows, alignments)` in `table_fmt.py` (added by PR #110, merged
2026-04-26) produces JSON via `dict(zip(header, row))` without checking that
each data row has the same column count as the header row. When a row is
shorter than the header, trailing header keys are silently dropped from the
emitted object. When a row is longer than the header, the extra cells are
silently discarded. Either form is quiet data loss in machine-parseable
output that downstream consumers will treat as authoritative.

`parse_table` does not normalise per-row column counts, so the JSON helper
sees raw, possibly-ragged rows. `format_table` pads ragged rows to the
widest row before formatting, so the markdown path masks the inconsistency
visually. `format_json` does not pad and does not error — it just truncates.

Three reviewers (correctness, testing, kieran-python) independently flagged
this as P2 in the ce-review of PR #110. The reviewers' suggested
resolutions, recorded verbatim in the harvested issue, are:

- (a) raise `ValueError` on mismatch — symmetrical with the existing
  duplicate-header guard.
- (b) normalise like `format_table` does.
- (c) document the truncation behavior in the docstring's Preconditions
  section.

The review noted that (a) is most consistent with the strict tone of the
existing helper.

## Requirements

- R1. `format_json` raises `ValueError` when any data row has a column
  count that differs from the header row's column count. The exception is
  raised before any output is produced (no partial JSON).
- R2. The error message identifies which data row is ragged and reports
  both the header column count and the row's column count, so the user can
  locate the offending input. The message follows the existing
  `--json requires …; …` phrasing pattern used by the duplicate-header
  guard so `main()` translates it consistently to `Error: …` on stderr.
- R3. `main()` continues to translate the new `ValueError` into the same
  `Error: <msg>` + exit 1 behavior already used for the no-separator and
  duplicate-header errors. No new exit code, no new stream, no special
  formatting.
- R4. When every data row has exactly the header's column count,
  `format_json` output is byte-for-byte identical to the pre-fix
  implementation. The change is additive — strictly a new failure path on
  inputs that were already silently broken.

## Success Criteria

- A row that is shorter than the header (e.g. trailing cell missing)
  produces a clear error and exit 1 under `--json`, instead of a
  silently-truncated JSON object.
- A row that is longer than the header (e.g. extra trailing cell) produces
  the same clear error and exit 1, instead of silently dropping the
  extras.
- All existing `FormatJsonTests` and `MainCliTests` still pass unchanged
  on rectangular input.
- The default markdown output mode remains untouched — `format_table`
  continues to pad ragged rows. The strictness is JSON-mode-only.

## Scope Boundaries

- Out of scope: changing `format_table`'s ragged-row handling. Markdown
  is visual; padding to the widest row is the established, intentional
  behavior.
- Out of scope: changing `parse_table` to normalize or reject ragged
  input. Other callers depend on the raw cell list.
- Out of scope: a `--json --lenient` (or similar) flag to opt back into
  truncation. YAGNI — there is no current consumer asking for it, and the
  default-strict behavior is the whole point of the fix.
- Out of scope: deduplication or normalization beyond column count (e.g.
  Unicode NFC/NFD header collapse, empty-string headers). Those are
  separate residual risks recorded in the source ce-review and out of
  scope for this issue.

## Key Decisions

- **Strict-error over normalize-or-document (Option A).** Symmetrical
  with the duplicate-header guard already in `format_json`; preserves the
  helper's strict tone; prevents silent data loss in the structural
  output mode where downstream consumers cannot detect it visually. The
  asymmetry vs. `format_table` is acceptable because markdown and JSON
  serve different consumer expectations.
- **First-mismatch reporting, not aggregated.** Match the duplicate-header
  guard, which raises on the first duplicate found. Aggregating across
  all rows would be more thorough but adds machinery for a CLI that
  expects users to fix the input and re-run.
- **No `zip(..., strict=True)`.** The repo has no declared minimum
  Python version (no `pyproject.toml`, `setup.cfg`, `tox.ini`, or
  `.python-version`); only a `#!/usr/bin/env python3` shebang. `strict=`
  is 3.10+. The fix should work under whatever the implicit floor is, so
  use an explicit `len(row) != len(header)` check instead. The source
  ce-review's residual-risks section calls this out specifically.

## Dependencies / Assumptions

- Assumes PR #110 (`feat(table_fmt): add --json output mode`) is in the
  base when this work lands. PR #110 is already merged on GitHub
  (`d4e064cb`). The fix's diff is small and additive — a check before
  the existing `dict(zip(...))` line plus a few tests.
- Assumes the existing `main()` `except ValueError as exc` handler in the
  `--json` branch continues to be the single boundary that translates
  helper errors to `Error: …` + exit 1. No change required there.

## Outstanding Questions

### Resolve Before Planning

(none — Option A is the recommended decision, error-message phrasing and
test scope are routine planning concerns.)

### Deferred to Planning

- [Affects R2][Technical] Exact error-message wording. Suggested form:
  `--json requires every data row to have the same column count as the
  header; row N has M cells but header has K`. Final wording is a
  planning-level call.
- [Affects R1][Technical] Whether to 1-index or 0-index the row number
  in the error message. User-facing convention is usually 1-indexed
  (first data row = "row 1"); planning should confirm against any
  in-repo precedent.
- [Affects R4][Technical] Whether the new test in `FormatJsonTests`
  asserts on the exact error string or only on `ValueError` type plus a
  substring match. The duplicate-header tests use substring matches —
  follow that precedent.

## Next Steps

→ `/ce:plan` for structured implementation planning.
