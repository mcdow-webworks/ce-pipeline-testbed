---
title: Missing MIT License File at Repo Root
date: 2026-04-15
category: docs/solutions/documentation-gaps
module: MIT License Addition
problem_type: documentation_gap
component: documentation
symptoms:
  - No LICENSE file present in repository root
  - Repository lacks any open-source license declaration
root_cause: inadequate_documentation
resolution_type: documentation_update
severity: medium
tags:
  - license
  - mit
  - open-source
  - compliance
---

# Missing MIT License File at Repo Root

## Problem

The repository had no LICENSE file, leaving the project without explicit terms under which others may use, copy, modify, or distribute the code. Without a license, software is implicitly "all rights reserved" regardless of whether it is publicly accessible.

## Symptoms

- No `LICENSE`, `LICENSE.md`, `LICENSE.txt`, or `COPYING` file exists at the repo root.
- The `README.md` contains no license badge, license section, or copyright notice.
- GitHub displays "No license" in the repository sidebar under "About."
- Automated dependency scanners (e.g., FOSSA, Snyk, Dependabot) flag the project as license-unknown.
- Contributors and downstream consumers have no legal basis to use or redistribute the code.

## What Didn't Work

No failed attempts — the fix was straightforward. The only uncertainty was determining the correct copyright holder name: "WebWorks" was inferred from the user's email domain (`mcdow@webworks.com`), which is not an authoritative source. The legal entity name should always be confirmed with the repo owner before committing.

## Solution

**1. Create the file.**

Add a file named exactly `LICENSE` (no extension) at the repository root. This is the conventional name recognized by GitHub, npm, PyPI, and most tooling.

**2. Use standard MIT boilerplate.**

```
MIT License

Copyright (c) <YEAR> <COPYRIGHT HOLDER>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**3. Determine the copyright holder name.**

Check in order of authority:

1. An existing copyright notice in source files or `README.md`.
2. The `author` field in `package.json`, `pyproject.toml`, `setup.py`, or equivalent manifest.
3. Git config: `git config user.name` or dominant committer via `git log --format="%an" | sort | uniq -c | sort -rn | head -1`.
4. The organization or user name of the GitHub remote: `git remote get-url origin`.

Inferring from an email domain introduces ambiguity — the legal holder could be an individual, a trading name, or a registered entity. Confirm with the repo owner before treating the name as authoritative.

**4. Determine the copyright year.**

Use the year of first public commit, or a range (e.g., `2024–2026`) if the project has history. For a brand-new repo, the current year is conventional.

```bash
# First commit year
git log --reverse --format="%ai" | head -1 | cut -c1-4

# Current year
date +%Y
```

For this repo (issue #77): `Copyright (c) 2026 WebWorks`.

## Why This Works

Copyright law in most jurisdictions grants the author exclusive rights the moment a work is created — no registration required. A repository published without a license is legally "all rights reserved," meaning anyone who forks, runs, or distributes it is technically infringing, even if the code is freely visible on a public platform.

Adding a `LICENSE` file grants explicit, irrevocable permissions to downstream users. MIT is one of the most permissive and widely recognized open-source licenses: it allows use, modification, and redistribution (including in proprietary products) with the sole requirement that the copyright notice be preserved. Its brevity and permissiveness make it a natural default for utility scripts and small tools.

Without a license:
- GitHub explicitly warns visitors "No license — all rights reserved."
- Corporate users with legal review requirements cannot adopt or contribute to the project.
- Package registries (npm, PyPI) surface the absence as a metadata warning.
- Automated compliance tools block or flag the dependency in downstream projects.

## Prevention

**During repo creation:**

- Use the GitHub web UI "Add a license" dropdown when initializing the repository.
- Use the CLI: `gh repo create <name> --license mit` — creates the `LICENSE` file automatically.
- Use a project template (`cookiecutter` or similar) that includes `LICENSE` as a scaffold artifact.

**Repo setup checklist:**

- [ ] `LICENSE` file exists at repo root (check with `ls LICENSE`).
- [ ] Copyright holder name is confirmed with the project owner — not inferred from email or git config.
- [ ] Copyright year reflects the first commit year, or a range if the project has history.
- [ ] `README.md` includes a license badge or section (e.g., `![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)`).

**CI/tooling enforcement:**

- `licensee` (Ruby gem) or `reuse` (REUSE spec tooling) can lint a repo for license compliance and run in CI.
- GitHub's dependency graph and security features work better when the license is a standard machine-readable `LICENSE` file with recognized SPDX text.

**Organizational policy:**

- Add a license requirement to your team's repo creation checklist or `CONTRIBUTING.md` template.
- Use a GitHub organization-level `.github` repo with a default community health file that references the license requirement.

## Related Issues

- **Issue #77** — direct trigger: added `LICENSE` (MIT, 2026, WebWorks) to repo root; committed as `docs: add MIT license file` (commit `6efb937`).
- **Issue #73** (closed) — prior occurrence of the same missing-license problem in this repo; confirms this is a recurring gap worth preventing at the organizational level.
- If this repository is ever published to a package registry (npm, PyPI), the `license` field in the manifest (`package.json`, `pyproject.toml`) should also be set to `"MIT"` to match the `LICENSE` file.
