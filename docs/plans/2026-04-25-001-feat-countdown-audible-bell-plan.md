---
title: "feat: Add audible bell to countdown completion"
type: feat
status: completed
date: 2026-04-25
origin: docs/brainstorms/2026-04-25-countdown-bell-requirements.md
---

# feat: Add Audible Bell to Countdown Completion

## Overview

`countdown.sh` prints "Time's up!" at zero but emits no audible cue. This plan adds a system bell (`\a`) at zero, keeps the existing `--silent` flag fully silent (no bell), and introduces a `--no-bell` flag for users who want the visual countdown without sound.

## Problem Frame

Users who step away from their screen receive no notification when the countdown expires. A terminal bell (`\a`) is the lightweight, universally available solution — no audio libraries or OS-specific APIs needed. (see origin: docs/brainstorms/2026-04-25-countdown-bell-requirements.md)

## Requirements Trace

- R1. Emit `\a` at zero before "Time's up!" in a normal run.
- R2. `--silent` suppresses the bell — silent means fully silent, no visual output and no bell.
- R3. Add `--no-bell` flag that suppresses the bell while keeping visual countdown and "Time's up!" intact.
- R4. Document `--silent` and `--no-bell` in the `--help` output.

## Scope Boundaries

- No changes to countdown timing logic.
- No changes to existing `--silent` visual-suppression behavior.
- Bell is a single `printf '\a'` — no audio libraries or OS-specific sound APIs.

## Context & Research

### Relevant Code and Patterns

- `countdown.sh` — sole implementation file; argument parsing uses a `for arg in "$@"` case-statement with boolean flag variables (`SILENT=false`); output via `printf`/`echo`.

## Key Technical Decisions

- **Bell before "Time's up!"**: Audible cue fires first so the sound draws attention before the user reads the message. (see origin)
- **`--silent` fully suppresses bell**: Consistent with the flag's existing intent — "silent" means no output of any kind.
- **`--no-bell` is additive**: Keeps all visual output intact; removes only the bell. Implemented as a separate boolean `NO_BELL` alongside the existing `SILENT`.
- **`printf '\a'`**: Standard portable bell — no external dependency, works across POSIX terminals.

## Open Questions

### Resolved During Planning

- **Should `--silent` suppress the bell?** Yes — "silent" is fully silent. (see origin)
- **Where should the bell fire relative to "Time's up!"?** Before, so sound draws attention first. (see origin)

### Deferred to Implementation

- None. All decisions are settled; the scope is fully contained within a single shell script.

## Implementation Units

- [x] **Unit 1: Add bell emission and `--no-bell` flag to `countdown.sh`**

**Goal:** Emit `\a` at countdown zero, suppressed by `--silent` or `--no-bell`; document both flags in `--help`.

**Requirements:** R1, R2, R3, R4

**Dependencies:** None

**Files:**
- Modify: `countdown.sh`

**Approach:**
- Add `NO_BELL=false` default alongside existing `SILENT=false`.
- Add `--no-bell)` case to the argument parser, setting `NO_BELL=true`.
- Emit `printf '\a'` after the countdown loop, guarded: only when `SILENT == false && NO_BELL == false`.
- Update `--help` block to document both `--silent` and `--no-bell` with one-line descriptions.

**Patterns to follow:**
- Existing `SILENT=false` / `--silent` boolean flag pattern in `countdown.sh`.

**Test scenarios:**
- `./countdown.sh 1` — visual countdown, bell at zero, "Time's up!"
- `./countdown.sh 1 --silent` — no countdown display, no bell, only "Time's up!"
- `./countdown.sh 1 --no-bell` — visual countdown and "Time's up!", no bell
- `./countdown.sh --help` — help text includes descriptions for both `--silent` and `--no-bell`

**Verification:**
- `printf '\a'` present in the final output block, gated by `SILENT == false && NO_BELL == false`
- `--no-bell` parsed in the case statement with `NO_BELL=true`
- `--help` output documents both flags

## Risks & Dependencies

- Terminal bell behavior depends on the user's terminal emulator and system audio settings — expected and acceptable. The bell character (`\a`) is a standard POSIX mechanism.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-25-countdown-bell-requirements.md](docs/brainstorms/2026-04-25-countdown-bell-requirements.md)
- Related code: `countdown.sh`
- Related commit: `06c6796 feat(countdown): add audible bell at countdown completion`
