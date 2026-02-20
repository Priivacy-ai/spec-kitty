---
description: Create the task breakdown document (tasks.md) with work package definitions, subtask lists, and dependency descriptions.
---

# /spec-kitty.tasks-outline - Create Task Breakdown Document

**Version**: 0.12.0+

## Purpose

Create `tasks.md` — the task breakdown document that defines work packages,
subtask lists, dependency descriptions, and sizing estimates. This step
produces the **outline only**; individual WP prompt files are generated in
the next step.

## ⚠️ CRITICAL: THIS IS THE MOST IMPORTANT PLANNING WORK

**You are creating the blueprint for implementation**. The quality of work packages determines:
- How easily agents can implement the feature
- How parallelizable the work is
- How reviewable the code will be
- Whether the feature succeeds or fails

**QUALITY OVER SPEED**: Take your time to understand the full scope deeply,
break work into clear pieces, and write detailed guidance.

---

## 📍 WORKING DIRECTORY: Stay in planning repository

**IMPORTANT**: This step works in the planning repository. NO worktrees created.

**Do NOT cd anywhere**. Stay in the planning repository root.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Check

Before proceeding, verify you are in the planning repository:

```bash
git branch --show-current
```

**Expected output:** the target branch (meta.json → target_branch), typically `main` or `2.x`

## Steps

### 1. Setup

Run `spec-kitty agent feature check-prerequisites --json --paths-only --include-tasks` from the repository root and capture `FEATURE_DIR` plus `AVAILABLE_DOCS`. All paths must be absolute.

**CRITICAL**: The command returns JSON with `FEATURE_DIR` as an ABSOLUTE path. **YOU MUST USE THIS PATH** for ALL subsequent file operations.

### 2. Load Design Documents

Read from `FEATURE_DIR` (only those present):
- **Required**: plan.md (tech architecture, stack), spec.md (user stories & priorities)
- **Optional**: data-model.md (entities), contracts/ (API schemas), research.md (decisions), quickstart.md (validation scenarios)

Scale your effort to the feature: simple UI tweaks deserve lighter coverage, multi-system releases require deeper decomposition.

### 3. Derive Fine-Grained Subtasks

Create complete list of subtasks with IDs `T001`, `T002`, etc.:
- Parse plan/spec to enumerate concrete implementation steps, tests (only if explicitly requested), migrations, and operational work.
- Capture prerequisites, dependencies, and parallelizability markers (`[P]` means safe to parallelize per file/concern).
- Assign IDs sequentially in execution order.
- **Ideal granularity**: One clear action (e.g., "Create user model", "Add login endpoint")

### 4. Roll Subtasks into Work Packages

Group subtasks into work packages (IDs `WP01`, `WP02`, ...):

**TARGET SIZE**: 3-7 subtasks per WP (200-500 line prompts)
**MAXIMUM**: 10 subtasks per WP (700 line prompts)
**If more than 10 subtasks needed**: Create additional WPs, don't pack them in

**GROUPING PRINCIPLES**:
- Each WP should be independently implementable
- Root in a single user story or cohesive subsystem
- Ensure every subtask appears in exactly one work package
- Name with succinct goal (e.g., "User Story 1 – Real-time chat happy path")
- Record metadata: priority, success criteria, risks, dependencies, included subtasks

### 5. Write `tasks.md`

Write to `FEATURE_DIR/tasks.md` using the bundled tasks template (`.kittify/missions/software-dev/templates/tasks-template.md`):
- Populate Work Package sections (setup, foundational, per-story, polish) with `WPxx` entries
- Under each work package include:
  - Summary (goal, priority, independent test)
  - Included subtasks (checkbox list referencing `Txxx`)
  - Implementation sketch (high-level sequence)
  - Parallel opportunities, dependencies, and risks
  - **Estimated prompt size** (e.g., "~400 lines")
- Preserve the checklist style so implementers can mark progress

**DO NOT generate WP prompt files in this step.** That happens in the next step.

## Output

After completing this step:
- `FEATURE_DIR/tasks.md` exists with full work package definitions
- Each WP has clear subtask lists, dependencies, and sizing estimates
- No WP prompt files have been created yet

**Next step**: `spec-kitty next --agent <name>` will advance to work package generation.

## Work Package Sizing Guidelines

**Target: 3-7 subtasks per WP** → 200-500 line prompts
**Maximum: 10 subtasks** → ~700 line prompts
**No arbitrary limit on WP count** — let complexity dictate

**Split if ANY of these are true**:
- More than 10 subtasks
- Prompt would exceed 700 lines
- Multiple independent concerns mixed together
- Different phases or priorities mixed

**Merge if ALL of these are true**:
- Each WP has <3 subtasks
- Combined would be <7 subtasks
- Both address the same concern/component
- No natural parallelization opportunity

## Dependency Detection

Analyze tasks.md for dependency relationships:
- Explicit phrases: "Depends on WP##", "Dependencies: WP##"
- Phase grouping: Phase 2 WPs typically depend on Phase 1
- Default to empty if unclear

Document dependencies clearly in each WP's section.

Context for work-package planning: {ARGS}
