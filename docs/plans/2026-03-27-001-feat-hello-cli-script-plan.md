---
title: "feat: Add hello.sh CLI greeting script"
type: feat
status: active
date: 2026-03-27
origin: docs/brainstorms/2026-03-27-hello-cli-requirements.md
---

# feat: Add hello.sh CLI greeting script

## Overview

Add a simple `hello.sh` bash script to the repo root that prints a personalized greeting with the current date. This is the project's first functional script.

## Problem Frame

The project needs a foundational CLI utility that greets the user by name with today's date. The scope is intentionally minimal — a single self-contained bash script with no dependencies. (see origin: `docs/brainstorms/2026-03-27-hello-cli-requirements.md`)

## Requirements Trace

- R1. Script accepts an optional positional name argument; defaults to "World" when omitted
- R2. Prints output in the format: `Hello, <name>! Today is YYYY-MM-DD.`
- R3. `--help` (and `-h`) flag prints usage information and exits
- R4. Script is a valid bash script with appropriate shebang (`#!/usr/bin/env bash`)

## Scope Boundaries

- Single file script only; no external dependencies
- No installation mechanism or packaging
- No interactive prompts; argument-only interface
- No logging, config files, or persistent state

## Key Technical Decisions

- **Positional argument for name** (not `--name` flag): Simpler UX for a single optional parameter. A named flag would be overengineering. (see origin)
- **Support both `-h` and `--help`**: Standard CLI convention at near-zero cost. (see origin)
- **Script placed at repo root as `hello.sh`**: Matches the issue description and keeps it discoverable. (see origin)
- **`date +%Y-%m-%d` for date formatting**: Portable across Linux and macOS, satisfies the YYYY-MM-DD requirement.

## Implementation Units

- [ ] **Unit 1: Create hello.sh script**

  **Goal:** Deliver the complete `hello.sh` script satisfying all requirements.

  **Requirements:** R1, R2, R3, R4

  **Dependencies:** None

  **Files:**
  - Create: `hello.sh`

  **Approach:**
  - Use `#!/usr/bin/env bash` shebang for portability
  - Parse arguments with a simple `case` or conditional check: if first arg is `-h` or `--help`, print usage and exit 0
  - If a positional argument is provided, use it as the name; otherwise default to `"World"`
  - Print greeting using `date +%Y-%m-%d` for the date portion
  - Mark the file as executable (`chmod +x`)

  **Patterns to follow:**
  - No existing patterns in the repo; follow standard bash script conventions (shebang, `set -e` optional for this scope, clean exit codes)

  **Test scenarios:**
  - `./hello.sh` outputs `Hello, World! Today is <today's date>.`
  - `./hello.sh Alice` outputs `Hello, Alice! Today is <today's date>.`
  - `./hello.sh --help` prints usage text and exits with code 0
  - `./hello.sh -h` prints the same usage text and exits with code 0
  - `./hello.sh "Two Words"` correctly handles a quoted multi-word name

  **Verification:**
  - Script runs without errors on bash
  - All test scenarios produce expected output
  - `file hello.sh` or `head -1 hello.sh` confirms valid shebang
  - Script has executable permission

## Risks & Dependencies

- None significant. The script has no external dependencies and cannot break existing functionality (the repo has no other code).

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-27-hello-cli-requirements.md](../brainstorms/2026-03-27-hello-cli-requirements.md)
