---
title: "Bash CLI Two-Token Flag Parsing: Use while/shift over for-loop"
date: 2026-04-26
category: docs/solutions/best-practices
module: countdown.sh
problem_type: best_practice
component: tooling
symptoms:
  - "A new flag that consumes the next argument (e.g. --start-message <text>) cannot be added without restructuring the argument parser"
  - "for arg in \"$@\" loop has no mechanism to advance past the next token, so two-token flags are structurally unsupported"
  - "Passing --start-message with no value silently no-ops instead of exiting with an error"
root_cause: missing_validation
resolution_type: code_fix
severity: low
tags:
  - bash
  - argument-parsing
  - while-shift
  - cli
  - flag-guard
  - countdown
  - start-message
  - silent
---

# Bash CLI Two-Token Flag Parsing: Use while/shift over for-loop

## Problem

`countdown.sh` used a `for arg in "$@"` parser that cannot consume the next positional argument, making it impossible to add flags that take a value (e.g. `--start-message <text>`) without a full parser rewrite. Adding `--start-message` as a new flag required restructuring to `while [[ $# -gt 0 ]]; do ... shift`.

## Symptoms

- Attempting to add a two-token flag (`--flag <value>`) to a `for arg in "$@"` loop has no clean path — there is no way to skip the next argument inside a `for` loop.
- `--start-message` with no following argument silently assigns an empty or garbage value instead of exiting with a clear error.
- New flags are undocumented in `--help` when added in a separate commit from the feature.

## What Didn't Work

N/A — this was a net-new feature addition. The `for`-loop parser was a structural blocker, not a failed attempt; switching to `while/shift` was the only viable path.

## Solution

Replace the `for arg in "$@"` pattern with `while [[ $# -gt 0 ]]; do ... shift`. This gives explicit control over the argument pointer so two-token flags can consume `$2` and advance by two positions with `shift 2`.

**Before (for-loop parser — cannot support two-token flags):**
```bash
for arg in "$@"; do
    case "$arg" in
        --silent)
            SILENT=true
            ;;
        --help)
            # print help...
            ;;
        *)
            DURATION="$arg"
            ;;
    esac
done
```

**After (while/shift parser — supports two-token flags with guard):**
```bash
START_MESSAGE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
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
        --help)
            # print help...
            ;;
        *)
            DURATION="$1"
            shift
            ;;
    esac
done

# Print start message if set and not silent
if [[ -n "$START_MESSAGE" && "$SILENT" == false ]]; then
    echo "$START_MESSAGE"
fi
```

The `--silent` suppression check at print-time (not at parse-time) means flag order doesn't matter for that interaction: `--silent --start-message "Go!"` and `--start-message "Go!" --silent` both suppress the message.

## Why This Works

`for arg in "$@"` iterates over a snapshot of all arguments; the loop variable advances automatically and there is no way to skip the next element. `while [[ $# -gt 0 ]]` inspects `$1` each iteration and lets you call `shift N` to consume however many tokens the current flag needs. `shift 1` for single-token flags, `shift 2` for two-token flags. The `$# -lt 2` guard catches the case where the flag token is the last argument with no value following it, exiting cleanly instead of silently misassigning.

## Prevention

- **Choose `while/shift` over `for arg` from the start** when a script may ever need two-token flags. Switching later requires a full parser rewrite; switching upfront costs nothing.
- **Add the missing-argument guard in the same commit** as a new two-token flag. The guard is a one-liner and eliminates the silent-failure class of bugs.
- **Document new flags in `--help` in the same commit** that implements them. Help text drifts when added separately.
- **Test all flag combinations at the cross-product level**: flag-only, flag + value, `--silent` before flag, `--silent` after flag, flag as last argument with no value. The interaction between `--silent` and `--start-message` is only safe if the suppression check is at print-time, not at parse-time.

### Known edge case (CORR-002, not yet fixed)

`./countdown.sh --start-message --silent 3` assigns the string `"--silent"` as the message text because the parser does not validate that `$2` looks like a flag token. A lookahead guard would close this:

```bash
--start-message)
    if [[ $# -lt 2 || "$2" =~ ^-- ]]; then
        echo "Error: --start-message requires a non-flag argument" >&2
        exit 1
    fi
    START_MESSAGE="$2"
    shift 2
    ;;
```

Until that guard is added, users must place `--silent` **before** `--start-message` when combining both flags.

## Related Issues

- Issue #103 — add `--start-message` flag to countdown.sh
- Commits `34b0479` (feature), `5494c20` (missing-argument guard)
