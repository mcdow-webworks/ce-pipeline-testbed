---
title: Format countdown remaining time as MM:SS
type: feat
status: active
date: 2026-04-25
origin: docs/brainstorms/2026-04-25-countdown-mmss-display-requirements.md
---

# Format countdown remaining time as MM:SS

## Overview

`countdown.sh` currently renders the per-second display as `Time remaining: Xs`
(bare seconds with an `s` suffix). For durations ≥ 1 minute this is hard to
read at a glance. This plan changes the value portion of that line into
clock-style formatting that flips bands live as time elapses:

- `< 60s` → bare seconds (`5`, `59`)
- `>= 60s, < 3600s` → `M:SS` / `MM:SS` (`1:30`, `10:00`)
- `>= 3600s` → `H:MM:SS` (`1:01:01`)

The label `Time remaining: ` and all non-display behavior (`--silent`,
`--help`, validation, exit codes, `Time's up!` final line) are preserved.

## Problem Frame

A user watching `Time remaining: 4127s` cannot quickly read how long is
left. Clock formatting is the conventional mental model for elapsed/
remaining time and is virtually free to implement. The change is purely a
display refinement (see origin: `docs/brainstorms/2026-04-25-countdown-mmss-display-requirements.md`).

## Requirements Trace

- **R1.** Render `H:MM:SS` for remaining seconds `>= 3600` (no leading zero
  on the hour component).
- **R2.** Render `M:SS` / `MM:SS` for remaining seconds in `[60, 3600)`
  (no forced leading zero on the minute component).
- **R3.** Render bare unpadded seconds for remaining seconds `< 60`.
- **R4.** Preserve the `Time remaining: ` label.
- **R5.** Format flips live as the countdown crosses each band threshold.
- **R6.** `--silent` mode unchanged.
- **R7.** `--help` output byte-identical to today's output.
- **R8.** Final `Time's up!` line unchanged.

## Scope Boundaries

- No new flags. No localization. No `--format=` customization.
- No changes to argument parsing, validation, or exit codes.
- No automated tests added in this change. (`countdown.sh` has none today;
  introducing a test harness is a separate scope, see *Documentation /
  Operational Notes* below.)
- No refactor of the loop structure beyond what the format change
  necessitates.

## Context & Research

### Relevant Code and Patterns

- `countdown.sh` — single-file bash script. Already uses `(( ... ))`
  arithmetic, `printf`, and `\r` carriage return for the live tick. The
  format-bands logic and width-padding fit naturally inside the existing
  loop without restructuring it.
- The script's existing style: function-free, top-to-bottom, single
  responsibility. Adding one tightly-scoped helper (`format_remaining`)
  is consistent with that style without over-abstracting.

### Institutional Learnings

- `docs/solutions/` was scanned; no entries are directly relevant to
  bash `printf` formatting or live-redraw correctness. No prior
  countdown-related learnings exist.

### External References

- Not needed. Bash arithmetic, integer division, and `printf` field-width
  padding are all unchanging POSIX/Bash 4 behavior already exercised
  elsewhere in the script.

## Key Technical Decisions

- **Extract a small `format_remaining()` helper rather than inlining a
  three-branch conditional inside the printf call.** The helper isolates
  the band logic, names it, and keeps the redraw site readable
  (`printf "\rTime remaining: %-${WIDTH}s" "$(format_remaining $i)"`).
  Rationale: the band selection is the only nontrivial logic in the
  change; giving it a name pays for itself in clarity at zero cost.

- **Resolve format contraction with `printf` left-aligned width
  padding** (`%-${WIDTH}s`), where `WIDTH` is computed once before the
  loop as the character length of the formatted initial `DURATION`.
  Rationale: the initial tick is necessarily the widest the formatted
  value will ever be (formatted length is monotonic non-increasing as
  seconds tick down — both within a band and across band transitions).
  Padding to that width makes every shorter render naturally overwrite
  the residue of the previous render. Chosen over `\033[K` because it
  introduces no new terminal-feature assumption beyond what the script
  already makes (`\r`), and chosen over manually appending trailing
  spaces because `printf` already provides this primitive.

- **Drop the `s` suffix entirely from the live tick.** The origin
  document's worked examples (`5`, `4`, …, `1`; `59`, `58`, …) explicitly
  show no suffix. The suffix only made sense in the bare-seconds-only
  world; in the new mixed format it would read as an inconsistency
  (`1:30s`, `59s`).

- **No `--silent` / `--help` code changes.** Both bypass the live tick
  entirely; preserving them costs nothing because the new code is
  scoped to the redraw printf path that `--silent` already skips.

## Open Questions

### Resolved During Planning

- **How to clear trailing characters when the format contracts** (e.g.,
  `1:00` → `59` leaving `:0` ghosts under naive `\r`). **Resolution:**
  use `printf "%-${WIDTH}s"` with `WIDTH` computed from the initial
  formatted `DURATION`. See the second key technical decision above.
- **Whether to add a smoke test in this change.** **Resolution:** no.
  The origin document explicitly excludes tests from scope; the change
  is small, manually verifiable, and a test harness for `countdown.sh`
  is a separately scoped initiative.

### Deferred to Implementation

- (none — implementation can proceed without further discovery.)

## Implementation Units

- [ ] **Unit 1: Render remaining time as MM:SS / H:MM:SS in `countdown.sh`**

**Goal:** Replace the bare-seconds tick output with banded clock-style
formatting that flips live across thresholds and redraws cleanly when
the format contracts.

**Requirements:** R1, R2, R3, R4, R5, R6, R7, R8

**Dependencies:** None.

**Files:**
- Modify: `countdown.sh`

**Approach:**
- Add a small helper `format_remaining()` that takes a non-negative
  integer second count and prints the formatted string using three
  bands:
  - `>= 3600` → `H:MM:SS` (hours unpadded; minutes and seconds
    zero-padded to two digits)
  - `>= 60` → `M:SS` / `MM:SS` (minutes unpadded; seconds zero-padded)
  - else → bare integer seconds
- Compute `WIDTH` once, before the countdown loop, as the character
  length of `format_remaining "$DURATION"`. This is the widest any
  tick in this run will ever be.
- Inside the existing loop, replace the current
  `printf "\rTime remaining: %ds" "$i"` line with a call that prints
  `format_remaining $i` into a `%-${WIDTH}s` left-aligned field, so
  shorter renders are space-padded to the original width and overwrite
  any residue from the prior render.
- Leave `--silent` and `--help` paths, validation, and the final
  `Time's up!` line untouched.

**Patterns to follow:**
- Existing top-to-bottom procedural style of `countdown.sh`.
- Existing `(( ... ))` arithmetic and `printf` usage already in the
  file (do not introduce `bc`, `awk`, `date`, or external tools — the
  formatting is integer arithmetic only).
- Existing carriage-return-based redraw pattern.

**Test scenarios** *(manual verification; no automated harness exists):*
- `./countdown.sh 5` prints `Time remaining: 5`, then `4`, `3`, `2`,
  `1`, then `Time's up!`. No `s` suffix, no leading zeros.
- `./countdown.sh 90` starts at `Time remaining: 1:30` and ticks down
  through `1:01`, `1:00`, then `59`, `58`, … `1`, `Time's up!`.
- `./countdown.sh 60` starts at `1:00` and crosses to `59` cleanly
  (no `:0` ghost trailing the `59`).
- `./countdown.sh 3661` starts at `1:01:01` and ticks `1:01:00`,
  `1:00:59`, … (band transitions H:MM:SS → MM:SS at `59:59`, then
  → bare seconds at `59`, all without leftover characters).
- `./countdown.sh 600` starts at `10:00`. As it ticks toward `9:59`
  the format contracts by one minute digit; verify no stale `0`
  on screen.
- `./countdown.sh --silent 3` produces no per-second output and
  prints `Time's up!` at the end.
- `./countdown.sh --help` produces output byte-identical to the
  pre-change `--help` and exits 0.
- `./countdown.sh 0` and `./countdown.sh abc` still produce the
  existing error message on stderr and exit 1 (validation path
  untouched).

**Verification:**
- Visual inspection of the four band-transition cases above shows no
  stale characters on the line at any tick.
- The three issue acceptance examples (5s, 90s, 3661s) produce
  exactly the sequences shown in the issue body.
- `--silent` and `--help` behavior is observably unchanged.
- Final line is `Time's up!` regardless of duration.

## System-Wide Impact

- **Interaction graph:** `countdown.sh` has no callers in this repo.
  No CI, no other script, and no documentation reference invokes it
  with assumptions about the output format. The display change is
  user-observable only.
- **Error propagation:** Unaffected. The error path (`exit 1` on
  invalid input) is upstream of the format change.
- **State lifecycle risks:** None. The script is stateless and
  short-lived.
- **API surface parity:** N/A — there is no parallel surface.
- **Integration coverage:** Manual verification of the band
  transitions covers what would otherwise be an integration concern.

## Risks & Dependencies

- **Risk: terminal width too narrow to fit `Time remaining: H:MM:SS`
  on a single line.** The script already assumed a terminal that
  honors `\r`; a too-narrow terminal would already wrap the existing
  `Time remaining: 3661s` output. This change does not regress that
  assumption (the new widest payload, e.g., `1:01:01`, is shorter
  than `3661s` on equivalent inputs in many cases and only marginally
  longer in edge ones). No mitigation warranted.
- **Risk: locale changes affecting `printf` numeric formatting.** The
  `%d` and `%02d` conversions are not locale-sensitive in bash's
  builtin `printf`. No mitigation needed.
- **Dependency: Bash 4+.** Already required by the script's existing
  use of `(( ... ))`. No new dependency introduced.

## Documentation / Operational Notes

- `--help` text is intentionally not updated to describe the new
  format; it remains a behavioral observation, per R7 of the origin
  document.
- `CHANGELOG.md` has an `[Unreleased] / Changed` slot; consider noting
  the display format change there during implementation. (Not strictly
  required by the origin doc, but the changelog convention is already
  established in this repo.)
- Future opportunity (out of scope here): introducing even a minimal
  smoke-test harness for `countdown.sh` (e.g., a `--tick-fn` injection
  or a sleep-skipping test mode) would let the band-transition
  behavior be locked down by an automated check rather than manual
  inspection. Surfaced for future planning, not for this change.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-25-countdown-mmss-display-requirements.md](../brainstorms/2026-04-25-countdown-mmss-display-requirements.md)
- Related code: `countdown.sh`
- Related issues: #99
