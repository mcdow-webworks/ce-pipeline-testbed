#!/usr/bin/env python3
"""Tests for countdown.sh: format_tick helper plus the --tick-format CLI flag."""

import os
import shlex
import subprocess
import unittest

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPT_REL = "./countdown.sh"


def format_tick(seconds, mode):
    """Source countdown.sh and call format_tick directly."""
    cmd = "source {script} && format_tick {s} {m}".format(
        script=shlex.quote(SCRIPT_REL),
        s=shlex.quote(str(seconds)),
        m=shlex.quote(mode),
    )
    return subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )


def run_countdown(*args):
    """Invoke countdown.sh as a subprocess."""
    return subprocess.run(
        ["bash", SCRIPT_REL, *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )


class FormatTickSecondsTests(unittest.TestCase):
    def test_seconds_mode_renders_bare_seconds(self):
        result = format_tick(30, "seconds")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "30s")

    def test_empty_mode_is_default_equivalent(self):
        result = format_tick(30, "")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "30s")


class FormatTickMmSsTests(unittest.TestCase):
    def test_under_a_minute_zero_pads_minutes(self):
        result = format_tick(30, "mm-ss")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "00:30")

    def test_one_minute_thirty(self):
        result = format_tick(90, "mm-ss")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "01:30")

    def test_ten_minutes_zero_pads_seconds(self):
        result = format_tick(600, "mm-ss")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "10:00")

    def test_zero_seconds_renders_double_zero(self):
        result = format_tick(0, "mm-ss")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "00:00")


class FormatTickHumanTests(unittest.TestCase):
    def test_seconds_only_when_under_a_minute(self):
        result = format_tick(30, "human")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "30s")

    def test_minutes_only_when_seconds_zero(self):
        result = format_tick(60, "human")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "1m")

    def test_minutes_and_seconds_when_both_nonzero(self):
        result = format_tick(90, "human")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "1m 30s")

    def test_ten_minutes_omits_zero_seconds(self):
        result = format_tick(600, "human")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "10m")

    def test_no_hour_rollup_at_sixty_minutes(self):
        result = format_tick(3600, "human")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "60m")

    def test_zero_seconds_renders_zero_s(self):
        result = format_tick(0, "human")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "0s")


class FormatTickUnknownModeTests(unittest.TestCase):
    def test_unknown_mode_returns_nonzero_with_empty_stdout(self):
        result = format_tick(30, "unknown")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


class CliTickFormatTests(unittest.TestCase):
    def test_mm_ss_equals_form_renders_padded_time(self):
        result = run_countdown("--tick-format=mm-ss", "1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Time remaining: 00:01", result.stdout)
        self.assertIn("Time's up!", result.stdout)

    def test_human_form_renders_compact_time(self):
        result = run_countdown("--tick-format", "human", "1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Time remaining: 1s", result.stdout)
        self.assertIn("Time's up!", result.stdout)

    def test_seconds_mode_matches_default_byte_for_byte(self):
        with_flag = run_countdown("--tick-format", "seconds", "1")
        no_flag = run_countdown("1")
        self.assertEqual(with_flag.returncode, 0)
        self.assertEqual(no_flag.returncode, 0)
        self.assertEqual(with_flag.stdout, no_flag.stdout)
        self.assertEqual(with_flag.stderr, no_flag.stderr)


class CliErrorPathTests(unittest.TestCase):
    def test_invalid_value_fails_before_loop(self):
        result = run_countdown("--tick-format", "foo", "1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--tick-format", result.stderr)
        self.assertIn("foo", result.stderr)
        self.assertIn("seconds", result.stderr)
        self.assertIn("mm-ss", result.stderr)
        self.assertIn("human", result.stderr)
        self.assertNotIn("Time remaining", result.stdout)
        self.assertNotIn("Time's up!", result.stdout)

    def test_missing_value_at_end_of_argv_errors(self):
        result = run_countdown("--tick-format")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--tick-format", result.stderr)
        self.assertNotIn("Time remaining", result.stdout)
        self.assertNotIn("Time's up!", result.stdout)

    def test_empty_value_via_equals_form_errors(self):
        result = run_countdown("--tick-format=", "1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--tick-format", result.stderr)
        self.assertNotIn("Time remaining", result.stdout)
        self.assertNotIn("Time's up!", result.stdout)


class CliSilentInteractionTests(unittest.TestCase):
    def test_silent_suppresses_ticker_regardless_of_format(self):
        result = run_countdown("--silent", "--tick-format", "human", "1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Time's up!", result.stdout)
        self.assertNotIn("Time remaining", result.stdout)


class CliHelpTests(unittest.TestCase):
    def test_help_documents_tick_format_and_all_modes(self):
        result = run_countdown("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--tick-format", result.stdout)
        self.assertIn("seconds", result.stdout)
        self.assertIn("mm-ss", result.stdout)
        self.assertIn("human", result.stdout)


if __name__ == "__main__":
    unittest.main()
