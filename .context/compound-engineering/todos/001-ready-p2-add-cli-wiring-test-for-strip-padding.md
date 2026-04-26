---
status: ready
priority: p2
issue_id: "001"
tags: [testing, cli, table_fmt]
dependencies: []
---

# Add CLI-level wiring test for `--strip-padding` in `table_fmt.py`

## Problem Statement

`main()` in `table_fmt.py` introduces argparse handling for `--strip-padding` and threads `args.strip_padding` into `format_table`. The current `StripPaddingTests` cover the `format_table` keyword path but no test invokes the CLI surface itself. A typo in the flag name, the argparse action, or the `args.strip_padding` attribute name would not be caught by the existing function-level tests.

## Findings

- `table_fmt.py:136-144` adds the argparse `--strip-padding` flag.
- `table_fmt.py:151` wires `args.strip_padding` into `format_table(rows, alignments, strip_padding=args.strip_padding)`.
- `test_table_fmt.py` imports `format_table` and `parse_table` directly — no `subprocess` invocation, no `main()` call, no `sys.argv` patching.
- `argparse` translates `--strip-padding` to the attribute `strip_padding` automatically. A future refactor that renames the flag, drops the `store_true` action, or accidentally references `args.stripPadding` would slip through every existing test.

## Proposed Solutions

### Option 1: Patch `sys.argv` / `sys.stdin` / `sys.stdout` and call `main()` directly

**Approach:** Use `unittest.mock.patch` to replace `sys.argv`, `sys.stdin`, and `sys.stdout` for the duration of the test, then call `table_fmt.main()`. Read the captured stdout buffer and assert on the content.

**Pros:**
- No subprocess overhead; runs in-process so coverage tools see it.
- Deterministic, no Python-interpreter-discovery flakiness on Windows or Linux.
- Fast (microseconds).

**Cons:**
- Slightly more setup than a subprocess test.
- Has to use `io.StringIO` for stdin/stdout swap.

**Effort:** 30 minutes.

**Risk:** Low.

### Option 2: `subprocess.run` with `sys.executable`

**Approach:** Spawn `python table_fmt.py --strip-padding` as a subprocess, pipe a known table to stdin, assert on stdout.

**Pros:**
- Tests the real entry-point path, including any `__main__` block side effects.
- Closer to how a user actually invokes the tool.

**Cons:**
- Slower; subprocess startup is order-of-magnitude more expensive than in-process.
- More moving pieces (interpreter discovery, working directory, encoding).
- More fragile in CI environments that swap interpreters or set `PYTHONHOME`.

**Effort:** 30 minutes.

**Risk:** Low-Medium (interpreter discovery flakiness).

## Recommended Action

Adopt **Option 1**. Add at least two test cases in a new `MainCliTests` class in `test_table_fmt.py`:
1. `test_main_with_strip_padding_emits_compact_data_rows` — patches `sys.argv = ["table_fmt.py", "--strip-padding"]`, pipes a known table via `sys.stdin`, asserts captured stdout contains `|a|b|`-style rows and a padded separator.
2. `test_main_without_flag_emits_padded_data_rows` — same setup with `sys.argv = ["table_fmt.py"]` (no flag), asserts the prior padded form.

Optional: add a third case asserting that `--help` lists `--strip-padding` (use `assertRaises(SystemExit)` and inspect stdout).

## Technical Details

**Affected files:**
- `test_table_fmt.py` — add `MainCliTests` class.

**Related components:**
- `table_fmt.main()` (table_fmt.py:131-151)

**Database changes:** none.

## Resources

- **PR:** Closes #96
- **ce-review run artifact:** `.context/compound-engineering/ce-review/20260425-210217-strip-padding-autofix/run.md`
- **Related finding:** ce-review testing reviewer, finding #1 (P2, conf 0.90)

## Acceptance Criteria

- [ ] At least one in-process test invokes `table_fmt.main()` with `sys.argv` containing `--strip-padding` and asserts the stripped output shape on captured stdout.
- [ ] At least one in-process test invokes `table_fmt.main()` without the flag and asserts the padded output shape.
- [ ] Tests do not require a subprocess interpreter and run reliably on Windows.
- [ ] All existing tests still pass; total suite remains green.

## Work Log

### 2026-04-25 - Surfaced by ce-review autofix

**By:** ce-review autofix run (run id `20260425-210217-strip-padding-autofix`)

**Actions:**
- Synthesized as P2 finding from `testing` reviewer at confidence 0.90.
- Routed to `downstream-resolver` (the reviewer marked it `manual` because subprocess CLI tests can be flaky; in-process patching was deemed safer than auto-applying without an explicit decision).
- Filed as `ready` since synthesis already triaged the work.

**Learnings:**
- Function-level tests do not exercise argparse wiring; the boundary deserves its own test.
