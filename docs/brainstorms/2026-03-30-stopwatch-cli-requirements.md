---
date: 2026-03-30
topic: stopwatch-cli
---

# Stopwatch CLI

## Problem Frame

The repo has a `countdown.sh` timer that counts down from a given duration. Users also need the inverse: a stopwatch that counts up from zero, tracks elapsed time, and supports lap/split recording for timing intervals.

## Requirements

- R1. Script starts counting up from 0 when launched with no arguments
- R2. Display updates frequently and shows elapsed time with millisecond precision: `Elapsed: 1m 23s 456ms`
- R3. Support a `--lap` flag that enables lap recording mode
- R4. In lap mode, sending SIGUSR1 records a split time without stopping the stopwatch
- R5. On exit via Ctrl+C (SIGINT), print a summary of all recorded laps with lap number, split time, and cumulative time
- R6. `--help` flag prints usage information and exits
- R7. Follow the same arg-parsing and structural conventions as `countdown.sh`

## Success Criteria

- Script runs in bash without external dependencies
- Time display updates in-place with millisecond precision using `\r`
- Lap times are accumulated and printed as a formatted summary on exit
- Ctrl+C is handled gracefully via `trap` — no ugly stack traces
- `--help` output is consistent with `countdown.sh` style

## Scope Boundaries

- No pause/resume functionality
- No output-to-file option
- No interactive keyboard input for laps (use SIGUSR1 signal instead)

## Key Decisions

- **Lap trigger via SIGUSR1:** Since the script runs a blocking `sleep` loop, interactive keypress detection is complex in pure bash. Using `kill -USR1 <pid>` to record laps is simple, portable, and avoids dependencies. The help text will document this usage.
- **Follow countdown.sh patterns:** Arg parsing, help text format, and script structure will mirror the existing `countdown.sh` for consistency.
- **In-place display with `\r`:** Matches the `countdown.sh` approach of using `printf "\r"` for updating the time display.
- **Millisecond precision via epoch timestamps:** Instead of incrementing a counter with `sleep 1`, capture the start time using `date +%s%N` (nanosecond epoch) and compute elapsed time as the difference between current time and start time. This gives accurate ms display and avoids drift from `sleep` imprecision.
- **Display update interval ~100ms:** Use `sleep 0.1` in the main loop so the millisecond display updates visibly. This is a reasonable balance between responsiveness and CPU usage.
- **Time format with ms:** Display as `Elapsed: 1m 23s 456ms`. Laps also show milliseconds in the summary table.

## Outstanding Questions

### Deferred to Planning

- [Affects R2][Technical] Should hours be shown when elapsed time exceeds 60 minutes (e.g., `1h 2m 3s 456ms`), or is `62m 3s 456ms` acceptable?
- [Affects R5][Technical] Exact format for the lap summary table — confirm column layout during implementation
- [Affects R2][Technical] Portability of `date +%s%N` — GNU date supports `%N` (nanoseconds) but macOS/BSD `date` does not. May need a fallback or note in docs. On systems without `%N`, could fall back to second-level precision with a warning.

## Next Steps

→ `/ce:plan` for structured implementation planning
