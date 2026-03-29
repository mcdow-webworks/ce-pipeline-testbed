---
title: "feat: Add weather CLI mock forecast script"
type: feat
status: completed
date: 2026-03-29
origin: docs/brainstorms/2026-03-29-weather-cli-requirements.md
---

# feat: Add weather CLI mock forecast script

## Overview

Add a standalone `weather.sh` bash script that prints a hardcoded 3-day weather forecast for a given city, with optional Celsius conversion and help output.

## Problem Frame

The project needs a simple CLI weather utility. All forecast data is hardcoded — no API calls. The script accepts an optional city name, supports a `--units celsius` flag for temperature conversion, and a `--help` flag for usage info. (see origin: docs/brainstorms/2026-03-29-weather-cli-requirements.md)

## Requirements Trace

- R1. Accept optional city name argument; default to "Springfield"
- R2. Print single-line 3-day forecast: `<City> forecast for <date>: <Day1> <temp> <condition>, <Day2> <temp> <condition>, <Day3> <temp> <condition>`
- R3. Day abbreviations (Mon, Tue, etc.) reflect actual days starting from today's date
- R4. `--units celsius` flag displays temperatures in Celsius
- R5. Celsius conversion: `(F - 32) * 5 / 9`, rounded to nearest integer
- R6. `--help` flag prints usage and exits
- R7. Forecast data is entirely hardcoded

## Scope Boundaries

- No real weather data or API integration
- No units beyond Fahrenheit and Celsius
- Always exactly 3 days — no range selection
- No colored output or formatting beyond single-line
- No installation or packaging — standalone script

## Context & Research

### Relevant Code and Patterns

- `hello.sh` (branch `claude/issue-3`, commit `1896736`) — closest prior art for script structure: `#!/usr/bin/env bash` shebang, `cat <<'USAGE'` heredoc for help, `case` argument parsing, `date +%Y-%m-%d` for date formatting
- Executable permission must be set via `git update-index --chmod=+x` on Windows
- Scripts placed at repo root

### Institutional Learnings

- None — `docs/solutions/` does not exist yet

## Key Technical Decisions

- **Flexible argument parsing with `while`/`shift` loop**: Unlike `hello.sh` which only checked `$1`, `weather.sh` has both a positional city argument and flag arguments. A `while`/`shift` loop allows flags in any position (e.g., both `weather.sh --units celsius Boston` and `weather.sh Boston --units celsius` work). (Resolves deferred question from origin doc)
- **Date format `YYYY-MM-DD`**: Matches the issue example and is consistent with `hello.sh` precedent using `date +%Y-%m-%d`. Not locale-dependent. (Resolves deferred question from origin doc)
- **Celsius rounding via shell integer arithmetic**: Use `$(( (F - 32) * 5 / 9 ))` or equivalent with rounding correction, avoiding dependency on `bc` or `awk`. Shell arithmetic with a rounding trick `$(( ((F - 32) * 5 + 9/2) / 9 ))` keeps the script dependency-free.
- **Three hardcoded forecast entries**: Fixed temperatures (72, 65, 58) and conditions (Sunny, Cloudy, Rain) matching the issue example.

## Open Questions

### Resolved During Planning

- **Argument parsing order** (from origin doc): Resolved — use `while`/`shift` loop for flexible ordering
- **Date format convention** (from origin doc): Resolved — `YYYY-MM-DD`, consistent with issue example and `hello.sh`

### Deferred to Implementation

- **Exact rounding behavior at boundary values**: Integer arithmetic rounding may differ by 1 degree from floating-point in edge cases. Acceptable given hardcoded data.

## Implementation Units

- [x] **Unit 1: Create weather.sh with core forecast output**

  **Goal:** Create the script with argument parsing, help output, default city handling, and Fahrenheit forecast display.

  **Requirements:** R1, R2, R3, R6, R7

  **Dependencies:** None

  **Files:**
  - Create: `weather.sh`

  **Approach:**
  - Shebang: `#!/usr/bin/env bash`
  - Help function using `cat <<'USAGE'` heredoc (matching `hello.sh` pattern)
  - `while`/`shift` loop for argument parsing: recognize `--help`, `--units` with its value, and collect remaining positional arg as city
  - Default city via variable default: `${city:-Springfield}`
  - Compute today's date with `date +%Y-%m-%d` and day abbreviations with `date +%a` offset by 0, 1, 2 days
  - Three hardcoded entries: 72/Sunny, 65/Cloudy, 58/Rain
  - Print single-line output matching the exact format from R2

  **Patterns to follow:**
  - `hello.sh` shebang, heredoc help, and `echo` output style

  **Test scenarios:**
  - No arguments: prints `Springfield forecast for <today>: <Day1> 72°F Sunny, <Day2> 65°F Cloudy, <Day3> 58°F Rain`
  - City argument: `weather.sh Boston` prints `Boston forecast for ...`
  - `--help`: prints usage info and exits with 0
  - Unknown flag: reasonable behavior (ignore or error)

  **Verification:**
  - Script runs without errors on bash
  - Output matches the format specified in R2
  - Day abbreviations match actual current weekday names

- [x] **Unit 2: Add Celsius conversion support**

  **Goal:** Implement `--units celsius` flag to convert hardcoded Fahrenheit temperatures to Celsius.

  **Requirements:** R4, R5

  **Dependencies:** Unit 1

  **Files:**
  - Modify: `weather.sh`

  **Approach:**
  - Track `units` variable from argument parsing (already handled in Unit 1's `while`/`shift` loop)
  - When `units` is `celsius`, convert each temperature using integer arithmetic with rounding: `$(( ((F - 32) * 5 + 4) / 9 ))` (adding half-divisor for rounding)
  - Display `°C` suffix instead of `°F`
  - Validate that only `celsius` is accepted as a units value; default is Fahrenheit

  **Patterns to follow:**
  - Bash arithmetic expansion `$(( ... ))`

  **Test scenarios:**
  - `--units celsius`: 72°F -> 22°C, 65°F -> 18°C, 58°F -> 14°C
  - `--units celsius` with city: `weather.sh --units celsius Boston`
  - `--units celsius` after city: `weather.sh Boston --units celsius`
  - Invalid units value: reasonable error or fallback

  **Verification:**
  - Celsius values are correctly rounded integers
  - Output format uses `°C` suffix
  - Flag works regardless of position relative to city argument

- [x] **Unit 3: Set executable permission and verify end-to-end**

  **Goal:** Ensure the script has executable permission in git and passes all acceptance criteria.

  **Requirements:** All (R1-R7)

  **Dependencies:** Unit 2

  **Files:**
  - Modify: `weather.sh` (git permission)

  **Approach:**
  - Use `git update-index --chmod=+x weather.sh` to set executable bit in the git index (required on Windows)
  - Run the script with all argument combinations to verify

  **Patterns to follow:**
  - `hello.sh` required the same permission fix on Windows

  **Test scenarios:**
  - `bash weather.sh` — default Springfield Fahrenheit output
  - `bash weather.sh Chicago` — custom city
  - `bash weather.sh --units celsius` — Celsius conversion
  - `bash weather.sh Chicago --units celsius` — city + Celsius
  - `bash weather.sh --help` — usage info

  **Verification:**
  - All acceptance criteria from the issue pass
  - Script file is marked executable in git index

## Risks & Dependencies

- **Windows date command compatibility**: `date` on Git Bash (MSYS2) supports GNU date flags like `date -d "+1 day"`. If date offset syntax differs, the day abbreviation calculation may need adjustment. Mitigated by testing during implementation.
- **No automated tests**: This is a standalone script with no test framework. Verification is manual. Acceptable given the minimal scope.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-29-weather-cli-requirements.md](docs/brainstorms/2026-03-29-weather-cli-requirements.md)
- Related prior art: `hello.sh` on branch `claude/issue-3`
