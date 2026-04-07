---
title: "Verify CREATE_NO_WINDOW Monkey-Patch and locking.py Import Fix Under Multi-Phase Workflow"
date: 2026-04-07
category: workflow-issues
module: claude-windows-worker
problem_type: workflow_issue
component: development_workflow
symptoms:
  - "Console windows flash on desktop during subprocess execution in headless mode"
  - "locking.py import failure prevents active session counting"
  - "Concurrent worker instances may exceed concurrency limits without session tracking"
root_cause: config_error
resolution_type: tooling_addition
severity: medium
tags:
  - subprocess
  - windows
  - console-window
  - create-no-window
  - session-counting
  - multi-phase-workflow
  - locking
  - engineer-auto
---

# Verify CREATE_NO_WINDOW Monkey-Patch and locking.py Import Fix Under Multi-Phase Workflow

## Problem

The Claude Windows Worker infrastructure required end-to-end verification that the CREATE_NO_WINDOW monkey-patch and locking.py import fix both function correctly under a realistic multi-phase workflow. There was no prior confirmation that subprocess execution remained windowless and that active session counting operated without errors when the full engineer-auto pipeline ran through all four phases.

## Symptoms

- Each subprocess spawned by the Windows worker would momentarily flash a console window on the desktop, making headless operation visibly non-headless and disrupting any user working on the machine.
- Without the locking.py import fix, active session counting would fail at import time, preventing the worker from correctly tracking concurrent sessions and potentially allowing multiple worker instances to exceed concurrency limits.

## What Didn't Work

This was a verification and smoke-test issue, not a debugging session. The CREATE_NO_WINDOW monkey-patch and the locking.py import fix had already been implemented in prior work. No failed approaches were involved -- the task was solely to confirm the existing fixes held up under engineer-auto multi-phase workflow conditions.

## Solution

Issue #36 was processed end-to-end through the engineer-auto workflow, exercising all four phases: work, review, compound, and complete. The verification artifact `test-windowless-workflow.md` was created and committed (commit `1cabdcc`), confirming:

- No observable console windows appeared during any phase
- No locking.py import errors occurred
- Active session counting functioned correctly throughout all phases

The engineer-auto workflow review phase (5 reviewers) returned "Ready to merge" with zero actionable findings.

## Why This Works

The CREATE_NO_WINDOW monkey-patch applies the Windows-specific `CREATE_NO_WINDOW` subprocess creation flag (`0x08000000`) at a low level, intercepting subprocess creation calls before they reach the OS. This flag instructs the Windows kernel not to allocate a console window for the new process. By monkey-patching at the infrastructure level rather than at each individual call site, all subprocess invocations -- including those made by third-party libraries -- inherit the suppression without per-call changes.

The locking.py module manages active session counting by tracking how many worker instances are currently executing. The import fix resolved a failure that occurred when locking.py was loaded, ensuring the session tracking state initializes correctly. With both fixes in place, the worker runs in a fully headless, windowless manner while safely enforcing concurrency limits.

## Prevention

- Re-run a similar smoke-test issue through the engineer-auto workflow periodically to verify windowless behavior has not regressed.
- Add a CI test that spawns a subprocess via the worker's patched path and asserts that `CREATE_NO_WINDOW` is present in the creation flags.
- Add an import smoke-test for locking.py that imports the module and calls the session count function, catching import-time regressions.
- When changes are made to subprocess invocation infrastructure or locking.py, require a windworker integration run before merging.
- Document the CREATE_NO_WINDOW patch and locking.py dependency in the worker's architecture notes so contributors understand the Windows-specific requirements.

## Related Issues

- [#36](https://github.com/mcdow-webworks/ce-pipeline-testbed/issues/36) — Test: Verify windowless subprocess execution with engineer-auto workflow
- [#28](https://github.com/mcdow-webworks/ce-pipeline-testbed/issues/28) — Smoke test: verify Python worker port processes issues correctly (same worker infrastructure)
