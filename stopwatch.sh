#!/usr/bin/env bash

# Defaults
LAP_MODE=false

# Argument parsing
for arg in "$@"; do
    case "$arg" in
        --help)
            cat <<'USAGE'
Usage: stopwatch.sh [OPTIONS]

Count up from zero and display elapsed time with millisecond precision.

Options:
  --help     Show this help message and exit
  --lap      Enable lap recording via SIGUSR1

Lap mode:
  When --lap is active, send SIGUSR1 to record a split time:
    kill -USR1 <pid>
  A summary of all laps is printed on exit (Ctrl+C).
USAGE
            exit 0
            ;;
        --lap)
            LAP_MODE=true
            ;;
        *)
            echo "Error: unknown option '$arg'" >&2
            exit 1
            ;;
    esac
done

# Time formatting: nanoseconds -> "Xh Ym Zs Xms" or "Xm Ys Xms"
format_time() {
    local ns=$1
    local total_ms=$(( ns / 1000000 ))
    local ms=$(( total_ms % 1000 ))
    local total_s=$(( total_ms / 1000 ))
    local s=$(( total_s % 60 ))
    local total_m=$(( total_s / 60 ))
    local m=$(( total_m % 60 ))
    local h=$(( total_m / 60 ))

    if (( h > 0 )); then
        printf "%dh %dm %ds %03dms" "$h" "$m" "$s" "$ms"
    else
        printf "%dm %ds %03dms" "$m" "$s" "$ms"
    fi
}

# Lap tracking state
LAP_ELAPSED=()
LAP_SPLIT=()
LAST_LAP_NS=0

# Capture start time in nanoseconds
START_NS=$(date +%s%N)

# Record a lap (SIGUSR1 handler)
record_lap() {
    local now_ns=$(date +%s%N)
    local elapsed_ns=$(( now_ns - START_NS ))
    local split_ns=$(( elapsed_ns - LAST_LAP_NS ))
    LAP_ELAPSED+=("$elapsed_ns")
    LAP_SPLIT+=("$split_ns")
    LAST_LAP_NS=$elapsed_ns
}

# SIGINT trap: print lap summary and exit
cleanup() {
    printf "\n"
    if [[ "$LAP_MODE" == true ]] && (( ${#LAP_ELAPSED[@]} > 0 )); then
        printf "\n%-6s %-20s %-20s\n" "Lap" "Split" "Elapsed"
        for (( i = 0; i < ${#LAP_ELAPSED[@]}; i++ )); do
            printf "%-6s %-20s %-20s\n" \
                "#$(( i + 1 ))" \
                "$(format_time "${LAP_SPLIT[$i]}")" \
                "$(format_time "${LAP_ELAPSED[$i]}")"
        done
    fi
    exit 0
}
trap cleanup INT

# Enable SIGUSR1 lap recording only in lap mode
if [[ "$LAP_MODE" == true ]]; then
    trap record_lap USR1
fi

# Main loop
while true; do
    NOW_NS=$(date +%s%N)
    ELAPSED_NS=$(( NOW_NS - START_NS ))
    printf "\rElapsed: %s" "$(format_time "$ELAPSED_NS")"
    sleep 0.1
done
