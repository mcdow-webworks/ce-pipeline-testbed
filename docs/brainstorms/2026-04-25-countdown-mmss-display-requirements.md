---
date: 2026-04-25
topic: countdown-mmss-display
---

# Format countdown remaining time as MM:SS

## Problem Frame

`countdown.sh` displays the running time as `Time remaining: Xs` where `X`
is a bare second count. For durations of a minute or more this is hard to
read at a glance — a user watching `Time remaining: 4127s` cannot quickly
tell how long they have left. Clock-style formatting (`MM:SS` /
`H:MM:SS`) is the standard mental model for elapsed/remaining time and
costs almost nothing to implement.

## Requirements

- R1. When the remaining whole seconds is `>= 3600`, display as
  `H:MM:SS`. The hour component has no leading zero; minutes and seconds
  are zero-padded to two digits. Example: `3661` → `1:01:01`.
- R2. When the remaining whole seconds is `>= 60` and `< 3600`, display
  as `M:SS` or `MM:SS` — the minute component has no forced leading zero
  (uses as many digits as needed), and the second component is
  zero-padded to two digits. Examples: `90` → `1:30`, `60` → `1:00`,
  `599` → `9:59`, `600` → `10:00`.
- R3. When the remaining whole seconds is `< 60`, display as a bare
  second count with no padding. Examples: `59` → `59`, `5` → `5`,
  `1` → `1`.
- R4. The display label `Time remaining: ` is preserved; only the value
  portion changes shape.
- R5. The format flips live as the countdown crosses each threshold.
  A 90-second countdown therefore prints `1:30`, `1:29`, …, `1:01`,
  `1:00`, `59`, `58`, …, `1`. A 3661-second countdown prints `1:01:01`,
  `1:01:00`, `1:00:59`, …, `1:00:00`, `59:59`, `59:58`, …
- R6. `--silent` mode continues to suppress the per-second line entirely.
- R7. `--help` output is unchanged in wording (no need to document the
  format inside `--help`; the format is observable behavior).
- R8. The final `Time's up!` line is unchanged.

## Success Criteria

- The three issue examples (5s, 90s, 3661s) produce exactly the
  sequences shown in the issue body.
- Running with `--silent` produces no per-second output and ends with
  `Time's up!`.
- Running with `--help` exits 0 with output byte-identical to today's
  `--help` output.
- No leftover characters remain on screen when the format width
  contracts (e.g., the transition `1:00` → `59` must not leave a stale
  `0` at the end of the line).

## Scope Boundaries

- No new flags. No format-string customization, no localization, no
  alternate display modes (e.g. `--format=seconds`).
- No change to error handling, validation, or exit codes.
- No change to `--silent` or `--help` behavior.
- No refactor of the loop structure beyond what the format change
  requires.
- No tests are added in this change. (`countdown.sh` has none today;
  introducing a test harness is a separate scope.)

## Key Decisions

- **Single-digit hours and minutes are not zero-padded.** The issue's
  worked examples use `1:30` (not `01:30`) and `1:01:01` (not
  `01:01:01`). Padding only applies to the components to the right of
  the largest non-zero unit. **Why:** matches the issue's acceptance
  examples exactly; matches the conventional "stopwatch" reading style.
- **Threshold is on the *current* remaining seconds, not the original
  duration.** A countdown started at 90 transitions to bare-seconds at
  the `60 → 59` tick. **Why:** the issue's 90s example explicitly shows
  this transition (`1:00`, `59`, `58`).
- **Line redraw must clear trailing characters when the format
  contracts.** Going from `1:00` (4 chars) to `59` (2 chars) using only
  `\r` would leave `590` on screen. The implementation must either pad
  with trailing spaces or use an explicit clear-to-end-of-line. **Why:**
  raised here so planning does not silently introduce a visual bug.
  *Note: this is a behavioral correctness requirement; the exact
  technique (trailing spaces vs `\033[K`) is a planning/implementation
  decision.*

## Dependencies / Assumptions

- Bash 4+ is available (already required by the existing `(( ... ))`
  arithmetic and `printf` usage in `countdown.sh`).
- Terminal honors `\r` carriage return for line redraw (already assumed
  by the existing implementation).

## Outstanding Questions

### Resolve Before Planning

(none — requirements are concrete enough to plan against.)

### Deferred to Planning

- [Affects R5][Technical] How to clear trailing characters on format
  contraction — pad-with-spaces vs `\033[K` vs printing a fixed-width
  field. Pad-with-spaces is the most portable; the planner should pick
  based on the existing style and choose deliberately.
- [Affects success criteria][Technical] Whether to add even a single
  smoke test (e.g., a fast non-`sleep` codepath, or piping a 5s run to
  a transcript and diffing) is a planning judgment call. Out of scope
  for this brainstorm but worth flagging.

## Next Steps

→ `/ce:plan` for structured implementation planning.
