#!/usr/bin/env python3
"""Tests for table_fmt: alignment parsing, separator emission, cell padding."""

import io
import json
import unittest
from unittest.mock import patch

import table_fmt
from table_fmt import format_json, format_table, parse_table


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


class FormatJsonTests(unittest.TestCase):
    def test_basic_happy_path(self):
        rows = [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]]
        out = format_json(rows, [None, None])
        self.assertEqual(
            json.loads(out),
            [{"Name": "Alice", "Age": "30"}, {"Name": "Bob", "Age": "25"}],
        )

    def test_alignment_metadata_dropped(self):
        rows = [["Name", "Age", "City"], ["Alice", "30", "NYC"]]
        out = format_json(rows, ["left", "right", "center"])
        # Alignment hints have no JSON representation — only header-keyed values.
        self.assertEqual(
            json.loads(out),
            [{"Name": "Alice", "Age": "30", "City": "NYC"}],
        )
        self.assertNotIn("left", out)
        self.assertNotIn("right", out)
        self.assertNotIn("center", out)

    def test_single_column_table(self):
        rows = [["X"], ["a"], ["b"]]
        out = format_json(rows, [None])
        self.assertEqual(json.loads(out), [{"X": "a"}, {"X": "b"}])

    def test_empty_cells_preserved_as_empty_string(self):
        rows = [["Name", "Age"], ["Alice", ""]]
        out = format_json(rows, [None, None])
        self.assertEqual(json.loads(out), [{"Name": "Alice", "Age": ""}])

    def test_pretty_printed_with_indent_2_and_trailing_newline(self):
        rows = [["A", "B"], ["x", "y"]]
        out = format_json(rows, [None, None])
        # Exact text shape: indent=2 nesting, single trailing newline.
        expected = '[\n  {\n    "A": "x",\n    "B": "y"\n  }\n]\n'
        self.assertEqual(out, expected)
        self.assertTrue(out.endswith("\n"))
        self.assertFalse(out.endswith("\n\n"))

    def test_no_header_row_raises_value_error(self):
        rows = [["A", "B"], ["x", "y"]]
        with self.assertRaises(ValueError) as cm:
            format_json(rows, [])
        self.assertIn("requires a header row", str(cm.exception))

    def test_duplicate_header_raises_value_error_naming_duplicate(self):
        rows = [["Name", "Name"], ["a", "b"]]
        with self.assertRaises(ValueError) as cm:
            format_json(rows, [None, None])
        self.assertIn("duplicate header", str(cm.exception))
        self.assertIn("'Name'", str(cm.exception))

    def test_non_ascii_cell_text_preserved_literally(self):
        rows = [["City"], ["Café"]]
        out = format_json(rows, [None])
        # ensure_ascii=False keeps the é literal rather than escaping to é.
        self.assertIn("Café", out)
        self.assertNotIn("\\u00e9", out)


class MainCliTests(unittest.TestCase):
    def _run_main(self, argv, stdin_text):
        """Invoke ``table_fmt.main`` in-process; return ``(stdout, stderr, exit_code)``."""
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = 0
        with patch.object(table_fmt.sys, "stdin", io.StringIO(stdin_text)), \
             patch.object(table_fmt.sys, "stdout", stdout), \
             patch.object(table_fmt.sys, "stderr", stderr):
            try:
                table_fmt.main(argv)
            except SystemExit as exc:
                code = exc.code
                exit_code = 0 if code is None else int(code)
        return stdout.getvalue(), stderr.getvalue(), exit_code

    def test_default_mode_byte_for_byte_parity_with_format_table(self):
        # Borrowed from RoundTripTests.test_mixed_alignments_round_trip.
        original = (
            "| Name | Age | City |\n"
            "| :--- | ---: | :---: |\n"
            "| Alice | 30 | NYC |\n"
        )
        rows, alignments = parse_table(original)
        expected = format_table(rows, alignments)

        stdout, stderr, code = self._run_main([], original)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout, expected)

    def test_json_flag_emits_json(self):
        stdin_text = (
            "| Name | Age |\n"
            "| --- | --- |\n"
            "| Alice | 30 |\n"
        )
        stdout, stderr, code = self._run_main(["--json"], stdin_text)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), [{"Name": "Alice", "Age": "30"}])

    def test_help_mentions_json_flag(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(table_fmt.sys, "stdin", io.StringIO("")), \
             patch.object(table_fmt.sys, "stdout", stdout), \
             patch.object(table_fmt.sys, "stderr", stderr):
            with self.assertRaises(SystemExit) as cm:
                table_fmt.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        help_text = stdout.getvalue()
        self.assertIn("--json", help_text)
        self.assertIn("JSON", help_text)

    def test_unknown_flag_exits_nonzero(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(table_fmt.sys, "stdin", io.StringIO("")), \
             patch.object(table_fmt.sys, "stdout", stdout), \
             patch.object(table_fmt.sys, "stderr", stderr):
            with self.assertRaises(SystemExit) as cm:
                table_fmt.main(["--xml"])
        # argparse uses exit code 2 for argument-parsing errors.
        self.assertNotEqual(cm.exception.code, 0)

    def test_no_table_with_json_flag_uses_existing_error_path(self):
        stdout, stderr, code = self._run_main(["--json"], "this is not a table\n")
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("no valid markdown table found", stderr)

    def test_no_header_row_with_json_flag_errors(self):
        stdin_text = (
            "| A | B |\n"
            "| x | y |\n"
        )
        stdout, stderr, code = self._run_main(["--json"], stdin_text)
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("requires a header row", stderr)

    def test_no_header_row_without_json_flag_still_works(self):
        # Sanity: existing default-mode behavior on header-less input is preserved.
        stdin_text = (
            "| A | B |\n"
            "| x | y |\n"
        )
        stdout, stderr, code = self._run_main([], stdin_text)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        # No-header input is handled by format_table (treats first row as header).
        self.assertIn("| A", stdout)

    def test_duplicate_header_with_json_flag_errors(self):
        stdin_text = (
            "| Name | Name |\n"
            "| --- | --- |\n"
            "| a | b |\n"
        )
        stdout, stderr, code = self._run_main(["--json"], stdin_text)
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("duplicate header", stderr)
        self.assertIn("'Name'", stderr)


if __name__ == "__main__":
    unittest.main()
