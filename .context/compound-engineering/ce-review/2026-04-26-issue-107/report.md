# ce-review run — issue #107 (`--tick-format` flag)

- Mode: `autofix`
- Branch: `claude/issue-107`
- Base: `d02bb44` (master merge-base)
- Files in scope: `countdown.sh`, `test_countdown.py`, `CHANGELOG.md`
- Out of scope (CE pipeline artifacts): `docs/brainstorms/`, `docs/plans/`

## Reviewer team
- correctness (always-on)
- testing (always-on)
- maintainability (always-on)
- agent-native (always-on)
- learnings-researcher (always-on)
- reliability (cross-cutting — touches validation/error handling)
- kieran-python (stack-specific — new Python test file)

Skipped: security (no auth/permissions/public surface), performance (small script, no DB or hot loops), api-contract (no API), data-migrations (none), kieran-rails / dhh-rails / kieran-typescript / julik-frontend-races (wrong stack), CE migration agents (no migrations).

## Synthesized findings

After ≥0.60 confidence gate and dedup, three actionable findings — all from the testing reviewer, all P3, all `safe_auto → review-fixer`:

| # | Severity | File | Issue | Fix |
|---|----------|------|-------|-----|
| 1 | P3 | `test_countdown.py` | `format_tick(0, mm-ss)` / `format_tick(0, human)` boundary not asserted | Added `test_zero_seconds_renders_double_zero` and `test_zero_seconds_renders_zero_s` |
| 2 | P3 | `test_countdown.py` | `format_tick`'s default arm (unknown mode → return 1) not covered | Added `FormatTickUnknownModeTests.test_unknown_mode_returns_nonzero_with_empty_stdout` |
| 3 | P3 | `test_countdown.py` | Invalid-value error path doesn't assert the helpful "one of: seconds, mm-ss, human" list reaches stderr | Strengthened `test_invalid_value_fails_before_loop` to assert `seconds`, `mm-ss`, `human` substrings |

All other reviewers (correctness, maintainability, agent-native, reliability, kieran-python, learnings) returned zero findings.

## Applied fixes

All three findings applied directly to `test_countdown.py`. Verification of the three new `format_tick` assertions against an LF-normalized copy of `countdown.sh`:

```
format_tick 0 mm-ss   → 00:00          ✓
format_tick 0 human   → 0s             ✓
format_tick 30 unknown → rc=1, stdout='' ✓
```

The strengthened error-message assertion is consistent with the actual error string at `countdown.sh:79`:
`Error: --tick-format must be one of: seconds, mm-ss, human (got '$TICK_FORMAT')`
— all three substrings are present.

## Residual actionable work

None. No `gated_auto` or `manual` findings to externalize.

## Pre-existing issues (informational, out of scope)

- **CRLF in working tree on Windows.** This checkout has `core.autocrlf=true` and no `.gitattributes`, so `countdown.sh` lands on disk with CRLF and bash refuses to source it (`$'\r': command not found`). This breaks all 22 tests in `test_countdown.py` in the current Windows worktree. The work-phase commit (`7d54171`) verified 30/30 pass — presumably in a Linux CI / non-CRLF environment, where the same tests work cleanly. Adding a `.gitattributes` with `*.sh text eol=lf` would address this, but that is a repo-wide line-ending decision outside the scope of this review.

## Advisory

- `correctness` flagged residual risks worth noting (no action required):
  - Multiple positional args silently last-wins (pre-existing).
  - `format_tick`'s default arm is unreachable from CLI but kept as a defensive guard for sourced testing.
  - `--tick-format` followed by another flag (e.g., `--tick-format --silent`) consumes the next token as the value, then the validator rejects it with a clear stderr message — fail-fast behavior.
- `learnings-researcher` found no prior solutions on Bash flag parsing or sourceable script test harnesses. This issue is a candidate for a future learnings doc.

## Verdict

**Ready to merge.** All P0/P1/P2 reviewers clean. Three P3 testing-coverage gaps applied as `safe_auto`. Pre-existing CRLF environment friction is independent of this PR's scope.
