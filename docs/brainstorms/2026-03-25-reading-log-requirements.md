---
date: 2026-03-25
topic: reading-log-command
---

# Reading Log Command

## Problem Frame

The user forgets when they read books and whether they liked them. Opening a spreadsheet is too much friction. A simple CLI that runs from the terminal fits their workflow naturally.

## Requirements

- R1. `bookshelf log start "<title>"` records today as the start date for a book, setting its status to "reading"
- R2. `bookshelf log finish "<title>"` records today as the finish date, setting its status to "finished"
- R3. `bookshelf log finish "<title>" --rating <1-5>` optionally records a star rating (integer 1-5) when finishing
- R4. `bookshelf log list` displays all books with status (reading/finished), start date, finish date (if applicable), and rating (if applicable)
- R5. Data is stored in `~/.bookshelf/reading-log.json`; the directory and file are created automatically on first use
- R6. Title matching is case-insensitive exact match (e.g., "the pragmatic programmer" matches "The Pragmatic Programmer")
- R7. Starting a book that is already "reading" is rejected with a clear message
- R8. Finishing a book that was never started auto-backfills the start date to the same day (so casual users aren't blocked)
- R9. `--date YYYY-MM-DD` flag on both `start` and `finish` overrides today's date (enables backfilling past reads)
- R10. Re-reading: starting a book that is already "finished" creates a new reading entry
- R11. Invalid ratings (outside 1-5 or non-integer) are rejected with a clear message
- R12. Works on Windows (PowerShell and Git Bash) and macOS
- R13. No external dependencies beyond Node.js standard library

## Success Criteria

- User can record starting and finishing books from the terminal in under 5 seconds
- Reading history persists across sessions in a human-readable JSON file
- Works identically on Windows and macOS without platform-specific code paths

## Scope Boundaries

- No edit or delete commands (v1 — users can hand-edit the JSON if needed)
- No filtering, sorting, or search in `list`
- No import/export
- No web service or API
- No configuration beyond the default storage path

## Key Decisions

- **Rating is optional on finish**: Reduces friction; not every book warrants a rating
- **Case-insensitive title matching**: Prevents frustrating "book not found" errors from capitalization differences
- **Auto-backfill start date on finish**: Unblocks casual users who finish a book without having logged the start
- **`--date` override flag**: Low implementation cost, high value for backfilling reading history
- **Re-reading creates new entry**: Simpler than updating an existing finished entry; preserves history of multiple reads

## Outstanding Questions

### Resolve Before Planning

(None)

### Deferred to Planning

- [Affects R4][Technical] What format should `list` output use — plain text table, or something else? Decide during implementation based on what looks good in a terminal.
- [Affects R5][Technical] JSON schema for reading-log.json — define during planning.

## Next Steps

-> `/ce:plan` for structured implementation planning
