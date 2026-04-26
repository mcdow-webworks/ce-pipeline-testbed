#!/usr/bin/env bash

# format_tick <seconds> <mode> -> stdout
# Renders the time substring of the ticker. An empty mode is treated as
# "seconds" so callers (and the default flag value) preserve the original
# bare-seconds output.
format_tick() {
    local s="$1"
    local mode="$2"
    case "$mode" in
        ""|seconds)
            printf '%ds' "$s"
            ;;
        mm-ss)
            printf '%02d:%02d' "$((s / 60))" "$((s % 60))"
            ;;
        human)
            local mins=$((s / 60))
            local secs=$((s % 60))
            if (( mins == 0 )); then
                printf '%ds' "$secs"
            elif (( secs == 0 )); then
                printf '%dm' "$mins"
            else
                printf '%dm %ds' "$mins" "$secs"
            fi
            ;;
        *)
            return 1
            ;;
    esac
}

main() {
    local DURATION=60
    local SILENT=false
    local TICK_FORMAT="seconds"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help)
                cat <<'USAGE'
Usage: countdown.sh [OPTIONS] [SECONDS]

Count down from SECONDS (default: 60) and print "Time's up!" at zero.

Options:
  --help               Show this help message and exit
  --silent             Only print the final message
  --tick-format MODE   Ticker format: seconds (default), mm-ss, or human
USAGE
                return 0
                ;;
            --silent)
                SILENT=true
                ;;
            --tick-format=*)
                TICK_FORMAT="${1#*=}"
                ;;
            --tick-format)
                if [[ $# -lt 2 ]]; then
                    echo "Error: --tick-format requires a value (one of: seconds, mm-ss, human)" >&2
                    return 1
                fi
                shift
                TICK_FORMAT="$1"
                ;;
            *)
                DURATION="$1"
                ;;
        esac
        shift
    done

    case "$TICK_FORMAT" in
        seconds|mm-ss|human)
            ;;
        *)
            echo "Error: --tick-format must be one of: seconds, mm-ss, human (got '$TICK_FORMAT')" >&2
            return 1
            ;;
    esac

    if ! [[ "$DURATION" =~ ^[0-9]+$ ]]; then
        echo "Error: duration must be a positive integer (got '$DURATION')" >&2
        return 1
    fi

    if (( DURATION == 0 )); then
        echo "Error: duration must be a positive integer (got '0')" >&2
        return 1
    fi

    for (( i = DURATION; i > 0; i-- )); do
        if [[ "$SILENT" == false ]]; then
            printf '\rTime remaining: %s' "$(format_tick "$i" "$TICK_FORMAT")"
        fi
        sleep 1
    done

    if [[ "$SILENT" == false ]]; then
        printf "\n"
    fi
    echo "Time's up!"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
