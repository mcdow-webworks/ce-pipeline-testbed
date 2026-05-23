#!/usr/bin/env python3
"""Tests for table_fmt: alignment parsing, separator emission, cell padding."""

import json
import os
import subprocess
import sys
import unittest

from table_fmt import (
    _is_empty_row,
    _strip_empty_rows,
    _yaml_scalar,
    format_json,
    format_table,
    format_yaml,
    parse_table,
)

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
        self.assertEqual(
            json.loads(out),
            [{"Name": "Alice", "Age": "30", "City": "NYC"}],
        )
        self.assertNotIn("left", out)
        self.assertNotIn("right", out)
        self.assertNotIn("center", out)

    def test_empty_cells_preserved_as_empty_string(self):
        rows = [["Name", "Age"], ["Alice", ""]]
        out = format_json(rows, [None, None])
        self.assertEqual(json.loads(out), [{"Name": "Alice", "Age": ""}])

    def test_pretty_printed_with_indent_2_and_trailing_newline(self):
        rows = [["A", "B"], ["x", "y"]]
        out = format_json(rows, [None, None])
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
        self.assertIn("Café", out)
        self.assertNotIn("\\u00e9", out)

    def test_header_only_table_emits_empty_array(self):
        out = format_json([["Name", "Age"]], [None, None])
        self.assertEqual(json.loads(out), [])
        self.assertEqual(out, "[]\n")


class YamlScalarTests(unittest.TestCase):
    def test_plain_value_unquoted(self):
        self.assertEqual(_yaml_scalar("hello"), "hello")

    def test_empty_string_single_quoted(self):
        self.assertEqual(_yaml_scalar(""), "''")

    def test_colon_mapping_indicator_quoted(self):
        self.assertEqual(_yaml_scalar("key: value"), "'key: value'")

    def test_value_ending_with_colon_quoted(self):
        self.assertEqual(_yaml_scalar("label:"), "'label:'")

    def test_hash_at_start_quoted(self):
        self.assertEqual(_yaml_scalar("#comment"), "'#comment'")

    def test_inline_comment_marker_quoted(self):
        self.assertEqual(_yaml_scalar("value #note"), "'value #note'")

    def test_dash_at_start_quoted(self):
        self.assertEqual(_yaml_scalar("- item"), "'- item'")

    def test_leading_whitespace_quoted(self):
        self.assertEqual(_yaml_scalar("  indented"), "'  indented'")

    def test_boolean_true_quoted(self):
        self.assertEqual(_yaml_scalar("true"), "'true'")

    def test_boolean_false_quoted(self):
        self.assertEqual(_yaml_scalar("false"), "'false'")

    def test_null_keyword_quoted(self):
        self.assertEqual(_yaml_scalar("null"), "'null'")

    def test_single_quote_doubled_when_quoting_required(self):
        # When quoting is triggered (here by leading #), embedded ' are doubled.
        self.assertEqual(_yaml_scalar("#it's"), "'#it''s'")

    def test_yaml11_special_floats_quoted(self):
        # YAML 1.1 parsers interpret these as float infinity / NaN
        for val in (".inf", "+.inf", "-.inf", ".nan", "+.nan", "-.nan"):
            with self.subTest(val=val):
                result = _yaml_scalar(val)
                self.assertTrue(result.startswith("'"), f"{val!r} should be quoted")

    def test_hex_integer_literal_quoted(self):
        # YAML 1.1 parsers parse 0xff as integer 255
        self.assertEqual(_yaml_scalar("0xff"), "'0xff'")
        self.assertEqual(_yaml_scalar("0xFF"), "'0xFF'")

    def test_octal_integer_literal_quoted(self):
        # Python-style 0o prefix; conservative to quote these
        self.assertEqual(_yaml_scalar("0o77"), "'0o77'")


class FormatYamlTests(unittest.TestCase):
    def test_happy_path(self):
        rows = [["Name", "Age", "City"], ["Alice", "30", "NYC"], ["Bob", "25", "LA"]]
        out = format_yaml(rows, [None, None, None])
        expected = (
            "- Name: Alice\n"
            "  Age: '30'\n"
            "  City: NYC\n"
            "- Name: Bob\n"
            "  Age: '25'\n"
            "  City: LA\n"
        )
        self.assertEqual(out, expected)

    def test_header_only_emits_empty_list(self):
        out = format_yaml([["Name", "Age"]], [None, None])
        self.assertEqual(out, "[]\n")

    def test_no_separator_row_raises_value_error(self):
        rows = [["A", "B"], ["x", "y"]]
        with self.assertRaises(ValueError) as cm:
            format_yaml(rows, [])
        self.assertIn("requires a header row", str(cm.exception))

    def test_duplicate_header_raises_value_error(self):
        rows = [["Name", "Name"], ["a", "b"]]
        with self.assertRaises(ValueError) as cm:
            format_yaml(rows, [None, None])
        self.assertIn("duplicate header", str(cm.exception))
        self.assertIn("'Name'", str(cm.exception))

    def test_special_characters_are_quoted(self):
        rows = [
            ["Key"],
            ["value: with colon"],
            ["#starts-with-hash"],
            ["- starts with dash"],
        ]
        out = format_yaml(rows, [None])
        self.assertIn("'value: with colon'", out)
        self.assertIn("'#starts-with-hash'", out)
        self.assertIn("'- starts with dash'", out)

    def test_trailing_newline(self):
        rows = [["A"], ["x"]]
        out = format_yaml(rows, [None])
        self.assertTrue(out.endswith("\n"))
        self.assertFalse(out.endswith("\n\n"))

    def test_ragged_row_pads_missing_cells_as_empty(self):
        # A data row shorter than the header should fill missing cells with ''.
        rows = [["A", "B", "C"], ["x"]]
        out = format_yaml(rows, [None, None, None])
        self.assertIn("B: ''", out)
        self.assertIn("C: ''", out)


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


class JsonCliTests(unittest.TestCase):
    """End-to-end CLI tests for --json mode."""

    def _run(self, stdin_text, *args):
        return subprocess.run(
            [sys.executable, SCRIPT_PATH, *args],
            input=stdin_text,
            capture_output=True,
            text=True,
        )

    def test_json_flag_emits_json(self):
        text = (
            "| Name | Age |\n"
            "| --- | --- |\n"
            "| Alice | 30 |\n"
        )
        result = self._run(text, "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(json.loads(result.stdout), [{"Name": "Alice", "Age": "30"}])

    def test_json_header_only_emits_empty_array(self):
        text = (
            "| Name | Age |\n"
            "| --- | --- |\n"
        )
        result = self._run(text, "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, "[]\n")

    def test_json_no_table_exits_1(self):
        result = self._run("not a table", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no valid markdown table found", result.stderr)

    def test_json_no_separator_row_exits_1(self):
        text = "| A | B |\n| x | y |\n"
        result = self._run(text, "--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("requires a header row", result.stderr)

    def test_help_documents_json_flag(self):
        result = self._run("", "--help")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--json", result.stdout)


class YamlCliTests(unittest.TestCase):
    """End-to-end CLI tests for --yaml mode."""

    def _run(self, stdin_text, *args):
        return subprocess.run(
            [sys.executable, SCRIPT_PATH, *args],
            input=stdin_text,
            capture_output=True,
            text=True,
        )

    def test_yaml_flag_emits_yaml(self):
        text = (
            "| Name | Age |\n"
            "| --- | --- |\n"
            "| Alice | 30 |\n"
        )
        result = self._run(text, "--yaml")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, "- Name: Alice\n  Age: '30'\n")

    def test_yaml_empty_input_exits_1(self):
        result = self._run("not a table", "--yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no valid markdown table found", result.stderr)

    def test_yaml_header_only_emits_empty_list(self):
        text = (
            "| Name | Age |\n"
            "| --- | --- |\n"
        )
        result = self._run(text, "--yaml")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, "[]\n")

    def test_yaml_special_characters_quoted(self):
        text = (
            "| Key | Value |\n"
            "| --- | --- |\n"
            "| port | host: value |\n"
            "| note | #comment |\n"
            "| item | - first |\n"
        )
        result = self._run(text, "--yaml")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("'host: value'", result.stdout)
        self.assertIn("'#comment'", result.stdout)
        self.assertIn("'- first'", result.stdout)

    def test_json_and_yaml_mutually_exclusive(self):
        text = (
            "| A | B |\n"
            "| --- | --- |\n"
            "| x | y |\n"
        )
        result = self._run(text, "--json", "--yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("mutually exclusive", result.stderr)

    def test_help_documents_yaml_flag(self):
        result = self._run("", "--help")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--yaml", result.stdout)

    def test_yaml_no_separator_row_exits_1(self):
        text = "| A | B |\n| x | y |\n"
        result = self._run(text, "--yaml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("requires a header row", result.stderr)


if __name__ == "__main__":
    unittest.main()
