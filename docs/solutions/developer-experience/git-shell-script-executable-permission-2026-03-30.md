---
title: Shell script committed without executable permission in git
date: 2026-03-30
category: developer-experience
module: shell-scripts
problem_type: developer_experience
component: development_workflow
symptoms:
  - "./hello.sh fails with Permission denied after a fresh clone"
  - "git ls-files -s shows 100644 instead of 100755"
  - "Local ls -la shows rwxr-xr-x but git did not record the executable bit"
root_cause: incomplete_setup
resolution_type: workflow_improvement
severity: medium
tags:
  - git
  - shell-scripts
  - file-permissions
  - executable-bit
---

# Shell script committed without executable permission in git

## Problem

After running `chmod +x hello.sh` locally and committing the file, the executable permission bit was not stored in the git index. The file was tracked as `100644` (non-executable), meaning a fresh clone would fail to execute `./hello.sh` with "Permission denied".

## Symptoms

- `./hello.sh` fails with `Permission denied` after a fresh clone
- `git ls-files -s hello.sh` reports mode `100644` instead of `100755`
- Local file shows `rwxr-xr-x` permissions via `ls -la`, giving a false impression that git has recorded the executable bit

## What Didn't Work

Running `chmod +x hello.sh` alone before committing was insufficient. `chmod` only modifies the working tree file permissions; it does not update the git index. Git committed the file with its original `100644` mode regardless of the local filesystem state.

## Solution

Use `git update-index` to set the execute bit directly in the git index, then commit:

```bash
git update-index --chmod=+x hello.sh
git add hello.sh
git commit -m "fix: Set executable permission on hello.sh in git"
```

Verification:

```bash
git ls-files -s hello.sh
# Should now show: 100755 <hash> 0	hello.sh
```

## Why This Works

Git stores a simplified permission model in its index — only two modes for regular files: `100644` (non-executable) and `100755` (executable). The git index is separate from the filesystem. `chmod` modifies the OS-level inode permissions but never touches the git index entry. `git update-index --chmod=+x` modifies the mode stored in git's object database, ensuring the `100755` mode is written into the commit object and reproduced faithfully on every clone.

## Prevention

**1. Set the permission before the initial `git add`.**

Stage the file after making it executable so git picks up the mode on first add:

```bash
chmod +x hello.sh
git add hello.sh        # git records 100755 at add time if core.fileMode=true
git commit -m "feat: add hello.sh"
```

**2. Verify with `git ls-files -s` before merging.**

```bash
git ls-files -s hello.sh
# Expect: 100755 ...
```

**3. Add a CI check for executable scripts.**

```yaml
- name: Check script permissions
  run: |
    mode=$(git ls-files -s hello.sh | awk '{print $1}')
    [ "$mode" = "100755" ] || (echo "hello.sh is not executable in git" && exit 1)
```

**4. Ensure `core.fileMode` is not disabled.**

On some Windows environments, git may be configured with `core.fileMode=false`, which prevents git from tracking permission changes. If the repo targets Unix systems, keep `core.fileMode=true` (the default on Linux/macOS):

```bash
git config core.fileMode true
```

## Related Issues

- [#3](https://github.com/mcdow-webworks/ce-pipeline-testbed/issues/3) — Add a hello-world CLI that prints a greeting with the current date (the issue where this was discovered)
- [PR #4](https://github.com/mcdow-webworks/ce-pipeline-testbed/pull/4) — Implementation PR; fix committed at `7eb0d3e`
