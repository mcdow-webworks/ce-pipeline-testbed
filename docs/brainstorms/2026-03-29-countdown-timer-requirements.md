---
date: 2026-03-29
topic: countdown-timer
---

# Countdown Timer CLI

## Problem Frame

The project needs a simple countdown timer script that users can run from the command line. It should accept a duration, display remaining time, and support silent mode for scripting contexts.

## Requirements

- R1. Accept an optional duration argument in seconds; default to 60 if omitted
- R2. Display countdown in the format `Time remaining: <N>s`, updating each second
- R3. Print `Time's up!` when the countdown reaches zero
- R4. `--help` flag prints usage information and exits
- R5. `--silent` flag suppresses intermediate countdown output; only the final `Time's up!` message prints
- R6. Validate that the duration is a positive integer; reject zero, negative numbers, floats, and non-numeric input with a clear error message and non-zero exit code

## Success Criteria

- Script runs in bash without external dependencies
- All flags and defaults behave as specified
- Invalid input produces a helpful error message and exits non-zero
- Silent mode is useful for scripting (no noisy intermediate output)

## Scope Boundaries

- No progress bar or fancy terminal formatting
- No pause/resume functionality
- No audio or system notification on completion
- Single-file script, no installation process

## Key Decisions

- **Output format uses `\r` carriage return for in-place updates**: Keeps the terminal clean by overwriting the same line. Falls back to newline-per-tick in silent mode (moot since output is suppressed).
- **Duration is positional, flags are GNU-style**: `countdown.sh [--silent] [--help] [SECONDS]` — simple and conventional.

## Outstanding Questions

### Deferred to Planning

- [Affects R2][Technical] Whether to use `\r` (carriage return) for in-place line updates or print a new line each second — both are valid; `\r` is cleaner but may complicate piped output

## Next Steps

-> `/ce:plan` for structured implementation planning
