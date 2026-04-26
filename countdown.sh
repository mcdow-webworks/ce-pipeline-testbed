#!/usr/bin/env bash

# Defaults
DURATION=60
SILENT=false
NO_BELL=false

# Argument parsing
for arg in "$@"; do
    case "$arg" in
        --help)
            cat <<'USAGE'
Usage: countdown.sh [OPTIONS] [SECONDS]

Count down from SECONDS (default: 60) and print "Time's up!" at zero.

Options:
  --help      Show this help message and exit
  --silent    Only print the final message; suppresses bell
  --no-bell   Show the visual countdown but suppress the audible bell
USAGE
            exit 0
            ;;
        --silent)
            SILENT=true
            ;;
        --no-bell)
            NO_BELL=true
            ;;
        *)
            DURATION="$arg"
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
if [[ "$SILENT" == false && "$NO_BELL" == false ]]; then
    printf '\a'
fi
echo "Time's up!"
