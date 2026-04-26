#!/usr/bin/env bash

# Defaults
DURATION=60
SILENT=false
START_MESSAGE=""

# Argument parsing
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help)
            cat <<'USAGE'
Usage: countdown.sh [OPTIONS] [SECONDS]

Count down from SECONDS (default: 60) and print "Time's up!" at zero.

Options:
  --help                    Show this help message and exit
  --silent                  Only print the final message
  --start-message <text>    Print a message before the countdown begins
                            (suppressed by --silent)
USAGE
            exit 0
            ;;
        --silent)
            SILENT=true
            shift
            ;;
        --start-message)
            if [[ $# -lt 2 ]]; then
                echo "Error: --start-message requires an argument" >&2
                exit 1
            fi
            START_MESSAGE="$2"
            shift 2
            ;;
        *)
            DURATION="$1"
            shift
            ;;
    esac
done

# Input validation
if ! [[ "$DURATION" =~ ^[0-9]+$ ]]; then
    echo "Error: duration must be a positive integer (got '$DURATION')" >&2
    exit 1
fi

if (( DURATION == 0 )); then
    echo "Error: duration must be a positive integer (got '0')" >&2
    exit 1
fi

# Print start message if set and not silent
if [[ -n "$START_MESSAGE" && "$SILENT" == false ]]; then
    echo "$START_MESSAGE"
fi

# Countdown loop
for (( i = DURATION; i > 0; i-- )); do
    if [[ "$SILENT" == false ]]; then
        printf "\rTime remaining: %ds" "$i"
    fi
    sleep 1
done

# Final output
if [[ "$SILENT" == false ]]; then
    printf "\n"
fi
echo "Time's up!"
