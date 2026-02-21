---
description: Generate grouped work packages with actionable subtasks and matching prompt files for the feature in one pass.
---

# /spec-kitty.tasks - Generate Work Packages

**Version**: 0.11.0+

## 📍 WORKING DIRECTORY: Stay in planning repository

**IMPORTANT**: Tasks works in the planning repository. NO worktrees created.

```bash
# Run from project root (same directory as /spec-kitty.plan):
# You should already be here if you just ran /spec-kitty.plan

# Creates:
# - kitty-specs/###-feature/tasks/WP01-*.md → In planning repository
# - kitty-specs/###-feature/tasks/WP02-*.md → In planning repository
# - Commits ALL to target branch
# - NO worktrees created
```

**Do NOT cd anywhere**. Stay in the planning repository root.

**Worktrees created later**: After tasks are generated, use `spec-kitty implement WP##` to create workspace for each WP.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Check (0.11.0+)

Before proceeding, verify you are in the planning repository:

**Check your current branch:**
```bash
git branch --show-current
```

**Expected output:** the target branch (meta.json → target_branch), typically `main` or `2.x`
**If you see a feature branch:** You're in the wrong place. Return to the target branch:
```bash
cd $(git rev-parse --show-toplevel)
git checkout <target-branch>
```

Work packages are generated directly in `kitty-specs/###-feature/` and committed to the target branch. Worktrees are created later when implementing each work package.

## Outline

1. **Setup**: Run `spec-kitty agent feature check-prerequisites --json --paths-only --include-tasks` from the repository root and capture `FEATURE_DIR` plus `AVAILABLE_DOCS`. All paths must be absolute.

   **CRITICAL**: The command returns JSON with `FEATURE_DIR` as an ABSOLUTE path (e.g., `/Users/robert/Code/new_specify/kitty-specs/001-feature-name`).

   **YOU MUST USE THIS PATH** for ALL subsequent file operations. Example:
   ```
   FEATURE_DIR = "/Users/robert/Code/new_specify/kitty-specs/001-a-simple-hello"
   tasks.md location: FEATURE_DIR + "/tasks.md"
   prompt location: FEATURE_DIR + "/tasks/WP01-slug.md"
   ```

   **DO NOT CREATE** paths like:
   - ❌ `tasks/WP01-slug.md` (missing FEATURE_DIR prefix)
   - ❌ `/tasks/WP01-slug.md` (wrong root)
   - ❌ `FEATURE_DIR/tasks/planned/WP01-slug.md` (WRONG - no subdirectories!)
   - ❌ `WP01-slug.md` (wrong directory)

2. **Load design documents** from `FEATURE_DIR` (only those present):
   - **Required**: plan.md (tech architecture, stack), spec.md (user stories & priorities)
   - **Optional**: data-model.md (entities), contracts/ (API schemas), research.md (decisions), quickstart.md (validation scenarios)
   - Scale your effort to the feature: simple UI tweaks deserve lighter coverage, multi-system releases require deeper decomposition.

3. **Derive fine-grained subtasks** (IDs `T001`, `T002`, ...):
   - Parse plan/spec to enumerate concrete implementation steps, tests (only if explicitly requested), migrations, and operational work.
   - Capture prerequisites, dependencies, and parallelizability markers (`[P]` means safe to parallelize per file/concern).
   - Maintain the subtask list internally; it feeds the work-package roll-up and the prompts.

4. **Roll subtasks into work packages** (IDs `WP01`, `WP02`, ...):
   - Target 4–10 work packages. Each should be independently implementable, rooted in a single user story or cohesive subsystem.
   - Ensure every subtask appears in exactly one work package.
   - Name each work package with a succinct goal (e.g., “User Story 1 – Real-time chat happy path”).
   - Record per-package metadata: priority, success criteria, risks, dependencies, and list of included subtasks.

5. **Write `tasks.md`** using `.kittify/templates/tasks-template.md`:
   - **Location**: Write to `FEATURE_DIR/tasks.md` (use the absolute FEATURE_DIR path from step 1)
   - Populate the Work Package sections (setup, foundational, per-story, polish) with the `WPxx` entries
   - Under each work package include:
     - Summary (goal, priority, independent test)
     - Included subtasks (checkbox list referencing `Txxx`)
     - Implementation sketch (high-level sequence)
     - Parallel opportunities, dependencies, and risks
   - Preserve the checklist style so implementers can mark progress

6. **Generate prompt files (one per work package)**:
   - **CRITICAL PATH RULE**: All work package files MUST be created in a FLAT `FEATURE_DIR/tasks/` directory, NOT in subdirectories!
   - Correct structure: `FEATURE_DIR/tasks/WPxx-slug.md` (flat, no subdirectories)
   - WRONG (do not create): `FEATURE_DIR/tasks/planned/`, `FEATURE_DIR/tasks/doing/`, or ANY lane subdirectories
   - WRONG (do not create): `/tasks/`, `tasks/`, or any path not under FEATURE_DIR
   - Ensure `FEATURE_DIR/tasks/` exists (create as flat directory, NO subdirectories)
   - For each work package:
     - Derive a kebab-case slug from the title; filename: `WPxx-slug.md`
     - Full path example: `FEATURE_DIR/tasks/WP01-create-html-page.md` (use ABSOLUTE path from FEATURE_DIR variable)
     - Use `.kittify/templates/task-prompt-template.md` to capture:
     - Frontmatter with `work_package_id`, `subtasks` array, `lane: "planned"`, `dependencies`, history entry
       - Objective, context, detailed guidance per subtask
       - Test strategy (only if requested)
       - Definition of Done, risks, reviewer guidance
     - Update `tasks.md` to reference the prompt filename
   - Keep prompts exhaustive enough that a new agent can complete the work package unaided

   **IMPORTANT**: All WP files live in flat `tasks/` directory. Lane status is tracked ONLY in the `lane:` frontmatter field, NOT by directory location. Agents can change lanes by editing the `lane:` field directly or using `spec-kitty agent tasks move-task`.

7. **Finalize tasks with dependency parsing and commit**:
   After generating all WP prompt files, run the finalization command to:
   - Parse dependencies from tasks.md
   - Update WP frontmatter with dependencies field
   - Validate dependencies (check for cycles, invalid references)
   - Commit all tasks to target branch

   **CRITICAL**: Run this command from repo root:
   ```bash
   spec-kitty agent feature finalize-tasks --json
   ```

   This step is MANDATORY for workspace-per-WP features. Without it:
   - Dependencies won't be in frontmatter
   - Agents won't know which --base flag to use
   - Tasks won't be committed to target branch

8. **Report**: Provide a concise outcome summary:
   - Path to `tasks.md`
   - Work package count and per-package subtask tallies
   - Parallelization highlights
   - MVP scope recommendation (usually Work Package 1)
   - Prompt generation stats (files written, directory structure, any skipped items with rationale)
   - Finalization status (dependencies parsed, X WP files updated, committed to target branch)
   - Next suggested command (e.g., `/spec-kitty.analyze` or `/spec-kitty.implement`)

Context for work-package planning: {ARGS}

The combination of `tasks.md` and the bundled prompt files must enable a new engineer to pick up any work package and deliver it end-to-end without further specification spelunking.

## Dependency Detection (0.11.0+)

**Parse dependencies from tasks.md structure**:

The LLM should analyze tasks.md for dependency relationships:
- Explicit phrases: "Depends on WP##", "Dependencies: WP##"
- Phase grouping: Phase 2 WPs typically depend on Phase 1
- Default to empty if unclear

**Generate dependencies in WP frontmatter**:

Each WP prompt file MUST include a `dependencies` field:
```yaml
---
work_package_id: "WP02"
title: "Build API"
lane: "planned"
dependencies: ["WP01"]  # Generated from tasks.md
subtasks: ["T001", "T002"]
---
```

**Include the correct implementation command**:
- No dependencies: `spec-kitty implement WP01`
- With dependencies: `spec-kitty implement WP02 --base WP01`

The WP prompt must show the correct command so agents don't branch from the wrong base.

## Task Generation Rules

**Tests remain optional**. Only include testing tasks/steps if the feature spec or user explicitly demands them.

1. **Subtask derivation**:
   - Assign IDs `Txxx` sequentially in execution order.
   - Use `[P]` for parallel-safe items (different files/components).
   - Include migrations, data seeding, observability, and operational chores.

2. **Work package grouping**:
   - Map subtasks to user stories or infrastructure themes.
   - Keep each work package laser-focused on a single goal; avoid mixing unrelated stories.
   - Do not exceed 10 work packages. Merge low-effort items into broader bundles when necessary.

3. **Prioritisation & dependencies**:
   - Sequence work packages: setup → foundational → story phases (priority order) → polish.
   - Call out inter-package dependencies explicitly in both `tasks.md` and the prompts.

4. **Prompt composition**:
   - Mirror subtask order inside the prompt.
   - Provide actionable implementation and test guidance per subtask—short for trivial work, exhaustive for complex flows.
   - Surface risks, integration points, and acceptance gates clearly so reviewers know what to verify.

5. **Think like a tester**: Any vague requirement should be tightened until a reviewer can objectively mark it done or not done.
