---
title: "fix: Handle escaped pipes (\\|) in markdown table cells"
type: fix
status: active
date: 2026-04-25
origin: docs/brainstorms/2026-04-25-handle-escaped-pipes-in-table-cells-requirements.md
---

# fix: Handle escaped pipes (\|) in markdown table cells

## Overview

`table_fmt.py` currently splits each table row on every `|`, so a cell that
contains the markdown literal-pipe escape `\|` is silently broken into two
cells. This plan threads pipe-escape awareness through both ends of the
formatter — parse and emit — so cells with literal pipes survive parse,
format, and round-trip.

## Problem Frame

Same class of "structural row carries metadata that the parser drops" mistake
addressed for column alignment in #92, applied now to the cell-splitting step.
A user table that holds a literal pipe in a cell is corrupted on first format.
Only `\|` is structurally relevant to the table grammar; this is not a general
markdown-unescape change (see origin: docs/brainstorms/2026-04-25-handle-escaped-pipes-in-table-cells-requirements.md).

## Requirements Trace

- R1. `parse_table` treats `\|` inside a row as a literal pipe in the current
  cell, not a separator. Parsed cell content unescapes `\|` to `|` so
  downstream consumers see the logical content.
- R2. `format_table` re-escapes literal `|` characters in cell content as `\|`
  on emit, preserving the parse → format round-trip fixed point.
- R3. Column-width math in `format_table` uses the encoded (post-escape)
  cell length so emitted markdown stays visually aligned.
- R4. Existing parse / format / round-trip behavior is unchanged for any cell
  with no escaped pipes — including leading/trailing pipes, separator rows,
  alignment hints, and bare-dash separators. All existing tests in
  `test_table_fmt.py` pass without modification.

## Scope Boundaries

- Out of scope: general markdown backslash-escape handling (`\*`, `\_`, `\#`,
  etc.). Only `\|` is interpreted; other backslash sequences pass through cell
  content verbatim.
- Out of scope: alternative pipe-escaping conventions (HTML entities like
  `&#124;`, Unicode lookalikes, fenced inline code spans).
- Out of scope: changing the public return shape of `parse_table` or
  `format_table`. Both signatures remain `parse_table(text) -> (rows, alignments)`
  and `format_table(rows, alignments=None) -> str`.

## Context & Research

### Relevant Code and Patterns

- `table_fmt.py:44` — `cells = stripped.split("|")` is the single split site
  to replace. The leading/trailing empty-cell trim that follows must continue
  to work against the new splitter's output.
- `table_fmt.py:52` — separator-row detection (`replace("-", "").replace(":", "")`)
  must keep matching after the splitter change. Separator cells never contain
  `\|`, so this should be unaffected, but worth verifying via the existing
  `RoundTripTests`.
- `table_fmt.py:88` — column-width computation reads `len(normalised[r][col])`.
  Per R3, this should be replaced with the length of the *encoded* form so
  visual alignment holds when a cell carries an escaped pipe.
- `table_fmt.py:101-103` — `format_row` joins padded cell text into the
  `| ... |` shape. Per R2, cell text passed to `pad_cell` must be the
  encoded form (`|` → `\|`); the bordering `|` separators are never escaped.
- `table_fmt.py:7-24` — `_parse_alignment` is the small-helper precedent for
  the new `_split_cells` (or similarly named) helper this plan introduces.
- `test_table_fmt.py` — existing `RoundTripTests` provide the regression
  net for R4 and the template for the new round-trip test in Unit 4.

### Institutional Learnings

- `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md`
  — Same module, same class of bug. Two recurring lessons apply directly
  here:
  - "When 'skipping' a structural row in a parser, check whether it carries
    metadata first." Here, the equivalent is: when splitting on a structural
    delimiter, check whether the delimiter is escaped first.
  - Round-trip fixed-point tests catch this entire class of regression. The
    new escaped-pipe round-trip test in Unit 4 follows that template.
- The same doc records that `parse_table` and `format_table` are consumed
  only by `main()` in `table_fmt.py` and by `test_table_fmt.py` — verified
  again via repo grep. No external callers, so internal refactoring carries
  no compatibility risk.

### External References

External research skipped intentionally: the codebase has a strong, recent
local pattern for this exact module (the alignment fix from #92), the change
is self-contained, and the brainstorm already worked through the relevant
edge cases (`\\|`, lone `\` at row end, escape-only-on-`|`).

## Key Technical Decisions

- **Char-by-char splitter, not regex.** A small scan that consumes `\X` as a
  2-char unit is shorter and provably correct on `\\|` (escaped backslash
  followed by real separator). Why: a regex like `(?<!\\)\|` mishandles `\\|`
  by treating the second `\` as escaping the `|`, breaking R4 for any cell
  whose author meant "literal backslash, then end of cell".
  (See origin: docs/brainstorms/2026-04-25-handle-escaped-pipes-in-table-cells-requirements.md, Key Decisions.)
- **Only `\|` unescapes; every other `\X` passes through verbatim.** Why:
  this is a table formatter, not a markdown renderer. Cells legitimately
  contain literal backslashes (paths, regex, code fragments). Touching any
  other escape would silently rewrite user data, violating R4.
- **Format-time escape of `|` only, not `\`.** Why: same reasoning. Only `|`
  is structurally significant to the table grammar. Encoding `\` to `\\`
  would corrupt cells whose logical content really is a single `\`.
- **Width is computed from the encoded form.** Why: the markdown source has
  to line up visually. Using the unescaped length would misalign pipes
  whenever a cell contains a literal `|` (the encoded form is always at
  least one character longer per `|`). Computing once on the encoded form
  keeps the change local to `format_table`.
- **Splitter is a private helper at module scope, named `_split_cells`.**
  Why: mirrors the `_parse_alignment` precedent set by the alignment fix —
  small, single-purpose, leading-underscore module-private helper that
  `parse_table` calls in place of the previous `str.split("|")`.

## Open Questions

### Resolved During Planning

- **Where does the new splitter live?** As a leading-underscore module-private
  helper in `table_fmt.py`, mirroring `_parse_alignment`. No new module.
- **Does separator-row detection need to change?** No. Separator cells are
  dashes and colons; they never contain `\|`. The existing
  `replace("-", "").replace(":", "") == ""` check still applies after the
  new splitter runs.
- **Does the parse-time leading/trailing empty-cell trim still apply?** Yes,
  unchanged. The splitter returns the same shape `str.split("|")` returned —
  including the empty leading/trailing elements produced by `| ... |`
  borders — so the existing trim at `table_fmt.py:45-48` keeps working.

### Deferred to Implementation

- **Lone trailing backslash at row end (e.g., `| foo \\` with no following
  `|`).** Implementation should append the lone `\` to the current cell and
  not treat the next iteration's character (which doesn't exist) specially.
  The exact loop shape is an implementation choice; the test scenario in
  Unit 1 documents the expected behavior so it isn't accidentally broken.
- **Whether to expose `_split_cells` as `split_cells`.** Stay private unless
  a second caller emerges; matches the `_parse_alignment` precedent.

## Implementation Units

- [ ] **Unit 1: Add a pipe-aware row splitter**

  **Goal:** Introduce a small private helper that splits a row string on
  bare `|` while treating `\X` as a 2-character unit, unescaping `\|` to `|`
  in the emitted cell text and passing every other `\X` through verbatim.

  **Requirements:** R1, R4

  **Dependencies:** None.

  **Files:**
  - Modify: `table_fmt.py`
  - Test: `test_table_fmt.py`

  **Approach:**
  - Add a module-private helper alongside `_parse_alignment`. The helper
    returns a list of cell strings for one row, including the empty leading
    and trailing entries produced by `| ... |` borders, so callers don't
    have to change their trim logic.
  - Implementation shape: walk the row character by character, accumulating
    into a current-cell buffer. On `\` followed by another character,
    consume both — append `|` to the buffer when the next char is `|`,
    otherwise append the two characters verbatim. On a bare `|`, flush the
    buffer as a cell and start a new one. At end of input, flush whatever
    is in the buffer (handles a lone trailing `\` correctly: it just stays
    in the current cell).

  **Patterns to follow:**
  - `_parse_alignment` at `table_fmt.py:7-24` — small, single-purpose,
    underscore-prefixed module-level helper with a focused docstring.

  **Test scenarios:**
  - `| a \| b |` → splitter returns leading-empty, single cell with logical
    content `a | b` (post-strip), trailing-empty.
  - `| a \\| b |` → splitter returns leading-empty, cell with literal `a \\`
    (the escaped backslash passes through), cell with `b`, trailing-empty.
    This is the case a naive regex gets wrong.
  - `| a \\\| b |` (escaped backslash, then escaped pipe) → cells reflect
    `a \\` then `| b` *within one cell*. Documents that the 2-char-unit rule
    composes left-to-right.
  - `| a \n b |` (backslash followed by a non-pipe) → the `\n` passes through
    verbatim into the cell; no unescape happens.
  - Lone trailing `\` at end of row (e.g., `| foo \`) → the `\` stays in the
    current cell; no out-of-range read.
  - Plain `| a | b |` (no escapes) → splitter returns the same shape
    `str.split("|")` returned previously, preserving R4.

  **Verification:**
  - The helper is a pure function with no external dependencies and is
    covered directly by the scenarios above.
  - All existing parse-level tests in `test_table_fmt.py` continue to pass
    once Unit 2 wires the helper in.

- [ ] **Unit 2: Wire `parse_table` to use the new splitter**

  **Goal:** Replace the `stripped.split("|")` call site in `parse_table` with
  the splitter from Unit 1 so escaped pipes survive parsing as logical
  cell content.

  **Requirements:** R1, R4

  **Dependencies:** Unit 1.

  **Files:**
  - Modify: `table_fmt.py` (around line 44)
  - Test: `test_table_fmt.py`

  **Approach:**
  - Swap `cells = stripped.split("|")` for `cells = _split_cells(stripped)`.
  - Leave the leading/trailing empty-cell trim and the separator-row
    detection logic in place. The splitter returns the same outer shape
    `str.split("|")` did, so neither needs to change.
  - Cell text from the splitter already has `\|` unescaped to `|`. The
    existing per-cell `c.strip()` in the row-append step (line 57) and the
    separator-detection check still apply.

  **Patterns to follow:**
  - The existing parse-time normalization shape — split, trim border
    empties, detect-and-skip separator, strip per cell — is preserved
    verbatim. Only the split call changes.

  **Test scenarios:**
  - Parse `| Name | Pipe |\n| --- | --- |\n| Alice | a \| b |\n` →
    `rows == [["Name", "Pipe"], ["Alice", "a | b"]]`, alignments `[None, None]`.
  - Parse `| a \| b |\n` (no separator row) → `rows == [["a | b"]]`,
    alignments `[]`.
  - Parse a separator row containing only dashes/colons remains classified
    as a separator (regression check for R4 — the splitter must not change
    this).

  **Verification:**
  - All cases in `ParseAlignmentTests` continue to pass (R4 regression net).
  - The new escaped-pipe parse cases above pass.

- [ ] **Unit 3: Escape `|` and use encoded width in `format_table`**

  **Goal:** When emitting a row, replace literal `|` in cell content with
  `\|`, and compute column widths from the encoded form so the output stays
  visually aligned.

  **Requirements:** R2, R3, R4

  **Dependencies:** None for the format change itself; lands cleanly with
  Unit 2 once both are merged so round-trip works end to end.

  **Files:**
  - Modify: `table_fmt.py` (around lines 86-103)
  - Test: `test_table_fmt.py`

  **Approach:**
  - At the top of `format_table`, build an `encoded` view of `normalised`
    where each cell has `|` replaced with `\|`. (No other characters are
    rewritten — `\` itself passes through unchanged, per the Key Decision.)
  - Drive both column-width computation and `pad_cell` from this encoded
    view. The separator-row width math is already encoded-equivalent
    (separator cells never contain `|`), so it does not need a parallel path.
  - The bordering `| ` and ` | ` produced by `format_row` are never
    rewritten — only cell *contents* are encoded.

  **Patterns to follow:**
  - The existing two-stage shape in `format_table`: normalise → compute
    widths → format. Inserting an encode pass before width computation
    keeps that shape intact.

  **Test scenarios:**
  - `format_table([["H1"], ["a | b"]])` produces a body row whose cell
    text is `a \| b` (5 chars encoded, padded to width).
  - `format_table([["Header"], ["a | b"]])` aligns columns to the wider
    of `Header` (6) vs `a \| b` (6) — both six characters in the encoded
    form, so the data cell is emitted as `a \| b` with no extra padding.
  - `format_table([["x"], ["a | b"]])` widens column 0 to the encoded
    cell's six characters (R3): the rendered separator is `------` and
    the rendered header is padded to match. Confirms width math is driven
    by encoded length, not logical length.
  - Regression: `format_table([["H1", "H2"], ["a", "b"]])` is byte-identical
    to its current output (R4 — no `|` in any cell, no escaping happens).

  **Verification:**
  - All cases in `FormatSeparatorTests`, `FormatRowPaddingTests`, and the
    existing `RoundTripTests` pass unchanged (R4 regression net).
  - The new format-level cases above pass.

- [ ] **Unit 4: Round-trip test for escaped-pipe tables**

  **Goal:** Lock in the parse → format → parse → format fixed point for
  tables containing escaped pipes, matching the precedent set for the
  alignment fix.

  **Requirements:** R1, R2, R3 (composed end-to-end).

  **Dependencies:** Units 1-3.

  **Files:**
  - Test: `test_table_fmt.py`

  **Approach:**
  - Add a test in `RoundTripTests` (or a new `EscapedPipeTests` class) that
    starts from a markdown table containing `\|` in at least one cell,
    runs parse → format → parse → format, and asserts the second format
    equals the first (idempotent fixed point).
  - Add a focused parse-level test for `| a \| b |` → single cell `a | b`,
    and a focused format-level test that a row whose cell content is
    `a | b` emits `a \| b` (with column widths driven by the encoded form).

  **Patterns to follow:**
  - `test_table_fmt.py::RoundTripTests::test_mixed_alignments_round_trip` —
    the same parse-once / format-once / parse-twice / format-twice shape.

  **Test scenarios:**
  - Parse-level: `| a \| b |\n` → `rows == [["a | b"]]`.
  - Format-level: `format_table([["H"], ["a | b"]])` body row contains
    `a \| b` (and column 0 width is at least 6).
  - Round-trip fixed point: a table with at least one cell containing a
    literal pipe, parsed and formatted twice, yields identical output on
    the second format.

  **Verification:**
  - All three new tests pass.
  - The full `test_table_fmt.py` suite passes (R4).

## System-Wide Impact

- **Interaction graph:** The change is contained to `parse_table` and
  `format_table` in `table_fmt.py`. The only caller is `main()` in the
  same file plus `test_table_fmt.py`. No other module imports either
  function (verified via repo grep).
- **Error propagation:** No new error paths. The splitter consumes any
  string and returns a list; malformed input (e.g., a row that starts
  with `\|` instead of `|`) is filtered upstream by the existing
  `if not stripped.startswith("|"): continue` guard.
- **State lifecycle risks:** None. Both functions are pure.
- **API surface parity:** `parse_table` and `format_table` keep their
  current signatures and return shapes. No downstream consumer needs an
  update.
- **Integration coverage:** The round-trip test in Unit 4 is the
  cross-layer scenario; per-unit parse and format tests don't prove
  the encode/decode pair composes correctly without it.

## Risks & Dependencies

- **Risk: regex temptation.** A future contributor may try to "simplify"
  the splitter into `re.split(r"(?<!\\)\|", ...)`. That regex breaks
  `\\|`. The Unit 1 test scenarios for `\\|` and `\\\|` are the regression
  net; the inline rationale in `_split_cells`' docstring should call this
  out so the trap is visible at the call site.
- **Risk: silent data rewrite if `\` is also escaped on emit.** Already
  ruled out in the Key Decisions, but worth a one-line comment in
  `format_table` so the next reader doesn't add a `\` → `\\` pass.
- **No external dependencies.** Self-contained change in one file.

## Documentation / Operational Notes

- After implementation, append a `docs/solutions/logic-errors/` entry in
  the same shape as `table-fmt-respect-column-alignment-2026-04-24.md`,
  capturing: the parse-time symptom (cells split on `\|`), the splitter
  design (char-by-char, only `\|` unescapes), the format-time symmetry
  (escape `|` and compute width on encoded form), and the round-trip
  test as the regression net. This is execution-time work, not part
  of the planned units; flagged here so it isn't forgotten.
- No README, CLI, or runtime behavior changes for tables that don't
  contain `\|`.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-25-handle-escaped-pipes-in-table-cells-requirements.md](../brainstorms/2026-04-25-handle-escaped-pipes-in-table-cells-requirements.md)
- Related code: `table_fmt.py`, `test_table_fmt.py`
- Prior art: `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md` (issue #92, same module, same class of fix)
- Related issues: #92 (column-alignment fix — completed), #94 (this work)
