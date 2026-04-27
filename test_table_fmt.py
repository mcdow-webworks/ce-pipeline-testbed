#!/usr/bin/env python3
"""Tests for table_fmt: alignment parsing, separator emission, cell padding."""

import os
import subprocess
import sys
import unittest

from table_fmt import _is_empty_row, _strip_empty_rows, format_table, parse_table

SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "table_fmt.py")


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


class IsEmptyRowTests(unittest.TestCase):
    def test_all_empty_strings_is_empty(self):
        self.assertTrue(_is_empty_row(["", "", ""]))

    def test_all_ascii_whitespace_is_empty(self):
        self.assertTrue(_is_empty_row(["   ", "\t", " \t "]))

    def test_unicode_whitespace_is_empty(self):
        # NBSP (U+00A0) and full-width space (U+3000) count as whitespace
        # under Python's default str.strip(); a row of them is "empty".
        self.assertTrue(_is_empty_row([" ", "　"]))

    def test_zero_width_char_is_not_whitespace(self):
        # U+200B is not str.isspace(); a row of zero-width chars is non-empty.
        self.assertFalse(_is_empty_row(["​"]))

    def test_mixed_with_one_non_empty_is_not_empty(self):
        self.assertFalse(_is_empty_row(["", "x", ""]))

    def test_single_empty_cell_is_empty(self):
        self.assertTrue(_is_empty_row([""]))

    def test_single_non_empty_cell_is_not_empty(self):
        self.assertFalse(_is_empty_row(["x"]))

    def test_empty_cell_list_vacuous_truth(self):
        # all() on an empty iterable returns True; pins the vacuous-truth contract.
        self.assertTrue(_is_empty_row([]))


class StripEmptyRowsTests(unittest.TestCase):
    def test_drops_all_empty_data_rows(self):
        rows = [["H1", "H2"], ["a", "b"], ["", ""], ["c", "d"]]
        self.assertEqual(
            _strip_empty_rows(rows),
            [["H1", "H2"], ["a", "b"], ["c", "d"]],
        )

    def test_drops_whitespace_only_data_rows(self):
        rows = [["H1", "H2"], [" ", "\t"], ["a", "b"]]
        self.assertEqual(
            _strip_empty_rows(rows),
            [["H1", "H2"], ["a", "b"]],
        )

    def test_keeps_rows_with_any_non_empty_cell(self):
        rows = [["H1", "H2", "H3"], ["", "x", ""]]
        self.assertEqual(_strip_empty_rows(rows), rows)

    def test_preserves_empty_header_row(self):
        rows = [["", "", ""], ["a", "b", "c"]]
        self.assertEqual(_strip_empty_rows(rows), rows)

    def test_preserves_empty_header_only_table(self):
        rows = [["", "", ""]]
        self.assertEqual(_strip_empty_rows(rows), rows)

    def test_short_data_row_with_only_empty_cells_is_dropped(self):
        # Edge case from issue: a 2-cell row in a 3-column table where both
        # written cells are empty — should be stripped before normalization
        # would otherwise pad it to a 3-empty-cell row.
        rows = [["H1", "H2", "H3"], ["a", "b", "c"], ["", ""]]
        self.assertEqual(
            _strip_empty_rows(rows),
            [["H1", "H2", "H3"], ["a", "b", "c"]],
        )

    def test_empty_input_returns_empty(self):
        self.assertEqual(_strip_empty_rows([]), [])


class FormatTableUnchangedWithoutFlagTests(unittest.TestCase):
    """``format_table`` itself must never strip empty rows."""

    def test_format_table_pads_empty_rows(self):
        rows = [["H1", "H2"], ["a", "b"], ["", ""], ["c", "d"]]
        out = format_table(rows)
        lines = out.splitlines()
        # 1 header + 1 separator + 3 data rows
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[3], "|     |     |")


class StripEmptyRowsCliTests(unittest.TestCase):
    """End-to-end CLI tests that exercise argparse wiring and behavior."""

    def _run(self, stdin_text, *args):
        return subprocess.run(
            [sys.executable, SCRIPT_PATH, *args],
            input=stdin_text,
            capture_output=True,
            text=True,
        )

    def test_strip_flag_drops_blank_data_rows(self):
        text = (
            "| A | B |\n"
            "| --- | --- |\n"
            "| x | y |\n"
            "|   |   |\n"
            "| u | v |\n"
        )
        result = self._run(text, "--strip-empty-rows")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        expected = (
            "| A | B |\n"
            "| - | - |\n"  # placeholder; recomputed below
        )
        # Compute exact expected output via the library.
        rows, alignments = parse_table(text)
        rows = _strip_empty_rows(rows)
        expected = format_table(rows, alignments)
        self.assertEqual(result.stdout, expected)

    def test_no_flag_preserves_byte_for_byte_behavior(self):
        text = (
            "| A | B |\n"
            "| --- | --- |\n"
            "| x | y |\n"
            "|   |   |\n"
            "| u | v |\n"
        )
        result = self._run(text)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        rows, alignments = parse_table(text)
        expected = format_table(rows, alignments)
        self.assertEqual(result.stdout, expected)

    def test_help_documents_strip_empty_rows_flag(self):
        result = self._run("", "--help")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--strip-empty-rows", result.stdout)

    def test_strip_flag_all_data_rows_empty_produces_header_only_output(self):
        text = (
            "| A | B |\n"
            "| --- | --- |\n"
            "|   |   |\n"
            "| \t | \t |\n"
        )
        result = self._run(text, "--strip-empty-rows")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        lines = result.stdout.splitlines()
        # All data rows stripped; output contains header + separator only.
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
