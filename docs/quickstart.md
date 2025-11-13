# Quick Start Guide

This guide will help you get started with Spec-Driven Development using Spec Kitty.

> Spec Kitty is a community-maintained fork of GitHub's [Spec Kit](https://github.com/github/spec-kit). All commands and examples have been updated to use the spec-kitty branding while honoring the upstream license.

> NEW: All automation scripts now provide both Bash (`.sh`) and PowerShell (`.ps1`) variants. The `spec-kitty` CLI auto-selects based on OS unless you pass `--script sh|ps`.

## 📖 New User? Start Here

**For the complete workflow from installation to merging features**, see the comprehensive guide in the [README: Getting Started section](https://github.com/Priivacy-ai/spec-kitty#-getting-started-complete-workflow).

The guide covers:
1. **CLI Installation & Project Initialization** (Terminal commands)
2. **Starting Your AI Agent** (Claude, Gemini, Cursor, etc.)
3. **Critical Context Switch** - When to `cd .worktrees/XXX-feature`
4. **Complete Command Flow** - Constitution → Specify → Plan → Tasks → Implement → Review → Accept → Merge
5. **Common Gotchas** - Where users typically get confused

## The Essential Process (Summary)

### 1. Install Spec Kitty CLI

**From PyPI (Recommended):**

**Using pip:**
```bash
pip install spec-kitty-cli
```

**Using uv:**
```bash
uv tool install spec-kitty-cli
```

**From GitHub (Development):**

**Using pip:**
```bash
pip install git+https://github.com/Priivacy-ai/spec-kitty.git
```

**Using uv:**
```bash
uv tool install spec-kitty-cli --from git+https://github.com/Priivacy-ai/spec-kitty.git
```

Then initialize your project:

```bash
spec-kitty init <PROJECT_NAME>
```

> Need more than one assistant? Pass a comma-separated list, e.g. `--ai claude,codex`, and the initializer will bring in the command files for both.

Pick script type explicitly (optional):
```bash
spec-kitty init <PROJECT_NAME> --script ps  # Force PowerShell
spec-kitty init <PROJECT_NAME> --script sh  # Force POSIX shell
```

### Optional: Automated Sandbox Setup

If you frequently spin up disposable sandboxes, run the helper script from the repo root. It installs the local CLI build, points `SPEC_KITTY_TEMPLATE_ROOT` at this checkout, and initializes the project in one go:

```bash
scripts/bash/setup-sandbox.sh --agents claude ~/Code/new_specify
```

Add `--reset` to recreate an existing directory, `--script-type ps` for PowerShell workflows, or `--agents claude,copilot` to preload multiple assistants.

### 2. Create the Spec

Use the `/spec-kitty.specify` command to describe what you want to build. Focus on the **what** and **why**, not the tech stack. Expect the CLI to interview you first and stay in discovery mode until you answer its questions.

```bash
/spec-kitty.specify Build an application that can help me organize my photos in separate photo albums. Albums are grouped by date and can be re-organized by dragging and dropping on the main page. Albums are never in other nested albums. Within each album, photos are previewed in a tile-like interface.
```

The command responds with `WAITING_FOR_DISCOVERY_INPUT` until you answer every discovery question it raises.

> When the command succeeds it checks out the feature branch inside `.worktrees/<feature-slug>`. Change into that directory before running planning or implementation commands (for example, `cd .worktrees/001-photo-albums`). Agents that cannot traverse into `.worktrees/` automatically fall back to the legacy single-worktree flow.

### 3. Create a Technical Implementation Plan

Use the `/spec-kitty.plan` command to provide your tech stack and architecture choices. The command will challenge the specification, ask you non-functional questions, and pause until you reply.

```bash
/spec-kitty.plan The application uses Vite with minimal number of libraries. Use vanilla HTML, CSS, and JavaScript as much as possible. Images are not uploaded anywhere and metadata is stored in a local SQLite database.
```

Expect `WAITING_FOR_PLANNING_INPUT` prompts whenever the planner needs more architectural detail.

### 4. Run Phase 0 Research

Use `/spec-kitty.research` after planning wraps up. The command scaffolds `research.md`, `data-model.md`, and the CSV evidence logs that Deep Research Kitty and other missions expect. Populate those files with the clarifications and references you gathered during planning before moving on.

### 5. Break Down and Implement

1. Run `/spec-kitty.tasks` to produce the summary checklist in `tasks.md` **and** generate up to ten bundled prompt files under `/tasks/planned/`. Each bundle covers a work package with the granular subtasks nested beneath it.
2. Use `/spec-kitty.implement` to move a prompt into `/tasks/doing/` and build the solution.
3. Finish with `/spec-kitty.review` to process items in `/tasks/for_review/` and move approved work to `/tasks/done/`.

### 6. Accept & Merge

Once `/tasks/done/` contains every work package and the checklist is complete, run `/spec-kitty.accept` (or `spec-kitty accept`) to:

- Validate that all prompts are in the correct lanes with required metadata and activity log entries.
- Surface any remaining `NEEDS CLARIFICATION` markers or unchecked tasks.
- Record acceptance metadata in `kitty-specs/<feature>/meta.json`, create a commit (optional), and print merge guidance (PR or local) plus cleanup steps (`git worktree remove`, branch deletion).

If you just need the readiness report, pass `--mode checklist` to see the findings without committing or printing merge instructions.

## Detailed Example: Building Taskify

Here's a complete example of building a team productivity platform:

### Step 1: Define Requirements with `/spec-kitty.specify`

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

### Step 2: Refine the Specification

After the initial specification is created, clarify any missing requirements:

```text
For each sample project or project that you create there should be a variable number of tasks between 5 and 15
tasks for each one randomly distributed into different states of completion. Make sure that there's at least
one task in each stage of completion.
```

Also validate the specification checklist:

```text
Read the review and acceptance checklist, and check off each item in the checklist if the feature spec meets the criteria. Leave it empty if it does not.
```

### Step 3: Generate Technical Plan with `/spec-kitty.plan`

Be specific about your tech stack and technical requirements:

```text
We are going to generate this using .NET Aspire, using Postgres as the database. The frontend should use
Blazor server with drag-and-drop task boards, real-time updates. There should be a REST API created with a projects API,
tasks API, and a notifications API.
```

### Step 4: Validate, Generate Prompts, and Implement

Audit the implementation plan:

```text
Now I want you to go and audit the implementation plan and the implementation detail files.
Read through it with an eye on determining whether or not there is a sequence of tasks that you need
to be doing that are obvious from reading this. Because I don't know if there's enough here.
```

Then run the build commands in order:

```text
implement kitty-specs/002-create-taskify/plan.md
```

Next:

```text
/spec-kitty.tasks
/spec-kitty.implement
/spec-kitty.review
```

## Key Principles

- **Be explicit** about what you're building and why
- **Don't focus on tech stack** during specification phase
- **Iterate and refine** your specifications before implementation
- **Validate** the plan before coding begins
- **Let the AI agent handle** the implementation details

## Next Steps

- Read the complete methodology for in-depth guidance
- Check out more examples in the repository
- Explore the source code on GitHub
