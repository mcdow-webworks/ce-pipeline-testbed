# ce-pipeline-testbed

A test environment for the Claude Windows Worker's CE (Compound Engineering) pipeline. This repo serves as a sandbox where the automated worker processes GitHub issues, generates brainstorms, plans, and implementations, and opens pull requests — all without affecting production systems.

**This is not a production repository.** The code and artifacts here exist solely to exercise and validate the CE pipeline workflow.

## Getting Started

### Prerequisites

- [Git](https://git-scm.com/)
- A GitHub account with access to this repository
- [Claude Code](https://claude.com/claude-code) (if running the CE pipeline locally)

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/mcdow-webworks/ce-pipeline-testbed.git
   cd ce-pipeline-testbed
   ```

2. Create a new issue to trigger the pipeline, or browse existing issues and pull requests to see example pipeline runs.

3. To run the CE pipeline locally, open the repo in Claude Code and use the available skills (`/ce:brainstorm`, `/ce:plan`, `/ce:work`).
