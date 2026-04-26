# ce-review run — issue #109 autofix

- **Run ID:** issue-109-autofix-20260426
- **Branch:** `claude/issue-109`
- **Base:** master @ `d02bb4428a9fdb7384c16db973a264bfaff50113`
- **Mode:** autofix
- **Verdict:** Ready with residual work — 2 P3 fixes applied, 2 P2 findings deferred to human

## Scope

| File | Role |
|------|------|
| `table_fmt.py` | New `format_json(rows, alignments)` helper + argparse-backed `main(argv=None)` |
| `test_table_fmt.py` | New `FormatJsonTests` (8 → 9) and `MainCliTests` (8 → 9) |
| `docs/brainstorms/2026-04-26-table-fmt-json-output-requirements.md` | Protected artifact |
| `docs/plans/2026-04-26-001-feat-table-fmt-json-output-plan.md` | Protected artifact |

Untracked: none. No migration files in scope.

## Intent

Add a `--json` output mode to `table_fmt.py` that emits the parsed table as a JSON array of header-keyed row objects. Default markdown-formatting behavior must remain byte-for-byte unchanged. New `format_json` is parallel to `format_table`; argparse used for flag handling; `main(argv=None)` for testability.

## Reviewer team

Always-on: correctness, testing, maintainability, agent-native-reviewer, learnings-researcher.
Conditional: kieran-python — `table_fmt.py` adds new public Python helper plus argparse wiring; tests use `unittest.mock.patch.object(table_fmt.sys, ...)` for in-process CLI testing.

Skipped: security (no auth/network/secrets), performance (no DB/cache/heavy loops), api-contract (CLI flag is small surface, well-documented and tested in-tree), data-migrations (none), reliability (no retries/timeouts/jobs).

## Synthesized findings

After dedupe across reviewers, four distinct findings:

### P2 — `format_json` silently truncates ragged rows via unchecked `zip()`

- **Reviewers:** correctness (0.85), testing (0.85), kieran-python (0.78) — three reviewers independently flagged.
- **File:** `table_fmt.py:155`
- **Route:** manual / human / requires_verification=true
- **Why it matters:** `parse_table` does not normalise per-row column counts; `format_table` explicitly does (lines 84-85), but `format_json` calls `dict(zip(header, row))` directly. A data row shorter than the header silently drops the trailing keys; a row longer than the header silently drops the extras. Either form is quiet data loss in JSON output that downstream consumers will treat as authoritative — and it diverges from the markdown path, where the same input gets padded.
- **Suggested resolution (human decision):** (a) raise `ValueError` on mismatch — symmetrical with the duplicate-header guard, (b) normalise like `format_table` does, or (c) document the truncation behavior in the docstring's Preconditions section. Option (a) is most consistent with the strict tone of the existing helper.
- **Why deferred:** behavioral choice between strict-error and silent-pad needs a human call.

### P2 — Byte-parity test compares `format_table` output to itself (tautology)

- **Reviewers:** testing (0.9)
- **File:** `test_table_fmt.py:209` (`test_default_mode_byte_for_byte_parity_with_format_table`)
- **Route:** manual / human / requires_verification=true
- **Why it matters:** R1 acceptance criterion is byte-for-byte parity *with the pre-flag implementation*. The current test does `expected = format_table(rows, alignments)` and asserts `main()` produces the same bytes — but `main()` literally calls `format_table(rows, alignments)`, so both sides would regress in lockstep. A regression in `format_table` itself would not fail this test.
- **Suggested resolution:** Replace the computed `expected` with a hardcoded golden string captured from the pre-flag binary, e.g. `expected = '| Name  | Age | City |\n| :---- | --: | :--: |\n| Alice |  30 | NYC  |\n'`.
- **Why deferred:** test design call about which assertion strength to commit to. Mechanical to apply, but the testing reviewer routed it as `manual`/`human`; per synthesis rules, do not widen the route without new evidence.

### P3 — `format_json` untested for header-only table — APPLIED

- **Reviewers:** testing (0.82)
- **Route:** safe_auto / review-fixer
- **Fix applied:** Added `test_header_only_table_emits_empty_array` to `FormatJsonTests`. Pins `format_json([["Name","Age"]], [None,None]) == "[]\n"`.

### P3 — `main(argv=None)` default branch never exercised — APPLIED

- **Reviewers:** testing (0.78)
- **Route:** safe_auto / review-fixer
- **Fix applied:** Added `test_main_with_default_argv_uses_sys_argv` to `MainCliTests`. Patches `sys.argv` and calls `table_fmt.main()` with no argument, exercising the default-arg path used by the production entrypoint at `table_fmt.py:199`.

## Applied fixes

| Finding | File | Test added |
|---------|------|------------|
| P3 header-only | `test_table_fmt.py` | `FormatJsonTests.test_header_only_table_emits_empty_array` |
| P3 default-argv | `test_table_fmt.py` | `MainCliTests.test_main_with_default_argv_uses_sys_argv` |

Verification: `python -m unittest test_table_fmt` → **30/30 passing** (was 28/28).

No production code (`table_fmt.py`) modified by autofix. Round 2 not needed — additive test scope, all green.

## Residual actionable work (owner=human)

Two findings remain. Both are deferred to human judgment per the testing/correctness/kieran-python reviewers' conservative routing. Per autofix-mode rules, no `docs/todos/` files are created for `owner=human` findings — they are surfaced here in the run artifact and report only.

1. **Decide ragged-row policy for `format_json`** — error / normalize / document. (See P2 finding above.)
2. **Strengthen the byte-parity test** — replace tautological `format_table(...)` expected with hardcoded golden string. (See P2 finding above.)

## Pre-existing

None — no findings flagged with `pre_existing: true`.

## Coverage

- Reviewers spawned: 6. Returned: 6. Failed/timed-out: 0.
- Suppressed below 0.60 confidence: 0.
- Intent uncertainty: none.

### Residual risks (collected from reviewers)

- Header keys with empty string `""` are accepted (only string-equality duplicate check applies). A single empty header silently produces a JSON object with a `""` key — valid JSON but possibly surprising.
- Duplicate-header detection is exact-string equality. Headers differing only by Unicode normalization (NFC vs NFD `é`) would not be detected as duplicates and would produce two ostensibly identical keys.
- argparse stderr capture in `MainCliTests` works because `patch.object(table_fmt.sys, ...)` mutates the shared module attribute. A future refactor that vendors its own argparse-equivalent could silently break `MainCliTests` error-text assertions.
- `format_json` assumes `rows` is non-empty. `main()` guards via `if not rows`, but the helper would raise `IndexError` if called directly with `[]`. Documented as a precondition, not enforced.
- Minimum Python version is unspecified (no `pyproject.toml`/`setup.cfg`/`tox.ini`/`.python-version`; only `#!/usr/bin/env python3` shebang). Blocks any future move to `zip(..., strict=True)` (3.10+) or PEP 604 type hints without first pinning a floor.

### Testing gaps (not closed)

- Ragged data rows (short or long vs header) under `--json` — addressed by the P2 finding above; closing the gap is gated on the human policy decision.
- Byte-parity test against a hardcoded golden string — addressed by the P2 finding above.
- Whitespace-only or empty-string header cells — duplicate path triggers but with confusing error text.
- Stdin containing zero bytes under `--json` — distinct from "not a table" but hits the same `if not rows` branch; not asserted.
- argparse `--json=value` (erroneous `=` for a `store_true`) rejection — implicit, not asserted.

## Agent-native review

No agent-native gaps. The diff is exemplary for agent parity:

- `--json` is discoverable via `--help` (asserted by `test_help_mentions_json_flag`).
- Purely additive — default mode is byte-for-byte unchanged (assertion strength caveat noted above).
- Stdin/stdout I/O — no interactive prompts, no TTY detection, no file-path negotiation.
- `format_json` is a public, importable primitive (no leading underscore).
- Errors are machine-parseable: stable `Error: ...` prefix on stderr, exit code 1 for input-content failures, exit code 2 from argparse for unknown flags — each path tested.
- `main(argv=None)` accepts an explicit argv list; in-process invocation from an agent harness is trivial.

## Learnings & past solutions

**Relevant:** `docs/solutions/logic-errors/table-fmt-respect-column-alignment-2026-04-24.md` documents the prior `table_fmt` change (issue #92) that turned `parse_table` into a tuple-returning function `(rows, alignments)` and added the `alignments` parameter to `format_table`. Three takeaways for #109:

1. The `format_json(rows, alignments)` signature mirrors the established convention — alignments are first-class downstream of `parse_table` and any new emitter accepts them, even if JSON serializes them as metadata rather than padding. This work follows that pattern.
2. The prior fix established a round-trip test pattern (`parse → format → parse`). For JSON mode, the analogous guard is "default markdown path is byte-identical" — the byte-parity finding above asks for a stronger version of exactly this.
3. Discipline of grepping all call sites before broadening shape was followed (`main()` was renamed to `main(argv=None)` with the existing `__main__` invocation still working).

**No prior solutions** for argparse / `main(argv=None)` patterns, JSON conventions (`indent=2`, `ensure_ascii`, trailing newline), header-keyed dict / duplicate-header handling, or `unittest.mock.patch.object(sys, ...)` CLI testing.

## Verdict

**Ready with residual work.** Two P3 testing-coverage gaps closed in autofix; two P2 findings deferred for human decision (ragged-row policy and byte-parity assertion strength). No P0/P1 findings. Maintainability reviewer returned zero findings. All 30 tests pass.
