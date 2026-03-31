---
title: "feat: Add dice roller CLI script"
type: feat
status: active
date: 2026-03-31
origin: docs/brainstorms/2026-03-31-dice-roller-requirements.md
---

# feat: Add dice roller CLI script

## Overview

Add a self-contained `dice.sh` bash script that rolls dice using standard tabletop notation (`NdS[+/-M]`), following the same conventions established by `countdown.sh`.

## Problem Frame

Tabletop RPG players and GMs need a quick terminal-based dice roller that understands standard notation. The repo already has CLI utility scripts; this adds another small, self-contained tool. (see origin: `docs/brainstorms/2026-03-31-dice-roller-requirements.md`)

## Requirements Trace

- R1. Accept dice notation as positional argument: `NdS`
- R2. Support optional modifier: `NdS+M` or `NdS-M`
- R3. Default to `1d6` when no argument provided
- R4. Print total result of the roll
- R5. `--verbose` shows individual die results alongside total (format: `Rolls: 3 5 2 | Total: 10`)
- R6. `--help` prints usage with notation examples, exits 0
- R7. Validate input: reject `0d6`, `1d0`, non-numeric/malformed notation
- R8. Exit non-zero (1) on validation errors
- R9. Use `$RANDOM` for randomness (no external dependencies)

## Scope Boundaries

- Single roll expression per invocation -- no compound expressions like `2d6+1d8`
- No persistent history or statistics
- No interactive/prompt mode
- No percentile dice (`d%`) or exploding dice
- No short flags (`-v`, `-h`) -- long flags only, matching `countdown.sh`

## Context & Research

### Relevant Code and Patterns

- `countdown.sh` -- canonical reference for argument parsing, help format, validation, error output
  - Shebang: `#!/usr/bin/env bash`
  - Arg parsing: `for arg in "$@"` with `case` statement
  - Help: heredoc via `cat <<'USAGE'`, exit 0
  - Errors: `echo "Error: ..." >&2`, exit 1, include bad value in parens
  - Validation: bash regex `=~` for format, then range checks
  - Structure order: defaults, arg parsing, validation, main logic, output

### Institutional Learnings

- No `docs/solutions/` directory exists -- no prior learnings to reference.

### External References

- Not needed. The codebase has clear conventions and this is standard bash scripting.

## Key Technical Decisions

- **Notation parsing via bash regex**: Use `=~ ^([0-9]*)d([0-9]+)([+-][0-9]+)?$` to extract N, S, and optional modifier in one step. Empty N defaults to 1, supporting `d20` shorthand. (see origin: scope boundaries, "nice-to-have")
- **Support `d20` shorthand**: The regex naturally allows omitting N. Cheap to include now; retrofitting later changes the core parser.
- **`$RANDOM % S + 1` for die rolls**: Modulo bias is negligible for typical dice sizes (d4 through d100). Acceptable for a casual tool. (see origin: outstanding questions)
- **Negative totals printed as-is**: `1d4-10` can produce negative results. No clamping -- mathematically correct and predictable for scripting.
- **Error on multiple positional arguments**: Since scope is "single roll expression," providing multiple expressions is an error, not silently using the last one.
- **Upper bounds**: Cap N at 1000 dice and S at 1,000,000 sides to prevent hangs and integer overflow.
- **Default output is just the total**: Pipe-friendly. `--verbose` adds the breakdown line. (see origin: key decisions)
- **Verbose format**: `Rolls: 3 5 2 | Total: 10` -- matches R5 example, clear and parseable.
- **Modifier with verbose**: When modifier is present, verbose shows `Rolls: 3 5 2 | Modifier: +5 | Total: 15`.

## Open Questions

### Resolved During Planning

- **Multiple positional arguments?** Error with message: `"Error: expected a single dice expression, got multiple arguments"`. Matches "single roll expression" scope boundary.
- **`d20` shorthand?** Yes, support it. Optional N capture group with default to 1.
- **Negative totals?** Print as-is. No clamping.
- **Upper bounds?** N <= 1000, S <= 1,000,000. Error if exceeded.
- **Verbose output format?** `Rolls: <space-separated> | Total: <number>`. With modifier: `Rolls: <values> | Modifier: +/-M | Total: <number>`.
- **`$RANDOM` modulo bias?** Acceptable for a casual tool at typical dice sizes.

### Deferred to Implementation

- Exact error message wording for each validation case (follow the `countdown.sh` pattern of `"Error: <description> (got '<value>')"`)

## Implementation Units

- [ ] **Unit 1: Script skeleton with help and argument parsing**

  **Goal:** Create `dice.sh` with the shebang, defaults, argument parsing loop, and `--help` output.

  **Requirements:** R3, R6

  **Dependencies:** None

  **Files:**
  - Create: `dice.sh`

  **Approach:**
  - Follow `countdown.sh` structure exactly: defaults section, `for arg in "$@"` loop with `case`
  - Defaults: `NOTATION="1d6"`, `VERBOSE=false`
  - `--help` branch prints usage heredoc with notation examples (`2d6`, `1d20`, `3d8+5`, `2d6-1`, `d20`) and exits 0
  - `--verbose` branch sets flag
  - `*` branch captures the dice expression; if one is already captured, error on multiple arguments
  - Make script executable

  **Patterns to follow:**
  - `countdown.sh` -- argument parsing structure, help format, shebang

  **Test scenarios:**
  - `./dice.sh --help` prints usage and exits 0
  - `./dice.sh` with no args uses default `1d6`
  - `./dice.sh --verbose 2d6` sets verbose flag and captures notation
  - `./dice.sh 2d6 1d8` errors on multiple expressions

  **Verification:**
  - `--help` prints usage text and exits 0
  - Running with no arguments does not error
  - Multiple positional arguments produce error on stderr and exit 1

- [ ] **Unit 2: Notation parsing and input validation**

  **Goal:** Parse the dice notation string into components (N, S, M) and validate all constraints.

  **Requirements:** R1, R2, R7, R8

  **Dependencies:** Unit 1

  **Files:**
  - Modify: `dice.sh`

  **Approach:**
  - Use bash regex: `^([0-9]*)d([0-9]+)([+-][0-9]+)?$` (case-insensitive not needed -- `d` is lowercase by convention)
  - Extract `BASH_REMATCH` groups: N (default 1 if empty), S, modifier string
  - Validate: N > 0, S > 0, N <= 1000, S <= 1000000
  - Parse modifier: strip sign, store as `MOD_SIGN` (+/-) and `MOD_VALUE`
  - All validation errors go to stderr with exit 1, following `countdown.sh` error format

  **Patterns to follow:**
  - `countdown.sh` -- regex validation (`=~`), error format (`"Error: ... (got '...')"`)

  **Test scenarios:**
  - `2d6` parses to N=2, S=6, no modifier
  - `3d8+5` parses to N=3, S=8, modifier +5
  - `1d20-3` parses to N=1, S=20, modifier -3
  - `d20` parses to N=1, S=20 (shorthand)
  - `0d6` errors: zero dice
  - `1d0` errors: zero sides
  - `abc` errors: malformed notation
  - `2d6+` errors: incomplete modifier
  - `1001d6` errors: too many dice
  - `1d9999999` errors: too many sides

  **Verification:**
  - All invalid inputs produce clear error on stderr and exit 1
  - All valid inputs are accepted without error

- [ ] **Unit 3: Dice rolling and output**

  **Goal:** Implement the core rolling logic and both default and verbose output modes.

  **Requirements:** R4, R5, R9

  **Dependencies:** Unit 2

  **Files:**
  - Modify: `dice.sh`

  **Approach:**
  - Loop N times, each iteration: `roll=$(( RANDOM % S + 1 ))`, accumulate sum, store rolls in a space-separated string for verbose mode
  - Apply modifier to sum: `total=$(( sum + MOD_SIGN MOD_VALUE ))` or equivalent arithmetic
  - Default mode: `echo "$total"`
  - Verbose mode: print `Rolls: <rolls> | Total: <total>` (without modifier) or `Rolls: <rolls> | Modifier: +/-M | Total: <total>` (with modifier)

  **Patterns to follow:**
  - `countdown.sh` -- uses `echo` for final output

  **Test scenarios:**
  - `./dice.sh` prints a number between 1 and 6
  - `./dice.sh 2d6` prints a number between 2 and 12
  - `./dice.sh 3d8+5` prints a number between 8 and 29
  - `./dice.sh 1d6-3` prints a number between -2 and 3
  - `./dice.sh --verbose 2d6` prints `Rolls: X Y | Total: Z` where X, Y are 1-6
  - `./dice.sh --verbose 2d6+3` prints `Rolls: X Y | Modifier: +3 | Total: Z`
  - Default mode output is a single number (pipe-friendly)

  **Verification:**
  - Default output is a single integer on stdout
  - Verbose output includes roll breakdown and total
  - Modifier is reflected in verbose output when present
  - Exit code is 0 on success

## System-Wide Impact

- **Interaction graph:** None -- standalone script with no callbacks or dependencies
- **Error propagation:** Validation errors exit 1 with stderr message; success exits 0
- **State lifecycle risks:** None -- stateless, single invocation
- **API surface parity:** N/A -- no other interfaces
- **Integration coverage:** Manual verification is sufficient for a standalone CLI script

## Risks & Dependencies

- **`$RANDOM` range limitation**: `$RANDOM` produces 0-32767, giving meaningful modulo bias only for S > ~1000. Mitigated by capping S at 1,000,000 and accepting this as a casual tool. Document in `--help`.
- **Bash version compatibility**: `=~` regex and `BASH_REMATCH` require bash 3.0+. This is universally available on modern systems.
- **No test infrastructure**: The repo has no test framework. Verification is manual. This is consistent with the existing `countdown.sh` approach.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-31-dice-roller-requirements.md](docs/brainstorms/2026-03-31-dice-roller-requirements.md)
- Related code: `countdown.sh` (argument parsing, validation, help format conventions)
- Related issue: #12
