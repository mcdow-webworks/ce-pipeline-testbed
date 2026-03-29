---
date: 2026-03-29
topic: weather-cli
---

# Weather CLI — Mock Forecast Script

## Problem Frame

The project needs a simple `weather.sh` bash script that prints a hardcoded 3-day weather forecast for a given city. This is a self-contained utility with no external dependencies.

## Requirements

- R1. Accept an optional city name argument; default to "Springfield" when omitted
- R2. Print a single-line mock 3-day forecast in the format: `<City> forecast for <date>: <Day1> <temp> <condition>, <Day2> <temp> <condition>, <Day3> <temp> <condition>`
- R3. Day abbreviations (Mon, Tue, Wed, etc.) should reflect actual days of the week starting from today's date
- R4. Support `--units celsius` flag to display temperatures in Celsius instead of Fahrenheit
- R5. Celsius conversion uses the formula `(F - 32) * 5 / 9`, rounded to the nearest integer
- R6. Support `--help` flag that prints usage information and exits
- R7. Forecast data (temperatures and conditions) is entirely hardcoded — no API calls

## Success Criteria

- Script runs in bash without errors
- Running with no arguments prints a forecast for Springfield in Fahrenheit
- Running with a city name prints a forecast for that city
- `--units celsius` converts all temperatures and displays with `°C` suffix
- `--help` prints clear usage info

## Scope Boundaries

- No real weather data or API integration
- No support for units other than Fahrenheit and Celsius
- No multi-day range selection — always exactly 3 days
- No colored output or formatting beyond the single-line format
- No installation or packaging — just a standalone script

## Key Decisions

- **Single-line output format**: Matches the example in the issue exactly — compact and scriptable
- **Hardcoded forecast data**: Temperatures and conditions are fixed values in the script, not randomized

## Outstanding Questions

### Resolve Before Planning

(none)

### Deferred to Planning

- [Affects R1][Technical] How should the city argument interact with flags? Decide argument parsing order (e.g., `weather.sh --units celsius Boston` vs `weather.sh Boston --units celsius`)
- [Affects R2][Technical] Should the date format be `YYYY-MM-DD` (as in the example) or locale-dependent?

## Next Steps

→ `/ce:plan` for structured implementation planning
