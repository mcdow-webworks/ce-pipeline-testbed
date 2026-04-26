---
date: 2026-04-26
topic: start-message-flag
---

# --start-message Flag for countdown.sh

## Problem Frame

`countdown.sh` begins counting immediately with no way to print a preamble. Users want to display context (e.g. "Go!", "Starting build timer…") before the countdown begins without wrapping the script in a shell one-liner.

## Requirements

- R1. Add a `--start-message <text>` flag that accepts the next positional argument as its value.
- R2. When `--start-message` is non-empty and `--silent` is not set, print the message on its own line before the countdown loop begins.
- R3. When `--silent` is set, suppress the start message entirely (silent wins).
- R4. Default value is empty string; omitting the flag preserves existing behavior exactly.
- R5. Document `--start-message` in `--help` output.

## Success Criteria

- `./countdown.sh 3 --start-message "Go!"` prints `Go!` on its own line, then the countdown.
- `./countdown.sh 3 --silent --start-message "Go!"` prints no extra line.
- `./countdown.sh 3` (no flag) preserves existing behavior — no extra line.
- `--help` documents the flag.

## Scope Boundaries

- No support for multi-word quoting beyond standard shell quoting (the shell handles it).
- No color, formatting, or delay on the start message.

## Key Decisions

- **Silent wins over start-message**: Consistent with existing `--silent` semantics — silent means no non-essential output.
- **Arg parsing changed to while/shift**: The current `for arg in "$@"` loop cannot consume the next argument. Switching to a positional `while`+`shift` pattern is the minimal change needed to support `--start-message <text>`.

## Next Steps

→ Implement directly (lightweight, requirements complete)
