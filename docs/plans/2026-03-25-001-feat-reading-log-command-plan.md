---
title: "feat: Add bookshelf log command for tracking reading history"
type: feat
status: active
date: 2026-03-25
origin: docs/brainstorms/2026-03-25-reading-log-requirements.md
---

# feat: Add bookshelf log command for tracking reading history

## Overview

Add a `bookshelf log` CLI command with `start`, `finish`, and `list` subcommands that lets the user record when they begin and complete books, optionally rate them, and view their reading history. Data persists in a local JSON file. This is a greenfield implementation — the repository has no existing code.

## Problem Frame

The user forgets when they read books and whether they liked them. A spreadsheet is too much friction. A terminal CLI fits their workflow naturally. (see origin: `docs/brainstorms/2026-03-25-reading-log-requirements.md`)

## Requirements Trace

- R1. `bookshelf log start "<title>"` records today as the start date, status "reading"
- R2. `bookshelf log finish "<title>"` records today as the finish date, status "finished"
- R3. `bookshelf log finish "<title>" --rating <1-5>` optionally records a star rating
- R4. `bookshelf log list` displays all books with status, dates, and rating
- R5. Data stored in `~/.bookshelf/reading-log.json`, auto-created on first use
- R6. Title matching is case-insensitive exact match
- R7. Starting a book already "reading" is rejected with a clear message
- R8. Finishing a never-started book auto-backfills start date to the same day
- R9. `--date YYYY-MM-DD` flag on both `start` and `finish` overrides today's date
- R10. Re-reading a finished book creates a new entry
- R11. Invalid ratings (outside 1-5 or non-integer) are rejected
- R12. Works on Windows (PowerShell, Git Bash) and macOS
- R13. No external dependencies beyond Node.js standard library

## Scope Boundaries

- No edit or delete commands (users can hand-edit JSON)
- No filtering, sorting, or search in `list`
- No import/export
- No web service or API
- No configuration beyond the default storage path

## Context & Research

### Relevant Code and Patterns

This is a greenfield project — no existing code. Conventions will be established by this plan.

### Key Technology Decisions

- **Node.js built-in `util.parseArgs`** (available since Node 18.3) for CLI argument parsing — satisfies R13 (no external dependencies)
- **Node.js built-in `node:test`** (available since Node 18) for testing — keeps dev dependencies minimal while providing a real test runner
- **`node:fs`**, **`node:path`**, **`node:os`** for cross-platform file I/O — `os.homedir()` resolves `~` portably (R12)
- **ESM modules** (`"type": "module"` in package.json) — modern Node.js convention

### Institutional Learnings

None — this is a new repository with no `docs/solutions/` directory.

## Key Technical Decisions

- **`util.parseArgs` for CLI parsing**: Built into Node.js 18+, avoids external dependencies. Handles `--rating`, `--date` flags cleanly. (see origin: R13)
- **Flat array JSON schema**: Each reading entry is an object in a top-level array. Simple, human-readable, easy to append. No need for indexed lookup at this scale.
- **`node:test` for testing**: Built into Node.js 18+, no dev dependencies needed. Aligns with the spirit of R13.
- **Single entry point with command router**: `bin/bookshelf.js` parses the top-level command (`log`) and delegates to subcommand handlers. Keeps the door open for future commands without over-engineering.
- **`list` output as aligned plain text**: Simple columnar output using string padding. No box-drawing or color dependencies. Readable in any terminal. (Resolves deferred question from origin doc.)

## JSON Schema for reading-log.json

> *Directional guidance for review, not implementation specification.*

```json
[
  {
    "title": "The Pragmatic Programmer",
    "startDate": "2026-03-20",
    "finishDate": "2026-03-25",
    "rating": 5,
    "status": "finished"
  },
  {
    "title": "Designing Data-Intensive Applications",
    "startDate": "2026-03-25",
    "finishDate": null,
    "rating": null,
    "status": "reading"
  }
]
```

- `title`: string, stored as-is (original casing from first entry)
- `startDate` / `finishDate`: ISO date strings (`YYYY-MM-DD`) or `null`
- `rating`: integer 1-5 or `null`
- `status`: `"reading"` or `"finished"`

## Open Questions

### Resolved During Planning

- **`list` output format** (deferred from origin): Plain text with aligned columns. Simple, no dependencies, works in all terminals.
- **JSON schema** (deferred from origin): Flat array of entry objects. See schema above.
- **Node.js minimum version**: 18.3+ (required for `util.parseArgs`). Document in README.

### Deferred to Implementation

- **Exact column widths and padding for `list` output**: Depends on how it looks in practice — tune during implementation.
- **Error message wording**: Write during implementation; keep concise and actionable.

## Implementation Units

- [ ] **Unit 1: Project scaffolding and CLI entry point**

  **Goal:** Establish the project structure, package.json, and a working `bookshelf` command that responds to `--help` or unknown input with a usage message.

  **Requirements:** R12, R13

  **Dependencies:** None

  **Files:**
  - Create: `package.json`
  - Create: `bin/bookshelf.js`
  - Create: `src/commands/log.js`

  **Approach:**
  - `package.json` with `"type": "module"`, `"bin": { "bookshelf": "./bin/bookshelf.js" }`, and `node:test` as the test script
  - `bin/bookshelf.js` has a shebang (`#!/usr/bin/env node`), reads `process.argv`, routes to the `log` command handler
  - `src/commands/log.js` exports a function that uses `util.parseArgs` to parse subcommands (`start`, `finish`, `list`) and flags (`--rating`, `--date`)
  - Print usage message for unrecognized commands

  **Patterns to follow:**
  - Standard Node.js CLI package conventions (`bin` field, shebang line)

  **Verification:**
  - `node bin/bookshelf.js log` prints usage or help text
  - `node bin/bookshelf.js` with no args prints top-level usage

- [ ] **Unit 2: Storage layer (read/write JSON)**

  **Goal:** Implement the data persistence layer that reads and writes `~/.bookshelf/reading-log.json`, auto-creating the directory and file on first use.

  **Requirements:** R5, R12

  **Dependencies:** Unit 1

  **Files:**
  - Create: `src/storage.js`
  - Create: `test/storage.test.js`

  **Approach:**
  - `loadLog()`: reads and parses the JSON file; returns `[]` if file doesn't exist
  - `saveLog(entries)`: writes the array to JSON with 2-space indent for human readability
  - `getLogPath()`: uses `os.homedir()` + `path.join()` for cross-platform path resolution
  - Auto-create `~/.bookshelf/` directory using `fs.mkdirSync` with `{ recursive: true }`
  - All file operations synchronous (CLI tool, simplicity over async)

  **Test scenarios:**
  - Load returns empty array when file doesn't exist
  - Load returns parsed entries from existing file
  - Save creates directory and file when they don't exist
  - Save overwrites existing file with updated entries
  - Round-trip: save then load returns identical data

  **Verification:**
  - Tests pass with `node --test test/storage.test.js`
  - Storage works with a temp directory (tests should not touch real `~/.bookshelf/`)

- [ ] **Unit 3: `start` and `finish` command logic**

  **Goal:** Implement the `start` and `finish` subcommands with all validation, edge cases, and flag handling.

  **Requirements:** R1, R2, R3, R6, R7, R8, R9, R10, R11

  **Dependencies:** Unit 2

  **Files:**
  - Modify: `src/commands/log.js`
  - Create: `test/commands/log.test.js`

  **Approach:**
  - `start`: find existing entry by case-insensitive title match; reject if status is "reading" (R7); if status is "finished", create new entry (R10); otherwise create new entry with status "reading"
  - `finish`: find existing "reading" entry by case-insensitive title match; if not found, auto-backfill with start date = today (R8); set status to "finished", record finish date
  - `--rating` on finish: validate integer 1-5 (R11), reject otherwise
  - `--date YYYY-MM-DD` on both: validate format, use as override date (R9)
  - Title is the first positional argument after the subcommand

  **Test scenarios:**
  - Start a new book: creates entry with status "reading" and today's date
  - Start a book already reading: rejected with message (R7)
  - Start a finished book: creates new entry, preserves old one (R10)
  - Finish a reading book: updates status to "finished", records date
  - Finish with rating: stores rating (R3)
  - Finish with invalid rating (0, 6, 3.5, "abc"): rejected (R11)
  - Finish unstarted book: auto-backfills start date (R8)
  - Start with `--date 2026-01-15`: uses provided date instead of today (R9)
  - Finish with `--date 2026-01-20`: uses provided date (R9)
  - Title matching is case-insensitive (R6)
  - Missing title argument: prints error

  **Verification:**
  - All test scenarios pass
  - Manual smoke test: start a book, finish it with rating, verify JSON file contents

- [ ] **Unit 4: `list` command and output formatting**

  **Goal:** Implement the `list` subcommand that displays all reading log entries in a readable table format.

  **Requirements:** R4

  **Dependencies:** Unit 2, Unit 3

  **Files:**
  - Modify: `src/commands/log.js`
  - Create or modify: `test/commands/log.test.js`

  **Approach:**
  - Load all entries from storage
  - Print a header row and one row per entry with columns: Title, Status, Started, Finished, Rating
  - Use `String.padEnd()` for column alignment
  - Show `—` or blank for null fields (finishDate, rating)
  - If no entries, print a friendly "No books logged yet" message
  - Output to `process.stdout` for testability

  **Test scenarios:**
  - Empty log: prints "No books logged yet"
  - Mix of reading and finished books: all fields display correctly
  - Book with no rating: rating column shows placeholder
  - Book with no finish date: finish column shows placeholder

  **Verification:**
  - Tests pass
  - Manual check: output is readable and aligned in both PowerShell and bash

## Risks & Dependencies

- **Node.js version requirement**: `util.parseArgs` requires Node 18.3+. Mitigated by documenting the minimum version in README and `package.json` `engines` field.
- **No external test isolation library**: Tests must manage temp directories manually for storage tests. Minor inconvenience, not a blocker.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-25-reading-log-requirements.md](docs/brainstorms/2026-03-25-reading-log-requirements.md)
- Related issue: #1
- Node.js `util.parseArgs` docs: https://nodejs.org/api/util.html#utilparseargsconfig
- Node.js `node:test` docs: https://nodejs.org/api/test.html
