#!/usr/bin/env python3
"""Tests for countdown.sh: --no-final-newline flag behavior and parser interactions."""

import subprocess
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_NAME = "countdown.sh"


def run_countdown(*args):
    """Invoke countdown.sh via bash with raw byte capture.

    Runs from SCRIPT_DIR with the bare filename so the test file is portable
    across CWDs and avoids backslash-escape pitfalls when handing absolute
    Windows paths to bash.
    """
    return subprocess.run(
        ["bash", SCRIPT_NAME, *args],
        capture_output=True,
        cwd=str(SCRIPT_DIR),
    )


class DefaultBehaviorTests(unittest.TestCase):
    def test_default_preserves_trailing_newline(self):
        """AE1: countdown.sh 1 ends with the bytes 'Time's up!\\n'."""
        result = run_countdown("1")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(
            result.stdout.endswith(b"Time's up!\n"),
            f"stdout did not end with 'Time's up!\\n'; tail={result.stdout[-16:]!r}",
        )


class NoFinalNewlineFlagTests(unittest.TestCase):
    def test_flag_with_visible_ticker_drops_trailing_newline(self):
        """AE2: --no-final-newline 1 ends with '!' (no trailing newline)."""
        result = run_countdown("--no-final-newline", "1")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout[-1:], b"!")
        self.assertTrue(
            result.stdout.endswith(b"Time's up!"),
            f"stdout did not end with 'Time's up!'; tail={result.stdout[-16:]!r}",
        )

    def test_flag_after_duration_still_drops_trailing_newline(self):
        """Flag order does not matter — '1 --no-final-newline' still drops the newline."""
        result = run_countdown("1", "--no-final-newline")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout[-1:], b"!")


class SilentInteractionTests(unittest.TestCase):
    def test_flag_under_silent_is_a_noop(self):
        """AE3: --silent --no-final-newline emits exactly 'Time's up!\\n'."""
        result = run_countdown("--silent", "--no-final-newline", "1")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"Time's up!\n")


class InvalidDurationTests(unittest.TestCase):
    def test_flag_with_invalid_duration_errors(self):
        """AE4: --no-final-newline abc exits non-zero with the duration error on stderr."""
        result = run_countdown("--no-final-newline", "abc")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"Error: duration must be a positive integer (got 'abc')",
            result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
