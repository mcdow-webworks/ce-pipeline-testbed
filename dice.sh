#!/usr/bin/env bash

# Defaults
NOTATION="1d6"
VERBOSE=false

# Argument parsing
EXPR_SET=false
for arg in "$@"; do
    case "$arg" in
        --help)
            cat <<'USAGE'
Usage: dice.sh [OPTIONS] [NOTATION]

Roll dice using standard tabletop notation.

Notation: NdS[+/-M]
  N = number of dice (default: 1)
  S = number of sides
  M = optional modifier (added to or subtracted from total)

Options:
  --help     Show this help message and exit
  --verbose  Show individual die results alongside total

Examples:
  dice.sh           Roll 1d6 (default)
  dice.sh 2d6       Roll two six-sided dice
  dice.sh 1d20      Roll one twenty-sided die
  dice.sh d20       Shorthand for 1d20
  dice.sh 3d8+5     Roll 3d8 and add 5
  dice.sh 2d6-1     Roll 2d6 and subtract 1

Note: Uses $RANDOM for randomness. Modulo bias is negligible for
typical dice sizes but exists for very large side counts.
USAGE
            exit 0
            ;;
        --verbose)
            VERBOSE=true
            ;;
        *)
            if [[ "$EXPR_SET" == true ]]; then
                echo "Error: expected a single dice expression, got multiple arguments" >&2
                exit 1
            fi
            NOTATION="$arg"
            EXPR_SET=true
            ;;
    esac
done

# Notation parsing
if ! [[ "$NOTATION" =~ ^([0-9]*)d([0-9]+)([+-][0-9]+)?$ ]]; then
    echo "Error: invalid dice notation (got '$NOTATION')" >&2
    exit 1
fi

NUM_DICE="${BASH_REMATCH[1]:-1}"
SIDES="${BASH_REMATCH[2]}"
MODIFIER="${BASH_REMATCH[3]}"

# Input validation
if (( NUM_DICE == 0 )); then
    echo "Error: number of dice must be at least 1 (got '${BASH_REMATCH[1]}')" >&2
    exit 1
fi

if (( SIDES == 0 )); then
    echo "Error: number of sides must be at least 1 (got '$SIDES')" >&2
    exit 1
fi

if (( NUM_DICE > 1000 )); then
    echo "Error: number of dice cannot exceed 1000 (got '$NUM_DICE')" >&2
    exit 1
fi

if (( SIDES > 1000000 )); then
    echo "Error: number of sides cannot exceed 1000000 (got '$SIDES')" >&2
    exit 1
fi

# Parse modifier
MOD_VALUE=0
MOD_SIGN=""
if [[ -n "$MODIFIER" ]]; then
    MOD_SIGN="${MODIFIER:0:1}"
    MOD_VALUE="${MODIFIER:1}"
fi

# Roll dice
SUM=0
ROLLS=""
for (( i = 0; i < NUM_DICE; i++ )); do
    ROLL=$(( RANDOM % SIDES + 1 ))
    SUM=$(( SUM + ROLL ))
    if [[ -n "$ROLLS" ]]; then
        ROLLS="$ROLLS $ROLL"
    else
        ROLLS="$ROLL"
    fi
done

# Apply modifier
TOTAL=$SUM
if [[ "$MOD_SIGN" == "+" ]]; then
    TOTAL=$(( SUM + MOD_VALUE ))
elif [[ "$MOD_SIGN" == "-" ]]; then
    TOTAL=$(( SUM - MOD_VALUE ))
fi

# Output
if [[ "$VERBOSE" == true ]]; then
    if [[ -n "$MOD_SIGN" ]]; then
        echo "Rolls: $ROLLS | Modifier: ${MOD_SIGN}${MOD_VALUE} | Total: $TOTAL"
    else
        echo "Rolls: $ROLLS | Total: $TOTAL"
    fi
else
    echo "$TOTAL"
fi
