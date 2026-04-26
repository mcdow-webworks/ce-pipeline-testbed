---
title: "Unit-testing a bash script from Python on Windows / WSL"
date: 2026-04-26
category: developer-experience
module: countdown.sh
problem_type: developer_experience
component: testing_framework
symptoms:
  - "`source ./countdown.sh && format_tick ...` returned exit 1 even though `format_tick` was defined"
  - "Python `subprocess` calls to bash with absolute Windows paths failed because backslashes were mangled at the WSL boundary"
  - "Positional args passed after `bash -c COMMAND arg1 arg2` were silently dropped, so `$1`/`$2` were empty in the sourced function"
  - "`--tick-format=` (explicit empty value) silently behaved like the default instead of triggering the validator"
root_cause: incomplete_setup
resolution_type: tooling_addition
severity: medium
tags:
  - bash
  - python-subprocess
  - windows
  - wsl
  - unit-testing
  - main-guard
  - shlex
  - sourcing
related_components:
  - tooling
  - development_workflow
---

# Unit-testing a bash script from Python on Windows / WSL

## Problem

`countdown.sh` was a flat, top-level imperative bash script with no way to exercise individual helpers in isolation. Adding the `--tick-format` flag (issue #107) created pressure to unit-test the formatter from Python on a Windows host that shells out to WSL bash — a path that quietly broke in four independent ways before tests could run at all.

## Symptoms

- `source countdown.sh` ran the entire countdown instead of just defining functions.
- Python tests doing `bash -c "source ./countdown.sh && format_tick 30 seconds"` returned exit 1 with empty stdout — `format_tick` was never invoked.
- `bash -c "format_tick 30 seconds" 30 seconds` (the documented `bash -c COMMAND ARG1 ARG2` form) silently dropped the positional args under WSL bash launched from Windows Python.
- Absolute Windows paths (`C:\Users\...\countdown.sh`) handed to `subprocess.run(["bash", ...])` failed to resolve at the WSL boundary.
- `--tick-format=` (explicit empty value) was silently treated as the default `seconds` instead of erroring out.

## What Didn't Work

- **One-liner main-guard with `&&`**: `[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"`. When the file is sourced the test is false, so the compound expression returns 1 — and that exit code propagates to the caller, killing any `source ... && next_command` chain.
- **`bash -c COMMAND ARG1 ARG2 ...`**: per `bash(1)` this should set `$0`, `$1`, etc. for COMMAND. Under WSL bash invoked from Windows Python it consistently lost the trailing positional args.
- **Absolute Windows paths in `subprocess.run`**: `C:\...\countdown.sh` doesn't survive the Windows-to-WSL translation cleanly.
- **Empty default + late fallback**: `local TICK_FORMAT=""` then `[[ -z "$TICK_FORMAT" ]] && TICK_FORMAT="seconds"` after parsing. Treats explicit `--tick-format=` as "user wants the default" and swallows what is almost certainly a bug in the caller.

## Solution

**Wrap imperative code in `main()` and gate it with the `if/fi` form** so sourcing leaves a clean exit status:

Before:

```bash
#!/usr/bin/env bash
DURATION="${1:-60}"
for (( i = DURATION; i > 0; i-- )); do
    printf '\rTime remaining: %ds' "$i"
    sleep 1
done
echo "Time's up!"
```

After:

```bash
#!/usr/bin/env bash

format_tick() {
    local s="$1" mode="$2"
    case "$mode" in
        ""|seconds) printf '%ds' "$s" ;;
        mm-ss)      printf '%02d:%02d' "$((s / 60))" "$((s % 60))" ;;
        # ...
        *)          return 1 ;;
    esac
}

main() {
    local TICK_FORMAT="seconds"   # real default, not ""
    # ...arg parsing writes raw value into TICK_FORMAT...
    case "$TICK_FORMAT" in
        seconds|mm-ss|human) ;;
        *) echo "Error: --tick-format must be one of: seconds, mm-ss, human (got '$TICK_FORMAT')" >&2
           return 1 ;;
    esac
    # ...countdown loop...
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```

**Drive bash from Python with `cwd` + relative path + inlined args**, never `bash -c COMMAND ARG1 ARG2` and never absolute Windows paths:

```python
import os, shlex, subprocess

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPT_REL = "./countdown.sh"

def format_tick(seconds, mode):
    cmd = "source {script} && format_tick {s} {m}".format(
        script=shlex.quote(SCRIPT_REL),
        s=shlex.quote(str(seconds)),
        m=shlex.quote(mode),
    )
    return subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True, text=True, check=False,
        cwd=REPO_ROOT,
    )

def run_countdown(*args):
    return subprocess.run(
        ["bash", SCRIPT_REL, *args],
        capture_output=True, text=True, check=False,
        cwd=REPO_ROOT,
    )
```

## Why This Works

- **`if/fi` instead of `&&`**: when sourced, control enters neither branch and the block is effectively a no-op — the shell's last-command exit status is whatever it was before, typically 0, so the `source ... && next_command` chain in the test harness keeps going. The `&&` form, by contrast, evaluates `[[ ... ]]` as the *last* command of the file; a false test is exit 1, which kills the chain.
- **`main()` wrapper**: imperative side effects only run inside a function body that the main-guard chooses whether to call. Sourcing now defines `main` and `format_tick` without executing either — the precondition for unit-testing helpers.
- **`cwd=REPO_ROOT` + `./countdown.sh`**: the only path that crosses the Windows/WSL boundary is `./countdown.sh`, which both sides agree means "relative to the current working directory." The cwd itself is set by Python via the OS-level process API and translated correctly. No backslashes or drive letters traverse the boundary.
- **Inlined `shlex.quote` args**: bypasses the `bash -c COMMAND ARG1 ARG2` machinery entirely. The args become literal tokens in the command string, so there is nothing for WSL bash's argv handling to drop.
- **Real default + validate-after-parse**: every code path through the parser writes *something* into `TICK_FORMAT`, including the empty string for `--tick-format=`. The validator's case statement only accepts the three real modes, so empty (and any other typo) fails fast with a clear stderr message before the loop starts.

## Prevention

Checklist for any bash script that should be unit-testable from another language:

- [ ] All imperative work lives inside functions; the only top-level code is the main-guard.
- [ ] Main-guard uses the `if/fi` form, never `[[ ... ]] && main "$@"`.
- [ ] Helpers that tests will call are top-level functions (not nested inside `main`).
- [ ] Functions use `return`, not `exit`, so a sourced caller is not killed on an error path.

Checklist for Python tests that shell out to bash on Windows:

- [ ] `subprocess.run` uses `cwd=REPO_ROOT` and a relative script path (`./script.sh`).
- [ ] Never pass absolute Windows paths through `bash`.
- [ ] When using `bash -c`, inline argument values with `shlex.quote` rather than relying on `bash -c COMMAND ARG1 ARG2 ...`.

Checklist for flag defaults:

- [ ] Initialize the variable to the real default value, not `""`.
- [ ] Validate the final value against an allowlist after parsing; reject empty explicitly.
- [ ] Add a regression test that asserts `--flag=` (empty value) is an error, not silently the default.

A single Python test that exercises `source ./script.sh && some_helper ...` is enough to catch a regression in any of the bash-side rules — it will fail loudly the moment someone reverts `if/fi` to `&&` or moves a helper inside `main`.

## Related Issues

- Issue #107 — original feature request that surfaced these patterns (`--tick-format` flag for `countdown.sh`).
- Issues #99, #101, #103 — sibling `countdown.sh` enhancements (banded MM:SS display, audible bell, `--start-message`) that hit the same testing surface but were shipped without a captured testing convention. Future enhancements to this script can lean on the patterns here instead of rediscovering them.
- Pre-existing CRLF caveat (out of scope for this learning): the Windows checkout has `core.autocrlf=true` and no `.gitattributes`, so `.sh` files land with CRLF and bash refuses to source them. Fixing that is a repo-wide line-ending decision; until it is addressed, the test harness here only runs cleanly on checkouts with LF endings.
