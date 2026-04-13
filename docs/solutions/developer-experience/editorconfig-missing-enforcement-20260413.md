---
title: Missing .editorconfig for Consistent Editor Settings
date: 2026-04-13
category: developer-experience
module: editor-configuration
problem_type: developer_experience
component: tooling
symptoms:
  - Inconsistent indentation styles across editors and contributors
  - Trailing whitespace not automatically trimmed on save
  - Files missing final newlines causing noisy diffs
  - Varying charset encoding across operating systems
root_cause: incomplete_setup
resolution_type: tooling_addition
severity: medium
related_components:
  - development_workflow
tags:
  - editorconfig
  - editor-settings
  - code-style
  - indentation
  - whitespace
  - contributor-workflow
---

# Missing .editorconfig for Consistent Editor Settings

## Problem

The repository lacked a `.editorconfig` file at the root, so different editors and contributors applied inconsistent indentation, charset, and whitespace settings — generating noisy diffs and style drift across the codebase.

## Symptoms

- Inconsistent indentation styles (tabs vs. spaces) across files and contributors
- Varying indentation sizes (2 vs. 4 spaces) in the same project
- Trailing whitespace not automatically removed on save
- Files missing a final newline (visible as diff noise on last lines)
- Non-UTF-8 character encoding artifacts on some platforms

## What Didn't Work

N/A — this was a missing configuration. No prior fix attempts failed.

## Solution

Created `.editorconfig` at the repository root:

```ini
root = true

[*]
charset = utf-8
indent_style = space
indent_size = 2
trim_trailing_whitespace = true
insert_final_newline = true

[*.py]
indent_size = 4
```

Key decisions:
- `root = true` prevents any parent-directory `.editorconfig` from overriding these settings
- `indent_size = 2` is the standard for JavaScript, TypeScript, YAML, JSON, and most web configs
- `[*.py] indent_size = 4` follows PEP 8 (Python convention)
- No `end_of_line` set — acceptable for a cross-platform team but worth revisiting if Windows CRLF becomes a problem

## Why This Works

EditorConfig is a tool-agnostic configuration format supported natively by virtually all modern editors (VS Code, JetBrains IDEs, Vim, Emacs, Sublime, etc.). When a developer opens a file, the editor reads `.editorconfig` and automatically applies the settings during editing and on save. Because the file is version-controlled, every contributor gets the same rules without any per-machine configuration.

This eliminates formatting inconsistencies at the source — before code is even committed — rather than catching them in CI or during code review.

## Prevention

- **Add CI enforcement**: Run `editorconfig-checker` (or `eclint`) in CI to flag files that violate the config. This catches violations from editors that don't natively support EditorConfig.
- **Document in onboarding**: Mention EditorConfig in `ONBOARDING.md` so new contributors know it exists and that most editors pick it up automatically.
- **Pair with a formatter**: If the project adopts Prettier or Black, configure them to respect EditorConfig settings (both tools support this natively) for double enforcement.
- **Review on language additions**: When a new language is introduced to the repo, add a language-specific override section if its indentation convention differs from the default `indent_size = 2`.

## Related Issues

- GitHub issue #65: "Add .editorconfig for consistent editor settings"
- CE review artifact: `.context/compound-engineering/ce-review/20260413-issue65/report.md`
