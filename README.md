<div align="center">
    <img src="https://github.com/Priivacy-ai/spec-kitty/raw/main/media/logo_small.webp" alt="Spec Kitty Logo"/>
    <h1>Spec Kitty</h1>
    <h2>Spec-Driven Development for AI coding agents</h2>
</div>

Spec Kitty is an open-source CLI workflow for **spec-driven development** with AI coding agents.
It helps teams turn product intent into implementation with a repeatable path:
`spec` -> `plan` -> `tasks` -> `implement` -> `review` -> `merge`.

### Why teams use it

AI coding workflows often break down on larger features:
- Requirements and design decisions drift over long agent sessions
- Parallel work is hard to coordinate across branches
- Review and acceptance criteria become inconsistent from one feature to the next

Spec Kitty addresses this with repository-native artifacts, work package workflows, and lane-aware git worktree isolation.

### Who it's for

- [Project Owners](architecture/audience/external/project-owner.md) who need explicit approval boundaries and outcome accountability
- [External Tech Lead Evaluators](architecture/audience/external/tech-lead-evaluator.md) assessing delivery predictability and adoption fit
- [External Architect Evaluators](architecture/audience/external/architect-evaluator.md) evaluating governance durability and boundary clarity
- [External Product Manager Evaluators](architecture/audience/external/product-manager-evaluator.md) validating intent-to-delivery traceability
- [Lead Developers](architecture/audience/internal/lead-developer.md) coordinating implementation quality and handoffs
- [Maintainers](architecture/audience/internal/maintainer.md) preserving operational consistency across features and agents

### Stakeholder Value Proposition

| Stakeholder Persona | Value Proposition |
|---|---|
| [Project Owner](architecture/audience/external/project-owner.md) | Faster onboarding with explicit governance checkpoints and acceptance accountability |
| [External Tech Lead Evaluator](architecture/audience/external/tech-lead-evaluator.md) | Deterministic, auditable multi-agent workflow with clear lifecycle guardrails |
| [External Architect Evaluator](architecture/audience/external/architect-evaluator.md) | C4 + ADR traceability with explicit host authority and integration boundaries |
| [External Product Manager Evaluator](architecture/audience/external/product-manager-evaluator.md) | Clear intent-to-artifact mapping and lower handoff ambiguity between product and engineering |
| [Lead Developer](architecture/audience/internal/lead-developer.md) | Structured work package flow, quality gates, and review-ready evidence trails |
| [Maintainer](architecture/audience/internal/maintainer.md) | Stable operational model with bounded external integrations and trackable state transitions |

**Try it now:** `pip install spec-kitty-cli && spec-kitty init my-project --ai claude`

---

## 🚀 What You Get in 2.1.x

| Capability | What Spec Kitty provides |
|------------|--------------------------|
| **Spec-driven artifacts** | Generates and maintains `spec.md`, `plan.md`, and `tasks.md` in `kitty-specs/<feature>/` |
| **Work package execution** | Uses canonical 2.x lifecycle lanes (`planned`, `claimed`, `in_progress`, `for_review`, `done`, `blocked`, `canceled`) with `doing` as UI alias for `in_progress` |
| **Parallel implementation model** | Creates isolated git worktrees under `.worktrees/`; lane-based features share a worktree per execution lane and legacy features may still use one worktree per work package |
| **Live project visibility** | Local dashboard for kanban and feature progress (`spec-kitty dashboard`) |
| **Acceptance + merge workflow** | Built-in acceptance checks and merge helpers (`spec-kitty accept`, `spec-kitty merge`) |
| **Multi-agent support** | Template and command generation for 12 AI agent integrations |

<p align="center">
    <a href="#-getting-started-complete-workflow">Quick Start</a> •
    <a href="docs/tutorials/claude-code-integration.md"><strong>Claude Code Guide</strong></a> •
    <a href="#-real-time-dashboard">Live Dashboard</a> •
    <a href="#-supported-ai-agents">12 AI Agents</a> •
    <a href="https://github.com/Priivacy-ai/spec-kitty/blob/main/spec-driven.md">Full Docs</a>
</p>

### From Idea to Production in 6 Automated Steps

```mermaid
graph LR
    A[📝 Specify<br/>WHAT to build] --> B[🎯 Plan<br/>HOW to build]
    B --> C[📋 Tasks<br/>Work packages]
    C --> D[⚡ Implement<br/>Agent workflows]
    D --> E[🔍 Review<br/>Quality gates]
    E --> F[🚀 Merge<br/>Ship it]

    style A fill:#e1f5ff
    style B fill:#e1f5ff
    style C fill:#fff3e0
    style D fill:#f3e5f5
    style E fill:#e8f5e9
    style F fill:#fce4ec
```

---

## 📊 Project Snapshot

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/Priivacy-ai/spec-kitty?style=for-the-badge&logo=github)](https://github.com/Priivacy-ai/spec-kitty/stargazers)
[![PyPI version](https://img.shields.io/pypi/v/spec-kitty-cli?style=for-the-badge&logo=pypi)](https://pypi.org/project/spec-kitty-cli/)
[![Downloads](https://img.shields.io/pypi/dm/spec-kitty-cli?style=for-the-badge&logo=pypi)](https://pypi.org/project/spec-kitty-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge)](https://www.python.org/downloads/)

[![AI Tools](https://img.shields.io/badge/AI_Tools-12_Supported-brightgreen?style=for-the-badge)](#-supported-ai-tools)
[![Dashboard](https://img.shields.io/badge/Dashboard-Kanban-orange?style=for-the-badge)](#-real-time-dashboard)
[![Workflow](https://img.shields.io/badge/Workflow-Spec--Plan--Tasks-6c757d?style=for-the-badge)](#-getting-started-complete-workflow)

</div>

**Current stable release line:** `v3.0.1` (`main`, GitHub Releases, and PyPI)

**3.0.1 highlights:**
- Canonical status hard cutover completed: active runtime paths no longer fall back to WP frontmatter lane state
- `finalize-tasks` bootstraps canonical `planned` state for generated work packages
- Release automation and maintainer tooling now accept semantic `vX.Y.Z` tags for 3.x publishing

**3.0.0 highlights:**
- Event log is now the sole authority for mutable work-package status
- Explicit feature targeting, MissionContext identity, and ownership manifests land on the 3.x stable line
- Sparse checkout is removed in favor of in-repo planning artifacts and standard worktrees

**Jump to:**
[Getting Started](#-getting-started-complete-workflow) •
[Examples](#-examples) •
[12 AI Tools](#-supported-ai-tools) •
[CLI Reference](#-spec-kitty-cli-reference) •
[Worktrees](#-worktree-strategy) •
[Troubleshooting](#-troubleshooting)

---

## 📌 Release Track

Spec Kitty now uses `main` as the stable `3.x` release line.
The former `1.x` line is deprecated and moves to `1.x-maintenance` for maintenance-only fixes.

| Branch | Version | Status | Install |
|--------|---------|--------|---------|
| **main** | **3.0.x** | Current stable line | `pip install spec-kitty-cli` |
| **1.x-maintenance** | **1.x** | Deprecated, maintenance-only | Install from a pinned maintenance tag or source checkout |

**For users:** install the stable line from PyPI with `pip install spec-kitty-cli`.
**For existing 1.x or 2.x users:** migrate to `3.0.x` where possible; `1.x-maintenance` is only for critical maintenance and will no longer publish new PyPI releases.

---

## 🤝 Multi-Agent Coordination for AI Coding

Run multi-agent delivery with an external orchestrator while keeping workflow state and guardrails in `spec-kitty`. Core CLI orchestration is exposed as `spec-kitty orchestrator-api`; there is no in-core `spec-kitty orchestrate` shim.

Terminology note:
- `Mission Type` = reusable blueprint
- `Mission` = concrete tracked item
- `Mission Run` = runtime/session instance
- `--feature` and commands such as `accept-feature` remain legacy software-dev compatibility surfaces for the tracked mission

```bash
# Verify host contract
spec-kitty orchestrator-api contract-version --json

# Use the reference external orchestrator
spec-kitty-orchestrator orchestrate --feature 034-my-feature --dry-run
spec-kitty-orchestrator orchestrate --feature 034-my-feature
```

Docs:
- External provider runbook: [`docs/how-to/run-external-orchestrator.md`](docs/how-to/run-external-orchestrator.md)
- Custom provider guide: [`docs/how-to/build-custom-orchestrator.md`](docs/how-to/build-custom-orchestrator.md)

```mermaid
sequenceDiagram
    participant Lead as 👨‍💼 Lead Architect
    participant Claude as 🤖 Claude (Spec)
    participant Cursor as 🤖 Cursor (Impl)
    participant Gemini as 🤖 Gemini (Review)
    participant Dashboard as 📊 Live Kanban

    Lead->>Claude: /spec-kitty.specify
    Claude->>Dashboard: WP01-WP05 (planned)

    par Parallel Work
        Lead->>Cursor: implement WP01
        Lead->>Cursor: implement WP02
    end

    Cursor->>Dashboard: WP01 → in_progress (Doing)
    Cursor->>Dashboard: WP01 → for_review
    Lead->>Gemini: /spec-kitty.review WP01
    Gemini->>Dashboard: WP01 → done

    Note over Dashboard: Real-time updates<br/>No branch switching
```

**Key Benefits:**
- 🔀 **Parallel execution** - Multiple WPs simultaneously
- 🌳 **Worktree isolation** - Lane-based features reuse shared lane worktrees; legacy features still isolate one workspace per WP
- 👀 **Full visibility** - Dashboard shows who's doing what
- 🔒 **Security boundary** - Orchestration policy and transitions are validated at the host API boundary

---

## 📊 Real-Time Dashboard

Spec Kitty includes a **live dashboard** that automatically tracks your feature development progress. View your kanban board, monitor work package status, and see which agents are working on what—all updating in real-time as you work.

<div align="center">
  <img src="https://github.com/Priivacy-ai/spec-kitty/raw/main/media/dashboard-kanban.png" alt="Spec Kitty Dashboard - Kanban Board View" width="800"/>
  <p><em>Kanban board showing work packages across all lanes with agent assignments</em></p>
</div>

<div align="center">
  <img src="https://github.com/Priivacy-ai/spec-kitty/raw/main/media/dashboard-overview.png" alt="Spec Kitty Dashboard - Feature Overview" width="800"/>
  <p><em>Feature overview with completion metrics and available artifacts</em></p>
</div>

The dashboard starts automatically when you run `spec-kitty init` and runs in the background. Access it anytime with the `/spec-kitty.dashboard` command or `spec-kitty dashboard`—the CLI will start the correct project dashboard automatically if it isn't already running, let you request a specific port with `--port`, or stop it cleanly with `--kill`.

**Key Features:**
- 📋 **Kanban Board**: Visual workflow across canonical lifecycle lanes (including `blocked` and `canceled`) with `Doing` rendered as `in_progress`
- 📈 **Progress Tracking**: Real-time completion percentages and task counts
- 👥 **Multi-Agent Support**: See which AI agents are working on which tasks
- 📦 **Artifact Status**: Track specification, plan, tasks, and other deliverables
- 🔄 **Live Updates**: Dashboard refreshes automatically as you work

### Kanban Workflow Automation

Work packages flow through automated quality gates using the canonical 2.x lifecycle FSM. Agents move tasks between lanes, and the dashboard tracks state transitions in real-time.

```mermaid
stateDiagram-v2
    [*] --> planned
    planned --> claimed
    claimed --> in_progress
    in_progress --> for_review
    for_review --> done
    for_review --> in_progress: changes requested
    for_review --> planned: replan
    planned --> blocked
    claimed --> blocked
    in_progress --> blocked
    for_review --> blocked
    blocked --> in_progress
    planned --> canceled
    claimed --> canceled
    in_progress --> canceled
    for_review --> canceled
    blocked --> canceled
```

Lane terminology follows the glossary: see
[`glossary/contexts/orchestration.md#lane`](glossary/contexts/orchestration.md#lane).

---

## 🚀 Getting Started: Complete Workflow

**New to Spec Kitty?** Here's the complete lifecycle from zero to shipping features:

### Phase 1: Install & Initialize (Terminal)

```bash
# 1. Install the CLI
pip install spec-kitty-cli
# or
uv tool install spec-kitty-cli

# 2. Initialize your project
spec-kitty init my-project --ai claude

# 3. Verify setup (optional)
cd my-project
spec-kitty verify-setup  # Checks that everything is configured correctly

# 4. View your dashboard
spec-kitty dashboard  # Opens http://localhost:3000-5000
```

**What just happened:**
- ✅ Created `.claude/commands/` (or `.gemini/`, `.cursor/`, etc.) with 13 slash commands
- ✅ Created `.kittify/` directory with scripts, templates, and mission configuration
- ✅ Started real-time kanban dashboard (runs in background)
- ✅ Initialized git repository with proper `.gitignore`

---

<details>
<summary><h2>🔄 Upgrading Existing Projects</h2></summary>

> **Important:** If you've upgraded `spec-kitty-cli` via pip/uv, run `spec-kitty upgrade` in each of your projects to apply structural migrations.

### Quick Upgrade

```bash
cd your-project
spec-kitty upgrade              # Upgrade to current version
```

### What Gets Upgraded

The upgrade command automatically migrates your project structure across versions:

| Version | Migration                                                           |
|---------|---------------------------------------------------------------------|
| **0.10.9** | Repair broken templates with bash script references (#62, #63, #64) |
| **0.10.8** | Move memory/ and AGENTS.md to .kittify/                             |
| **0.10.6** | Simplify implement/review templates to use workflow commands        |
| **0.10.2** | Update slash commands to Python CLI and flat structure              |
| **0.10.0** | **Remove bash scripts, migrate to Python CLI**                      |
| **0.9.1** | Complete lane migration + normalize frontmatter                     |
| **0.9.0** | Flatten task lanes to frontmatter-only (no directory-based lanes)   |
| **0.8.0** | Remove active-mission (missions now per-feature)                    |
| **0.7.3** | Update scripts for worktree feature numbering                       |
| **0.6.7** | Ensure software-dev and research missions present                   |
| **0.6.5** | Rename commands/ → command-templates/                               |
| **0.5.0** | Install encoding validation git hooks                               |
| **0.4.8** | Add all 12 AI agent tooling directories to .gitignore               |
| **0.2.0** | Rename .specify/ → .kittify/ and /specs/ → /kitty-specs/            |

> Run `spec-kitty upgrade --verbose` to see which migrations apply to your project.

### Upgrade Options

```bash
# Preview changes without applying
spec-kitty upgrade --dry-run

# Show detailed migration information
spec-kitty upgrade --verbose

# Upgrade to specific version
spec-kitty upgrade --target 0.6.5

# Skip worktree upgrades (main project only)
spec-kitty upgrade --no-worktrees

# JSON output for CI/CD integration
spec-kitty upgrade --json
```

### When to Upgrade

Run `spec-kitty upgrade` after:
- Installing a new version of `spec-kitty-cli`
- Cloning a project that was created with an older version
- Seeing "Unknown mission" or missing slash commands

The upgrade command is **idempotent** - safe to run multiple times. It automatically detects your project's version and applies only the necessary migrations.

</details>

---

### Phase 2: Start Your AI Agent (Terminal)

```bash
# Launch your chosen AI coding agent
claude   # For Claude Code
# or
gemini   # For Gemini CLI
# or
code     # For GitHub Copilot / Cursor
```

**Verify slash commands loaded:**
Type `/spec-kitty` and you should see autocomplete with all 13 commands.

### Phase 3: Establish Project Principles (In Agent)

**Still in main repo** - Start with your project's governing principles:

```text
/spec-kitty.constitution

Create principles focused on code quality, testing standards,
user experience consistency, and performance requirements.
```

**What this creates:**
- `.kittify/memory/constitution.md` - Your project's architectural DNA
- These principles will guide all subsequent development
- Missions do not have separate constitutions; the project constitution is the single source of truth

### Phase 4: Create Your First Feature (In Agent)

Now begin the feature development cycle:

#### 4a. Define WHAT to Build

```text
/spec-kitty.specify

Build a user authentication system with email/password login,
password reset, and session management. Users should be able to
register, login, logout, and recover forgotten passwords.
```

**What this does:**
- Creates `kitty-specs/001-auth-system/spec.md` with user stories
- **Enters discovery interview** - Answer questions before continuing!
- All planning happens in the main repo (worktrees created later during implementation)

**⚠️ Important:** Continue in the same session - no need to change directories!

#### 4b. Define HOW to Build (In Main Repo)

```text
/spec-kitty.plan

Use Python FastAPI for backend, PostgreSQL for database,
JWT tokens for sessions, bcrypt for password hashing,
SendGrid for email delivery.
```

**What this creates:**
- `kitty-specs/001-auth-system/plan.md` - Technical architecture
- `kitty-specs/001-auth-system/data-model.md` - Database schema
- `kitty-specs/001-auth-system/contracts/` - API specifications
- **Enters planning interview** - Answer architecture questions!

#### 4c. Optional: Research Phase

```text
/spec-kitty.research

Investigate best practices for password reset token expiration,
JWT refresh token rotation, and rate limiting for auth endpoints.
```

**What this creates:**
- `kitty-specs/001-auth-system/research.md` - Research findings
- Evidence logs for decisions made

#### 4d. Break Down Into Tasks

```text
/spec-kitty.tasks
```

**What this creates:**
- `kitty-specs/001-auth-system/tasks.md` - Kanban checklist
- `kitty-specs/001-auth-system/tasks/WP01.md` - Work package prompts (flat structure)
- Up to 10 work packages ready for implementation

**Check your dashboard:** You'll now see tasks in the `planned` lane.

### Phase 5: Implement Features (In Execution Workspace)

#### 5a. Execute Implementation

```text
/spec-kitty.implement
```

**What this does:**
- Auto-detects first WP with `lane: "planned"` (or specify WP ID)
- Automatically advances toward `lane: "in_progress"` (displayed as "Doing") and shows the prompt
- Shows clear "WHEN YOU'RE DONE" instructions
- Agent implements, then runs command to move to `lane: "for_review"`

**Repeat** until all work packages are done!

#### 5b. Review Completed Work

```text
/spec-kitty.review
```

**What this does:**
- Auto-detects first WP with `lane: "for_review"` (or specify WP ID)
- Moves review execution to `lane: "in_progress"` (displayed as "Doing") and shows the prompt
- Agent reviews code and provides feedback or approval
- Shows commands to move to `lane: "done"` (passed) or `lane: "planned"` (changes needed)

### Phase 6: Accept & Merge

#### 6a. Validate Feature Complete

```text
/spec-kitty.accept
```

**What this does:**
- Verifies all WPs have `lane: "done"`
- Checks metadata and activity logs
- Confirms no `NEEDS CLARIFICATION` markers remain
- Records acceptance timestamp

#### 6b. Merge to Main

```text
/spec-kitty.merge --push
```

**What this does:**
- Switches to main branch
- Merges feature branch
- Pushes to remote (if `--push` specified)
- Cleans up worktree
- Deletes feature branch

**🎉 Feature complete!** Return to main repo and start your next feature with `/spec-kitty.specify`

---

## 📋 Quick Reference: Command Order

### Required Workflow (Once per project)
```
1️⃣  /spec-kitty.constitution     → In main repo (sets project principles)
```

### Required Workflow (Each feature)
```
2️⃣  /spec-kitty.specify          → Create spec (in main repo)
3️⃣  /spec-kitty.plan             → Define technical approach (in main repo)
4️⃣  /spec-kitty.tasks            → Generate work packages (in main repo)
5️⃣  spec-kitty implement WP01    → Create or reuse the execution workspace for WP01
    /spec-kitty.implement        → Build the work package
6️⃣  /spec-kitty.review           → Review completed work
7️⃣  /spec-kitty.accept           → Validate feature ready
8️⃣  /spec-kitty.merge            → Merge to main + cleanup
```

### Optional Enhancement Commands
```
/spec-kitty.research   → After /plan: Investigate technical decisions
/spec-kitty.analyze    → After /tasks: Cross-artifact consistency check
/spec-kitty.checklist  → Anytime: Generate custom quality checklists
/spec-kitty.dashboard  → Anytime: Open/restart the kanban dashboard
```

---

## 🔒 Agent Directory Best Practices

**Important**: Agent directories (`.claude/`, `.codex/`, `.gemini/`, etc.) should **NEVER** be committed to git.

### Why?

These directories may contain:
- Authentication tokens and API keys
- User-specific credentials (auth.json)
- Session data and conversation history

### Automatic Protection

Spec Kitty automatically protects you with multiple layers:

**During `spec-kitty init`:**
- ✅ Adds all 12 agent directories to `.gitignore`
- ✅ Creates `.claudeignore` to optimize AI scanning (excludes `.kittify/` templates)

**Worktree Constitution Sharing:**
When creating execution workspaces, Spec Kitty uses symlinks to share the constitution:
```
.worktrees/001-feature-lane-a/.kittify/memory -> ../../../../.kittify/memory
```
This ensures all work packages follow the same project principles.

### What Gets Committed?

✅ **DO commit:**
- `.kittify/templates/` - Command templates (source)
- `.kittify/missions/` - Mission workflows
- `.kittify/memory/constitution.md` - Project principles
- `.gitignore` - Protection rules

❌ **NEVER commit:**
- `.claude/`, `.gemini/`, `.cursor/`, etc. - Agent runtime directories
- Any `auth.json` or credentials files

See [AGENTS.md](.kittify/AGENTS.md) for complete guidelines.

---

<details>
<summary><h2>📚 Terminology</h2></summary>

Spec Kitty differentiates between the **project** that holds your entire codebase, the **features** you build within that project, and the **mission** that defines your workflow. Use these definitions whenever you write docs, prompts, or help text.

For glossary-first terminology (including semantic-integrity rules), see [`glossary/README.md`](glossary/README.md).

### Project
**Definition**: The entire codebase (one Git repository) that contains all missions, features, and `.kittify/` automation.

**Examples**:
- "spec-kitty project" (this repository)
- "priivacy_rust project"
- "my-agency-portal project"

**Usage**: Projects are initialized once with `spec-kitty init`. A project contains:
- One active mission at a time
- Multiple features (each with its own spec/plan/tasks)
- Shared automation under `.kittify/`

**Commands**: Initialize with `spec-kitty init` for the current directory by default (or pass `spec-kitty init my-project` to create a project directory).

---

### Feature
**Definition**: A single unit of work tracked by Spec Kitty. Every feature has its own spec, plan, tasks, and one or more execution worktrees.

**Examples**:
- "001-auth-system feature"
- "005-refactor-mission-system feature" (this document)
- "042-dashboard-refresh feature"

**Structure**:
- Specification: `/kitty-specs/###-feature-name/spec.md`
- Plan: `/kitty-specs/###-feature-name/plan.md`
- Tasks: `/kitty-specs/###-feature-name/tasks.md`
- Implementation: `.worktrees/###-feature-name-lane-a/` (modern lane-based features) or `.worktrees/###-feature-name-WP01/` (legacy fallback)

**Lifecycle**:
1. `/spec-kitty.specify` – Create the feature and its branch
2. `/spec-kitty.plan` – Document the technical design
3. `/spec-kitty.tasks` – Break work into packages
4. `/spec-kitty.implement` – Build the feature inside the execution workspace printed by Spec Kitty
5. `/spec-kitty.review` – Peer review
6. `/spec-kitty.accept` – Validate according to gates
7. `/spec-kitty.merge` – Merge and clean up

**Commands**: Always create features with `/spec-kitty.specify`.

**Compatibility note**: In current 2.x, feature slugs remain the practical artifact key for `kitty-specs/` and worktrees.

---

### Mission
**Definition**: A domain adapter that configures Spec Kitty (workflows, templates, validation). Missions are project-wide; all features in a project share the same active mission.

**Examples**:
- "software-dev mission" (ship software with TDD)
- "research mission" (conduct systematic investigations)
- "writing mission" (future workflow)

**What missions define**:
- Workflow phases (e.g., design → implement vs. question → gather findings)
- Templates (spec, plan, tasks, prompts)
- Validation rules (tests pass vs. citations documented)
- Path conventions (e.g., `src/` vs. `research/`)

**Scope**: Entire project. In current 2.x, mission is selected at init and remains fixed for the project lifecycle.

**Runtime note**: Mission-run identity (`mission_id` / `mission_run_id`) is the preferred runtime collaboration scope when available.

**Commands**:
- Select at init: `spec-kitty init my-project --mission research`
- Inspect: `spec-kitty mission current` / `spec-kitty mission list`

---

### Quick Reference

| Term | Scope | Example | Key Command |
|------|-------|---------|-------------|
| **Project** | Entire codebase | "spec-kitty project" | `spec-kitty init my-project` |
| **Feature** | Unit of work | "001-auth-system feature" | `/spec-kitty.specify "auth system"` |
| **Mission** | Workflow adapter | "research mission" | `spec-kitty init --mission research` |

### Common Questions

**Q: What's the difference between a project and a feature?**  
A project is your entire git repository. A feature is one unit of work inside that project with its own spec/plan/tasks.

**Q: Can I have multiple missions in one project?**  
Only one mission is active at a time in current 2.x. Select it during `spec-kitty init`.

**Q: Should I create a new project for every feature?**  
No. Initialize a project once, then create as many features as you need with `/spec-kitty.specify`.

**Q: What's a task?**
Tasks (T001, T002, etc.) are subtasks within a feature's work packages. They are **not** separate features or projects.

</details>

---

## 📦 Examples

Learn from real-world workflows used by teams building production software with AI agents. Each playbook demonstrates specific coordination patterns and best practices:

### Featured Workflows

- **[Multi-Agent Feature Development](https://github.com/Priivacy-ai/spec-kitty/blob/main/examples/multi-agent-feature-development.md)**
  *Coordinate 3-5 AI agents on a single large feature using an external orchestrator plus host API*

- **[Parallel Implementation Tracking](https://github.com/Priivacy-ai/spec-kitty/blob/main/examples/parallel-implementation-tracking.md)**
  *Monitor multiple teams/agents delivering features simultaneously with dashboard metrics*

- **[Dashboard-Driven Development](https://github.com/Priivacy-ai/spec-kitty/blob/main/examples/dashboard-driven-development.md)**
  *Product trio workflow: PM + Designer + Engineers using live kanban visibility*

- **[Claude + Cursor Collaboration](https://github.com/Priivacy-ai/spec-kitty/blob/main/examples/claude-cursor-collaboration.md)**
  *Blend different AI agents within a single spec-driven workflow*

### More Examples

Browse our [examples directory](https://github.com/Priivacy-ai/spec-kitty/tree/main/examples) for additional workflows including:
- Agency client transparency workflows
- Solo developer productivity patterns
- Enterprise parallel development
- Research mission templates

## 🤖 Supported AI Tools

| Tool                                                      | Support | Notes                                             |
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

<details>
<summary><h2>🔧 Spec Kitty CLI Reference</h2></summary>

The `spec-kitty` command supports the following options. Every run begins with a discovery interview, so be prepared to answer follow-up questions before files are touched.

### Commands

| Command     | Description                                                    |
|-------------|----------------------------------------------------------------|
| `init`      | Initialize a new Spec Kitty project from templates |
| `upgrade`   | **Upgrade project structure to current version** (run after updating spec-kitty-cli) |
| `repair`    | **Repair broken template installations** (fixes bash script references from v0.10.0-0.10.8) |
| `accept`    | Validate mission readiness before merging to main |
| `check`     | Check that required tooling is available |
| `dashboard` | Open or stop the Spec Kitty dashboard |
| `diagnostics` | Show project health and diagnostics information |
| `merge`     | Merge a completed feature branch into main and clean up resources |
| `orchestrator-api` | Host contract for external orchestrators (JSON envelope interface) |
| `research`  | Execute Phase 0 research workflow to scaffold artifacts |
| `verify-setup` | Verify that the current environment matches Spec Kitty expectations |

### `spec-kitty init` Arguments & Options

| Argument/Option        | Type     | Description                                                                  |
|------------------------|----------|------------------------------------------------------------------------------|
| `<project-name>`       | Argument | Name for your new project directory (omit to initialize in the current directory, same as `--here`) |
| `--ai`                 | Option   | AI assistant to use: `claude`, `gemini`, `copilot`, `cursor`, `qwen`, `opencode`, `codex`, `windsurf`, `kilocode`, `auggie`, `roo`, or `q` |
| `--script`             | Option   | (Deprecated in v0.10.0) Script variant - all commands now use Python CLI     |
| `--mission`            | Option   | Mission type key to seed templates (`software-dev`, `research`, ...)        |
| `--template-root`      | Option   | Override template location (useful for development mode or custom sources)   |
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
# Basic initialization in current directory (default)
spec-kitty init --ai claude

# Basic project initialization in a new directory
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

# Use custom template location (development mode)
spec-kitty init my-project --ai claude --template-root=/path/to/local/spec-kitty

# Check system requirements
spec-kitty check
```

### `spec-kitty upgrade` Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without applying them |
| `--force` | Skip confirmation prompts |
| `--target <version>` | Target version to upgrade to (defaults to current CLI version) |
| `--json` | Output results as JSON (for CI/CD integration) |
| `--verbose`, `-v` | Show detailed migration information |
| `--no-worktrees` | Skip upgrading worktrees (main project only) |

**Examples:**
```bash
# Upgrade to current version
spec-kitty upgrade

# Preview what would be changed
spec-kitty upgrade --dry-run

# Upgrade with detailed output
spec-kitty upgrade --verbose

# Upgrade to specific version
spec-kitty upgrade --target 0.6.5

# JSON output for scripting
spec-kitty upgrade --json

# Skip worktree upgrades
spec-kitty upgrade --no-worktrees
```

### `spec-kitty agent` Commands

The `spec-kitty agent` namespace provides programmatic access to all workflow automation commands. All commands support `--json` output for agent consumption.

**Feature Management:**
- `spec-kitty agent mission create-feature <name>` – Create new feature with worktree
- `spec-kitty agent mission check-prerequisites` – Validate project setup and feature context
- `spec-kitty agent mission setup-plan` – Initialize plan template for feature
- `spec-kitty agent context update` – Update agent context files
- `spec-kitty agent mission accept` – Run acceptance workflow
- `spec-kitty agent mission merge` – Merge feature branch and cleanup

**Task Workflow:**
- `spec-kitty agent action implement <id> --agent __AGENT__` – Advance planned/claimed → in_progress → for_review automatically
- `spec-kitty agent action review <id> --agent __AGENT__` – Advance for_review → in_progress → planned/done automatically
- `spec-kitty agent tasks list-tasks` – List all tasks grouped by lane
- `spec-kitty agent tasks mark-status <id> --status <status>` – Mark task status
- `spec-kitty agent tasks add-history <id> --note <message>` – Add activity log entry
- `spec-kitty agent tasks validate-workflow <id>` – Validate task metadata

**Workflow Commands:**
- `spec-kitty agent action implement [WP_ID] --agent __AGENT__` – Display WP prompt and auto-move to `in_progress` ("Doing")
- `spec-kitty agent action review [WP_ID] --agent __AGENT__` – Display WP prompt for review and auto-move to `in_progress` ("Doing")

**Note:** In generated agent command files, `__AGENT__` is replaced at init time with the agent key (e.g., `codex`, `claude`). If you run commands manually, replace `__AGENT__` with your agent name.

**Example Usage:**
```bash
# Create feature (agent-friendly)
spec-kitty agent mission create-feature "Payment Flow" --json

# Display WP prompt and auto-move to in_progress ("Doing")
spec-kitty agent action implement WP01 --agent __AGENT__

# Run workflow to advance lanes
spec-kitty agent action implement WP01 --agent __AGENT__

# Validate workflow
spec-kitty agent tasks validate-workflow WP01 --json

# Accept mission (legacy `--feature` flag name)
spec-kitty agent mission accept --json
```

### `spec-kitty dashboard` Options

| Option | Description |
|--------|-------------|
| `--port <number>` | Preferred port for the dashboard (falls back to first available port) |
| `--kill` | Stop the running dashboard for this project and clear its metadata |

**Examples:**
```bash
# Open dashboard (auto-detects port)
spec-kitty dashboard

# Open on specific port
spec-kitty dashboard --port 4000

# Stop dashboard
spec-kitty dashboard --kill
```

### `spec-kitty accept` Options

| Option | Description |
|--------|-------------|
| `--feature <slug>` | Mission slug to accept. Legacy flag name retained as a software-dev compatibility alias. |
| `--mode <mode>` | Acceptance mode: `auto`, `pr`, `local`, or `checklist` (default: `auto`) |
| `--actor <name>` | Name to record as the acceptance actor |
| `--test <command>` | Validation command to execute (repeatable) |
| `--json` | Emit JSON instead of formatted text |
| `--lenient` | Skip strict metadata validation |
| `--no-commit` | Skip auto-commit; report only |
| `--allow-fail` | Return checklist even when issues remain |

**Examples:**
```bash
# Validate feature (auto-detect)
spec-kitty accept

# Validate specific mission
spec-kitty accept --feature 001-auth-system

# Get checklist only (no commit)
spec-kitty accept --mode checklist

# Accept with custom test validation
spec-kitty accept --test "pytest tests/" --test "npm run lint"

# JSON output for CI integration
spec-kitty accept --json
```

### `spec-kitty merge` Options

| Option | Description |
|--------|-------------|
| `--strategy <type>` | Merge strategy: `merge`, `squash`, or `rebase` (default: `merge`) |
| `--delete-branch` / `--keep-branch` | Delete or keep feature branch after merge (default: delete) |
| `--remove-worktree` / `--keep-worktree` | Remove or keep resolved execution worktrees after merge (default: remove) |
| `--push` | Push to origin after merge |
| `--target <branch>` | Target branch to merge into (default: `main`) |
| `--dry-run` | Show what would be done without executing |

**Examples:**
```bash
# Standard merge and push
spec-kitty merge --push

# Squash commits into one
spec-kitty merge --strategy squash --push

# Keep branch for reference
spec-kitty merge --keep-branch --push

# Preview merge without executing
spec-kitty merge --dry-run

# Merge to different target
spec-kitty merge --target develop --push
```

### `spec-kitty verify-setup`

Verifies that the current environment matches Spec Kitty expectations:
- Checks for `.kittify/` directory structure
- Validates agent command files exist
- Confirms dashboard can start
- Reports any configuration issues

**Example:**
```bash
cd my-project
spec-kitty verify-setup
```

### `spec-kitty diagnostics`

Shows project health and diagnostics information:
- Active mission
- Available features
- Dashboard status
- Git configuration
- Agent command availability

**Example:**
```bash
spec-kitty diagnostics
```

### Available Slash Commands

After running `spec-kitty init`, your AI coding agent will have access to these slash commands for structured development.

> **📋 Quick Reference:** See the [command order flowchart above](#-quick-reference-command-order) for a visual workflow guide.

#### Core Commands (In Recommended Order)

**Workflow sequence for spec-driven development:**

| # | Command                  | Description                                                           |
|---|--------------------------|-----------------------------------------------------------------------|
| 1 | `/spec-kitty.constitution`  | (**First in main repo**) Create or update project governing principles and development guidelines |
| 2 | `/spec-kitty.specify`       | Define what you want to build (requirements and user stories; creates worktree) |
| 3 | `/spec-kitty.plan`          | Create technical implementation plans with your chosen tech stack     |
| 4 | `/spec-kitty.research`      | Run Phase 0 research scaffolding to populate research.md, data-model.md, and evidence logs |
| 5 | `/spec-kitty.tasks`         | Generate actionable task lists and work package prompts in flat tasks/ directory |
| 6 | `/spec-kitty.implement`     | Display WP prompt, auto-move to `in_progress` ("Doing"), show completion instructions |
| 7 | `/spec-kitty.review`        | Display WP prompt for review, auto-move to `in_progress` ("Doing"), show next steps |
| 8 | `/spec-kitty.accept`        | Run final acceptance checks, record metadata, and verify feature complete |
| 9 | `/spec-kitty.merge`         | Merge feature into main branch and clean up worktree                  |

#### Quality Gates & Development Tools

**Optional commands for enhanced quality and development:**

| Command              | When to Use                                                           |
|----------------------|-----------------------------------------------------------------------|
| `/spec-kitty.analyze`   | **Optional, after `/spec-kitty.tasks`, before `/spec-kitty.implement`**: Cross-artifact consistency & coverage analysis |
| `/spec-kitty.checklist` | **Optional, anytime after `/spec-kitty.plan`**: Generate custom quality checklists that validate requirements completeness, clarity, and consistency |
| `/spec-kitty.dashboard` | **Anytime (runs in background)**: Open the real-time kanban dashboard in your browser. Automatically starts with `spec-kitty init` and updates as you work. |

</details>

## 🌳 Worktree Strategy

> **📖 Quick Start:** See the [Getting Started guide](#-getting-started-complete-workflow) for practical examples of worktree usage in context.

Spec Kitty uses an **opinionated execution-workspace model** for parallel feature development:

### Parallel Development Without Branch Switching

```mermaid
graph TD
    Main[main branch<br/>🔒 Clean production code]
    WT1[.worktrees/001-auth-lane-a<br/>🔐 Shared foundation lane]
    WT2[.worktrees/001-auth-lane-b<br/>💾 Parallel API lane]
    WT3[.worktrees/002-dashboard-lane-a<br/>📊 Dashboard lane]

    Main --> WT1
    Main --> WT2
    Main --> WT3

    WT1 -.->|🚀 Parallel work| WT2
    WT2 -.->|✅ No conflicts| WT3

    style Main fill:#e8f5e9
    style WT1 fill:#e1f5ff
    style WT2 fill:#fff3e0
    style WT3 fill:#f3e5f5
```

**Why this works:**
- Planning stays in the main checkout, so artifacts remain visible and auditable
- Lane-based features can share a worktree across sequential WPs in the same execution lane
- Independent lanes still run in parallel in separate directories with separate branches
- Legacy features without `lanes.json` still fall back to one worktree per WP
- Main branch stays clean without manual `git checkout` juggling

### The Pattern
```
my-project/                    # Main repo (main branch)
├── .worktrees/
│   ├── 001-auth-system-lane-a/  # Feature 1 lane A (shared by sequential WPs)
│   ├── 001-auth-system-lane-b/  # Feature 1 lane B (parallel work)
│   └── 002-dashboard-WP01/      # Legacy feature fallback
├── .kittify/
├── kitty-specs/
└── ... (main branch files)
```

### The Rules
1. **Planning commands** run in the primary repo root
2. **Implementation branches** live under `.worktrees/`
3. **Trust the path printed by Spec Kitty** instead of guessing the worktree name
4. **Lane-based features** reuse `.worktrees/<feature>-lane-<id>` when multiple WPs share a lane
5. **Legacy features without `lanes.json`** still use `.worktrees/<feature>-WP##`
6. **Automatic cleanup** removes execution worktrees after merge

### The Complete Workflow

```bash
# ========== IN MAIN REPO ==========
/spec-kitty.constitution     # Step 1: Establish project governance (one time per project)

# ========== PLAN IN MAIN REPO ==========
/spec-kitty.specify          # Step 2: Create the feature artifacts
/spec-kitty.plan             # Step 3: Design technical implementation
/spec-kitty.research         # Step 4 (as needed): Research technologies, patterns, etc.
/spec-kitty.tasks            # Step 5: Break plan into actionable tasks
/spec-kitty.analyze          # Step 6 (optional): Check cross-artifact consistency

# ========== CREATE OR RESOLVE EXECUTION WORKSPACE ==========
spec-kitty implement WP01    # Step 7: Creates or reuses the execution workspace
cd .worktrees/001-my-feature-lane-a  # Use the exact path Spec Kitty printed

# ========== IN EXECUTION WORKSPACE ==========
/spec-kitty.implement        # Step 8: Execute implementation tasks
/spec-kitty.review           # Step 9: Review and refine completed work
/spec-kitty.accept           # Step 10: Acceptance checks & final metadata
/spec-kitty.merge --push     # Step 11: Merge to main + cleanup execution worktrees

# ========== BACK IN MAIN REPO ==========
# Ready for next feature!
```

## 🧭 Mission System

Spec Kitty supports **missions**: curated bundles of templates, commands, and guardrails for different domains. Two missions ship out of the box:

- **Software Dev Kitty** – the original Spec-Driven Development workflow for shipping application features (default).
- **Deep Research Kitty** – a methodology-focused workflow for evidence gathering, analysis, and synthesis.

Each mission lives under `.kittify/missions/<mission-key>/` and provides:

- Mission-specific templates (`spec-template.md`, `plan-template.md`, `tasks-template.md`, etc.)
- Command guidance tuned to the domain (`specify`, `plan`, `tasks`, `implement`, `review`, `accept`)
- Optional constitutions to bias the agent toward best practices

### Selecting a Mission

Choose your mission during initialization:

```bash
# Select mission interactively
spec-kitty init my-project --ai claude

# Or specify mission directly
spec-kitty init my-project --ai claude --mission software-dev
spec-kitty init research-project --ai claude --mission research
```

### Mission Configuration

After initialization, mission selection is recorded in project metadata:

```bash
# View active mission
spec-kitty mission current

# Project metadata
cat .kittify/metadata.yaml
```

**Note:** In current 2.x, missions are selected during `spec-kitty init` and remain active for the project lifecycle.

### Environment Variables

| Variable         | Description                                                                                    |
|------------------|------------------------------------------------------------------------------------------------|
| `SPECIFY_FEATURE` | Override feature detection for non-Git repositories. Set to the feature directory name (e.g., `001-photo-albums`) to work on a specific feature when not using Git branches.<br/>**Must be set in the context of the agent you're working with prior to using `/spec-kitty.plan` or follow-up commands. |
| `SPEC_KITTY_TEMPLATE_ROOT` | Optional. Point to a local checkout whose `templates/`, `scripts/`, and `memory/` directories should seed new projects (handy while developing Spec Kitty itself). |
| `SPECIFY_TEMPLATE_REPO` | Optional. Override the GitHub repository slug (`owner/name`) to fetch templates from when you explicitly want a remote source. |
| `CODEX_HOME` | Required when using the Codex CLI so it loads project-specific prompts. Point it to your project’s `.codex/` directory—set it manually with `export CODEX_HOME=\"$(pwd)/.codex\"` or automate it via [`direnv`](https://github.com/Priivacy-ai/spec-kitty/blob/main/docs/index.md#codex-cli-automatically-load-project-prompts-linux-macos-wsl) on Linux/macOS/WSL. |


## 🔧 Prerequisites

- **Linux/macOS** (or WSL2 on Windows)
- AI coding agent: [Claude Code](https://www.anthropic.com/claude-code), [GitHub Copilot](https://code.visualstudio.com/), [Gemini CLI](https://github.com/google-gemini/gemini-cli), [Cursor](https://cursor.sh/), [Qwen CLI](https://github.com/QwenLM/qwen-code), [opencode](https://opencode.ai/), [Codex CLI](https://github.com/openai/codex), [Windsurf](https://windsurf.com/), or [Amazon Q Developer CLI](https://aws.amazon.com/developer/learning/q-developer-cli/)
- [uv](https://docs.astral.sh/uv/) for package management
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

If you encounter issues with an agent, please open an issue so we can refine the integration.

<details>
<summary><h2>🚀 Releasing Stable Versions on GitHub and PyPI (Maintainers)</h2></summary>

The stable `3.x` line now lives on `main` and publishes from semantic tags in the form `vX.Y.Z`.
The release workflow publishes both GitHub release artifacts and the PyPI package.

### 0. One-Time Setup

- Configure PyPI Trusted Publishing for `spec-kitty-cli` against `.github/workflows/release.yml`.
- Keep `1.x-maintenance` maintenance-only; do not use it for new PyPI releases.

### 1. Prepare Release Branch

```bash
git checkout main
git pull origin main
git checkout -b release/vX.Y.Z

# Update pyproject.toml to a semantic version (example: X.Y.Z)
# Add CHANGELOG.md entry under: ## [X.Y.Z] - YYYY-MM-DD
```

### 2. Validate Locally

```bash
python scripts/release/validate_release.py --mode branch --tag-pattern "v*.*.*"
python -m pytest
python -m build
twine check dist/*
rm -rf dist/ build/
```

### 3. Open and Merge PR to `main`

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): prepare X.Y.Z"
git push origin release/vX.Y.Z
```

After review, merge into `main` with a linear-history strategy (`rebase`).

### 4. Tag and Push

```bash
git checkout main
git pull origin main
git tag vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

This triggers `.github/workflows/release.yml`.

### 5. Verify GitHub Release and PyPI Publication

```bash
gh release view vX.Y.Z
python -m pip index versions spec-kitty-cli
```

### Guardrails

- `release-readiness.yml`: runs on PRs to `main` (and `2.x` if the maintenance branch is still active) to validate version/changelog/tests.
- `release.yml`: runs on `v*.*.*` tags and performs:
  - test execution
  - release metadata validation
  - artifact build and checksums
  - PyPI publication via Trusted Publishing
  - GitHub Release creation with changelog notes

### Troubleshooting

**Validation fails**: "Version does not advance beyond latest tag"
- Check latest tag: `git tag --list 'v*.*.*' --sort=-version:refname | head -1`
- Bump `pyproject.toml` to a higher semantic version

**Validation fails**: "CHANGELOG.md lacks a populated section"
- Add `## [X.Y.Z]` with release notes in `CHANGELOG.md`

**Tag already exists**:
```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
git tag vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

### References

- `RELEASE_CHECKLIST.md`
- `docs/how-to/2-1-main-cutover-checklist.md`
- `scripts/release/README.md`
- `.github/workflows/release.yml`

</details>

## 📖 Learn more

- **[Complete Spec-Driven Development Methodology](https://github.com/Priivacy-ai/spec-kitty/blob/main/spec-driven.md)** - Deep dive into the full process
- **[Getting Started Guide](#-getting-started-complete-workflow)** - Step-by-step walkthrough from installation to feature completion

---

## 🛠️ Development Setup

If you're contributing to Spec Kitty or working with the source code directly, you'll need to install it in development mode:

### From Local Checkout

```bash
# Clone the repository
git clone https://github.com/Priivacy-ai/spec-kitty.git
cd spec-kitty

# Install in editable mode with development dependencies
pip install -e ".[test]"

# When running spec-kitty init, set the template root to your local checkout:
export SPEC_KITTY_TEMPLATE_ROOT=$(pwd)
spec-kitty init <PROJECT_NAME> --ai=claude

# Or use the --template-root flag directly (no env var needed):
spec-kitty init <PROJECT_NAME> --ai=claude --template-root=/path/to/spec-kitty
```

### Template Discovery Priority

The CLI searches for templates in this order:
1. **Command-line override**: `--template-root` flag (highest priority)
2. **Environment variable**: `SPEC_KITTY_TEMPLATE_ROOT` (local checkout)
3. **Packaged resources**: Built-in templates from PyPI installation
4. **Remote repository**: `SPECIFY_TEMPLATE_REPO` environment variable

This means development installs automatically find templates when running from the cloned repository, but you may need to set `SPEC_KITTY_TEMPLATE_ROOT` if you move the directory.

---

<details>
<summary><h2>🔍 Troubleshooting</h2></summary>

### Template Discovery Issues

#### Error: "Templates could not be found in any of the expected locations"

This error occurs when `spec-kitty init` cannot locate the template files. Here's how to diagnose and fix it:

**For PyPI installations:**
```bash
# Reinstall the package
pip install --upgrade spec-kitty-cli

# Verify templates are bundled
python -c "from importlib.resources import files; print(files('specify_cli').joinpath('templates'))"
```

**For development installations:**
```bash
# Make sure you installed in editable mode from the repo root
cd /path/to/spec-kitty
pip install -e .

# Option 1: Use environment variable
export SPEC_KITTY_TEMPLATE_ROOT=$(pwd)
spec-kitty init my-project --ai=claude

# Option 2: Use --template-root flag (no env var needed)
spec-kitty init my-project --ai=claude --template-root=$(pwd)

# Option 3: Verify the path exists
ls -la ./templates/commands
```

**For moved repositories:**
If you cloned the spec-kitty repo and moved the directory, update the environment variable:
```bash
export SPEC_KITTY_TEMPLATE_ROOT=/new/path/to/spec-kitty
spec-kitty init my-project --ai=claude
```

**Debugging with verbose output:**
```bash
# Use --debug flag to see which paths were checked
spec-kitty init my-project --ai=claude --debug --template-root=/path/to/spec-kitty
```

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

</details>

## 👥 Maintainers

- Robert Douglass ([@robertDouglass](https://github.com/robertDouglass))

## 💬 Support

For support, please open a [GitHub issue](https://github.com/Priivacy-ai/spec-kitty/issues/new). We welcome bug reports, feature requests, and questions about using Spec-Driven Development.

## 🙏 Acknowledgements

This project is heavily influenced by and based on the work and research of [John Lam](https://github.com/jflam).

## 📄 License

This project is licensed under the terms of the MIT open source license. Please refer to the [LICENSE](https://github.com/Priivacy-ai/spec-kitty/blob/main/LICENSE) file for the full terms.
