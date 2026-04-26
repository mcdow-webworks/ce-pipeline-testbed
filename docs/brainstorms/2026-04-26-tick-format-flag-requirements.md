---
date: 2026-04-26
topic: tick-format-flag
---

# `--tick-format` Flag for `countdown.sh`

## Problem Frame

`countdown.sh` currently prints the ticker as `Time remaining: <N>s`, which works for short
countdowns but is awkward for longer ones (e.g., `Time remaining: 600s` is harder to scan than
`10:00` or `10m`). Users running longer countdowns want a more readable rendering without
breaking the existing default for callers that already parse or expect the current format.

## Requirements

- **R1.** Add `--tick-format <value>` to `countdown.sh`, accepting exactly one of: `seconds`,
  `mm-ss`, `human`.
- **R2.** When `--tick-format` is omitted, the ticker keeps its current output verbatim
  (`Time remaining: <N>s`) for backward compatibility.
- **R3.** `--tick-format seconds` produces the literal current output (`Time remaining: <N>s`).
- **R4.** `--tick-format mm-ss` renders the remaining time as zero-padded `MM:SS`
  (e.g., `Time remaining: 00:30`, `Time remaining: 01:30`, `Time remaining: 10:00`). The
  `Time remaining: ` prefix and the carriage-return ticker behavior are preserved.
- **R5.** `--tick-format human` renders compact human-readable form, omitting any unit whose
  value is zero. Specifically:
  - `30` → `30s`
  - `60` → `1m`
  - `90` → `1m 30s`
  - `600` → `10m`
  - Minutes are not rolled up into hours; long values stay in minutes (e.g., `3600` → `60m`).
- **R6.** An invalid `--tick-format` value (e.g., `--tick-format foo`, missing argument) prints
  an error to stderr and exits non-zero. Validation runs before the duration loop starts so
  bad input fails fast.
- **R7.** `--silent` continues to suppress the ticker entirely regardless of `--tick-format`.
- **R8.** `--help` documents the new flag, its accepted values, and the default behavior when
  the flag is omitted.

## Success Criteria

- Each of the three format modes produces the documented rendering for representative values
  (sub-minute, exact-minute, multi-minute, multi-minute-with-seconds).
- Omitting `--tick-format` produces output byte-for-byte identical to the pre-change behavior.
- Invalid `--tick-format` values fail with a clear stderr message and a non-zero exit code,
  before any countdown work happens.
- `--help` output mentions `--tick-format` with all three accepted values.
- Tests cover each mode plus the invalid-value error path.

## Scope Boundaries

- **No** localization or i18n.
- **No** custom format strings (printf-style templates, user-defined patterns).
- **No** change to the default tick format.
- **No** changes to `dashboard.html` or the Python utilities.
- **No** new units beyond `m` and `s` for `human` mode (no `h`/`d` rollup).
- **No** change to the `Time remaining: ` prefix or the carriage-return ticker mechanics.

## Key Decisions

- **`seconds` mode equals the current literal output, not a bare integer.** The issue example
  shows `30` as shorthand for `seconds` mode, but the acceptance criterion "matches current
  bare-seconds output" is authoritative. Current output is `Time remaining: 30s`, and the
  `s` suffix is preserved. This keeps `seconds` mode and "no flag" identical, which is the
  simplest, least surprising mapping.
- **The `Time remaining: ` prefix is shared across all three modes.** The flag controls only
  how the time value is rendered, not the surrounding template. This keeps the ticker visually
  consistent and avoids inventing a second formatting concept.
- **`human` mode does not roll up to hours.** Examples in the issue only show `m`/`s`. Adding
  hours would be speculative scope; users with hour-scale countdowns can use `mm-ss` or
  `seconds`.
- **Validation happens at argument-parse time, before the loop.** Mirrors the existing pattern
  for duration validation and matches the issue's "fail fast" note.

## Dependencies / Assumptions

- **A1.** Bash 4+ is available (already assumed by existing `(( ))` arithmetic and
  `[[ =~ ]]` regex usage in `countdown.sh`).
- **A2.** Tests live alongside or near `countdown.sh` following whatever convention the repo
  uses; planning will confirm the test harness (likely `bats` or a shell-based runner).
- **A3.** The current ticker writes with `\r` (no newline) and a single `\n` after the loop.
  All three formats keep this behavior; only the time substring changes.

## Outstanding Questions

### Resolve Before Planning

_None._ All product decisions are settled by the issue plus the assumptions above.

### Deferred to Planning

- **[Affects R1, R6][Technical]** Argument-parsing strategy for `--tick-format <value>`. The
  current loop uses `for arg in "$@"` with case statements, which does not naturally support
  `--flag value` (separate args). Planning should pick between (a) supporting both
  `--tick-format=<value>` and `--tick-format <value>`, or (b) `--tick-format=<value>` only,
  and align with how `--silent` extends if a value form is added later.
- **[Affects R5][Technical]** Exact rendering when remaining time is exactly a minute boundary
  in `human` mode (e.g., `60` → `1m`, not `1m 0s`). Documented in R5; planning confirms the
  conditional logic in shell.
- **[Affects all][Needs research]** Confirm whether the repo has an existing test framework
  for shell scripts (`bats`, plain shell, or none). If none, planning should propose the
  smallest viable harness rather than introduce a heavyweight one.

## Next Steps

→ `/ce:plan` for structured implementation planning.
