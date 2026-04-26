#!/usr/bin/env python3
"""Tests for table_fmt: alignment parsing, separator emission, cell padding."""

import unittest

from table_fmt import _split_cells, format_table, parse_table


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


class SplitCellsTests(unittest.TestCase):
    def test_plain_row_matches_str_split(self):
        row = "| a | b | c |"
        self.assertEqual(_split_cells(row), row.split("|"))

    def test_escaped_pipe_unescapes_in_cell(self):
        # `| a \| b |` -> single cell with logical content `a | b`
        self.assertEqual(_split_cells(r"| a \| b |"), ["", " a | b ", ""])

    def test_escaped_backslash_then_separator(self):
        # `| a \\| b |` -> cell ends in literal `\\`, then a real separator.
        # The naive (?<!\\)\| regex misclassifies this case.
        self.assertEqual(_split_cells(r"| a \\| b |"), ["", r" a \\", " b ", ""])

    def test_escaped_backslash_then_escaped_pipe(self):
        # `| a \\\| b |` -> single cell whose content is ` a \\| b `.
        # Documents that the 2-char-unit rule composes left-to-right.
        self.assertEqual(_split_cells(r"| a \\\| b |"), ["", r" a \\| b ", ""])

    def test_non_pipe_escape_passes_through(self):
        # Backslash followed by anything other than `|` is left verbatim.
        self.assertEqual(_split_cells(r"| a \n b |"), ["", r" a \n b ", ""])

    def test_lone_trailing_backslash_stays_in_cell(self):
        # Trailing `\` with no following char must not read out of range.
        self.assertEqual(_split_cells("| foo \\"), ["", " foo \\"])


class EscapedPipeTests(unittest.TestCase):
    def test_parse_treats_escaped_pipe_as_literal(self):
        rows, alignments = parse_table(r"| a \| b |" + "\n")
        self.assertEqual(rows, [["a | b"]])
        self.assertEqual(alignments, [])

    def test_parse_full_table_with_escaped_pipe(self):
        text = (
            "| Name | Pipe |\n"
            "| --- | --- |\n"
            r"| Alice | a \| b |" + "\n"
        )
        rows, alignments = parse_table(text)
        self.assertEqual(rows, [["Name", "Pipe"], ["Alice", "a | b"]])
        self.assertEqual(alignments, [None, None])

    def test_format_re_escapes_literal_pipe(self):
        out = format_table([["H"], ["a | b"]])
        body = out.splitlines()[2]
        self.assertEqual(body, r"| a \| b |")

    def test_format_width_uses_encoded_form(self):
        # Logical "a | b" (5 chars) encodes to "a \| b" (6 chars). Column width
        # must be driven by the encoded length, not the logical length.
        out = format_table([["x"], ["a | b"]])
        lines = out.splitlines()
        self.assertEqual(lines[0], "| x      |")
        self.assertEqual(lines[1], "| ------ |")
        self.assertEqual(lines[2], r"| a \| b |")

    def test_round_trip_fixed_point_with_escaped_pipe(self):
        original = (
            "| Name | Pipe   |\n"
            "| ---- | ------ |\n"
            r"| A    | a \| b |" + "\n"
        )
        rows, alignments = parse_table(original)
        once = format_table(rows, alignments)
        rows2, alignments2 = parse_table(once)
        twice = format_table(rows2, alignments2)
        self.assertEqual(once, twice)
        self.assertEqual(rows2, [["Name", "Pipe"], ["A", "a | b"]])


if __name__ == "__main__":
    unittest.main()
