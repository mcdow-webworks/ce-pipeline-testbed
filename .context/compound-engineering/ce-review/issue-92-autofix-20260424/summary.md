# ce-review run — issue #92 autofix

- Run ID: issue-92-autofix-20260424
- Branch: claude/issue-92
- Base: master (merge-base 1bdf86355ab1500afc05aeed6d81c2d95ab10651)
- Mode: autofix
- Date: 2026-04-24

## Intent

Respect markdown column-alignment syntax (`:---`, `---:`, `:---:`) in the table
separator row when formatting. `parse_table` now returns `(rows, alignments)`;
`format_table` takes optional `alignments` and applies per-column padding
plus colon-marked separator cells.

## Review team

Always-on: correctness, testing, maintainability, agent-native, learnings-researcher.
Conditional: api-contract (return-signature change), kieran-python (Python diff).

## Findings summary (after merge, dedup, 0.60 confidence gate)

- P1: 1 (committed bytecode / missing `.gitignore`)
- P2: 3 (breaking tuple-return contract, `main()` coverage gap, alignments length-mismatch coverage gap)
- P3: 13
- Suppressed: 1 (maintainability non-finding, conf 0.55)

## Applied fixes (safe_auto → review-fixer)

1. Remove `__pycache__/table_fmt.cpython-313.pyc` and
   `__pycache__/test_table_fmt.cpython-313.pyc` from git tracking. Add
   `.gitignore` covering `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`,
   `.pytest_cache/`.
2. Expand `_parse_alignment` docstring to explain why `None` is distinct
   from `'left'` (preserves plain-dash separator on round-trip).
3. Expand `format_table` docstring to make shorter-than-`num_cols` and
   longer-than-`num_cols` `alignments` behavior explicit.

All 12 tests in `test_table_fmt.py` still pass after fixes.

## Residual actionable work (manual → downstream-resolver)

| # | Finding | Source | Severity |
|---|---|---|---|
| F3 | Add CLI / `main()` coverage (subprocess tests for stdin→stdout, exit code 1 on empty) | testing | P2 |
| F4 | Test `alignments` length mismatch (shorter and longer than `num_cols`) | testing, api-contract | P2 |
| F5 | Unit tests for `_parse_alignment` degenerate inputs (`''`, `':'`, `':-'`, `'-:'`, `':-:'`) | testing | P3 |
| F6 | Test `format_table([])` early return | testing | P3 |
| F7 | Relax brittle `str.center` assertion | testing | P3 |
| F8 | Add fixed-point assertion to no-hints round-trip test | testing | P3 |
| F15 | Test data-cell-wider-than-header with non-default alignment | testing | P3 |
| F16 | Test malformed `parse_table` input (no pipes, blank lines, separator-before-header) | testing | P3 |
| F17 | Replace hardcoded width comments with computed expected strings | testing | P3 |

## Gated (deferred; not auto-applied)

| # | Finding | Source | Notes |
|---|---|---|---|
| F11 | Add `typing.Literal`/`Optional` hints to public API | kieran-python | Additive but stylistic; hand off for a dedicated typing pass |
| F13 | Promote `pad_cell`/`separator_cell` to module-scope pure helpers | kieran-python | Refactor; low risk but not required |
| F14 | Rewrite column-width computation via `zip(*normalised)` | kieran-python | Refactor; changes core computation, defer |

## Advisory (not actionable this PR)

- **F2 breaking contract.** `parse_table` return type changed from
  `list[list[str]]` to `tuple[list[list[str]], list[str|None]]`. Repo
  grep confirms only `table_fmt.main()` and `test_table_fmt.py` reference
  `parse_table` — both updated. No external importers exist. Severity stays
  at P2 given contained blast radius.
- **F12 malformed-cell tolerance.** `_parse_alignment` accepts `':'` and
  `'::'` (cells with no dashes) as valid alignment hints because the outer
  separator detector in `parse_table` accepts any dash/colon-only cell.
  Issue non-goals explicitly exclude escaped-pipe / Unicode / numeric
  hardening; leaving permissive.
- **Separator-before-header positional tolerance.** Pre-existing behavior;
  not introduced by this PR.

## Affirmations (kieran-python)

- Keep `if alignments is None: alignments = []`. Do **not** rewrite to
  `alignments = alignments or []` — that would collapse the legitimate
  empty-list case (what `parse_table` returns when no separator is present).
- Keep `separator_seen` boolean flag — documents intent and guards against
  a second separator-like row overwriting the first.
- Keep string literals `'left' | 'right' | 'center'`. An `enum.Enum` is
  overkill at this module size. If typing is added later, prefer
  `typing.Literal`.

## Agent-native

PASS (4/4 capabilities accessible; stdin/stdout CLI + documented importable
functions).

## Learnings

No relevant past solutions in `docs/solutions/`.

## Verdict

Ready with fixes. P1 hygiene addressed in this commit. Residual items are
test-coverage additions and stylistic refactors best handled by a follow-up.
