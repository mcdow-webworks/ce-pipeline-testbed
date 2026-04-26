#!/usr/bin/env bash

# Defaults
DURATION=60
SILENT=false

# Argument parsing
for arg in "$@"; do
    case "$arg" in
        --help)
            cat <<'USAGE'
Usage: countdown.sh [OPTIONS] [SECONDS]

Count down from SECONDS (default: 60) and print "Time's up!" at zero.

Options:
  --help     Show this help message and exit
  --silent   Only print the final message
USAGE
            exit 0
            ;;
        --silent)
            SILENT=true
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

# Format a non-negative integer second count as H:MM:SS, M:SS / MM:SS,
# or bare seconds depending on magnitude.
format_remaining() {
    local secs=$1
    if (( secs >= 3600 )); then
        printf '%d:%02d:%02d' $(( secs / 3600 )) $(( (secs % 3600) / 60 )) $(( secs % 60 ))
    elif (( secs >= 60 )); then
        printf '%d:%02d' $(( secs / 60 )) $(( secs % 60 ))
    else
        printf '%d' "$secs"
    fi
}

# The initial tick is the widest the formatted value will ever be in
# this run, so pad every later render to that width to overwrite the
# residue of the previous (longer) render under \r.
WIDTH=$(format_remaining "$DURATION")
WIDTH=${#WIDTH}

# Countdown loop
for (( i = DURATION; i > 0; i-- )); do
    if [[ "$SILENT" == false ]]; then
        printf "\rTime remaining: %-${WIDTH}s" "$(format_remaining "$i")"
    fi
    sleep 1
done

# Final output
if [[ "$SILENT" == false ]]; then
    printf "\n"
fi
echo "Time's up!"
