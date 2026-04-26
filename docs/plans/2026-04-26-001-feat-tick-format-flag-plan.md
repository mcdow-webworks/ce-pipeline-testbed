---
title: "feat: Add --tick-format flag to countdown.sh"
type: feat
status: active
date: 2026-04-26
origin: docs/brainstorms/2026-04-26-tick-format-flag-requirements.md
---

# feat: Add `--tick-format` flag to `countdown.sh`

## Overview

Add a `--tick-format <value>` flag to `countdown.sh` that controls how the
remaining-time substring of the ticker is rendered. Values are `seconds`
(default-equivalent), `mm-ss`, and `human`. Omitting the flag preserves the
current output byte-for-byte. Invalid values fail fast at argument-parse time.

A small refactor inside `countdown.sh` extracts a pure `format_tick` shell
function so the formatter is unit-testable without running the 1-second sleep
loop. A `main`-guard added at the bottom of the script keeps the executable
behavior unchanged when `countdown.sh` is run directly.

## Problem Frame

`countdown.sh` currently prints `Time remaining: <N>s`, which becomes hard to
scan for longer countdowns (e.g., `Time remaining: 600s`). The brainstorm
(`docs/brainstorms/2026-04-26-tick-format-flag-requirements.md`) settled on
three opt-in formats and explicitly preserved the existing default for
backward compatibility with any caller that parses the ticker.

## Requirements Trace

- **R1.** `--tick-format <value>` accepts exactly `seconds`, `mm-ss`, or `human`. → Unit 2
- **R2.** Omitting `--tick-format` preserves current output verbatim. → Unit 1, Unit 2
- **R3.** `--tick-format seconds` matches the literal current output. → Unit 2, Unit 3
- **R4.** `--tick-format mm-ss` renders zero-padded `MM:SS`. → Unit 2, Unit 3
- **R5.** `--tick-format human` omits zero units (`30s`, `1m`, `1m 30s`, `60m`). → Unit 2, Unit 3
- **R6.** Invalid `--tick-format` value prints to stderr and exits non-zero before the loop. → Unit 2, Unit 3
- **R7.** `--silent` continues to suppress the ticker regardless of `--tick-format`. → Unit 2, Unit 3
- **R8.** `--help` documents the new flag and accepted values. → Unit 2, Unit 3

## Scope Boundaries

- No localization, i18n, printf-style custom formats, or new units beyond `m`/`s`.
- No change to the default tick format or to the `Time remaining: ` prefix.
- No change to `dashboard.html`, `table_fmt.py`, or any Python utility.
- No new dependencies (no `bats`, no shellcheck plumbing) — tests piggyback on the existing Python `unittest` pattern.
- No restructuring of unrelated CLI flags (`--help`, `--silent` semantics stay).

## Context & Research

### Relevant Code and Patterns

- `countdown.sh` — current implementation: `for arg in "$@"` parser, a single `printf "\rTime remaining: %ds" "$i"` ticker line, and `(( ))` / `[[ =~ ]]` validation idioms. The new code mirrors these idioms.
- `test_table_fmt.py` — repo's only existing test file. Uses `unittest.TestCase`, lives at the repo root, and is named `test_<module>.py`. New tests follow the same convention as `test_countdown.py`.
- `README.md` — confirms this repo is a CE-pipeline sandbox, so introducing a heavyweight shell test framework would be out of proportion to the rest of the repo.

### Institutional Learnings

- `docs/solutions/README.md` was scanned. None of the existing entries (dashboard implementation, CHANGELOG addition, MIT license, `table_fmt` alignment, concurrent-pipeline mention handling) materially affect this work.

### External References

- None gathered. The change is self-contained shell scripting against well-known Bash 4+ idioms; the brainstorm's assumption set (A1–A3) already captures the relevant constraints. External research would not improve the plan.

## Key Technical Decisions

- **Argument-parsing strategy: `while [[ $# -gt 0 ]]` + `shift`.**
  Replace `for arg in "$@"` with a `while`/`case`/`shift` loop. Accept both
  `--tick-format=<value>` (split via `${1#*=}`) and `--tick-format <value>`
  (consume next arg via `shift`). Canonical bash pattern; no measurable cost
  vs. the current loop and aligns with how future value-bearing flags would
  extend. **Resolves brainstorm deferred question 1.**

- **`format_tick` helper function in `countdown.sh`.**
  Extract the time-substring rendering into `format_tick <seconds> <mode>` so
  the unit tests can source the script and call the formatter directly without
  triggering the 1-second `sleep` loop. The function returns the substring on
  stdout; the caller wraps it with the existing `Time remaining: ` prefix and
  `\r`. Keeps the prefix shared across all three modes (per brainstorm decision).

- **Main guard at the bottom of `countdown.sh`.**
  Wrap the parse + validate + countdown sequence in a `main` function and call
  it only when `countdown.sh` is executed directly:
  `[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"`. This makes the file safe
  to `source` from a test runner without side effects. Standard
  "library + executable in one file" bash pattern.

- **`human` mode conditional ladder.**
  `mins=$((s/60))`, `secs=$((s%60))`. If `mins==0` → `${secs}s`; elif `secs==0`
  → `${mins}m`; else `${mins}m ${secs}s`. Matches every example in R5
  (30→`30s`, 60→`1m`, 90→`1m 30s`, 600→`10m`, 3600→`60m`). No hour rollup.
  **Resolves brainstorm deferred question 2.**

- **`seconds` mode equals the current literal output.**
  Returns `${s}s` (e.g., `30s`), preserving the existing format. The brainstorm
  explicitly resolves the issue's "bare-seconds" wording in favor of the
  current literal output.

- **`mm-ss` mode uses `printf '%02d:%02d'`.**
  `printf` zero-pads to a minimum of 2 digits; values ≥ 100 minutes simply
  widen (`100:00`), which is the right behavior for long countdowns.

- **Validation order: `--tick-format` value validated before duration loop.**
  Mirrors the existing duration validation. Bad input fails before any sleep.
  Done inside `main`, after argument parsing, before the loop.

- **Test harness: Python `unittest` + `subprocess`.**
  Matches `test_table_fmt.py`. Unit-level coverage of `format_tick` is done by
  invoking `bash -c 'source countdown.sh && format_tick <s> <mode>'` and
  asserting stdout. Integration coverage (invalid value, `--help`, `--silent`)
  is done via `subprocess.run(["bash", "countdown.sh", ...])` against
  `DURATION=1` to keep total test time under ~3 seconds.
  **Resolves brainstorm deferred question 3.**

## Open Questions

### Resolved During Planning

- *(see Key Technical Decisions for resolutions to brainstorm deferred questions 1–3.)*

### Deferred to Implementation

- **Exact wording of the `--tick-format` error message and `--help` description.** The plan fixes the requirements (stderr, non-zero exit, mentions all three values) but leaves the exact phrasing to implementation, where it can be matched against the existing error-message style in `countdown.sh` (e.g., `"Error: duration must be a positive integer (got '$DURATION')"`).
- **Whether to support `--tick-format=` with an empty value as a distinct error case.** Treating it as "missing value → invalid" is the natural consequence of the validator and does not need a separate code path; the implementer should confirm the resulting error message reads clearly.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
countdown.sh (post-change, conceptual shape)
────────────────────────────────────────────
format_tick(seconds, mode) -> string         # pure function, prints to stdout
    case mode in
        seconds | "")  echo "${seconds}s"
        mm-ss          printf '%02d:%02d' (seconds/60) (seconds%60)
        human          ladder: 0-min | 0-sec | both
    esac

validate_tick_format(mode) -> 0 | 1          # called from main, before loop
    case mode in
        ""|seconds|mm-ss|human) return 0
        *) echo "Error: ..." >&2; return 1
    esac

main(argv...) -> exit code
    parse argv:
        while [[ $# > 0 ]]:
            case $1 in
                --help)               print usage; exit 0
                --silent)             SILENT=true
                --tick-format=*)      TICK_FORMAT=${1#*=}
                --tick-format)        shift; TICK_FORMAT=$1
                *)                    DURATION=$1
            esac
            shift
    validate DURATION (existing logic)
    validate TICK_FORMAT (new)
    for i in DURATION..1:
        if !SILENT: printf '\rTime remaining: %s' "$(format_tick i TICK_FORMAT)"
        sleep 1
    if !SILENT: printf '\n'
    echo "Time's up!"

[[ ${BASH_SOURCE[0]} == ${0} ]] && main "$@"   # main guard for source-ability
```

The shape preserves the existing `Time remaining: ` prefix, the `\r` ticker,
and the trailing `\n` + `Time's up!` — the only thing the flag changes is the
substring substituted in for the time value.

## Implementation Units

- [ ] **Unit 1: Refactor `countdown.sh` for testability (no behavior change)**

  **Goal:** Extract the existing logic into a `main` function and add a main-guard so the script is source-able from tests without triggering the countdown loop. No user-visible behavior change.

  **Requirements:** R2 (preserves backward-compatible output by being a pure refactor)

  **Dependencies:** None.

  **Files:**
  - Modify: `countdown.sh`

  **Approach:**
  - Wrap the existing parse + validate + countdown body in a `main()` function.
  - Add `[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"` at the bottom.
  - Keep all current behavior identical: same defaults, same error messages, same `--help` text, same ticker output. This unit is intentionally a no-op for end users.

  **Patterns to follow:**
  - Existing `countdown.sh` style (uppercase env-style locals, `(( ))` arithmetic, `[[ =~ ]]` regex, here-doc for usage).
  - Standard "library + executable in one file" bash pattern.

  **Test scenarios:**
  - Running `bash countdown.sh 1` produces the same output as before (smoke check).
  - Running `bash countdown.sh --help` produces unchanged help text.
  - Sourcing the file (`bash -c 'source countdown.sh; echo sourced'`) does **not** start a countdown.

  **Verification:**
  - `bash countdown.sh 1` and `bash countdown.sh --silent 1` produce byte-identical output to the pre-change behavior.
  - Sourcing the file is side-effect-free.

- [ ] **Unit 2: Add `--tick-format` flag, formatter, and validation**

  **Goal:** Implement the user-facing feature: a `format_tick` helper, the new flag with both `--tick-format <value>` and `--tick-format=<value>` forms, fail-fast validation, integration into the ticker output, and updated `--help`.

  **Requirements:** R1, R2, R3, R4, R5, R6, R7, R8

  **Dependencies:** Unit 1 (uses the new `main` structure and main-guard).

  **Files:**
  - Modify: `countdown.sh`

  **Approach:**
  - Switch the argument loop from `for arg in "$@"` to `while [[ $# -gt 0 ]]; do case "$1" in ... esac; shift; done` so a flag can consume its following arg with an inner `shift`.
  - Default `TICK_FORMAT` to the empty string. Treat empty == `seconds` everywhere in formatting and validation, so omitting the flag is identical to passing `--tick-format seconds` and the current literal output is preserved.
  - Implement `format_tick "$seconds" "$mode"` returning the time substring on stdout (no prefix, no newline). Cases: `seconds`/empty → `${s}s`; `mm-ss` → `printf '%02d:%02d' $((s/60)) $((s%60))`; `human` → conditional ladder.
  - Implement validation in `main` after parsing, before the duration validation block, rejecting any value not in `{"", seconds, mm-ss, human}`. Print the error to stderr and exit non-zero. Match the wording style of the existing `Error: duration must be a positive integer (got '$DURATION')` message.
  - Replace `printf "\rTime remaining: %ds" "$i"` with `printf '\rTime remaining: %s' "$(format_tick "$i" "$TICK_FORMAT")"`.
  - Update the `--help` here-doc to add a `--tick-format <value>` line listing the three accepted values and noting the default behavior when omitted.

  **Patterns to follow:**
  - Existing duration validation block in `countdown.sh` for stderr message style and exit code.
  - Existing `--help` here-doc layout (two-space option indent, single-line description).

  **Test scenarios:** *(asserted in Unit 3)*
  - Each format mode renders the documented value for representative seconds.
  - `--tick-format` omitted produces output byte-for-byte identical to pre-change.
  - Invalid value, including `--tick-format foo` and a missing value (`--tick-format` at end of argv), exits non-zero with a stderr message before any tick is printed.
  - `--silent` overrides every format mode (no ticker emitted).
  - `--help` mentions `--tick-format` and all three values.

  **Verification:**
  - Running `bash countdown.sh --tick-format mm-ss 1` shows `Time remaining: 00:01` then `Time's up!`.
  - Running `bash countdown.sh --tick-format human 90` (or any sample) renders the documented human form.
  - Running `bash countdown.sh --tick-format foo 1` exits non-zero with a stderr error and no countdown.

- [ ] **Unit 3: Add `test_countdown.py` covering all formats, errors, `--help`, and `--silent` interaction**

  **Goal:** Lock down the new behavior with the smallest reasonable test surface, mirroring the existing `test_table_fmt.py` shape so the repo's testing story stays consistent.

  **Requirements:** R3, R4, R5, R6, R7, R8 (and indirectly R2 via the seconds-mode equivalence test)

  **Dependencies:** Unit 1 (source-ability), Unit 2 (feature implementation).

  **Files:**
  - Create: `test_countdown.py`
  - Test: `test_countdown.py` (self)

  **Approach:**
  - Use `unittest.TestCase` and `subprocess.run` (matching `test_table_fmt.py`'s style; `unittest`-only, no pytest dependency).
  - Group tests by behavior, not by mode, so each test file section reads as one feature.
  - For unit-level formatter tests, invoke `bash -c 'source ./countdown.sh && format_tick "$1" "$2"' _ <seconds> <mode>` and assert on stdout. The main guard added in Unit 1 keeps this fast (no sleep).
  - For integration tests, invoke `bash countdown.sh ...` with `DURATION=1` for end-to-end smokes; rely on the `--help` early-exit path for help-text assertions (no sleep).
  - Resolve `countdown.sh` via an absolute path computed from `__file__` so tests are runnable from any working directory.
  - Use `text=True` and `check=False` on subprocess calls; assert `returncode`, `stdout`, and `stderr` explicitly.

  **Test scenarios:**
  - **`format_tick` unit cases**
    - `(30, "seconds")` → `30s`
    - `(30, "")` → `30s` (empty is treated as default-equivalent)
    - `(30, "mm-ss")` → `00:30`
    - `(90, "mm-ss")` → `01:30`
    - `(600, "mm-ss")` → `10:00`
    - `(30, "human")` → `30s`
    - `(60, "human")` → `1m`
    - `(90, "human")` → `1m 30s`
    - `(600, "human")` → `10m`
    - `(3600, "human")` → `60m` (no hour rollup)
  - **CLI integration cases**
    - `countdown.sh --tick-format=mm-ss 1` exits 0; final stdout contains `Time remaining: 00:01` and `Time's up!`.
    - `countdown.sh --tick-format human 1` exits 0; final stdout contains `Time remaining: 1s`.
    - `countdown.sh --tick-format seconds 1` produces output byte-for-byte identical to `countdown.sh 1` (R3 + R2 cross-check).
    - `countdown.sh --tick-format foo 1` exits non-zero; stderr contains the error message; stdout does **not** contain `Time remaining` or `Time's up!`.
    - `countdown.sh --tick-format 1` (missing value, end of argv) exits non-zero; stderr contains an error.
    - `countdown.sh --silent --tick-format human 1` exits 0; stdout contains `Time's up!` and does **not** contain `Time remaining`.
    - `countdown.sh --help` exits 0; stdout contains `--tick-format` and each of `seconds`, `mm-ss`, `human`.

  **Verification:**
  - `python -m unittest test_countdown.py` exits 0 with all tests passing on a clean checkout.
  - Total wall time for the new test file is small (a handful of `DURATION=1` integration runs plus instant unit calls).

- [ ] **Unit 4: Update `CHANGELOG.md` `[Unreleased]` → `Added`**

  **Goal:** Record the new flag in the changelog under the existing Keep a Changelog structure.

  **Requirements:** None directly — this is project hygiene that the repo already practices (see existing CHANGELOG `[Unreleased]` skeleton).

  **Dependencies:** Units 1–3 (entry should be added once the feature is implemented).

  **Files:**
  - Modify: `CHANGELOG.md`

  **Approach:**
  - Add a single bullet under `## [Unreleased] → ### Added`, naming the flag and listing the three accepted values plus the omitted-flag behavior. Keep wording short and user-facing, consistent with Keep a Changelog norms.
  - Do not introduce a release version or date — `[Unreleased]` stays unreleased.

  **Patterns to follow:**
  - Existing `CHANGELOG.md` skeleton (Added/Changed/Deprecated/Removed/Fixed/Security headings).

  **Test scenarios:** *(documentation-only; no automated assertion)*

  **Verification:**
  - `CHANGELOG.md` `[Unreleased] → Added` lists the new flag.
  - No other sections are modified.

## System-Wide Impact

- **Interaction graph:** `countdown.sh` is a leaf script; no other repo file imports or sources it today. The new `format_tick` function is internal and the main guard is invisible to existing callers.
- **Error propagation:** New validation surfaces a stderr error and a non-zero exit before any countdown work, matching the existing duration-error path. Callers that branch on exit code see a clean failure.
- **State lifecycle risks:** None — the script is stateless and synchronous. The main guard does not change process exit semantics.
- **API surface parity:** The "API" here is the CLI flag set. `--tick-format` is purely additive; `--silent`, `--help`, and the positional `[SECONDS]` argument retain their current contracts.
- **Integration coverage:** The Python integration tests exercise the full process boundary (argv → stdout/stderr → exit code), which unit-level `format_tick` tests alone would not prove.

## Risks & Dependencies

- **Risk: argv parser refactor accidentally changes how `[SECONDS]` is consumed.** The current `for arg in "$@"` puts `*) DURATION="$arg" ;;` last; the new `while`/`shift` loop must keep the positional fall-through equivalent. Mitigation: a regression test asserts that `countdown.sh 1` (no flags) and `countdown.sh --tick-format seconds 1` produce the same output as before.
- **Risk: ticker `\r` rewrite alignment.** When the time substring shrinks between ticks (e.g., `Time remaining: 1m 30s` → `Time remaining: 1m`), the trailing characters from the previous tick can linger because `\r` doesn't clear. The current ticker has the same property (`30s` → `9s` is shorter than `30s`), so this is preexisting behavior, not a regression introduced by the flag. Out of scope; if it becomes a complaint, follow up with a separate "clear-line" change.
- **Risk: shell portability surprises (`/bin/sh` vs `bash`).** The script uses `#!/usr/bin/env bash` and Bash-only features (`(( ))`, `[[ =~ ]]`, `${var#*=}`); tests must invoke `bash` explicitly to avoid a non-bash shell on a contributor's `PATH` masking failures. The Python tests will run `bash countdown.sh ...`, not `sh countdown.sh ...`.
- **Dependency: Bash 4+** (already an existing assumption per brainstorm A1; no new requirement).

## Documentation / Operational Notes

- `--help` output is the user-facing documentation surface and is updated in Unit 2.
- `CHANGELOG.md` updated in Unit 4.
- `README.md` is not updated — it does not describe `countdown.sh` flags today, and adding flag-level documentation there would exceed scope.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-26-tick-format-flag-requirements.md](../brainstorms/2026-04-26-tick-format-flag-requirements.md)
- Related code: `countdown.sh`, `test_table_fmt.py` (test pattern), `CHANGELOG.md`
- Related issues: #107
