#!/usr/bin/env python3
"""Tests for table_fmt: alignment parsing, separator emission, cell padding."""

import argparse
import io
import sys
import unittest
from unittest import mock

from table_fmt import _positive_int_at_least_4, format_table, main, parse_table


class ParseAlignmentTests(unittest.TestCase):
    def test_parses_mixed_alignments(self):
        text = (
            "| Name | Age | City |\n"
            "| :--- | ---: | :---: |\n"
            "| Alice | 30 | NYC |\n"
        )
        rows, alignments = parse_table(text)
        self.assertEqual(rows, [["Name", "Age", "City"], ["Alice", "30", "NYC"]])
        self.assertEqual(alignments, ["left", "right", "center"])

    def test_no_alignment_hints_yields_none_per_column(self):
        text = (
            "| A | B |\n"
            "| --- | --- |\n"
            "| x | y |\n"
        )
        rows, alignments = parse_table(text)
        self.assertEqual(rows, [["A", "B"], ["x", "y"]])
        self.assertEqual(alignments, [None, None])

    def test_table_without_separator_row(self):
        text = (
            "| A | B |\n"
            "| x | y |\n"
        )
        rows, alignments = parse_table(text)
        self.assertEqual(rows, [["A", "B"], ["x", "y"]])
        self.assertEqual(alignments, [])


class FormatSeparatorTests(unittest.TestCase):
    def test_emits_colons_for_each_alignment(self):
        rows = [["H1", "H2", "H3"], ["a", "b", "c"]]
        alignments = ["left", "right", "center"]
        out = format_table(rows, alignments)
        sep = out.splitlines()[1]
        # Column widths are min 3, so the separator cells are 3 chars wide.
        self.assertEqual(sep, "| :-- | --: | :-: |")

    def test_plain_separator_when_no_alignment(self):
        rows = [["H1", "H2"], ["a", "b"]]
        out = format_table(rows)
        sep = out.splitlines()[1]
        self.assertEqual(sep, "| --- | --- |")

    def test_none_entries_emit_plain_dashes(self):
        rows = [["H1", "H2"], ["a", "b"]]
        out = format_table(rows, [None, None])
        sep = out.splitlines()[1]
        self.assertEqual(sep, "| --- | --- |")


class FormatRowPaddingTests(unittest.TestCase):
    def test_right_aligned_cells_use_rjust(self):
        rows = [["Header"], ["x"]]
        out = format_table(rows, ["right"])
        lines = out.splitlines()
        self.assertEqual(lines[0], "| Header |")
        self.assertEqual(lines[2], "|      x |")

    def test_center_aligned_cells_use_center(self):
        rows = [["Header"], ["x"]]
        out = format_table(rows, ["center"])
        lines = out.splitlines()
        # Column width is 6 ("Header"). Python's str.center puts extra padding
        # on the right, so "x".center(6) == "  x   " (2 left, 3 right).
        self.assertEqual(lines[2], "|   x    |")

    def test_left_default_matches_prior_behavior(self):
        rows = [["Header"], ["x"]]
        out = format_table(rows)
        lines = out.splitlines()
        self.assertEqual(lines[2], "| x      |")

    def test_mixed_alignment_data_row(self):
        rows = [["Name", "Age", "City"], ["Alice", "30", "NYC"]]
        alignments = ["left", "right", "center"]
        out = format_table(rows, alignments)
        lines = out.splitlines()
        # Widths: 5, 3, 4
        self.assertEqual(lines[0], "| Name  | Age | City |")
        self.assertEqual(lines[2], "| Alice |  30 | NYC  |")


class RoundTripTests(unittest.TestCase):
    def test_mixed_alignments_round_trip(self):
        original = (
            "| Name | Age | City |\n"
            "| :--- | ---: | :---: |\n"
            "| Alice | 30 | NYC |\n"
        )
        rows, alignments = parse_table(original)
        formatted_once = format_table(rows, alignments)

        # Feed the formatted output back in — alignments should survive.
        rows2, alignments2 = parse_table(formatted_once)
        self.assertEqual(alignments2, ["left", "right", "center"])

        # And a second format should be a fixed point (idempotent).
        formatted_twice = format_table(rows2, alignments2)
        self.assertEqual(formatted_once, formatted_twice)

    def test_no_hints_still_left_justified(self):
        original = (
            "| A | B |\n"
            "| --- | --- |\n"
            "| x | y |\n"
        )
        rows, alignments = parse_table(original)
        out = format_table(rows, alignments)
        expected = (
            "| A   | B   |\n"
            "| --- | --- |\n"
            "| x   | y   |\n"
        )
        self.assertEqual(out, expected)


class MaxWidthValidatorTests(unittest.TestCase):
    """Pure unit tests for the argparse type= validator."""

    def test_accepts_minimum_value(self):
        self.assertEqual(_positive_int_at_least_4("4"), 4)

    def test_accepts_larger_value(self):
        self.assertEqual(_positive_int_at_least_4("100"), 100)

    def test_rejects_non_integer(self):
        with self.assertRaises(argparse.ArgumentTypeError) as exc:
            _positive_int_at_least_4("foo")
        self.assertIn("--max-width", str(exc.exception))
        self.assertIn("integer", str(exc.exception))

    def test_rejects_zero(self):
        with self.assertRaises(argparse.ArgumentTypeError) as exc:
            _positive_int_at_least_4("0")
        self.assertIn(">= 4", str(exc.exception))

    def test_rejects_three(self):
        with self.assertRaises(argparse.ArgumentTypeError) as exc:
            _positive_int_at_least_4("3")
        self.assertIn(">= 4", str(exc.exception))

    def test_rejects_negative(self):
        with self.assertRaises(argparse.ArgumentTypeError) as exc:
            _positive_int_at_least_4("-1")
        self.assertIn(">= 4", str(exc.exception))


class MaxWidthFormatTests(unittest.TestCase):
    """Function-level tests for the truncation pre-pass in format_table."""

    def test_basic_truncation_of_oversized_column(self):
        rows = [["A", "B"], ["x", "this_is_a_long_cell"]]
        out = format_table(rows, max_width=10)
        lines = out.splitlines()
        # Col 0 widest is 1 → minimum-3 padding, untouched.
        # Col 1 widest is 19 > 10 → truncated to exactly 10 chars.
        self.assertEqual(lines[0], "| A   | B          |")
        truncated = lines[2].split("|")[2].strip()
        self.assertEqual(truncated, "this_is...")
        self.assertEqual(len(truncated), 10)
        self.assertTrue(truncated.endswith("..."))
        # Untouched column matches the no-flag layout for that column.
        self.assertTrue(lines[2].startswith("| x   |"))

    def test_mixed_only_oversized_column_changes(self):
        rows = [
            ["L", "M", "R"],
            ["a", "much_longer_middle", "z"],
        ]
        baseline = format_table(rows).splitlines()
        truncated = format_table(rows, max_width=10).splitlines()
        # Outer columns are byte-for-byte identical between baseline and
        # truncated runs; only the middle column changes.
        for line_b, line_t in zip(baseline, truncated):
            cells_b = line_b.split("|")
            cells_t = line_t.split("|")
            self.assertEqual(cells_b[1], cells_t[1])  # left col cell text
            self.assertEqual(cells_b[3], cells_t[3])  # right col cell text
            self.assertNotEqual(cells_b[2], cells_t[2])  # middle differs
        # Middle data cell ends with "...".
        middle_data = truncated[2].split("|")[2].strip()
        self.assertTrue(middle_data.endswith("..."))
        self.assertEqual(len(middle_data), 10)

    def test_already_short_input_is_byte_identical(self):
        # When every column already fits, --max-width is a no-op at the byte
        # level — proves R1's "columns that already fit are emitted unchanged".
        rows = [["A", "B"], ["x", "y"]]
        without = format_table(rows)
        with_flag = format_table(rows, max_width=10)
        self.assertEqual(without, with_flag)

    def test_header_row_is_truncated(self):
        rows = [["VERY_LONG_HEADER", "B"], ["x", "y"]]
        out = format_table(rows, max_width=10)
        lines = out.splitlines()
        header_cell = lines[0].split("|")[1].strip()
        self.assertEqual(header_cell, "VERY_LO...")
        self.assertEqual(len(header_cell), 10)
        # Separator regenerates against the narrowed col width (10 dashes).
        sep_cell = lines[1].split("|")[1].strip()
        self.assertEqual(sep_cell, "-" * 10)

    def test_alignment_honored_after_truncation(self):
        # Right-aligned column whose widest cell triggers truncation: the
        # truncated cell is exactly N chars (no extra padding) and shorter
        # cells right-justify into the narrowed width.
        rows = [["VERY_LONG_HEADER"], ["x"]]
        out = format_table(rows, ["right"], max_width=10)
        lines = out.splitlines()
        self.assertEqual(lines[0], "| VERY_LO... |")
        self.assertEqual(lines[1], "| ---------: |")
        self.assertEqual(lines[2], "|          x |")

    def test_idempotent_under_repeated_max_width(self):
        # parse → format → parse → format with the same max_width must be a
        # fixed point. Mirrors the existing test_mixed_alignments_round_trip
        # pattern from RoundTripTests.
        original = (
            "| Name | Description | Code |\n"
            "| :--- | --- | ---: |\n"
            "| Alice | a_very_long_description_field | 30 |\n"
        )
        rows, alignments = parse_table(original)
        once = format_table(rows, alignments, max_width=15)
        rows2, alignments2 = parse_table(once)
        twice = format_table(rows2, alignments2, max_width=15)
        self.assertEqual(once, twice)

    def test_n_equals_minimum_4_leaves_one_content_char(self):
        # Boundary: max_width == 4 produces (1 content char) + "..." = 4 total.
        rows = [["H"], ["abcdef"]]
        out = format_table(rows, max_width=4)
        data_cell = out.splitlines()[2].split("|")[1].strip()
        self.assertEqual(data_cell, "a...")
        self.assertEqual(len(data_cell), 4)


# Note: --max-width × --json interaction is intentionally not tested here.
# --json mode (PR #109) does not exist on this branch's base. See
# docs/brainstorms/2026-04-26-table-fmt-max-width-requirements.md §D3.


def _run_main(argv, stdin_text):
    """Helper: invoke main() with patched argv/stdin/stdout/stderr.

    Returns (exit_code, stdout, stderr). exit_code is 0 if main() returned
    normally; otherwise the SystemExit code (argparse uses 2 for validation
    failures, the script uses 1 for "no valid table" input).
    """
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch.object(sys, "argv", argv), \
         mock.patch.object(sys, "stdin", io.StringIO(stdin_text)), \
         mock.patch.object(sys, "stdout", stdout), \
         mock.patch.object(sys, "stderr", stderr):
        try:
            main()
            exit_code = 0
        except SystemExit as exc:
            exit_code = exc.code if exc.code is not None else 0
    return exit_code, stdout.getvalue(), stderr.getvalue()


class CLIArgparseTests(unittest.TestCase):
    """End-to-end CLI tests via patched sys.argv/stdin/stdout/stderr."""

    def test_no_flag_path_byte_for_byte_parity(self):
        # R3: no-flag invocation matches in-process format_table output, the
        # same fixture used by the existing RoundTripTests.
        text = (
            "| Name | Age | City |\n"
            "| :--- | ---: | :---: |\n"
            "| Alice | 30 | NYC |\n"
        )
        rows, alignments = parse_table(text)
        expected = format_table(rows, alignments)
        code, out, err = _run_main(["table_fmt.py"], text)
        self.assertEqual(code, 0)
        self.assertEqual(out, expected)
        self.assertEqual(err, "")

    def test_max_width_truncates_via_cli(self):
        text = (
            "| Name | Description |\n"
            "| --- | --- |\n"
            "| Alice | a_long_description_value |\n"
        )
        code, out, _ = _run_main(
            ["table_fmt.py", "--max-width", "10"], text
        )
        self.assertEqual(code, 0)
        # Every non-empty cell, after stripping, is at most 10 chars.
        for line in out.splitlines():
            for cell in line.split("|"):
                stripped = cell.strip()
                if stripped:
                    self.assertLessEqual(len(stripped), 10)
        # The long Description cell is truncated and ends with "...".
        data_cell = out.splitlines()[2].split("|")[2].strip()
        self.assertTrue(data_cell.endswith("..."))
        self.assertEqual(len(data_cell), 10)

    def test_max_width_foo_is_rejected(self):
        code, out, err = _run_main(
            ["table_fmt.py", "--max-width", "foo"], ""
        )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--max-width", err)
        self.assertIn("integer", err)

    def test_max_width_zero_is_rejected(self):
        code, _, err = _run_main(
            ["table_fmt.py", "--max-width", "0"], ""
        )
        self.assertEqual(code, 2)
        self.assertIn("--max-width", err)
        self.assertIn(">= 4", err)

    def test_max_width_three_is_rejected(self):
        code, _, err = _run_main(
            ["table_fmt.py", "--max-width", "3"], ""
        )
        self.assertEqual(code, 2)
        self.assertIn(">= 4", err)

    def test_max_width_four_smoke_test(self):
        # N=4 is the boundary. Just confirm acceptance and a sane output.
        text = (
            "| A | B |\n"
            "| --- | --- |\n"
            "| x | y |\n"
        )
        code, out, _ = _run_main(
            ["table_fmt.py", "--max-width", "4"], text
        )
        self.assertEqual(code, 0)
        self.assertIn("|", out)

    def test_help_documents_max_width_with_minimum(self):
        # R5: --help mentions the flag and the minimum value of 4.
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", ["table_fmt.py", "--help"]), \
             mock.patch.object(sys, "stdout", stdout), \
             mock.patch.object(sys, "stderr", stderr):
            with self.assertRaises(SystemExit) as exc:
                main()
        self.assertEqual(exc.exception.code, 0)
        help_text = stdout.getvalue()
        self.assertIn("--max-width", help_text)
        self.assertIn("4", help_text)


if __name__ == "__main__":
    unittest.main()
