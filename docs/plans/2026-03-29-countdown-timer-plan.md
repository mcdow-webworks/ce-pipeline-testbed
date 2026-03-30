---
date: 2026-03-29
topic: countdown-timer
source: docs/brainstorms/2026-03-29-countdown-timer-requirements.md
---

# Countdown Timer — Implementation Plan

## Overview

Create a single `countdown.sh` bash script at the repository root. The script accepts an optional duration in seconds (default 60), displays a live countdown using carriage return for in-place updates, and supports `--help` and `--silent` flags.

**Complexity:** Low — single file, no dependencies, well-defined acceptance criteria.

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `countdown.sh` | Create | The countdown timer script |

## Implementation Steps

### Step 1: Script skeleton and argument parsing

Create `countdown.sh` with:

- Shebang line (`#!/usr/bin/env bash`)
- Default `DURATION=60` and `SILENT=false`
- Loop through `"$@"` to parse arguments:
  - `--help` → print usage, exit 0
  - `--silent` → set `SILENT=true`
  - Anything else → treat as the duration value
- Allow flags and duration in any order: `countdown.sh --silent 30` or `countdown.sh 30 --silent`

**Usage output for `--help`:**

```
Usage: countdown.sh [OPTIONS] [SECONDS]

Count down from SECONDS (default: 60) and print "Time's up!" at zero.

Options:
  --help     Show this help message and exit
  --silent   Only print the final message
```

### Step 2: Input validation

After parsing, validate the duration value:

- Must match the regex `^[0-9]+$` (digits only — rejects negatives, floats, empty strings, and non-numeric input)
- Must be greater than 0 (rejects `0`)
- On failure, print an error to stderr and exit with code 1

**Error messages:**

- Non-numeric / float / negative: `Error: duration must be a positive integer (got '<value>')`
- Zero: `Error: duration must be a positive integer (got '0')`

### Step 3: Countdown loop

```
for (( i = DURATION; i > 0; i-- )); do
    if [[ "$SILENT" == false ]]; then
        printf "\rTime remaining: %ds" "$i"
    fi
    sleep 1
done
```

- Uses `printf "\r..."` for in-place carriage-return updates (R2, deferred question resolved)
- Silent mode skips the printf entirely (R5)

### Step 4: Final output

After the loop:

- If not silent, print a newline to clear the carriage-return line, then print `Time's up!`
- If silent, just print `Time's up!`

```
if [[ "$SILENT" == false ]]; then
    printf "\n"
fi
echo "Time's up!"
```

### Step 5: Make executable

```bash
chmod +x countdown.sh
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Use `\r` carriage return for display | Cleaner terminal output; single line updates in place. Brainstorm flagged this as deferred — resolved here since it's the conventional approach for countdown displays. |
| Place script at repo root | Simplest location; no `bin/` or `src/` directory exists yet in this repo. |
| Parse args with a simple loop | No need for `getopt`/`getopts` for just two flags. Keeps the script portable and dependency-free. |
| Validate with regex + arithmetic | `^[0-9]+$` catches non-numeric, negative, and float input in one check. Separate `> 0` check catches zero. |
| Print errors to stderr | Standard Unix convention; allows stdout to remain clean for piping. |

## Verification

- `./countdown.sh` → counts down from 60, prints "Time's up!"
- `./countdown.sh 5` → counts down from 5
- `./countdown.sh --silent 5` → waits 5 seconds, prints only "Time's up!"
- `./countdown.sh --help` → prints usage, exits 0
- `./countdown.sh -1` → error to stderr, exit 1
- `./countdown.sh abc` → error to stderr, exit 1
- `./countdown.sh 0` → error to stderr, exit 1
- `./countdown.sh 3.5` → error to stderr, exit 1

## Requirements Traceability

| Requirement | Covered in |
|-------------|------------|
| R1 — Optional duration, default 60 | Step 1 (default), Step 2 (validation) |
| R2 — Display format `Time remaining: <N>s` | Step 3 |
| R3 — Print `Time's up!` at zero | Step 4 |
| R4 — `--help` flag | Step 1 |
| R5 — `--silent` flag | Steps 1, 3, 4 |
| R6 — Validate positive integer | Step 2 |
