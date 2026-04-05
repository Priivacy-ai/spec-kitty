# Slash Command Reference

Slash commands are invoked inside your AI agent (Claude Code, Codex CLI, Cursor, etc.). They are generated from Spec Kitty command templates and typically accept optional free-form arguments.

Syntax format in this reference:
- `COMMAND`: `/spec-kitty.<name> [arguments]`
- `Arguments`: free-form text passed as `$ARGUMENTS` in templates

---

## /spec-kitty.specify

**Syntax**: `/spec-kitty.specify [description]`

**Purpose**: Create or update a mission specification from a natural-language description.

**Prerequisites**:
- Run from the main repository root (no worktree).
- Discovery interview is required before generating artifacts.

**What it does**:
- Runs a discovery interview and confirms an intent summary.
- Determines mission (software-dev or research).
- Calls `spec-kitty agent mission create-feature` to create mission scaffolding.

**Creates/updates**:
- `kitty-specs/<feature>/spec.md`
- `kitty-specs/<feature>/meta.json`
- `kitty-specs/<feature>/checklists/requirements.md`

**Related**: `/spec-kitty.plan`, `/spec-kitty.charter`

---

## /spec-kitty.plan

**Syntax**: `/spec-kitty.plan [notes]`

**Purpose**: Create the implementation plan and design artifacts based on the spec.

**Prerequisites**:
- Run from the main repository root.
- Spec exists for the feature.

**What it does**:
- Conducts planning interrogation.
- Calls `spec-kitty agent mission setup-plan`.
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
- Calls `spec-kitty agent mission finalize-tasks` to populate dependencies.

**Creates/updates**:
- `kitty-specs/<feature>/tasks.md`
- `kitty-specs/<feature>/tasks/WPxx-*.md` (flat directory)

**Related**: `/spec-kitty.plan`, `/spec-kitty.implement`, `/spec-kitty.analyze`

---

## /spec-kitty.implement

**Syntax**: `/spec-kitty.implement [WP_ID] [--base WP_ID]`

**Purpose**: Resolve the execution workspace and start implementation for a specific work package.

**Prerequisites**:
- Work packages exist in `kitty-specs/<feature>/tasks/`.
- Run from the main repository for the action prompt; the execution workspace is created or reused by the CLI.

**What it does**:
- If explicit slash-command args are provided, forwards the WP/base selection into the resolver-first action flow.
- Step 1: `spec-kitty agent action implement WP## --agent <agent>` to show the prompt and move the WP to `doing`.
- Step 2: `spec-kitty implement WP## [--base WP##]` to create or reuse the execution workspace.
- Implementation happens inside the resolved workspace path printed by the command.

**Creates/updates**:
- `.worktrees/<feature>-lane-<id>/` for lane-based features, or `.worktrees/<feature>-WP##/` for legacy fallback
- `kitty-specs/<feature>/tasks/WP##-*.md` lane status updates

**Related**: `/spec-kitty.tasks`, `/spec-kitty.review`

---

## /spec-kitty.review

**Syntax**: `/spec-kitty.review [WP_ID]`

**Purpose**: Review a completed work package and update its lane status.

**Prerequisites**:
- Run from any checkout where the mission can be resolved; review will attach to the canonical execution workspace if needed.
- WP must be in `lane: "for_review"`.

**What it does**:
- If `WP_ID` is provided, forwards it to the resolver-first workflow as an explicit `--wp-id`.
- Loads the WP prompt, supporting artifacts, and code changes.
- Performs structured review and records feedback via `--review-feedback-file`.
- Persists feedback in shared git common-dir and writes frontmatter `review_feedback` pointer (`feedback://...`) in the WP file.
- Moves the WP to `done` (approved) or back to `planned` (needs changes).
- Updates `tasks.md` status when approved.

**Creates/updates**:
- `kitty-specs/<feature>/tasks/WP##-*.md` (review feedback, lane changes)
- `kitty-specs/<feature>/tasks.md` (checkbox status)

**Related**: `/spec-kitty.implement`, `/spec-kitty.accept`

---

## /spec-kitty.accept

**Syntax**: `/spec-kitty.accept [options]`

**Purpose**: Validate mission readiness and generate acceptance results.

**Prerequisites**:
- Run from any checkout or branch where mission auto-detection works.
- All WPs should be in `done` or intentionally waived.

**What it does**:
- Auto-detects mission slug and validation commands when possible.
- Runs `spec-kitty agent mission accept` to perform acceptance checks.
- Outputs acceptance summary and merge instructions.

**Creates/updates**:
- Acceptance output in the mission directory (and optional commits depending on mode)

**Related**: `/spec-kitty.review`, `/spec-kitty.merge`

---

## /spec-kitty.merge

**Syntax**: `/spec-kitty.merge [options]`

**Purpose**: Merge an accepted mission into the target branch and clean up worktrees.

**Prerequisites**:
- Run from any checkout where the mission can be resolved (main checkout or execution workspace).
- Mission must pass `/spec-kitty.accept`.

**What it does**:
- Executes `spec-kitty merge` with selected strategy and cleanup flags.
- Optionally pushes to origin and deletes worktrees/branches.

**Creates/updates**:
- Merges mission branch into target branch.
- Deletes worktree and/or mission branch depending on flags.

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

## /spec-kitty.charter

**Syntax**: `/spec-kitty.charter`

**Purpose**: Create or update the project charter.

**Prerequisites**:
- Run from the main repository root.

**What it does**:
- Runs a phase-based discovery interview (minimal or comprehensive).
- Writes project-wide principles to the charter file.

**Creates/updates**:
- `.kittify/memory/charter.md`

**Related**: `/spec-kitty.specify`, `/spec-kitty.plan`

---

## /spec-kitty.research

**Syntax**: `/spec-kitty.research [--force]`

**Purpose**: Scaffold research artifacts for Phase 0 research.

**Prerequisites**:
- Run from any checkout where the mission can be resolved.

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
- Run from any checkout where the mission can be resolved.

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
- Run from any checkout where the mission can be resolved.
- `spec.md`, `plan.md`, and `tasks.md` must exist.

**What it does**:
- Reads spec, plan, tasks, and charter (if present).
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
