<div align="center">
    <img src="assets/images/logo_small.webp"/>
    <h1>Spec Kitty</h1>
    <h3><em>Build high-quality software faster.</em></h3>
</div>

<p align="center">
    <strong>An effort to allow organizations to focus on product scenarios rather than writing undifferentiated code with the help of Spec-Driven Development.</strong>
</p>

> **Note:** Spec Kitty is a community-maintained fork of GitHub's [Spec Kit](https://github.com/github/spec-kit). We retain the original attribution per the Spec Kit license while evolving the toolkit under the Spec Kitty banner.
---
## 🎯 Why Spec-Kitty?

Unlike traditional spec-driven tools, Spec-Kitty includes a **live kanban dashboard** that gives you real-time visibility into your AI coding workflows:

- 📊 **Visual Task Tracking**: See exactly what your AI agents are working on
- 🔄 **Real-Time Progress**: Live updates as work moves through planned → doing → review → done
- 👥 **Multi-Agent Orchestration**: Coordinate multiple AI coding agents simultaneously  
- 📦 **Artifact Management**: Track specifications, plans, tasks, and deliverables in one place
- ⚡ **Zero Configuration Dashboard**: Automatically starts with `spec-kitty init`

Perfect for teams using Claude Code, Cursor, Windsurf, Gemini CLI, or GitHub Copilot.

> Spec Kitty combines specification-first rigor with a live kanban dashboard, agent-aware prompts, and automated lane scripts—features you will not find bundled together in other SDD toolkits.

## 📊 Real-Time Dashboard

Spec Kitty includes a **live dashboard** that automatically tracks your feature development progress. View your kanban board, monitor work package status, and see which agents are working on what—all updating in real-time as you work.

<div align="center">
  <img src="assets/images/dashboard-kanban.png" alt="Spec Kitty Dashboard - Kanban Board View" width="800"/>
  <p><em>Kanban board showing work packages across all lanes with agent assignments</em></p>
</div>

<div align="center">
  <img src="assets/images/dashboard-overview.png" alt="Spec Kitty Dashboard - Feature Overview" width="800"/>
  <p><em>Feature overview with completion metrics and available artifacts</em></p>
</div>

The dashboard starts automatically when you run `spec-kitty init` and runs in the background. Access it anytime with the `/spec-kitty.dashboard` command or `spec-kitty dashboard`—the CLI will start the correct project dashboard automatically if it isn’t already running, and supports `--port` (preferred port) and `--kill` (clean shutdown).

**Key Features:**
- 📋 **Kanban Board**: Visual workflow across planned → doing → for review → done lanes
- 📈 **Progress Tracking**: Real-time completion percentages and task counts
- 👥 **Multi-Agent Support**: See which AI agents are working on which tasks
- 📦 **Artifact Status**: Track specification, plan, tasks, and other deliverables
- 🔄 **Live Updates**: Dashboard refreshes automatically as you work

---

## Table of Contents

- [🎯 Why Spec-Kitty?](#-why-spec-kitty)
- [📊 Real-Time Dashboard](#-real-time-dashboard)
- [🔍 Spec-Kitty vs. Other Spec-Driven Tools](#-spec-kitty-vs-other-spec-driven-tools)
- [📦 Examples](#-examples)
- [🤔 What is Spec-Driven Development?](#-what-is-spec-driven-development)
- [⚡ Get started](#-get-started)
- [🤖 Supported AI Agents](#-supported-ai-agents)
- [🔧 Spec Kitty CLI Reference](#-spec-kitty-cli-reference)
- [🌳 Worktree Strategy](#-worktree-strategy)
- [✅ Feature Acceptance & Merge Workflow](#-feature-acceptance--merge-workflow)
- [🔧 Prerequisites](#-prerequisites)
- [📖 Learn more](#-learn-more)
- [📋 Detailed process](#-detailed-process)
- [🔍 Troubleshooting](#-troubleshooting)
- [👥 Maintainers](#-maintainers)
- [💬 Support](#-support)
- [🙏 Acknowledgements](#-acknowledgements)
- [📄 License](#-license)

## 🤔 What is Spec-Driven Development?

Spec-Driven Development **flips the script** on traditional software development. For decades, code has been king — specifications were just scaffolding we built and discarded once the "real work" of coding began. Spec-Driven Development changes this: **specifications become executable**, directly generating working implementations rather than just guiding them.

## ⚡ Get started

### 1. Install Spec Kitty CLI

Choose your preferred installation method:

#### Option 1: From PyPI (Recommended - Stable Releases)

Install the latest stable release from PyPI:

**Using pip:**
```bash
pip install spec-kitty-cli
```

**Using uv:**
```bash
uv tool install spec-kitty-cli
```

Then use the tool from any directory:

```bash
spec-kitty init <PROJECT_NAME>
spec-kitty check
```

#### Option 2: From GitHub (Latest Development)

Install the latest development version from source:

**Using pip:**
```bash
pip install git+https://github.com/Priivacy-ai/spec-kitty.git
```

**Using uv:**
```bash
uv tool install spec-kitty-cli --from git+https://github.com/Priivacy-ai/spec-kitty.git
```

#### Option 3: One-time Usage

Run directly without installing:

**Using pipx:**
```bash
pipx run spec-kitty-cli init <PROJECT_NAME>
```

**Using uvx:**
```bash
uvx spec-kitty-cli init <PROJECT_NAME>
```

**Benefits of persistent installation:**

- Tool stays installed and available in PATH
- No need to create shell aliases
- Better tool management (`pip list`, `uv tool list`, etc.)
- Faster execution (no download on each run)
- Cleaner shell configuration

### 2. Establish project principles

Use the **`/spec-kitty.constitution`** command to create your project's governing principles and development guidelines that will guide all subsequent development.

```bash
/spec-kitty.constitution Create principles focused on code quality, testing standards, user experience consistency, and performance requirements
```

### 3. Create the spec

Use the **`/spec-kitty.specify`** command to describe what you want to build. Focus on the **what** and **why**, not the tech stack. The assistant will interview you first and refuses to continue until you answer its discovery questions.

```bash
/spec-kitty.specify Build an application that can help me organize my photos in separate photo albums. Albums are grouped by date and can be re-organized by dragging and dropping on the main page. Albums are never in other nested albums. Within each album, photos are previewed in a tile-like interface.
```

> After `/spec-kitty.specify` completes, move into the dedicated worktree it creates (for example, `cd .worktrees/001-photo-albums`) before running planning or implementation commands. If your environment blocks access to `.worktrees/`, the CLI automatically falls back to the single-worktree flow, so nothing breaks.

The assistant asks **one focused question at a time**, blocks with `WAITING_FOR_DISCOVERY_INPUT`, and only generates the spec once an Intent Summary is confirmed. No assumptions without your explicit approval.

### 4. Create a technical implementation plan

Use the **`/spec-kitty.plan`** command to provide your tech stack and architecture choices. Expect it to challenge the spec, ask for missing non-functional details, and pause until you respond.

```bash
/spec-kitty.plan The application uses Vite with minimal number of libraries. Use vanilla HTML, CSS, and JavaScript as much as possible. Images are not uploaded anywhere and metadata is stored in a local SQLite database.
```

Like `/spec-kitty.specify`, the planner asks **one question at a time** and blocks with `WAITING_FOR_PLANNING_INPUT` until tech stack, architecture, and operational constraints are confirmed in an Engineering Alignment summary.

### 5. Break down into tasks & prompts

Use **`/spec-kitty.tasks`** to create an actionable task list *and* the matching prompt files for your mini-kanban board. The command writes `tasks.md`, groups subtasks into up to ten work packages, generates one prompt file per package under `/tasks/planned/`, and links each work package to its bundled brief.

```bash
/spec-kitty.tasks
```

### 6. Execute implementation

Use **`/spec-kitty.implement`** to pick up a prompt from `/tasks/planned/`, move it to `/tasks/doing/`, and build the feature according to the plan.

```bash
/spec-kitty.implement
```

**Mandatory workflow initialization:** Before coding begins, the command enforces the kanban workflow by moving prompts to `/tasks/doing/`, updating frontmatter metadata (`lane`, `agent`, `shell_pid`), adding activity log entries, and committing the transition. After implementation completes, prompts move to `/tasks/for_review/` with completion metadata.

### 7. Review & close tasks

Finish the cycle by running **`/spec-kitty.review`** to process files in `/tasks/for_review/`, capture feedback, and move approved work to `/tasks/done/` while marking the task complete in `tasks.md`.

```bash
/spec-kitty.review
```

For detailed step-by-step instructions, see our [comprehensive guide](./spec-driven.md).

## 🔍 Spec-Kitty vs. Other Spec-Driven Tools

| Capability | Spec Kitty | Other SDD Toolkits |
|------------|-----------|---------------------|
| Real-time kanban dashboard with agent telemetry | ✅ Built-in dashboard with lane automation | ⚠️ Often requires third-party integrations |
| AI discovery interview gates (`WAITING_FOR_*_INPUT`) | ✅ Mandatory across spec, plan, tasks | ⚠️ Frequently optional or absent |
| Worktree-aware prompt generation | ✅ Prompts align with git worktrees and task lanes | ❌ Typically manual setup |
| Multi-agent orchestration playbooks | ✅ Bundled docs + scripts for coordination | ⚠️ Sparse or ad-hoc guidance |
| Agent-specific command scaffolding (Claude, Gemini, Cursor, etc.) | ✅ Generated during `spec-kitty init` | ⚠️ Usually limited to one assistant |
| Specification, plan, tasks, and merge automation | ✅ End-to-end command suite | ⚠️ Partial coverage |

## 📦 Examples

We maintain real-world playbooks under [`examples/`](examples):

- [`multi-agent-feature-development.md`](examples/multi-agent-feature-development.md) – orchestrate large agent squads on a single feature.
- [`parallel-implementation-tracking.md`](examples/parallel-implementation-tracking.md) – monitor parallel delivery with dashboard metrics.
- [`dashboard-driven-development.md`](examples/dashboard-driven-development.md) – run a product trio from the kanban dashboard.
- [`claude-cursor-collaboration.md`](examples/claude-cursor-collaboration.md) – blend Claude and Cursor within the Spec Kitty workflow.

## 🤖 Supported AI Agents

| Agent                                                     | Support | Notes                                             |
|-----------------------------------------------------------|---------|---------------------------------------------------|
| [Claude Code](https://www.anthropic.com/claude-code)      | ✅ |                                                   |
| [GitHub Copilot](https://code.visualstudio.com/)          | ✅ |                                                   |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | ✅ |                                                   |
| [Cursor](https://cursor.sh/)                              | ✅ |                                                   |
| [Qwen Code](https://github.com/QwenLM/qwen-code)          | ✅ |                                                   |
| [opencode](https://opencode.ai/)                          | ✅ |                                                   |
| [Windsurf](https://windsurf.com/)                         | ✅ |                                                   |
| [Kilo Code](https://github.com/Kilo-Org/kilocode)         | ✅ |                                                   |
| [Auggie CLI](https://docs.augmentcode.com/cli/overview)   | ✅ |                                                   |
| [Roo Code](https://roocode.com/)                          | ✅ |                                                   |
| [Codex CLI](https://github.com/openai/codex)              | ✅ |                                                   |
| [Amazon Q Developer CLI](https://aws.amazon.com/developer/learning/q-developer-cli/) | ⚠️ | Amazon Q Developer CLI [does not support](https://github.com/aws/amazon-q-developer-cli/issues/3064) custom arguments for slash commands. |

## 🔧 Spec Kitty CLI Reference

The `spec-kitty` command supports the following options. Every run begins with a discovery interview, so be prepared to answer follow-up questions before files are touched.

### Commands

| Command     | Description                                                    |
|-------------|----------------------------------------------------------------|
| `init`      | Initialize a new Spec Kitty project from the latest template      |
| `research`  | Scaffold Phase 0 research artifacts (`research.md`, `data-model.md`, CSV logs) |
| `check`     | Check for installed tools (`git`, `claude`, `gemini`, `code`/`code-insiders`, `cursor-agent`, `windsurf`, `qwen`, `opencode`, `codex`) |

### `spec-kitty init` Arguments & Options

| Argument/Option        | Type     | Description                                                                  |
|------------------------|----------|------------------------------------------------------------------------------|
| `<project-name>`       | Argument | Name for your new project directory (optional if using `--here`, or use `.` for current directory) |
| `--ai`                 | Option   | AI assistant to use: `claude`, `gemini`, `copilot`, `cursor`, `qwen`, `opencode`, `codex`, `windsurf`, `kilocode`, `auggie`, `roo`, or `q` |
| `--script`             | Option   | Script variant to use: `sh` (bash/zsh) or `ps` (PowerShell)                 |
| `--mission`            | Option   | Mission key to seed templates (`software-dev`, `research`, ...)             |
| `--ignore-agent-tools` | Flag     | Skip checks for AI agent tools like Claude Code                             |
| `--no-git`             | Flag     | Skip git repository initialization                                          |
| `--here`               | Flag     | Initialize project in the current directory instead of creating a new one   |
| `--force`              | Flag     | Force merge/overwrite when initializing in current directory (skip confirmation) |
| `--skip-tls`           | Flag     | Skip SSL/TLS verification (not recommended)                                 |
| `--debug`              | Flag     | Enable detailed debug output for troubleshooting                            |
| `--github-token`       | Option   | GitHub token for API requests (or set GH_TOKEN/GITHUB_TOKEN env variable)  |

If you omit `--mission`, the CLI will prompt you to pick one during `spec-kitty init`.

### Examples

```bash
# Basic project initialization
spec-kitty init my-project

# Initialize with specific AI assistant
spec-kitty init my-project --ai claude

# Initialize with the Deep Research mission
spec-kitty init my-project --mission research

# Initialize with Cursor support
spec-kitty init my-project --ai cursor

# Initialize with Windsurf support
spec-kitty init my-project --ai windsurf

# Initialize with PowerShell scripts (Windows/cross-platform)
spec-kitty init my-project --ai copilot --script ps

# Initialize in current directory
spec-kitty init . --ai copilot
# or use the --here flag
spec-kitty init --here --ai copilot

# Force merge into current (non-empty) directory without confirmation
spec-kitty init . --force --ai copilot
# or 
spec-kitty init --here --force --ai copilot

# Skip git initialization
spec-kitty init my-project --ai gemini --no-git

# Enable debug output for troubleshooting
spec-kitty init my-project --ai claude --debug

# Use GitHub token for API requests (helpful for corporate environments)
spec-kitty init my-project --ai claude --github-token ghp_your_token_here

# Check system requirements
spec-kitty check
```

### Available Slash Commands

After running `spec-kitty init`, your AI coding agent will have access to these slash commands for structured development:

#### Core Commands

Essential commands for the Spec-Driven Development workflow:

| Command                  | Description                                                           |
|--------------------------|-----------------------------------------------------------------------|
| `/spec-kitty.dashboard`     | Open the real-time kanban dashboard in your browser                   |
| `/spec-kitty.constitution`  | Create or update project governing principles and development guidelines |
| `/spec-kitty.specify`       | Define what you want to build (requirements and user stories)        |
| `/spec-kitty.plan`          | Create technical implementation plans with your chosen tech stack     |
| `/spec-kitty.research`      | Run Phase 0 research scaffolding to populate research.md, data-model.md, and evidence logs |
| `/spec-kitty.tasks`         | Generate actionable task lists and kanban-ready prompt files          |
| `/spec-kitty.implement`     | Execute tasks by working from `/tasks/doing/` prompts                 |
| `/spec-kitty.review`        | Review work in `/tasks/for_review/` and move finished prompts to `/tasks/done/` |
| `/spec-kitty.accept`        | Run final acceptance checks, record metadata, and verify feature complete |
| `/spec-kitty.merge`         | Merge feature into main branch and clean up worktree                  |

#### Optional Commands

Additional commands for enhanced quality and validation:

| Command              | Description                                                           |
|----------------------|-----------------------------------------------------------------------|
| `/spec-kitty.clarify`   | Clarify underspecified areas (recommended before `/spec-kitty.plan`; formerly `/quizme`) |
| `/spec-kitty.analyze`   | Cross-artifact consistency & coverage analysis (run after `/spec-kitty.tasks`, before `/spec-kitty.implement`) |
| `/spec-kitty.checklist` | Generate custom quality checklists that validate requirements completeness, clarity, and consistency (like "unit tests for English") |

## Worktree Strategy

Spec Kitty uses an **opinionated worktree approach** for parallel feature development:

### The Pattern
```
my-project/                    # Main repo (main branch)
├── .worktrees/
│   ├── 001-auth-system/      # Feature 1 worktree (isolated sandbox)
│   ├── 002-dashboard/        # Feature 2 worktree (work in parallel)
│   └── 003-notifications/    # Feature 3 worktree (no branch switching)
├── .kittify/
├── kitty-specs/
└── ... (main branch files)
```

### The Rules
1. **Main branch** stays in the primary repo root
2. **Feature branches** live in `.worktrees/<feature-slug>/`
3. **Work on features** happens in their worktrees (complete isolation)
4. **No branch switching** in main repo - just `cd` between worktrees
5. **Automatic cleanup** - worktrees removed after merge

### The Complete Workflow
```bash
# Start in main repo
/spec-kitty.specify          # Creates branch + worktree
cd .worktrees/001-my-feature # Enter isolated sandbox
/spec-kitty.constitution     # (first time only)
/spec-kitty.plan
/spec-kitty.research
/spec-kitty.tasks
/spec-kitty.implement
/spec-kitty.review
/spec-kitty.accept           # Verify feature complete
/spec-kitty.merge --push     # Merge to main + cleanup
# Back in main repo, ready for next feature!
```

## Feature Acceptance & Merge Workflow

### Step 1: Accept
Once every work package lives in `tasks/done/`, verify the feature is ready:

```bash
/spec-kitty.accept
```

The accept command:
- Verifies kanban lanes, frontmatter metadata, activity logs, `tasks.md`, and required spec artifacts
- Records acceptance metadata in `kitty-specs/<feature>/meta.json`
- Creates an acceptance commit
- Confirms the feature is ready to merge

### Step 2: Merge
After acceptance checks pass, integrate the feature:

```bash
/spec-kitty.merge --push
```

The merge command:
- Switches to main branch
- Pulls latest changes
- Merges your feature (creates merge commit by default)
- Pushes to origin (if `--push` specified)
- Removes the feature worktree
- Deletes the feature branch

**Merge strategies:**
```bash
# Default: merge commit (preserves history)
/spec-kitty.merge --push

# Squash: single commit (cleaner history)
/spec-kitty.merge --strategy squash --push

# Keep branch for reference
/spec-kitty.merge --keep-branch --push

# Dry run to see what will happen
/spec-kitty.merge --dry-run
```

## Task Workflow Automation

- `scripts/bash/move-task-to-doing.sh WP01 kitty-specs/FEATURE` – moves a work-package prompt from `tasks/planned/` to `tasks/doing/`, updates frontmatter (lane, agent, shell PID), appends an Activity Log entry, and prints the canonical location.
- `scripts/bash/validate-task-workflow.sh WP01 kitty-specs/FEATURE` – blocks implementation if the work-package prompt is not in the `doing` lane or is missing required metadata.
- Work-package IDs follow the pattern `WPxx` and reference bundled subtasks (`Txxx`) listed in `tasks.md`.
- Optional git hook: `ln -s ../../scripts/git-hooks/pre-commit-task-workflow.sh .git/hooks/pre-commit` to enforce lane metadata before every commit.
- Prefer running scripts from the feature worktree (`.worktrees/<feature-slug>`). After `/spec-kitty.specify`, `cd .worktrees/<feature-slug>` when that directory exists; if worktree creation was skipped, stay in the primary checkout on the feature branch or recreate the worktree with `git worktree add …`.

## 🧭 Mission System

Spec Kitty now supports **missions**: curated bundles of templates, commands, and guardrails for different domains. Two missions ship out of the box:

- **Software Dev Kitty** – the original Spec-Driven Development workflow for shipping application features (default).
- **Deep Research Kitty** – a methodology-focused workflow for evidence gathering, analysis, and synthesis.

Each mission lives under `.kittify/missions/<mission-key>/` and provides:

- Mission-specific templates (`spec-template.md`, `plan-template.md`, `tasks-template.md`, etc.).
- Command guidance tuned to the domain (`specify`, `plan`, `tasks`, `implement`, `review`, `accept`).
- Optional constitutions or constitutions to bias the agent toward best practices.

Use the new CLI group to manage missions inside a project:

```bash
spec-kitty mission list        # Show available missions and the active one
spec-kitty mission current     # Display summary for the active mission
spec-kitty mission switch research   # Point the project at Deep Research Kitty
spec-kitty mission info research     # Inspect templates, phases, and artifacts
```

When you switch missions the CLI updates `.kittify/active-mission`, and subsequent commands (spec, plan, tasks, etc.) pull templates from that mission. Plan accordingly—artifact names can differ (e.g., research missions expect `findings.md`).

### Environment Variables

| Variable         | Description                                                                                    |
|------------------|------------------------------------------------------------------------------------------------|
| `SPECIFY_FEATURE` | Override feature detection for non-Git repositories. Set to the feature directory name (e.g., `001-photo-albums`) to work on a specific feature when not using Git branches.<br/>**Must be set in the context of the agent you're working with prior to using `/spec-kitty.plan` or follow-up commands. |
| `SPEC_KITTY_TEMPLATE_ROOT` | Optional. Point to a local checkout whose `templates/`, `scripts/`, and `memory/` directories should seed new projects (handy while developing Spec Kitty itself). |
| `SPECIFY_TEMPLATE_REPO` | Optional. Override the GitHub repository slug (`owner/name`) to fetch templates from when you explicitly want a remote source. |

### Codex CLI: Automatically Load Project Prompts (Linux, macOS, WSL)

The Codex CLI only discovers Spec Kitty command prompts when the `CODEX_HOME` environment variable points to your project’s `.codex/` directory. Without this, Codex falls back to its global prompt store and ignores your Spec Kitty workflow files.

**One-off export**

```bash
export CODEX_HOME="$(pwd)/.codex"
```

Run this in each terminal session before launching Codex if you do not plan to automate the setup.

**Recommended: automate with `direnv`**

`direnv` keeps `CODEX_HOME` in sync automatically whenever you enter the project directory. These steps apply to Linux, macOS, and Windows Subsystem for Linux (WSL):

1. Install `direnv`
   - macOS (Homebrew): `brew install direnv`
   - Debian/Ubuntu/WSL: `sudo apt install direnv`
2. Hook `direnv` into your shell:
   - Bash: add `eval "$(direnv hook bash)"` to `~/.bashrc`
   - Zsh: add `eval "$(direnv hook zsh)"` to `~/.zshrc`
3. In the root of your Spec Kitty project, create `.envrc` containing:

   ```bash
   export CODEX_HOME="$PWD/.codex"
   ```

4. Allow the new configuration once:

   ```bash
   direnv allow
   ```

Each time you `cd` into the project, you should see `direnv: export +CODEX_HOME`, and Codex will pick up the Spec Kitty prompts automatically. Verify with `echo $CODEX_HOME`.

> **Tip:** For shells without `direnv` support (e.g., PowerShell outside WSL), export `CODEX_HOME` through your profile script or set it globally via the operating system’s environment-variable settings.


## 🔧 Prerequisites

- **Linux/macOS** (or WSL2 on Windows)
- AI coding agent: [Claude Code](https://www.anthropic.com/claude-code), [GitHub Copilot](https://code.visualstudio.com/), [Gemini CLI](https://github.com/google-gemini/gemini-cli), [Cursor](https://cursor.sh/), [Qwen CLI](https://github.com/QwenLM/qwen-code), [opencode](https://opencode.ai/), [Codex CLI](https://github.com/openai/codex), [Windsurf](https://windsurf.com/), or [Amazon Q Developer CLI](https://aws.amazon.com/developer/learning/q-developer-cli/)
- [uv](https://docs.astral.sh/uv/) for package management
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

If you encounter issues with an agent, please open an issue so we can refine the integration.

## 🚀 Automated PyPI Releases

Spec Kitty CLI is automatically published to PyPI whenever a new version is tagged. The release pipeline ensures quality through automated validation, testing, and checks before publishing.

**For Users**: Install the latest version from PyPI:
```bash
pip install --upgrade spec-kitty-cli
```

**For Maintainers**: Follow the [Release Readiness Checklist](releases/readiness-checklist.md) to publish a new version:

1. **Prepare Release**: Bump version in `pyproject.toml`, add changelog entry
2. **Validate**: Run `python scripts/release/validate_release.py --mode branch`
3. **Merge PR**: Open PR, ensure all checks pass, merge to `main`
4. **Tag & Publish**: Create tag `git tag vX.Y.Z`, push tag `git push origin vX.Y.Z`
5. **Automated Pipeline**: GitHub Actions builds, validates, and publishes to PyPI automatically

The release workflow enforces:
- ✅ Version bump validation (must be > latest tag)
- ✅ Changelog completeness check
- ✅ Full test suite execution
- ✅ Package metadata validation
- ✅ Secure secret handling (PYPI_API_TOKEN)

See [Release Readiness Checklist](releases/readiness-checklist.md) and [Release Scripts Documentation](../scripts/release/README.md) for details.

## 📖 Learn more

- **[Complete Spec-Driven Development Methodology](./spec-driven.md)** - Deep dive into the full process
- **[Detailed Walkthrough](#-detailed-process)** - Step-by-step implementation guide

---

## 📋 Detailed process

:::details Click to expand the detailed step-by-step walkthrough

You can use the Spec Kitty CLI to bootstrap your project, which will bring in the required artifacts in your environment. Run:

```bash
spec-kitty init <project_name>
```

Or initialize in the current directory:

```bash
spec-kitty init .
# or use the --here flag
spec-kitty init --here
# Skip confirmation when the directory already has files
spec-kitty init . --force
# or
spec-kitty init --here --force
```

You will be prompted to select the AI agent you are using. You can also proactively specify it directly in the terminal:

```bash
spec-kitty init <project_name> --ai claude
spec-kitty init <project_name> --ai gemini
spec-kitty init <project_name> --ai copilot
spec-kitty init <project_name> --ai claude,codex

# Or in current directory:
spec-kitty init . --ai claude
spec-kitty init . --ai codex

# or use --here flag
spec-kitty init --here --ai claude
spec-kitty init --here --ai codex

# Force merge into a non-empty current directory
spec-kitty init . --force --ai claude

# or
spec-kitty init --here --force --ai claude
```

The CLI will check if you have Claude Code, Gemini CLI, Cursor CLI, Qwen CLI, opencode, Codex CLI, or Amazon Q Developer CLI installed. If you do not, or you prefer to get the templates without checking for the right tools, use `--ignore-agent-tools` with your command:

```bash
spec-kitty init <project_name> --ai claude --ignore-agent-tools
```

You can pass multiple assistants at once by comma-separating the values (e.g., `--ai claude,codex`). The generator pulls in the combined commands on a single run so both agents share the same workspace.

### **STEP 1:** Establish project principles

Go to the project folder and run your AI agent. In our example, we're using `claude`.

You will know that things are configured correctly if you see the `/spec-kitty.dashboard`, `/spec-kitty.constitution`, `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks`, `/spec-kitty.implement`, and `/spec-kitty.review` commands available.

The first step should be establishing your project's governing principles using the `/spec-kitty.constitution` command. This helps ensure consistent decision-making throughout all subsequent development phases:

```text
/spec-kitty.constitution Create principles focused on code quality, testing standards, user experience consistency, and performance requirements. Include governance for how these principles should guide technical decisions and implementation choices.
```

This step creates or updates the `.kittify/memory/constitution.md` file with your project's foundational guidelines that the AI agent will reference during specification, planning, and implementation phases.

### **STEP 2:** Create project specifications

With your project principles established, you can now create the functional specifications. Use the `/spec-kitty.specify` command and then provide the concrete requirements for the project you want to develop.

>[!IMPORTANT]
>Be as explicit as possible about _what_ you are trying to build and _why_. **Do not focus on the tech stack at this point**.

An example prompt:

```text
Develop Taskify, a team productivity platform. It should allow users to create projects, add team members,
assign tasks, comment and move tasks between boards in Kanban style. In this initial phase for this feature,
let's call it "Create Taskify," let's have multiple users but the users will be declared ahead of time, predefined.
I want five users in two different categories, one product manager and four engineers. Let's create three
different sample projects. Let's have the standard Kanban columns for the status of each task, such as "To Do,"
"In Progress," "In Review," and "Done." There will be no login for this application as this is just the very
first testing thing to ensure that our basic features are set up. For each task in the UI for a task card,
you should be able to change the current status of the task between the different columns in the Kanban work board.
You should be able to leave an unlimited number of comments for a particular card. You should be able to, from that task
card, assign one of the valid users. When you first launch Taskify, it's going to give you a list of the five users to pick
from. There will be no password required. When you click on a user, you go into the main view, which displays the list of
projects. When you click on a project, you open the Kanban board for that project. You're going to see the columns.
You'll be able to drag and drop cards back and forth between different columns. You will see any cards that are
assigned to you, the currently logged in user, in a different color from all the other ones, so you can quickly
see yours. You can edit any comments that you make, but you can't edit comments that other people made. You can
delete any comments that you made, but you can't delete comments anybody else made.
```

After this prompt is entered, you should see Claude Code kick off the planning and spec drafting process. Claude Code will also trigger some of the built-in scripts to set up the repository.

Once this step is completed, you should have a new branch created (e.g., `001-create-taskify`), as well as a new specification in the `kitty-specs/001-create-taskify` directory.

The produced specification should contain a set of user stories and functional requirements, as defined in the template.

At this stage, your project folder contents should resemble the following:

```text
.
├── .kittify
│   ├── memory
│   │   └── constitution.md
│   ├── scripts
│   │   ├── check-prerequisites.sh
│   │   ├── common.sh
│   │   ├── create-new-feature.sh
│   │   ├── setup-plan.sh
│   │   └── update-claude-md.sh
│   └── templates
│       ├── plan-template.md
│       ├── spec-template.md
│       └── tasks-template.md
└── kitty-specs
    └── 001-create-taskify
        └── spec.md
```

### **STEP 3:** Functional specification clarification (required before planning)

With the baseline specification created, you can go ahead and clarify any of the requirements that were not captured properly within the first shot attempt.

You should run the structured clarification workflow **before** creating a technical plan to reduce rework downstream.

Preferred order:
1. Use `/spec-kitty.clarify` (structured) – sequential, coverage-based questioning that records answers in a Clarifications section.
2. Optionally follow up with ad-hoc free-form refinement if something still feels vague.

If you intentionally want to skip clarification (e.g., spike or exploratory prototype), explicitly state that so the agent doesn't block on missing clarifications.

Example free-form refinement prompt (after `/spec-kitty.clarify` if still needed):

```text
For each sample project or project that you create there should be a variable number of tasks between 5 and 15
tasks for each one randomly distributed into different states of completion. Make sure that there's at least
one task in each stage of completion.
```

You should also ask Claude Code to validate the **Review & Acceptance Checklist**, checking off the things that are validated/pass the requirements, and leave the ones that are not unchecked. The following prompt can be used:

```text
Read the review and acceptance checklist, and check off each item in the checklist if the feature spec meets the criteria. Leave it empty if it does not.
```

It's important to use the interaction with Claude Code as an opportunity to clarify and ask questions around the specification - **do not treat its first attempt as final**.

### **STEP 4:** Generate a plan

You can now be specific about the tech stack and other technical requirements. You can use the `/spec-kitty.plan` command that is built into the project template with a prompt like this:

```text
We are going to generate this using .NET Aspire, using Postgres as the database. The frontend should use
Blazor server with drag-and-drop task boards, real-time updates. There should be a REST API created with a projects API,
tasks API, and a notifications API.
```

The output of this step will include a number of implementation detail documents, with your directory tree resembling this:

```text
.
├── CLAUDE.md
├── memory
│	 └── constitution.md
├── scripts
│	 ├── check-prerequisites.sh
│	 ├── common.sh
│	 ├── create-new-feature.sh
│	 ├── setup-plan.sh
│	 └── update-claude-md.sh
├── specs
│	 └── 001-create-taskify
│	     ├── contracts
│	     │	 ├── api-spec.json
│	     │	 └── signalr-spec.md
│	     ├── data-model.md
│	     ├── plan.md
│	     ├── quickstart.md
│	     ├── research.md
│	     └── spec.md
└── templates
    ├── CLAUDE-template.md
    ├── plan-template.md
    ├── spec-template.md
    └── tasks-template.md
```

Check the `research.md` document to ensure that the right tech stack is used, based on your instructions. You can ask Claude Code to refine it if any of the components stand out, or even have it check the locally-installed version of the platform/framework you want to use (e.g., .NET).

Additionally, you might want to ask Claude Code to research details about the chosen tech stack if it's something that is rapidly changing (e.g., .NET Aspire, JS frameworks), with a prompt like this:

```text
I want you to go through the implementation plan and implementation details, looking for areas that could
benefit from additional research as .NET Aspire is a rapidly changing library. For those areas that you identify that
require further research, I want you to update the research document with additional details about the specific
versions that we are going to be using in this Taskify application and spawn parallel research tasks to clarify
any details using research from the web.
```

During this process, you might find that Claude Code gets stuck researching the wrong thing - you can help nudge it in the right direction with a prompt like this:

```text
I think we need to break this down into a series of steps. First, identify a list of tasks
that you would need to do during implementation that you're not sure of or would benefit
from further research. Write down a list of those tasks. And then for each one of these tasks,
I want you to spin up a separate research task so that the net results is we are researching
all of those very specific tasks in parallel. What I saw you doing was it looks like you were
researching .NET Aspire in general and I don't think that's gonna do much for us in this case.
That's way too untargeted research. The research needs to help you solve a specific targeted question.
```

>[!NOTE]
>Claude Code might be over-eager and add components that you did not ask for. Ask it to clarify the rationale and the source of the change.

### **STEP 5:** Have Claude Code validate the plan

With the plan in place, you should have Claude Code run through it to make sure that there are no missing pieces. You can use a prompt like this:

```text
Now I want you to go and audit the implementation plan and the implementation detail files.
Read through it with an eye on determining whether or not there is a sequence of tasks that you need
to be doing that are obvious from reading this. Because I don't know if there's enough here. For example,
when I look at the core implementation, it would be useful to reference the appropriate places in the implementation
details where it can find the information as it walks through each step in the core implementation or in the refinement.
```

This helps refine the implementation plan and helps you avoid potential blind spots that Claude Code missed in its planning cycle. Once the initial refinement pass is complete, ask Claude Code to go through the checklist once more before you can get to the implementation.

You can also ask Claude Code (if you have the [GitHub CLI](https://docs.github.com/en/github-cli/github-cli) installed) to go ahead and create a pull request from your current branch to `main` with a detailed description, to make sure that the effort is properly tracked.

>[!NOTE]
>Before you have the agent implement it, it's also worth prompting Claude Code to cross-check the details to see if there are any over-engineered pieces (remember - it can be over-eager). If over-engineered components or decisions exist, you can ask Claude Code to resolve them. Ensure that Claude Code follows the [constitution](base/memory/constitution.md) as the foundational piece that it must adhere to when establishing the plan.

### STEP 6: Implementation

Once ready, use the `/spec-kitty.implement` command to execute your implementation plan:

```text
/spec-kitty.implement
```

The `/spec-kitty.implement` command will:
- Validate that all prerequisites are in place (constitution, spec, plan, and tasks)
- Parse the task breakdown from `tasks.md`
- Execute tasks in the correct order, respecting dependencies and parallel execution markers
- Follow the TDD approach defined in your task plan
- Provide progress updates and handle errors appropriately

>[!IMPORTANT]
>The AI agent will execute local CLI commands (such as `dotnet`, `npm`, etc.) - make sure you have the required tools installed on your machine.

Once the implementation is complete, test the application and resolve any runtime errors that may not be visible in CLI logs (e.g., browser console errors). You can copy and paste such errors back to your AI agent for resolution.

:::

---

## 🔍 Troubleshooting

### Git Credential Manager on Linux

If you're having issues with Git authentication on Linux, you can install Git Credential Manager:

```bash
#!/usr/bin/env bash
set -e
echo "Downloading Git Credential Manager v2.6.1..."
wget https://github.com/git-ecosystem/git-credential-manager/releases/download/v2.6.1/gcm-linux_amd64.2.6.1.deb
echo "Installing Git Credential Manager..."
sudo dpkg -i gcm-linux_amd64.2.6.1.deb
echo "Configuring Git to use GCM..."
git config --global credential.helper manager
echo "Cleaning up..."
rm gcm-linux_amd64.2.6.1.deb
```

## 👥 Maintainers

- Robert Douglass ([@robertDouglass](https://github.com/robertDouglass))

## 💬 Support

For support, please open a [GitHub issue](https://github.com/Priivacy-ai/spec-kitty/issues/new). We welcome bug reports, feature requests, and questions about using Spec-Driven Development.

## 🙏 Acknowledgements

This project is heavily influenced by and based on the work and research of [John Lam](https://github.com/jflam).

## 📄 License

This project is licensed under the terms of the MIT open source license. Please refer to the [LICENSE](./LICENSE) file for the full terms.
