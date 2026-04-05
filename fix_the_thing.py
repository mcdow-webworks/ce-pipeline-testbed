#!/usr/bin/env python3
"""Utility that identifies and reports common issues in a project directory."""

import os
import sys


def check_missing_readme() -> bool:
    """Returns True if README.md is missing."""
    return not os.path.isfile("README.md")


def check_empty_files() -> list[str]:
    """Returns list of empty files in the current directory."""
    empty = []
    for entry in os.listdir("."):
        if os.path.isfile(entry) and os.path.getsize(entry) == 0:
            empty.append(entry)
    return sorted(empty)


def check_trailing_whitespace(filepath: str) -> list[int]:
    """Returns line numbers with trailing whitespace."""
    line_numbers = []
    with open(filepath, "r") as f:
        for i, line in enumerate(f, start=1):
            stripped = line.rstrip("\n\r")
            if stripped != stripped.rstrip():
                line_numbers.append(i)
    return line_numbers


def main() -> int:
    """Runs all checks and prints a summary report. Returns exit code."""
    issues_found = False

    # Check for missing README
    if check_missing_readme():
        print("ISSUE: README.md is missing")
        issues_found = True
    else:
        print("OK: README.md exists")

    # Check for empty files
    empty_files = check_empty_files()
    if empty_files:
        print(f"ISSUE: Found {len(empty_files)} empty file(s):")
        for f in empty_files:
            print(f"  - {f}")
        issues_found = True
    else:
        print("OK: No empty files found")

    # Check for trailing whitespace in all files
    trailing_ws_found = False
    for entry in sorted(os.listdir(".")):
        if not os.path.isfile(entry):
            continue
        try:
            lines = check_trailing_whitespace(entry)
            if lines:
                print(f"ISSUE: Trailing whitespace in {entry} on line(s): {', '.join(str(n) for n in lines)}")
                trailing_ws_found = True
        except UnicodeDecodeError:
            pass  # binary file, nothing to check
        except PermissionError:
            print(f"WARNING: Could not read {entry}, skipping")

    if trailing_ws_found:
        issues_found = True

    if not trailing_ws_found:
        print("OK: No trailing whitespace found")

    if issues_found:
        print("\nSummary: Issues detected.")
        return 1
    else:
        print("\nSummary: No issues found.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
