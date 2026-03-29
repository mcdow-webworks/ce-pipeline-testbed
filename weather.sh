#!/usr/bin/env bash

show_help() {
  cat <<'USAGE'
Usage: weather.sh [OPTIONS] [CITY]

Print a mock 3-day weather forecast for the given city.

Arguments:
  CITY              City name (default: Springfield)

Options:
  --units celsius   Display temperatures in Celsius
  --help            Show this help message and exit

Examples:
  weather.sh
  weather.sh Boston
  weather.sh --units celsius
  weather.sh Chicago --units celsius
USAGE
}

# Defaults
city=""
units="fahrenheit"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help)
      show_help
      exit 0
      ;;
    --units)
      units="$2"
      shift 2
      ;;
    *)
      city="$1"
      shift
      ;;
  esac
done

city="${city:-Springfield}"

# Today's date
today=$(date +%Y-%m-%d)

# Day abbreviations for today, tomorrow, day after
day1=$(date +%a)
day2=$(date -d "+1 day" +%a 2>/dev/null || date -v+1d +%a)
day3=$(date -d "+2 days" +%a 2>/dev/null || date -v+2d +%a)

# Hardcoded forecast data (Fahrenheit)
temps=(72 65 58)
conditions=("Sunny" "Cloudy" "Rain")

# Convert to Celsius if requested
if [[ "$units" == "celsius" ]]; then
  suffix="C"
  for i in 0 1 2; do
    f=${temps[$i]}
    temps[$i]=$(( ((f - 32) * 5 + 4) / 9 ))
  done
else
  suffix="F"
fi

echo "$city forecast for $today: $day1 ${temps[0]}°$suffix ${conditions[0]}, $day2 ${temps[1]}°$suffix ${conditions[1]}, $day3 ${temps[2]}°$suffix ${conditions[2]}"
