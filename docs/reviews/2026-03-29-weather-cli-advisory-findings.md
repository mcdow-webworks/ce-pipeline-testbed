---
date: 2026-03-29
topic: weather-cli
type: review-advisory-findings
---

# Weather CLI — Unfixed Advisory Findings

These findings were identified during the code review of `weather.sh` (PR #6) and left as advisory for the author's discretion.

## Finding #2 — Multi-word city names silently truncated

- **Severity:** P2 (moderate)
- **Location:** `weather.sh:39`
- **Confidence:** 0.90
- **Category:** correctness

**Description:** Multi-word city names are silently truncated to the last word. For example, `weather.sh New York` produces a forecast for "York" instead of "New York" because the `while`/`shift` argument parser treats each space-separated token as a separate positional argument, and only the last one is kept as the city name.

**Suggested fix:** Accumulate all non-flag positional arguments into the city variable, or require quoting (and document it in `--help` output). For example:

```bash
# Option A: accumulate positional args
*)
  city="${city:+$city }$1"
  shift
  ;;

# Option B: document quoting requirement
#   weather.sh "New York" --units celsius
```

---

## Finding #5 — Variable name `suffix` lacks semantic clarity

- **Severity:** P3 (low)
- **Location:** `weather.sh:62`
- **Confidence:** 0.62
- **Category:** maintainability

**Description:** The variable `suffix` describes the formatting position (it appears after the temperature number) rather than the semantic meaning of its content. A name like `unit_label` would more clearly communicate that it holds the temperature unit indicator (`°F` or `°C`).

**Suggested fix:**

```bash
# Before
suffix="°F"

# After
unit_label="°F"
```
