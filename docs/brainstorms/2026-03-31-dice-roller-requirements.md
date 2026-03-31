---
date: 2026-03-31
topic: dice-roller
---

# Dice Roller CLI

## Problem Frame

Tabletop RPG players and GMs need a quick way to roll dice from the terminal using standard notation (e.g., `2d6`, `1d20+5`). The repo already has CLI utility scripts (`countdown.sh`); this adds another small, self-contained tool.

## Requirements

- R1. Accept dice notation as a positional argument in the form `NdS` (N = number of dice, S = sides per die)
- R2. Support optional modifier: `NdS+M` (addition) and `NdS-M` (subtraction), where M is a non-negative integer
- R3. Default to `1d6` when no argument is provided
- R4. Print the total result of the roll
- R5. `--verbose` flag shows individual die results alongside the total (e.g., `Rolls: 3 5 2 | Total: 10`)
- R6. `--help` flag prints usage information with notation examples, then exits
- R7. Validate input and reject with a clear error message:
  - Zero dice (`0d6`)
  - Zero sides (`1d0`)
  - Non-numeric or malformed notation
- R8. Exit with non-zero status on validation errors
- R9. Use `$RANDOM` or `/dev/urandom` for randomness (no external dependencies)

## Scope Boundaries

- Single roll expression per invocation (no `2d6+1d8` compound expressions)
- No persistent history or statistics tracking
- No interactive/prompt mode — single invocation only
- No percentile dice (`d%`) or exploding dice notation — standard `NdS[+/-M]` only
- Shorthand `d20` (omitting N=1) is nice-to-have but not required

## Success Criteria

- Script runs in bash without external dependencies
- All acceptance criteria from the issue are met
- Follows the same conventions as `countdown.sh` (argument parsing style, error output to stderr, help format)

## Key Decisions

- **Single script, no library extraction**: Same pattern as `countdown.sh` — one self-contained file
- **Default output is concise**: Without `--verbose`, just print the total. Verbose adds the breakdown. This keeps piping/scripting friendly
- **Modifier in notation string, not separate flag**: `3d8+5` is the standard tabletop convention and more natural than `--modifier 5`

## Outstanding Questions

### Deferred to Planning

- [Affects R5][Technical] Exact output format for verbose mode (delimiter style, labeling)
- [Affects R9][Technical] Whether `$RANDOM` modulo bias matters for typical dice sizes, or if it's acceptable for a casual tool

## Next Steps

-> `/ce:plan` for structured implementation planning
