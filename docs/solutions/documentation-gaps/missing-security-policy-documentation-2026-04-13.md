---
title: Add SECURITY.md with vulnerability reporting policy
date: 2026-04-13
category: documentation-gaps
module: security-policy
problem_type: documentation_gap
component: documentation
symptoms:
  - No SECURITY.md file existed in the repository root
  - No documented process for reporting security vulnerabilities
  - No contact email for responsible disclosure
  - GitHub security policy tab showed no policy configured
root_cause: inadequate_documentation
resolution_type: documentation_update
severity: low
tags:
  - security-policy
  - responsible-disclosure
  - community-health
  - github-recommended-files
---

# Add SECURITY.md with vulnerability reporting policy

## Problem

The repository lacked a `SECURITY.md` file, meaning GitHub could not surface a security policy and there was no documented process for responsible vulnerability disclosure.

## Symptoms

- GitHub's Security Policy tab showed no policy configured for the repo
- Visitors finding a vulnerability had no documented channel for private reporting
- Risk of vulnerabilities being disclosed via public GitHub issues

## What Didn't Work

N/A — straightforward documentation task with no failed approaches.

## Solution

Created a 25-line `SECURITY.md` at the repo root with three sections:

1. **Supported Versions** — only the latest release on `master` is actively supported
2. **Reporting a Vulnerability** — directs reporters to email `security@mcdow-webworks.com` with description, reproduction steps, and impact assessment; 48-hour acknowledgment SLA and 7-day fix timeline; explicit instruction not to open public issues
3. **Disclosure Policy** — coordinated disclosure practice

Committed on branch `claude/issue-69` as `4f1e115`.

## Why This Works

GitHub natively recognizes `SECURITY.md` files placed at the repository root (or in `.github/` or `docs/`). Once present, the file populates the repo's Security Policy tab and replaces the generic prompt with the project's specific contact instructions, closing the gap between a reporter finding a vulnerability and knowing how to disclose it privately.

## Prevention

- Add `SECURITY.md` to new repository templates or an organization-level `.github` repo so all future repos inherit a baseline policy automatically
- Verify contact emails are monitored inboxes before publishing (the address `security@mcdow-webworks.com` was inferred, not sourced from existing config)
- Confirm response timelines (48h acknowledgment, 7-day fix) match actual team capacity
- Consider CODEOWNERS or branch protection rules for `SECURITY.md` to prevent accidental contact detail drift

## Related Issues

- [#69](https://github.com/mcdow-webworks/ce-pipeline-testbed/issues/69) — Add SECURITY.md (this issue)
- [#68](https://github.com/mcdow-webworks/ce-pipeline-testbed/issues/68) — Add CODE_OF_CONDUCT.md (adjacent community health file, same pattern)
- [#64](https://github.com/mcdow-webworks/ce-pipeline-testbed/issues/64) — Add CONTRIBUTING.md (resolved; same community health file pattern)
