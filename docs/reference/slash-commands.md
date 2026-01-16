# Slash Command Reference

Slash commands are invoked inside your AI agent (Claude Code, Codex CLI, Cursor, etc.). They are generated from Spec Kitty command templates and typically accept optional free-form arguments.

Syntax format in this reference:
- `COMMAND`: `/spec-kitty.<name> [arguments]`
- `Arguments`: free-form text passed as `$ARGUMENTS` in templates

---

## /spec-kitty.specify

**Syntax**: `/spec-kitty.specify [description]`

**Purpose**: Create or update a feature specification from a natural-language description.

**Prerequisites**:
- Run from the main repository root (no worktree).
- Discovery interview is required before generating artifacts.

**What it does**:
- Runs a discovery interview and confirms an intent summary.
- Determines mission (software-dev or research).
- Calls `spec-kitty agent feature create-feature` to create feature scaffolding.

**Creates/updates**:
- `kitty-specs/<feature>/spec.md`
- `kitty-specs/<feature>/meta.json`
- `kitty-specs/<feature>/checklists/requirements.md`

**Related**: `/spec-kitty.plan`, `/spec-kitty.constitution`

---

## /spec-kitty.plan

**Syntax**: `/spec-kitty.plan [notes]`

**Purpose**: Create the implementation plan and design artifacts based on the spec.

**Prerequisites**:
- Run from the main repository root.
- Spec exists for the feature.

**What it does**:
- Conducts planning interrogation.
- Calls `spec-kitty agent feature setup-plan`.
- Generates planning artifacts and updates agent context files.

**Creates/updates** (as applicable):
- `kitty-specs/<feature>/plan.md`
- `kitty-specs/<feature>/research.md`
- `kitty-specs/<feature>/data-model.md`
- `kitty-specs/<feature>/contracts/`
- `kitty-specs/<feature>/quickstart.md`
- Agent context file (e.g., `CLAUDE.md`)

**Related**: `/spec-kitty.specify`, `/spec-kitty.tasks`, `/spec-kitty.research`

---

## /spec-kitty.tasks

**Syntax**: `/spec-kitty.tasks [notes]`

**Purpose**: Generate work packages and task prompts from spec and plan.

**Prerequisites**:
- Run from the main repository root.
- `spec.md` and `plan.md` exist.

**What it does**:
- Reads spec/plan (and optional research artifacts).
- Writes `tasks.md` plus one prompt file per work package.
- Calls `spec-kitty agent feature finalize-tasks` to populate dependencies.

**Creates/updates**:
- `kitty-specs/<feature>/tasks.md`
- `kitty-specs/<feature>/tasks/WPxx-*.md` (flat directory)

**Related**: `/spec-kitty.plan`, `/spec-kitty.implement`, `/spec-kitty.analyze`

---

## /spec-kitty.implement

**Syntax**: `/spec-kitty.implement [WP_ID]`

**Purpose**: Create a worktree and start implementation for a specific work package.

**Prerequisites**:
- Work packages exist in `kitty-specs/<feature>/tasks/`.
- Run from main repository for the workflow prompt; worktree is created by CLI.

**What it does**:
- Step 1: `spec-kitty agent workflow implement WP## --agent <agent>` to show the prompt and move the WP to `doing`.
- Step 2: `spec-kitty implement WP## [--base WP##]` to create the worktree.
- Implementation happens inside the created worktree.

**Creates/updates**:
- `.worktrees/<feature>-WP##/` worktree directory
- `kitty-specs/<feature>/tasks/WP##-*.md` lane status updates

**Related**: `/spec-kitty.tasks`, `/spec-kitty.review`

---

## /spec-kitty.review

**Syntax**: `/spec-kitty.review [WP_ID or prompt path]`

**Purpose**: Review a completed work package and update its lane status.

**Prerequisites**:
- Run from the feature worktree.
- WP must be in `lane: "for_review"`.

**What it does**:
- Loads the WP prompt, supporting artifacts, and code changes.
- Performs structured review and records feedback in the WP file.
- Moves the WP to `done` (approved) or back to `planned` (needs changes).
- Updates `tasks.md` status when approved.

**Creates/updates**:
- `kitty-specs/<feature>/tasks/WP##-*.md` (review feedback, lane changes)
- `kitty-specs/<feature>/tasks.md` (checkbox status)

**Related**: `/spec-kitty.implement`, `/spec-kitty.accept`

---

## /spec-kitty.accept

**Syntax**: `/spec-kitty.accept [options]`

**Purpose**: Validate feature readiness and generate acceptance results.

**Prerequisites**:
- Run from a feature worktree or branch where feature auto-detection works.
- All WPs should be in `done` or intentionally waived.

**What it does**:
- Auto-detects feature slug and validation commands when possible.
- Runs `spec-kitty agent feature accept` to perform acceptance checks.
- Outputs acceptance summary and merge instructions.

**Creates/updates**:
- Acceptance output in the feature directory (and optional commits depending on mode)

**Related**: `/spec-kitty.review`, `/spec-kitty.merge`

---

## /spec-kitty.merge

**Syntax**: `/spec-kitty.merge [options]`

**Purpose**: Merge an accepted feature into the target branch and clean up worktrees.

**Prerequisites**:
- Run from the feature worktree (not main).
- Feature must pass `/spec-kitty.accept`.

**What it does**:
- Executes `spec-kitty merge` with selected strategy and cleanup flags.
- Optionally pushes to origin and deletes worktrees/branches.

**Creates/updates**:
- Merges feature branch into target branch.
- Deletes worktree and/or feature branch depending on flags.

**Related**: `/spec-kitty.accept`

---

## /spec-kitty.status

**Syntax**: `/spec-kitty.status`

**Purpose**: Display current kanban status for work packages.

**Prerequisites**:
- Run from a repo or worktree with access to `kitty-specs/<feature>/tasks/`.

**What it does**:
- Runs `spec-kitty agent tasks status`.
- Shows a lane-based status board, progress metrics, and next steps.

**Creates/updates**: None (read-only).

**Related**: `/spec-kitty.tasks`, `/spec-kitty.implement`

---

## /spec-kitty.dashboard

**Syntax**: `/spec-kitty.dashboard`

**Purpose**: Open or stop the Spec Kitty dashboard in the browser.

**Prerequisites**:
- Can run from main repo or any worktree.

**What it does**:
- Runs `spec-kitty dashboard` to start or stop the dashboard server.

**Creates/updates**: None (read-only status server).

**Related**: `/spec-kitty.status`

---

## /spec-kitty.constitution

**Syntax**: `/spec-kitty.constitution`

**Purpose**: Create or update the project constitution.

**Prerequisites**:
- Run from the main repository root.

**What it does**:
- Runs a phase-based discovery interview (minimal or comprehensive).
- Writes project-wide principles to the constitution file.

**Creates/updates**:
- `.kittify/memory/constitution.md`

**Related**: `/spec-kitty.specify`, `/spec-kitty.plan`

---

## /spec-kitty.clarify

**Syntax**: `/spec-kitty.clarify [notes]`

**Purpose**: Identify underspecified areas in the spec and record clarifications.

**Prerequisites**:
- Run from the feature worktree.
- `spec.md` must exist.

**What it does**:
- Asks up to five targeted questions.
- Updates `spec.md` with clarified requirements.

**Creates/updates**:
- `kitty-specs/<feature>/spec.md`

**Related**: `/spec-kitty.specify`, `/spec-kitty.plan`

---

## /spec-kitty.research

**Syntax**: `/spec-kitty.research [--force]`

**Purpose**: Scaffold research artifacts for Phase 0 research.

**Prerequisites**:
- Run from the feature worktree.

**What it does**:
- Runs `spec-kitty research` to create research templates.

**Creates/updates**:
- `kitty-specs/<feature>/research.md`
- `kitty-specs/<feature>/data-model.md`
- `kitty-specs/<feature>/research/evidence-log.csv`
- `kitty-specs/<feature>/research/source-register.csv`

**Related**: `/spec-kitty.plan`

---

## /spec-kitty.checklist

**Syntax**: `/spec-kitty.checklist [scope]`

**Purpose**: Generate a requirements-quality checklist for the current feature.

**Prerequisites**:
- Run from the feature worktree.

**What it does**:
- Uses `spec-kitty agent check-prerequisites` for paths.
- Creates a domain-specific checklist file (e.g., `ux.md`, `security.md`).

**Creates/updates**:
- `kitty-specs/<feature>/checklists/<domain>.md`

**Related**: `/spec-kitty.specify`, `/spec-kitty.analyze`

---

## /spec-kitty.analyze

**Syntax**: `/spec-kitty.analyze [notes]`

**Purpose**: Cross-artifact consistency analysis after tasks generation.

**Prerequisites**:
- Run from the feature worktree.
- `spec.md`, `plan.md`, and `tasks.md` must exist.

**What it does**:
- Reads spec, plan, tasks, and constitution (if present).
- Produces a read-only analysis report of gaps and conflicts.

**Creates/updates**:
- `kitty-specs/<feature>/analysis.md`

**Related**: `/spec-kitty.tasks`, `/spec-kitty.implement`

## Getting Started
- [Claude Code Integration](../tutorials/claude-code-integration.md)
- [Claude Code Workflow](../tutorials/claude-code-workflow.md)

## Practical Usage
- [Use the Dashboard](../how-to/use-dashboard.md)
- [Non-Interactive Init](../how-to/non-interactive-init.md)
