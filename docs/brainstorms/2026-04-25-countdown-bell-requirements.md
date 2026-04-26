---
date: 2026-04-25
topic: countdown-audible-bell
---

# Countdown Audible Bell

## Problem Frame

`countdown.sh` provides a visual countdown but emits no audible cue when the timer expires. Users who step away from their screen receive no notification. The fix is a system bell (`\a`) at zero, with existing `--silent` suppressing it and a new `--no-bell` flag for users who want visuals only.

## Requirements

- R1. Emit a system bell (`\a`) at zero before the "Time's up!" line in a normal (non-silent, non-no-bell) run.
- R2. Suppress the bell when `--silent` is set — silent means no visual output and no bell.
- R3. Add `--no-bell` flag that suppresses the bell while keeping the visual countdown and final "Time's up!" line intact.
- R4. Document `--silent` and `--no-bell` in the `--help` output.

## Success Criteria

- `./countdown.sh 3` produces the visual countdown, an audible bell at zero, and "Time's up!".
- `./countdown.sh 3 --silent` produces only "Time's up!" — no countdown display and no bell.
- `./countdown.sh 3 --no-bell` produces the visual countdown and "Time's up!" but no bell.
- Help text documents both `--silent` and `--no-bell`.

## Scope Boundaries

- No changes to countdown timing logic.
- No changes to the existing `--silent` behavior for visual output.
- Bell is a single `printf '\a'` — no additional audio libraries or OS-specific sound APIs.

## Key Decisions

- **Bell before "Time's up!"**: Audible cue fires first so the sound draws the user's attention before they read the message.
- **`--silent` suppresses bell**: "Silent" is interpreted as fully silent — consistent with the flag's existing intent.
- **`--no-bell` is additive**: Keeps all visual output intact; only removes the bell.

## Next Steps

→ Proceed directly to work (scope is lightweight and all requirements are concrete).
