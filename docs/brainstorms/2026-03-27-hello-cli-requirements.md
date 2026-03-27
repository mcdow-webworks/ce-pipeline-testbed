---
date: 2026-03-27
topic: hello-cli
---

# Hello-World CLI Greeting Script

## Problem Frame

The project needs a simple `hello.sh` CLI script that prints a personalized greeting with the current date. This is a foundational utility for the project.

## Requirements

- R1. Script accepts an optional positional name argument; defaults to "World" when omitted
- R2. Prints output in the format: `Hello, <name>! Today is YYYY-MM-DD.`
- R3. `--help` (and `-h`) flag prints usage information and exits
- R4. Script is a valid bash script with appropriate shebang (`#!/usr/bin/env bash`)

## Success Criteria

- Running `./hello.sh` outputs `Hello, World! Today is <today's date>.`
- Running `./hello.sh Alice` outputs `Hello, Alice! Today is <today's date>.`
- Running `./hello.sh --help` prints usage and exits cleanly
- Date uses system date in YYYY-MM-DD format via `date +%Y-%m-%d`

## Scope Boundaries

- Single file script only; no external dependencies
- No installation mechanism or packaging
- No interactive prompts; argument-only interface
- No logging, config files, or persistent state

## Key Decisions

- **Positional argument over named flag for name**: Simpler UX for a single optional parameter. `--name` flag would be overengineering for this scope.
- **Support both `-h` and `--help`**: Standard CLI convention at near-zero cost.
- **Place script at repo root as `hello.sh`**: Matches the issue description and keeps it discoverable.

## Next Steps

-> `/ce:plan` for structured implementation planning
