---
title: "feat: Add --no-final-newline flag to countdown.sh"
type: feat
status: active
date: 2026-04-26
origin: docs/brainstorms/2026-04-26-no-final-newline-flag-requirements.md
---

# feat: Add `--no-final-newline` flag to countdown.sh

## Overview

Add a `--no-final-newline` long flag to `countdown.sh` that suppresses the trailing newline on the final `Time's up!` message. Default behavior remains byte-identical, the flag is a documented no-op when combined with `--silent`, and a new `test_countdown.py` proves the four behaviors enumerated in the origin brainstorm.

## Problem Frame

`countdown.sh` always emits a trailing newline after `Time's up!` because the final emission uses `echo`. Callers that pipe the output, embed it in a status line, or compare bytes cannot suppress that newline today. Issue #118 asks for an opt-in flag that removes the newline on the final message only — every other byte of output (ticker, errors, the `\n` that closes the ticker line) must stay the same. The origin brainstorm resolved the `--silent` interaction (no-op, allowed, documented) and the implementation switch (`echo` → `printf` only on the active path).

## Requirements Trace

- R1. Accepts `--no-final-newline`; final message omits trailing newline when set and `--silent` is not also set; default behavior preserved byte-for-byte (origin R1, AE1, AE2).
- R2. `--no-final-newline` is a documented no-op under `--silent`; the combination is allowed without error and `--help` notes the no-op (origin R2, AE3).
- R3. Flag does not affect ticker output or the separating newline that closes the ticker line before the final message (origin R3).
- R4. Argument parsing handles the new flag in the existing parse pass; unknown tokens still fall through to the duration slot; duration validation continues to run after parsing (origin R4, AE4).
- R5. `--help` lists `--no-final-newline` alongside `--silent` and `--help` with a short description and the silent-no-op note (origin R5).
- R6. New `test_countdown.py` covers four scenarios: default unchanged; flag with visible ticker (final byte `!`); flag with `--silent` (final byte `\n`, no-op confirmed); flag with invalid duration (non-zero exit + stderr message) (origin R6).

**Origin acceptance examples:** AE1 (default preservation), AE2 (flag with ticker), AE3 (no-op under silent), AE4 (eager validation).

## Scope Boundaries

- Only `countdown.sh` and the new `test_countdown.py` change. `dashboard.html`, `table_fmt.py`, and other repo files are untouched.
- The flag affects the final `Time's up!` line only — ticker output, the separating `\n`, and error messages are unchanged.
- No short alias (e.g., `-n`), no environment-variable equivalent, no rewrite of the existing argument parser beyond what the new flag requires.
- The `--silent` no-op is intentional; revisiting that interaction is out of scope.

## Context & Research

### Relevant Code and Patterns

- `countdown.sh` (current parser, lines 7-29) — single-pass `for arg in "$@"` loop with a `case` that handles `--help`, `--silent`, and a fall-through `*)` that captures the duration. New flag slots in as another `case` arm following the existing style.
- `countdown.sh` final emission (lines 50-54) — currently `printf "\n"` (only when not silent) followed by `echo "Time's up!"`. The `printf` already imported into the script means switching the final line to `printf` adds no new dependency.
- `test_table_fmt.py` — repo's reference test style: `unittest.TestCase` classes grouped by behavior, `unittest.main()` entrypoint, no third-party deps. New `test_countdown.py` mirrors this shape and shells out via `subprocess`.
- `README.md` and `--help` text — both surface user-facing flag descriptions; the `--help` block inside `countdown.sh` is the in-script source of truth that this plan updates.

### Institutional Learnings

- None of the four `docs/solutions/` entries (table_fmt alignment, dashboard implementation, missing license, changelog format, concurrent pipeline mention handling) overlap with this work. No prior learning to apply.

## Key Technical Decisions

- **Switch the final emission to `printf` only on the active path; keep `echo` everywhere else.** Rationale: `echo` always emits a trailing newline in bash. Branching at the final line keeps the default byte-for-byte identical (the existing `echo "Time's up!"` literal stays) and isolates the `printf "Time's up!"` form to the single new path. Decision carried from origin.
- **Allow `--silent --no-final-newline` as a no-op rather than an error.** Rationale: origin issue mandates it; allowing the combination spares callers from branching on whether silent mode is active, and `--help` documents the no-op. Decision carried from origin.
- **Keep the parser as a single-pass loop with one new `case` arm.** Rationale: the existing parser is small and consistent. Introducing `getopts` or a separate parse pass adds risk of changing how unknown tokens fall through to the duration slot — which would break R4/AE4. The minimal addition preserves existing parser semantics exactly.
- **Tests shell out to `countdown.sh` with `duration=1` via `subprocess`.** Rationale: the script's behavior includes wall-clock `sleep 1` calls. Using duration=1 keeps each test under ~1.5s. Capturing raw `stdout` bytes (not text) is necessary so the trailing-byte assertions are unambiguous about `\n` vs `!`.

## Open Questions

### Resolved During Planning

- **Where does the `--no-final-newline` arm live in the parser?** Resolved: as a new `case` arm between `--silent` and the `*)` fall-through, mirroring the existing style. No reordering of existing arms.
- **What does the final emission block look like after the change?** Resolved: keep `printf "\n"` (the ticker-closing newline) unchanged; replace the single `echo "Time's up!"` with a small conditional that picks between `printf "Time's up!"` (when `SILENT=false` AND `NO_FINAL_NEWLINE=true`) and `echo "Time's up!"` (everything else, including silent + flag). Verifies R1, R2, R3 simultaneously.
- **Issue body says `test_countdown.py` is "existing" but it is missing.** Resolved per origin assumption: treat as a new file to create, modeled on `test_table_fmt.py`.

### Deferred to Implementation

- **Exact `unittest` method names and class grouping inside `test_countdown.py`.** A single test class with four `test_*` methods is sufficient given the small surface; final naming is a stylistic call at write time.
- **Whether to use `subprocess.run(..., capture_output=True)` versus piping stdout/stderr explicitly.** Both work; pick at write time based on what reads cleanest for the byte-level assertions.

## Implementation Units

- U1. **Add `--no-final-newline` flag to `countdown.sh`**

**Goal:** Introduce the new flag with parser support, `--help` documentation, and a final-emission branch that suppresses the trailing newline only when the flag is active and `--silent` is not.

**Requirements:** R1, R2, R3, R4, R5

**Dependencies:** None

**Files:**
- Modify: `countdown.sh`

**Approach:**
- Add `NO_FINAL_NEWLINE=false` default alongside `SILENT=false`.
- Add a new `--no-final-newline)` arm in the existing `case` between the `--silent)` arm and the `*)` fall-through. Set `NO_FINAL_NEWLINE=true` and continue.
- Update the `--help` here-doc to list `--no-final-newline` with a short description and an explicit note that it is a no-op under `--silent`.
- Replace the final `echo "Time's up!"` line with a conditional: when `SILENT=false` AND `NO_FINAL_NEWLINE=true`, emit `printf "Time's up!"`; otherwise keep `echo "Time's up!"`. Leave the preceding `printf "\n"` (which closes the ticker line) untouched so R3 holds.
- Do not touch the duration validation block. Unknown tokens (including `abc` after the flag) must continue to fall through to the duration slot exactly as today, so AE4 holds.

**Patterns to follow:**
- Existing `case` arms in `countdown.sh` (lines 9-28) for arm ordering and the `;;` style.
- The here-doc `--help` block (lines 11-19) for description tone (short, imperative, one line per option).

**Test scenarios:** *Behavioral coverage lives in U2; U1 is verified via U2's tests plus the static checks below.*

**Verification:**
- `bash -n countdown.sh` parses cleanly.
- `countdown.sh --help` exits 0 and the help text now lists `--no-final-newline` with the silent-no-op note.
- `countdown.sh 1` produces output that ends with `Time's up!` followed by a newline (default unchanged).
- `countdown.sh --no-final-newline 1` produces output whose last byte is `!` (no trailing `\n`).
- `countdown.sh --silent --no-final-newline 1` produces `Time's up!\n` (no-op under silent).
- `countdown.sh --no-final-newline abc` exits non-zero with the existing duration error on stderr.

---

- U2. **Add `test_countdown.py` covering the four origin acceptance scenarios**

**Goal:** Create a new `unittest`-style test module that shells out to `countdown.sh` and asserts the four behaviors enumerated in the origin brainstorm — providing automated regression coverage for AE1–AE4.

**Requirements:** R6 (and indirectly R1–R4 via behavioral assertions)

**Dependencies:** U1

**Files:**
- Create: `test_countdown.py`
- Test: `test_countdown.py` (this file is itself the test artifact)

**Approach:**
- Mirror `test_table_fmt.py` style: top-level docstring, `unittest.TestCase` subclass, `unittest.main()` at bottom, no third-party deps.
- Resolve `countdown.sh` path relative to the test file (alongside it in the repo root) so the tests run from any CWD.
- Use `subprocess.run` with the script path and a small duration (`"1"`) per test. Capture stdout/stderr as bytes so trailing-byte assertions are unambiguous.
- Assert on the last byte(s) of stdout rather than the entire stream — the ticker output uses `\r` overwrites and any equality check on the full ticker is brittle. The four scenarios only need to assert the tail (`Time's up!\n` or `Time's up!`) and, for AE4, that the stderr contains the duration error and exit code is non-zero.

**Patterns to follow:**
- `test_table_fmt.py` for `TestCase` grouping, `unittest.main()` entry, and bare-stdlib imports.

**Test scenarios:**
- Covers AE1. Happy path — no flags. Run `countdown.sh 1`; assert exit 0 and stdout ends with the bytes `Time's up!\n` (default behavior preserved).
- Covers AE2. Happy path — flag with visible ticker. Run `countdown.sh --no-final-newline 1`; assert exit 0 and stdout's last byte is `!` (not `\n`), and that `Time's up!` appears at the very end.
- Covers AE3. Happy path — flag with `--silent` is a no-op. Run `countdown.sh --silent --no-final-newline 1`; assert exit 0 and stdout equals exactly `Time's up!\n` (silent-mode output, newline preserved).
- Covers AE4. Error path — flag with invalid duration. Run `countdown.sh --no-final-newline abc`; assert non-zero exit and that stderr contains `Error: duration must be a positive integer (got 'abc')`.
- Edge case — flag order does not matter. Run `countdown.sh 1 --no-final-newline` (flag after duration); assert stdout's last byte is `!` (proves the parser handles either order, AE2 generalized).

**Verification:**
- `python -m unittest test_countdown.py` exits 0 with all five tests passing.
- Total wall-clock runtime is ≲ 6s (each test runs ~1s of `sleep`).

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Test wall-clock runtime accumulates if more scenarios are added later. | Cap each test at duration=1; document the constraint inline so future scenarios stay short or use a different harness if many are needed. |
| Future refactor of the argument parser silently breaks the flag-after-duration order. | The U2 edge-case test (flag after duration) catches regressions on the fall-through behavior. |
| `echo` vs `printf` byte-emission differences on exotic bash builds (e.g., `echo` interpreting backslashes under `xpg_echo`). | The current `echo "Time's up!"` already runs in production unchanged; this plan only adds an alternate `printf "Time's up!"` path with no escape sequences in the literal. The existing default path uses the same `echo` call as today, so no exotic-shell regression is introduced. |

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-26-no-final-newline-flag-requirements.md](../brainstorms/2026-04-26-no-final-newline-flag-requirements.md)
- Related code: `countdown.sh`, `test_table_fmt.py`
- Related issue: #118
