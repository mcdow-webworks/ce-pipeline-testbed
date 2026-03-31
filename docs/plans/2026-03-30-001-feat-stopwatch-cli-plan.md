---
title: "feat: Add stopwatch CLI with lap tracking"
type: feat
status: completed
date: 2026-03-30
origin: docs/brainstorms/2026-03-30-stopwatch-cli-requirements.md
---

# feat: Add stopwatch CLI with lap tracking

## Overview

Add a `stopwatch.sh` script that counts up from zero, displays elapsed time with millisecond precision, supports lap/split recording via SIGUSR1, and prints a lap summary on exit. This is a natural companion to the existing `countdown.sh`.

## Problem Frame

The repo has `countdown.sh` for counting down from a duration. Users also need the inverse: a stopwatch that counts up from zero with split/lap tracking for timing intervals. (see origin: `docs/brainstorms/2026-03-30-stopwatch-cli-requirements.md`)

## Requirements Trace

- R1. Script starts counting up from 0 when launched with no arguments
- R2. Display updates frequently (~100ms) and shows elapsed time with millisecond precision: `Elapsed: 1m 23s 456ms` (with `Xh` prefix when >= 1 hour)
- R3. Support a `--lap` flag that enables lap recording mode
- R4. In lap mode, sending SIGUSR1 records a split time without stopping the stopwatch
- R5. On exit via Ctrl+C (SIGINT), print a summary of all recorded laps with lap number, split time, and cumulative time
- R6. `--help` flag prints usage information and exits
- R7. Follow the same arg-parsing and structural conventions as `countdown.sh`

## Scope Boundaries

- No pause/resume functionality
- No output-to-file option
- No interactive keyboard input for laps (use SIGUSR1 signal instead)

## Context & Research

### Relevant Code and Patterns

- `countdown.sh` — establishes conventions for:
  - Shebang: `#!/usr/bin/env bash`
  - Arg parsing: `for arg in "$@"; do case "$arg" in` pattern
  - Help text: heredoc with `cat <<'USAGE'` format
  - In-place display: `printf "\r"` with format strings
  - Input validation after arg parsing
  - Clean final output with `printf "\n"` before final message

### Institutional Learnings

- No `docs/solutions/` entries exist yet.

## Key Technical Decisions

- **Millisecond precision via epoch timestamps:** Instead of incrementing a counter with `sleep 1`, capture the start time using `date +%s%N` (nanosecond epoch) and compute elapsed time as the difference between current time and start time. This gives accurate ms display and avoids drift from `sleep` imprecision. (see origin: `docs/brainstorms/2026-03-30-stopwatch-cli-requirements.md`)
- **Display update interval ~100ms:** Use `sleep 0.1` in the main loop so the millisecond display updates visibly. Reasonable balance between responsiveness and CPU usage. (see origin: `docs/brainstorms/2026-03-30-stopwatch-cli-requirements.md`)
- **Lap trigger via SIGUSR1:** Since the script runs a blocking `sleep` loop, interactive keypress detection is complex in pure bash. Using `kill -USR1 <pid>` to record laps is simple, portable, and avoids dependencies. The help text will document this. (see origin: `docs/brainstorms/2026-03-30-stopwatch-cli-requirements.md`)
- **Hours display:** Show `Xh Ym Zs Xms` format when elapsed time >= 3600 seconds for readability. Below that threshold, use `Xm Ys Xms`.
- **Lap summary format:** Plain-text columns — `Lap  Split  Elapsed` — printed to stdout on SIGINT exit, with millisecond precision in all time values. Consistent with the terminal-first aesthetic of the repo.
- **SIGUSR1 trap only when `--lap` is active:** Without `--lap`, SIGUSR1 is not trapped, keeping behavior predictable.
- **Exit code 0 on Ctrl+C:** The SIGINT trap prints the summary and exits cleanly with code 0 rather than the default 130.

## Open Questions

### Resolved During Planning

- **Hours format:** Show `1h 2m 3s 456ms` when >= 3600s rather than `62m 3s 456ms`. More natural to read and trivial to implement.
- **Lap summary columns:** Three columns — lap number, split time since last lap, cumulative elapsed time. Example:
  ```
  Lap  Split            Elapsed
  #1   0m 32s 456ms     0m 32s 456ms
  #2   1m 05s 123ms     1m 37s 579ms
  ```
- **Portability of `date +%s%N`:** GNU date supports `%N` but macOS/BSD `date` does not. Target environment is Linux/Git Bash where `%N` is available. No fallback — add a note in help text or fail early if `%N` is unsupported.

### Deferred to Implementation

- Exact helper function naming for time formatting (e.g., `format_time`) — will be determined during implementation based on what reads cleanly.

## Implementation Units

- [x] **Unit 1: Core stopwatch with help and display**

  **Goal:** Create `stopwatch.sh` with arg parsing, `--help` output, and the main counting loop that displays elapsed time in-place with millisecond precision.

  **Requirements:** R1, R2, R6, R7

  **Dependencies:** None

  **Files:**
  - Create: `stopwatch.sh`

  **Approach:**
  - Mirror `countdown.sh` structure: shebang, defaults, arg-parsing loop, main loop
  - Arg parsing handles `--help`, `--lap` (sets a flag), and unknown args (print error to stderr, exit 1). Unlike `countdown.sh`, stopwatch takes no positional args — reject unknown arguments
  - Capture start time with `date +%s%N` before the loop
  - Time formatting function converts elapsed nanoseconds to `Xh Ym Zs Xms` or `Xm Ys Xms` string (hours only when >= 3600s)
  - Main loop: infinite `while true` with `sleep 0.1`, computing elapsed as `$(date +%s%N) - START_NS`, displaying via `printf "\r"`
  - Basic SIGINT trap that prints a newline and exits cleanly (no lap summary yet)

  **Patterns to follow:**
  - `countdown.sh` — arg parsing structure, help text format, `printf "\r"` display

  **Test scenarios:**
  - Running with no args starts counting from `0m 0s 000ms`
  - `--help` prints usage and exits 0
  - Unknown flag prints error to stderr and exits 1
  - Display updates in-place approximately every 100ms with visible millisecond changes
  - Ctrl+C exits cleanly with a newline (no partial line left)
  - Elapsed time >= 3600s shows hours prefix

  **Verification:**
  - Script is executable and runs under bash
  - `./stopwatch.sh --help` prints usage matching `countdown.sh` style
  - Running the script shows `Elapsed: 0m 0s 000ms` updating with millisecond precision
  - Ctrl+C produces a clean exit

- [x] **Unit 2: Lap recording and summary**

  **Goal:** Add SIGUSR1-based lap recording when `--lap` is passed, and print a formatted lap summary on SIGINT exit.

  **Requirements:** R3, R4, R5

  **Dependencies:** Unit 1

  **Files:**
  - Modify: `stopwatch.sh`

  **Approach:**
  - When `--lap` is active, trap SIGUSR1 to record the current elapsed nanoseconds
  - Track both the cumulative time and the split (time since last lap) for each lap entry using bash arrays
  - On SIGINT, if laps were recorded, print a formatted summary table (with ms precision) before exiting
  - If no laps were recorded (even with `--lap`), just exit cleanly as in Unit 1
  - Help text updated to document `--lap` flag and SIGUSR1 usage, including `kill -USR1 <pid>` example

  **Patterns to follow:**
  - Bash arrays for lap storage
  - `trap` for SIGUSR1 and SIGINT signal handling

  **Test scenarios:**
  - `--lap` with no SIGUSR1 sent: exits cleanly with no summary
  - `--lap` with one SIGUSR1: prints one-row summary on exit
  - `--lap` with multiple SIGUSR1: prints multi-row summary with correct splits and cumulative times (all with ms precision)
  - Without `--lap`: SIGUSR1 has no effect
  - Summary format matches planned column layout

  **Verification:**
  - Run `./stopwatch.sh --lap &`, send `kill -USR1 $!` one or more times, then `kill -INT $!`
  - Lap summary prints with correct lap numbers, split times, and cumulative elapsed times, all with millisecond precision
  - Help text documents the `--lap` flag and SIGUSR1 mechanism

## System-Wide Impact

- **Interaction graph:** Standalone script with no callbacks or dependencies on other repo code
- **Error propagation:** Errors (bad flags) go to stderr with exit 1; normal exit is 0
- **State lifecycle risks:** None — all state is in-memory (shell variables/arrays) for the script's lifetime
- **API surface parity:** N/A — no external API
- **Integration coverage:** Manual verification is sufficient for a standalone CLI script

## Risks & Dependencies

- **Signal availability:** SIGUSR1 is standard on POSIX systems but may not be available on all environments (e.g., some minimal containers). Low risk for the target use case.
- **`date +%s%N` portability:** GNU `date` supports `%N` (nanoseconds) but macOS/BSD `date` does not. The script targets Linux and Git Bash environments where `%N` is available. If unsupported, the script will produce incorrect output. Acceptable per scope boundaries.
- **Sleep precision:** `sleep 0.1` precision varies by system. Display update rate may not be exactly 100ms but will be close enough for visual feedback. Elapsed time accuracy is unaffected since it is computed from epoch timestamps, not sleep intervals.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-30-stopwatch-cli-requirements.md](docs/brainstorms/2026-03-30-stopwatch-cli-requirements.md)
- Related code: `countdown.sh`
- Related issue: #10
