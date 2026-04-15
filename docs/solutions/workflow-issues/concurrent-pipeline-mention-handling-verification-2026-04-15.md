---
title: Handling @mention directives in PR review comments during concurrent pipelines
date: 2026-04-15
category: workflow-issues
module: development_workflow
problem_type: workflow_issue
component: development_workflow
symptoms:
  - PR review comment directive recognized but not executed during Phase 3
  - Requested file change not applied despite explicit @mention directive in PR review
root_cause: missing_workflow_step
resolution_type: workflow_improvement
severity: low
tags:
  - concurrent-pipelines
  - mention-handling
  - workflow-verification
  - stress-test
  - engineer-auto
---

# Handling @mention directives in PR review comments during concurrent pipelines

## Problem

The engineer-auto pipeline's Phase 3 (Compound) recognized a free-form PR review comment directive but did not execute it, leaving a requested file change unimplemented until the next pipeline invocation.

## Symptoms

- PR review comment containing `@windworker` directive was classified as "Provide feedback" in Phase 3 output rather than applied as a file change
- HTML comment `<!-- Stress test mention: this comment verifies @mention handling during concurrent pipelines -->` was not added to the top of `CHANGELOG.md` despite the explicit directive
- The directive appeared in Phase 3 metadata but was not committed to the working branch

## What Didn't Work

Phase 3 (Compound) identified the PR comment as an `@windworker` mention directive but treated it as an informational note rather than an actionable file-change request. The phase surfaced the directive in its work journal without applying the change.

## Solution

Apply the directive as a file change on the working branch. For this issue, the HTML comment was added to the top of `CHANGELOG.md`:

```markdown
<!-- Stress test mention: this comment verifies @mention handling during concurrent pipelines -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
```

When a PR review comment contains `@windworker` followed by a file-change instruction, parse the directive and apply the change before committing.

## Why This Works

@mention directives in PR review comments provide a lightweight way for reviewers to request inline changes without requiring separate commits or workflow interruptions. Applying the directive in the current pipeline invocation ensures the change lands on the working branch before the PR is merged, keeping review feedback and implementation co-located in the same commit history.

## Prevention

- When Phase 3 detects an `@windworker` directive in PR review comments, determine whether it requests a file change (vs. a feedback or routing action); if so, apply it before running compound documentation
- Log all detected directives with the parsed action type (`file_change`, `feedback`, `route`, etc.) to aid debugging
- Verify directive syntax before execution: confirm the target file exists and the instruction is unambiguous
- Test @mention directive parsing under concurrent pipeline conditions to ensure changes are not dropped when multiple phases are running in parallel

## Related Issues

- GitHub issue #76: Add CHANGELOG.md (this directive was part of its PR review)
- `docs/solutions/documentation-gaps/add-changelog-keep-a-changelog-format-2026-04-15.md` — covers CHANGELOG.md structure; the directive handling concern is distinct
