---
date: 2026-03-30
topic: stopwatch-cli
---

# Stopwatch CLI

## Problem Frame

The repo has a `countdown.sh` timer that counts down from a given duration. Users also need the inverse: a stopwatch that counts up from zero, tracks elapsed time, and supports lap/split recording for timing intervals.

## Requirements

- R1. Script starts counting up from 0 when launched with no arguments
- R2. Display updates every second in the format: `Elapsed: 1m 23s`
- R3. Support a `--lap` flag that enables lap recording mode
- R4. In lap mode, sending SIGUSR1 records a split time without stopping the stopwatch
- R5. On exit via Ctrl+C (SIGINT), print a summary of all recorded laps with lap number, split time, and cumulative time
- R6. `--help` flag prints usage information and exits
- R7. Follow the same arg-parsing and structural conventions as `countdown.sh`

## Success Criteria

- Script runs in bash without external dependencies
- Time display updates in-place every second using `\r`
- Lap times are accumulated and printed as a formatted summary on exit
- Ctrl+C is handled gracefully via `trap` — no ugly stack traces
- `--help` output is consistent with `countdown.sh` style

## Scope Boundaries

- No pause/resume functionality
- No output-to-file option
- No millisecond precision — second-level granularity only
- No interactive keyboard input for laps (use SIGUSR1 signal instead)

## Key Decisions

- **Lap trigger via SIGUSR1:** Since the script runs a blocking `sleep` loop, interactive keypress detection is complex in pure bash. Using `kill -USR1 <pid>` to record laps is simple, portable, and avoids dependencies. The help text will document this usage.
- **Follow countdown.sh patterns:** Arg parsing, help text format, and script structure will mirror the existing `countdown.sh` for consistency.
- **In-place display with `\r`:** Matches the `countdown.sh` approach of using `printf "\r"` for updating the time display.

## Outstanding Questions

### Deferred to Planning

- [Affects R2][Technical] Should hours be shown when elapsed time exceeds 60 minutes (e.g., `1h 2m 3s`), or is `62m 3s` acceptable?
- [Affects R5][Technical] Exact format for the lap summary table — confirm column layout during implementation

## Next Steps

→ `/ce:plan` for structured implementation planning
