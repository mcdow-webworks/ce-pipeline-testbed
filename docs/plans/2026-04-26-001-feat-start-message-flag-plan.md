---
title: "feat: Add --start-message flag to countdown.sh"
type: feat
status: active
date: 2026-04-26
origin: docs/brainstorms/2026-04-26-start-message-flag-requirements.md
---

# feat: Add --start-message flag to countdown.sh

## Overview

Add a `--start-message <text>` flag to `countdown.sh` that prints a custom message line before the countdown begins. The flag defaults to an empty string (no change to existing behavior) and is suppressed when `--silent` is active.

## Problem Frame

`countdown.sh` begins counting immediately with no way to print a preamble. Users want to display context (e.g. "Go!", "Starting build timer…") before the countdown starts without wrapping the script in a shell one-liner. (see origin: docs/brainstorms/2026-04-26-start-message-flag-requirements.md)

## Requirements Trace

- R1. Add a `--start-message <text>` flag that consumes the next argument as its value.
- R2. When non-empty and `--silent` is not set, print the message on its own line before the countdown loop.
- R3. `--silent` suppresses the start message (silent wins).
- R4. Default is empty string; omitting the flag preserves existing behavior exactly.
- R5. Document `--start-message` in `--help` output.

## Scope Boundaries

- No multi-word quoting beyond standard shell quoting — the shell handles it.
- No color, formatting, or delay on the start message.

## Context & Research

### Relevant Code and Patterns

- `countdown.sh` — the sole file being modified; existing `--silent` flag establishes the pattern for suppression logic.

### Institutional Learnings

- None applicable for this scope.

## Key Technical Decisions

- **Silent wins over start-message**: Consistent with existing `--silent` semantics; silent means no non-essential output.
- **Arg parsing converted to `while`/`shift`**: The prior `for arg in "$@"` loop cannot consume the next positional argument. A `while [[ $# -gt 0 ]]; do case/shift` pattern is the minimal change needed.
- **Variable initialized at top with empty default**: Ensures backward-compatible behavior when the flag is omitted.

## Open Questions

### Resolved During Planning

- *Can the while/shift refactor break existing positional arg handling?* No — the numeric duration argument falls through to the `*` case and is consumed with a single `shift`, preserving current behavior.

### Deferred to Implementation

- None — requirements and approach are fully specified.

## Implementation Units

- [ ] **Unit 1: Add --start-message flag to countdown.sh**

**Goal:** Implement the flag with argparse handling, conditional output, and help documentation.

**Requirements:** R1, R2, R3, R4, R5

**Dependencies:** None

**Files:**
- Modify: `countdown.sh`

**Approach:**
- Initialize `START_MESSAGE=""` alongside the other defaults at the top of the script.
- Convert the existing argument loop to `while [[ $# -gt 0 ]]; do case "$1"` to support consuming `$2` for the flag value.
- Add a `--start-message)` branch that assigns `"$2"` to `START_MESSAGE` and does `shift 2`.
- After argument parsing and validation, add a guarded print: if `START_MESSAGE` is non-empty and `SILENT` is false, `echo "$START_MESSAGE"`.
- Add the flag documentation under `Options:` in the `--help` heredoc.

**Patterns to follow:**
- Existing `--silent` flag pattern for suppression guard.
- Existing `--help` heredoc formatting for documentation.

**Test scenarios:**
- `./countdown.sh 3 --start-message "Go!"` → prints `Go!` on its own line, then countdown proceeds.
- `./countdown.sh 3 --silent --start-message "Go!"` → no extra line printed (silent wins).
- `./countdown.sh 3 --start-message "Go!" --silent` → same as above regardless of flag order.
- `./countdown.sh 3` → existing behavior unchanged, no extra line.
- `./countdown.sh --help` → output includes `--start-message <text>` with description.
- `./countdown.sh 3 --start-message ""` → no line printed (empty string treated as unset).

**Verification:**
- Running each acceptance scenario from the issue produces the documented output.
- `--help` output includes the flag entry.
- No regression in the basic `./countdown.sh <N>` invocation.

## System-Wide Impact

- **Interaction graph:** No callbacks, middleware, or observers — `countdown.sh` is a standalone script.
- **Error propagation:** No new error paths introduced; flag is optional with a safe default.
- **State lifecycle risks:** None — stateless script.
- **API surface parity:** N/A.
- **Integration coverage:** Manual smoke tests cover all acceptance scenarios.

## Risks & Dependencies

- Low risk. Single-file change with a well-established shell pattern. The while/shift conversion is the only structural change, and it is equivalent to the prior for-loop for all existing invocations.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-26-start-message-flag-requirements.md](docs/brainstorms/2026-04-26-start-message-flag-requirements.md)
- Related code: `countdown.sh`
