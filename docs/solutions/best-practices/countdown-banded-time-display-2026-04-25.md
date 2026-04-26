---
title: Banded time display for live countdown CLIs (H:MM:SS / M:SS / bare seconds)
date: 2026-04-25
category: best-practices
module: countdown.sh
problem_type: best_practice
component: tooling
symptoms:
  - "Time remaining: 90s" was hard to scan at a glance for durations longer than a minute
  - Live tick gave no visual landmark for minute or hour boundaries on long countdowns
  - Bare-seconds format scaled poorly to multi-minute or multi-hour timers
root_cause: incomplete_setup
resolution_type: code_fix
severity: low
tags:
  - countdown
  - bash
  - cli
  - time-format
  - carriage-return
  - in-place-update
---

# Banded time display for live countdown CLIs (H:MM:SS / M:SS / bare seconds)

## Problem

`countdown.sh` rendered the live tick as bare seconds with a trailing `s`
(`Time remaining: 90s`). For durations of a minute or more this was hard
to read at a glance, and for multi-hour countdowns there was no
visual cue separating hours from minutes from seconds.

## Symptoms

- A 90-second countdown displayed `90s, 89s, … 61s, 60s, 59s` with no minute boundary
- A 1-hour countdown displayed `3600s` — no hour landmark, no minute landmark
- Operators had to do mental arithmetic to read elapsed/remaining time on long timers

## What Didn't Work

- A naive width-per-tick approach (`WIDTH=${#current}` recomputed every iteration) is wasteful and unnecessary: a countdown is monotonically decreasing, so the formatted value of the *initial* `DURATION` is by construction the widest it will ever be. Pre-compute once before the loop.
- Dropping the `%-${WIDTH}s` left-pad and relying on the terminal's "clear-to-EOL" behavior is fragile: in pipelines, dumb terminals, and `tee`-captured logs there's no clear-to-EOL, so the `\r` cursor return alone leaves stale tail characters on band contractions (e.g., `1:00` → `59` would render as `590`).

## Solution

Three small pieces, in order:

**1. A banded formatter helper.** Three magnitude bands, with two-digit zero-padding only on the trailing fields so the leading field stays compact (`1:30`, not `01:30`).

```bash
format_remaining() {
    local secs=$1
    if (( secs >= 3600 )); then
        printf '%d:%02d:%02d' $(( secs / 3600 )) $(( (secs % 3600) / 60 )) $(( secs % 60 ))
    elif (( secs >= 60 )); then
        printf '%d:%02d' $(( secs / 60 )) $(( secs % 60 ))
    else
        printf '%d' "$secs"
    fi
}
```

**2. Pre-compute display width once from the initial duration.** The initial value is the widest the formatted string will ever be in a monotonically-decreasing loop, so a single bash parameter expansion pins the column width for the rest of the run.

```bash
WIDTH=$(format_remaining "$DURATION")
WIDTH=${#WIDTH}
```

**3. Left-pad the live tick to `WIDTH` so contractions overwrite cleanly under `\r`.**

```bash
for (( i = DURATION; i > 0; i-- )); do
    if [[ "$SILENT" == false ]]; then
        printf "\rTime remaining: %-${WIDTH}s" "$(format_remaining "$i")"
    fi
    sleep 1
done
```

`%-${WIDTH}s` left-justifies and right-pads with spaces, so the string `59` rendered into a 4-wide field becomes `59  ` — overwriting the `:0` ghost from the previous `1:00` frame.

## Why This Works

A live countdown's display has two correctness requirements that are easy to overlook:

1. **The format must communicate the magnitude visibly** — bare seconds works for short timers, but readers parse `M:SS` and `H:MM:SS` an order of magnitude faster for longer ones. Banding the format on order-of-magnitude boundaries (60, 3600) mirrors how humans actually read time.
2. **The tick must overwrite cleanly when the format contracts.** `\r` returns the cursor to column 0 but does not clear what comes after; if the previous frame was 5 characters wide and the current frame is 2 characters wide, three stale characters remain on screen. The fix is to right-pad every frame to a fixed width.

Pre-computing `WIDTH` from `DURATION` before the loop is a free optimization for monotonic countdowns: the initial frame is necessarily the widest, so one strlen substitutes for `DURATION` strlens during the run.

## Prevention

- **For any in-place TTY update under `\r`, fix the column width and pad every frame to it.** This is a general rule for live-updating CLI output, not a countdown-specific trick. Any time a string can contract between frames (a counter, a percentage, an ETA, a download speed), `printf "\r%-${WIDTH}s"` is the right primitive. The alternative — relying on terminal clear-to-EOL — fails silently in pipelines and dumb terminals.
- **Band magnitude-formatted output on order-of-magnitude boundaries.** Bytes (B / KB / MB / GB), durations (s / m / h / d), distances, and percentages all benefit from the same three-band pattern: a low-magnitude raw form, a mid-magnitude compact form, and a high-magnitude full form. Don't unify them under a single format that's awkward at one end of the range.
- **For monotonic loops, derive once-and-only-once values before the loop body.** Width, format strings, totals, and any value that is provably constant across iterations should be computed before the loop, not on each iteration. The proof here is "`format_remaining` is monotonically non-increasing in `secs` for the lengths it produces" — easy to state, easy to verify, worth a one-line comment near the precomputation so a future reader doesn't second-guess and move the computation back inside.
- **Use `printf` (not `echo`) for any output that needs `\r`, padding, or precise control characters.** `echo` portability across shells is a long-standing footgun; `printf` is consistent and supports the `%-${WIDTH}s` directive directly.

A round-trip pattern that would have caught this kind of regression earlier (worth applying to future formatter changes):

```bash
# Snapshot the rendered frames for a representative duration and assert
# every frame has identical width, so any future format change that
# breaks contraction-overwrite shows up as a width-mismatch failure.
DURATION=3661
expected_width=$(format_remaining "$DURATION"); expected_width=${#expected_width}
for i in 3661 3600 599 60 59 1; do
    rendered=$(format_remaining "$i")
    [[ ${#rendered} -le $expected_width ]] || echo "frame width regressed at $i"
done
```

## Related Issues

- GitHub issue #99 — Format countdown remaining time as MM:SS
- Commits: `e66e4a4` (feat), `4c8feca` (ce-review autofix collapsing the single-use `INITIAL_FORMATTED` scratch global)
- Plan: `docs/plans/2026-04-25-001-feat-countdown-mmss-display-plan.md`
- Structurally similar prior solution (CLI formatter, different problem): [`logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`](../logic-errors/table-fmt-respect-column-alignment-2026-04-24.md)
