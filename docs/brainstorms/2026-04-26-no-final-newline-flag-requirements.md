---
date: 2026-04-26
topic: countdown-no-final-newline-flag
---

# Countdown `--no-final-newline` Flag

## Problem Frame

`countdown.sh` always emits a trailing newline after `Time's up!` because the final message uses `echo`. Callers who pipe the script's output into another command, embed it in a status line, or compare its output byte-for-byte cannot suppress that newline today. Add a `--no-final-newline` flag that opts out of the trailing newline on the final message only, leaving every other byte of output unchanged. Tracked by issue #118.

## Requirements

- The script accepts a new long flag `--no-final-newline`. When present and `--silent` is not also set, the final `Time's up!` output is emitted without a trailing newline. When the flag is absent, output is preserved byte-for-byte against today's behavior.
- The flag is a no-op when combined with `--silent`. With `--silent`, the final message keeps its trailing newline regardless of `--no-final-newline`. The combination is allowed (no error), and `--help` documents the no-op interaction.
- The flag does not affect the in-place ticker output (`\rTime remaining: Ns…\n`) or the separating newline that closes the ticker line before the final message.
- Argument parsing validates the flag combination eagerly during the parse pass — unknown tokens still fall through to the duration slot exactly as they do today, and validation of the duration value runs after parsing as it does now.
- `--help` lists `--no-final-newline` alongside `--silent` and `--help` with a short description and a note that it is a no-op under `--silent`.
- A new test module `test_countdown.py` covers: (a) default behavior unchanged when the flag is absent, (b) flag present with the visible ticker — final byte is `!` not `\n`, (c) flag present together with `--silent` — final byte remains `\n` (no-op confirmed), (d) flag present together with an invalid duration — exit status is non-zero and the duration error is emitted on stderr.

## Acceptance Examples

- AE1. **Covers default preservation.** Running `countdown.sh 1` with no other flags emits the same bytes it emits today, ending with `Time's up!\n`.
- AE2. **Covers flag with ticker.** Running `countdown.sh --no-final-newline 1` emits the ticker as today and ends with the literal bytes `Time's up!` — no `\n` after the `!`.
- AE3. **Covers no-op under silent.** Running `countdown.sh --silent --no-final-newline 1` emits only `Time's up!\n` — the trailing newline is preserved because `--silent` makes the flag a no-op.
- AE4. **Covers eager validation.** Running `countdown.sh --no-final-newline abc` exits non-zero with the existing `Error: duration must be a positive integer (got 'abc')` on stderr. Flag order relative to the duration token does not matter.

## Success Criteria

- A pipe-aware caller can invoke `countdown.sh --no-final-newline N` and reliably get a final byte of `!` without writing a `tr -d '\n'` workaround.
- Existing callers who do not pass the flag observe no change in stdout, stderr, exit codes, or timing.
- A downstream agent reading `--help` understands the flag's behavior — including the `--silent` no-op interaction — without needing to read the script source.

## Scope Boundaries

- Only `countdown.sh` and the new `test_countdown.py` change. `dashboard.html`, `table_fmt.py`, and other repo files are untouched.
- The flag affects the final message only — ticker output, error messages, and the separating newline that closes the ticker line stay as-is.
- No new short-flag alias (e.g., `-n`) is added. No environment-variable equivalent. No reordering or rewrite of the existing argument parser beyond what the new flag requires.
- The `--silent` no-op is intentional per issue #118; revisiting that interaction (e.g., making the flag effective under `--silent`) is out of scope.

## Key Decisions

- **`--silent + --no-final-newline` is allowed and silently a no-op, not an error.** Rationale: issue #118 mandates it; allowing the combination keeps callers from having to branch on whether silent mode is in play, and `--help` documents the no-op so the behavior is discoverable.
- **Switch the final emission from `echo` to `printf` when the flag is active.** Rationale: `echo` always emits a trailing newline in bash; `printf` gives byte-level control without changing any other behavior.

## Dependencies / Assumptions

- **Assumption (issue-body discrepancy).** Issue #118 describes `test_countdown.py` as an "existing file." Pre-verification confirms it is missing from the worktree. This brainstorm treats `test_countdown.py` as a new file to create; planning should follow the unittest style of `test_table_fmt.py`.
- **Assumption (issue-body discrepancy).** Issue #118's "Behavior" example shows `3\n2\n1\nTime's up!\n` for the current default output. The actual ticker uses `\r`-overwriting `Time remaining: Ns` plus a single `\n` before `Time's up!`. The intent — suppress only the trailing newline after `Time's up!` — is unambiguous; the simplified example does not change the requirement.
- Tests run under the worker's standard Python `unittest` runner, the same one that exercises `test_table_fmt.py`. Tests must invoke `countdown.sh` via `subprocess` with a small duration (e.g., 1) to keep wall-clock cost bounded.

## Next Steps

-> `/ce-plan` for structured implementation planning.
