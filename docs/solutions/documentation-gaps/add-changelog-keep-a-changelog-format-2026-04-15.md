---
title: Add CHANGELOG.md following Keep a Changelog format
date: 2026-04-15
category: documentation-gaps
module: documentation
problem_type: documentation_gap
component: documentation
symptoms:
  - No CHANGELOG.md file at the repository root
  - No structured record of project changes or version history
root_cause: inadequate_documentation
resolution_type: documentation_update
severity: low
tags:
  - changelog
  - keep-a-changelog
  - documentation
---

# Add CHANGELOG.md following Keep a Changelog format

## Problem

The repository lacked a CHANGELOG.md file, providing no structured record of changes, features, or fixes for users and contributors to reference across versions.

## Symptoms

- No CHANGELOG.md existed at the repo root
- No centralized record of project changes or version history for users or contributors

## What Didn't Work

- Initial CHANGELOG.md was created without blank lines between subsection headers (`### Added`, `### Changed`, etc.), causing suboptimal markdown rendering — a second commit was required to fix spacing

## Solution

Create `CHANGELOG.md` at the repository root following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) v1.1.0:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security
```

Key implementation detail: include blank lines between each subsection header for correct markdown rendering.

## Why This Works

Keep a Changelog is an industry-standard format that categorizes changes by type (Added, Changed, Deprecated, Removed, Fixed, Security), aligns naturally with Semantic Versioning, and is immediately familiar to open-source contributors. The [Unreleased] section template guides future contributors on where to record changes before a release is cut.

## Prevention

- Always include blank lines between subsection headers — markdown renderers may collapse sections without them
- Update the `[Unreleased]` section as changes are merged; before each release, rename it to a versioned section (e.g., `## [1.0.0] - YYYY-MM-DD`)
- Keep entries brief but user-facing: describe what changed, not how the code changed
- Add comparison links at the bottom for version diffs (e.g., `[Unreleased]: https://github.com/owner/repo/compare/v1.0.0...HEAD`)

## Related Issues

- GitHub issue #76: Add CHANGELOG.md
- GitHub issue #72: Add CHANGELOG.md (closed predecessor, identical requirements)
