---
title: Missing CONTRIBUTING.md — No Contributor Guidelines at Repo Root
module: contributing-guidelines
date: 2026-04-13
category: docs/solutions/documentation-gaps/
problem_type: documentation_gap
component: documentation
symptoms:
  - No CONTRIBUTING.md file existed at the repository root
  - Contributors lacked guidance on how to report bugs
  - No documented process for submitting changes via fork and PR
  - No code style expectations communicated to external contributors
root_cause: inadequate_documentation
resolution_type: documentation_update
severity: low
tags:
  - contributing
  - onboarding
  - documentation
  - pull-request
  - code-style
  - developer-experience
---

# Missing CONTRIBUTING.md — No Contributor Guidelines at Repo Root

## Problem

The repository had no `CONTRIBUTING.md` file, leaving contributors without any guidance on how to report bugs, submit changes, or follow code style conventions. GitHub's "Contribute" prompt in the repository UI had no file to link to, creating friction for first-time contributors.

## Symptoms

- No `CONTRIBUTING.md` present at the repository root
- Contributors had to infer the PR workflow and code style expectations from existing code and commits
- GitHub's contribution prompt surfaced with no linked guidelines

## What Didn't Work

- Adding extra sections (CI setup, license details, code of conduct) was explicitly ruled out — these belong in their own dedicated files and would grow the file beyond its intended scope
- An initial draft used a hardcoded `` `master` `` branch reference in the "submit changes" steps; this was a staleness risk if the default branch is ever renamed and was replaced in review

## Solution

A 16-line `CONTRIBUTING.md` was created at the repository root, with tone calibrated to match the existing `README.md`. The file contains exactly three sections:

```markdown
# Contributing

## Reporting Bugs

Open a [GitHub issue](../../issues) with a clear description of the problem,
steps to reproduce it, and the expected vs. actual behavior.

## Submitting Changes

1. Fork the repository.
2. Create a branch with a descriptive name (e.g., `fix/typo-in-readme`, `feat/add-formatter`).
3. Make your changes and commit them with a clear message.
4. Open a pull request against the repository's default branch and describe what you changed and why.

## Code Style

Follow the conventions already present in the codebase. When in doubt, match
the style of the surrounding code.
```

Key review fix applied: "Create a branch from `master`" was replaced with "Create a branch from the repository's default branch" to avoid staleness across branch renames.

## Why This Works

The absence of `CONTRIBUTING.md` was a pure documentation gap — no process was broken, the file simply didn't exist. The fix is minimal and scoped to exactly what contributors need to take action: where to report a problem, how to submit a change, and what code style to follow. Keeping it under 40 lines means it will actually be read. Avoiding hardcoded branch names and CI-specific details means the file stays accurate without requiring updates when infrastructure changes.

## Prevention

1. **Repo initialization checklist**: Add `CONTRIBUTING.md` alongside `README.md` and `.gitignore` as a required item when creating a new repository. A GitHub repository template (`Settings > Template repository`) can include a skeleton `CONTRIBUTING.md` so every repo forked from it starts with one.

2. **Keep a three-section skeleton**: Maintain a neutral template snippet (in `docs/templates/` or a team wiki) with bug reporting link, fork/branch/PR steps using "default branch" phrasing, and a one-line code style note. New repos copy and trim rather than write from scratch.

3. **Avoid hardcoded branch names**: Always write "the repository's default branch" rather than `` `master` `` or `` `main` `` in contribution guides. This keeps the file accurate across branch renames.

4. **Scope discipline**: Keep CI setup, license details, and code of conduct in their own dedicated files. Document this separation so future contributors don't grow `CONTRIBUTING.md` beyond its intended scope.

5. **PR template check**: Add a line to your PR template: "If this is a new repository, does a `CONTRIBUTING.md` exist at the root?" This catches the gap at the point where someone is already thinking about process.

## Related Issues

- GitHub Issue #64: "Add a CONTRIBUTING.md with basic contribution guidelines"
- Related documentation gap: `docs/solutions/best-practices/project-status-dashboard-implementation-2026-04-06.md` (separate improvement to repo setup)
