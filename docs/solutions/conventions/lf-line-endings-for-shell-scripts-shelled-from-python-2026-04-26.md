---
title: Enforce LF line endings for shell scripts shelled from Python tests
date: 2026-04-26
category: conventions
module: repo-wide
problem_type: convention
component: tooling
severity: medium
applies_when:
  - Adding a `.sh` script that any test or tool will invoke via Python `subprocess.run(["bash", ...])`
  - Onboarding a Windows developer to a repo that contains bash scripts
  - A previously-green test starts failing on Windows with `$'\r': command not found` or similar CR-related errors
tags:
  - line-endings
  - gitattributes
  - bash
  - windows
  - cross-platform
  - subprocess
  - testing
---

# Enforce LF line endings for shell scripts shelled from Python tests

## Context

While adding a `--no-final-newline` flag to `countdown.sh` (#118), the new `test_countdown.py` shelled out to `bash` via `subprocess.run(["bash", "countdown.sh", ...])`. On a Windows checkout with `core.autocrlf=true` and no `.gitattributes`, every test invocation failed with errors like:

```
countdown.sh: line 4: $'\r': command not found
countdown.sh: line 5: $'\r': command not found
...
```

The script ran fine in an interactive shell on the same machine. The script also ran fine when Claude Code invoked it via its own Bash tool. Only Python's `subprocess.run` failed. That asymmetry is what makes this gotcha worth writing down — the test infrastructure is silently broken on one platform while every other invocation looks healthy.

The cause is a two-layer interaction:

1. **`core.autocrlf=true` (the Windows default for Git for Windows)** rewrites checked-out text files to CRLF in the working tree. With no `.gitattributes`, `*.sh` files get CRLF on Windows even though they are stored as LF in the index.
2. **Two different `bash` binaries are on PATH on a typical Windows dev box**:
   - Git's MSYS bash (5.2) — handles CR gracefully, treats CRLF lines as if they were LF
   - WSL bash (5.1) — treats `\r` as part of each line, so `#!/usr/bin/env bash\r`, `DURATION=60\r`, etc. all get parsed as commands containing a literal carriage return
3. The Bash tool used by AI agents (and most interactive terminals) typically resolves to **MSYS bash**, so the script appears to work. Python's `subprocess.run` resolves `bash` via the underlying `CreateProcess` / PATH lookup, and on machines where WSL is installed, **WSL bash wins**. Running the same script under `subprocess` blows up where running it interactively did not.

## Guidance

For any repository that contains `.sh` scripts and runs on Windows developer machines, commit a `.gitattributes` at the repo root that pins shell scripts to LF in the working tree:

```gitattributes
# Shell scripts must be LF on every platform — bash on Linux (and the WSL
# bash that subprocess.run finds first on Windows) treats CR as part of the
# command on each line, breaking CRLF-checked-out scripts.
*.sh text eol=lf
```

Notes on adoption:

- `.gitattributes` only changes future checkouts. Existing working-tree files keep whatever line endings they had. After committing the rule, run `git rm --cached -r .` followed by `git reset --hard` (or `git add --renormalize .` when you want a single commit that fixes the working tree) so the new rule actually takes effect on already-checked-out files.
- If a single file already has CRLF and you cannot do a full re-checkout, `tr -d '\r' < script.sh > script.sh.tmp && mv script.sh.tmp script.sh` is a one-shot fix for that file.
- Add this rule **before** writing tests that shell out to bash, not after. The first author hits the issue once; everyone after benefits silently.

## Why This Matters

This bug class is invisible until it surfaces, and when it surfaces it looks like nonsense:

- **CI on Linux is green.** Linux checkouts are LF-only by default, so CI never sees CRLF.
- **Interactive testing on Windows is green** when the developer's `bash` is MSYS (Git Bash, the default for most Windows devs).
- **Only `subprocess.run(["bash", …])` on Windows machines that also have WSL installed** trips the bug. That is a narrow but growing slice — WSL is increasingly the default, and any Python test harness that shells out to bash will hit it the moment one such developer joins the project.
- **The error message (`$'\r': command not found`) does not name CRLF, line endings, WSL, or `core.autocrlf`.** A new contributor hitting it for the first time will spend significant time re-tracing the same investigation that produced this doc.

The durable fix is one line of `.gitattributes`. Skipping it costs every future Windows-on-WSL contributor that same investigation.

## When to Apply

- Any repo containing `.sh` files that are executed by tests, build scripts, CI hooks, or developer tools — apply preemptively
- Any Python test that uses `subprocess.run` (or `Popen`, `check_output`, etc.) to invoke `bash`, `sh`, `zsh`, or any other shell
- Any time a previously passing bash-invoking test fails with `$'\r': command not found`, "syntax error near unexpected token", or other CR-shaped errors after a Windows checkout
- Apply the rule to other shell-family extensions too (`*.bash`, `*.zsh`) when those exist in the repo

Do **not** apply `eol=lf` blindly to all text — it is correct for shell scripts, makefiles, and other tools that parse line-by-line, but Windows-specific files like `*.bat` and `*.ps1` should keep CRLF (`*.bat text eol=crlf`).

## Examples

**Repo state at the start of #118 (broken):**

```
$ python -m unittest test_countdown.py -v
test_default_preserves_trailing_newline (test_countdown.DefaultBehaviorTests) ... FAIL

======================================================================
FAIL: test_default_preserves_trailing_newline
----------------------------------------------------------------------
AssertionError: 1 != 0  # exit code from bash
stderr: countdown.sh: line 4: $'\r': command not found
        countdown.sh: line 5: $'\r': command not found
        ...
```

**After committing `.gitattributes` and renormalizing the working tree:**

```
$ python -m unittest test_countdown.py -v
test_default_preserves_trailing_newline ... ok
test_flag_after_duration_still_drops_trailing_newline ... ok
test_flag_with_visible_ticker_drops_trailing_newline ... ok
test_flag_under_silent_is_a_noop ... ok
test_flag_with_invalid_duration_errors ... ok

----------------------------------------------------------------------
Ran 5 tests in 8.0s

OK
```

**Diagnostic one-liners worth knowing:**

```bash
# Which bash will subprocess.run actually invoke on this machine?
python -c "import shutil; print(shutil.which('bash'))"

# Does this file have CR bytes?
od -c countdown.sh | head -3
# Look for "\r" tokens between the visible characters

# What does Git think the working-tree and index encodings are?
git ls-files --eol countdown.sh
# i/lf  w/crlf  attr/text=auto  countdown.sh   <-- working tree is CRLF, index is LF
# i/lf  w/lf    attr/-text eol=lf countdown.sh <-- after the fix
```

### Bonus learning — verifying trailing newlines in tests

This investigation surfaced a related test-writing gotcha that is worth keeping nearby: **`$(cmd)` command substitution strips trailing newlines.** It cannot be used to assert presence or absence of a final newline byte. To verify trailing-byte behavior in a test, capture raw bytes via `subprocess.run(..., capture_output=True)` and inspect `result.stdout[-1:]` or `result.stdout.endswith(b"...\n")`:

```python
result = subprocess.run(
    ["bash", "countdown.sh", "--no-final-newline", "1"],
    capture_output=True,
    cwd=str(SCRIPT_DIR),  # bare filename + cwd avoids backslash-escape issues on Windows
)
self.assertEqual(result.stdout[-1:], b"!")
self.assertTrue(result.stdout.endswith(b"Time's up!"))
```

The `cwd=SCRIPT_DIR` + bare filename pattern also dodges a separate Windows pitfall — passing an absolute Windows path like `C:\Users\…\countdown.sh` to bash, where `\U` gets reinterpreted as a Unicode escape sequence and the path is silently mangled.

## Related

- GitHub issue #118 — `--no-final-newline` flag for `countdown.sh`
- Commits: `1de938c` (feat — adds `.gitattributes` alongside the flag), `e5781eb` (test assertion strengthening)
- Files: `.gitattributes`, `test_countdown.py`, `countdown.sh`
