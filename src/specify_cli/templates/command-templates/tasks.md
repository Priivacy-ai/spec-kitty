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

1. Run `spec-kitty agent feature check-prerequisites --json --paths-only --include-tasks` from the repository root and capture:
   - `current_branch`
   - `target_branch` / `base_branch`
   - `planning_base_branch` / `merge_target_branch`
   - `branch_matches_target`
   - `TARGET_BRANCH` / `BASE_BRANCH` (uppercase aliases)
   - `feature_dir`, `artifact_files`, `artifact_dirs`

   Treat this JSON as canonical branch context for this command. Do not read `meta.json` to infer branch expectations.
   If `branch_matches_target` is false, stop and tell the user the current checkout does not match the intended planning branch. Do not probe git manually; `check-prerequisites` already resolved this in Python.

Work packages are generated directly in `kitty-specs/###-feature/` and committed to the target branch. Worktrees are created later when implementing each work package.

## Outline

1. **Detect feature context** (mandatory in new sessions):
   - Resolve the feature slug from explicit user direction, current branch, or current directory path.
   - If context is ambiguous, run `check-prerequisites` once without `--feature`, parse the JSON candidate list, and pick one explicit feature slug before continuing.

2. **Setup**: Run `spec-kitty agent feature check-prerequisites --json --paths-only --include-tasks --feature <feature-slug>` from the repository root and capture:
   - `feature_dir`
   - `artifact_files` / `artifact_dirs` (if present)
   - `available_docs`
   - `current_branch`
   - `target_branch` / `base_branch`
   - `planning_base_branch` / `merge_target_branch`
   - `branch_matches_target`
   All paths must be absolute.

   **CRITICAL**: The command returns JSON with `feature_dir` as an ABSOLUTE path (e.g., `/Users/robert/Code/new_specify/kitty-specs/001-feature-name`).
   It also returns `runtime_vars.now_utc_iso` (`NOW_UTC_ISO`) for deterministic timestamp fields.

   **YOU MUST USE THIS PATH** for ALL subsequent file operations. Example:
   ```
   feature_dir = "/Users/robert/Code/new_specify/kitty-specs/001-a-simple-hello"
   tasks.md location: feature_dir + "/tasks.md"
   prompt location: feature_dir + "/tasks/WP01-slug.md"
   ```

   **DO NOT CREATE** paths like:
   - ❌ `tasks/WP01-slug.md` (missing feature_dir prefix)
   - ❌ `/tasks/WP01-slug.md` (wrong root)
   - ❌ `feature_dir/tasks/planned/WP01-slug.md` (WRONG - no subdirectories!)
   - ❌ `WP01-slug.md` (wrong directory)

3. **Load design documents** from `feature_dir` (only those present):
   - **Required**: plan.md (tech architecture, stack), spec.md (user stories & priorities)
   - **Optional**: data-model.md (entities), contracts/ (API schemas), research.md (decisions), quickstart.md (validation scenarios)
   - Scale your effort to the feature: simple UI tweaks deserve lighter coverage, multi-system releases require deeper decomposition.

4. **Derive fine-grained subtasks** (IDs `T001`, `T002`, ...):
   - Parse plan/spec to enumerate concrete implementation steps, tests (only if explicitly requested), migrations, and operational work.
   - Capture prerequisites, dependencies, and parallelizability markers (`[P]` means safe to parallelize per file/concern).
   - Maintain the subtask list internally; it feeds the work-package roll-up and the prompts.

5. **Roll subtasks into work packages** (IDs `WP01`, `WP02`, ...):
   - Target 4–10 work packages. Each should be independently implementable, rooted in a single user story or cohesive subsystem.
   - Ensure every subtask appears in exactly one work package.
   - Name each work package with a succinct goal (e.g., “User Story 1 – Real-time chat happy path”).
   - Record per-package metadata: priority, success criteria, risks, dependencies, and list of included subtasks.

6. **Write `tasks.md`** using `.kittify/templates/tasks-template.md`:
   - **Location**: Write to `feature_dir/tasks.md` (use the absolute feature_dir path from step 1)
   - Populate the Work Package sections (setup, foundational, per-story, polish) with the `WPxx` entries
   - Under each work package include:
     - Summary (goal, priority, independent test)
     - Included subtasks (checkbox list referencing `Txxx`)
     - Implementation sketch (high-level sequence)
     - Parallel opportunities, dependencies, and risks
   - Preserve the checklist style so implementers can mark progress

7. **Generate prompt files (one per work package)**:
   - **CRITICAL PATH RULE**: All work package files MUST be created in a FLAT `feature_dir/tasks/` directory, NOT in subdirectories!
   - Correct structure: `feature_dir/tasks/WPxx-slug.md` (flat, no subdirectories)
   - WRONG (do not create): `feature_dir/tasks/planned/`, `feature_dir/tasks/doing/`, or ANY lane subdirectories
   - WRONG (do not create): `/tasks/`, `tasks/`, or any path not under feature_dir
   - Use `artifact_dirs.tasks_dir` when available.
   - Do **not** shell out with `mkdir -p`; `create-feature` already creates `tasks/` in normal flow.
   - If `tasks/` is missing unexpectedly, report the path mismatch instead of improvising shell setup.
   - For each work package:
     - Derive a kebab-case slug from the title; filename: `WPxx-slug.md`
     - Full path example: `feature_dir/tasks/WP01-create-html-page.md` (use ABSOLUTE path from feature_dir variable)
     - Use `.kittify/templates/task-prompt-template.md` to capture:
     - Frontmatter with `work_package_id`, `subtasks` array, `lane: "planned"`, `dependencies`, `planning_base_branch`, `merge_target_branch`, `branch_strategy`, and history entry
       - Objective, context, detailed guidance per subtask
       - A Branch Strategy section that repeats the planning branch, final merge target, and notes that the actual `base_branch` may later differ for stacked WPs during `/spec-kitty.implement`
       - Test strategy (only if requested)
       - Definition of Done, risks, reviewer guidance
     - Update `tasks.md` to reference the prompt filename
   - Keep prompts exhaustive enough that a new agent can complete the work package unaided

   **IMPORTANT**: All WP files live in flat `tasks/` directory. Lane status is tracked ONLY in the `lane:` frontmatter field, NOT by directory location. Agents can change lanes by editing the `lane:` field directly or using `spec-kitty agent tasks move-task`.

8. **Finalize tasks with dependency parsing and commit**:
   After generating all WP prompt files, run the finalization command to:
   - Parse dependencies from tasks.md
   - Update WP frontmatter with dependencies field
   - Validate dependencies (check for cycles, invalid references)
   - Commit all tasks to target branch

   **CRITICAL**: Run this command from repo root:
   ```bash
   spec-kitty agent feature finalize-tasks --json --feature <feature-slug>
   ```

   This step is MANDATORY for workspace-per-WP features. Without it:
   - Dependencies won't be in frontmatter
   - Branching-strategy metadata won't be normalized into every WP prompt
   - Requirement refs won't be validated/normalized
   - Agents won't know which --base flag to use
   - Tasks won't be committed to target branch

9. **Report**: Provide a concise outcome summary:
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

## Requirement Reference Mapping (MANDATORY)

After creating all WP sections and prompt files, register requirement mappings using the CLI.
The CLI validates each ref against spec.md and writes `requirement_refs` directly into each
WP file's YAML frontmatter — no sidecar files needed.

**Batch mode (recommended)** — register all WP mappings at once:
```bash
spec-kitty agent tasks map-requirements --batch '{"WP01":["FR-001","FR-002"],"WP02":["FR-003","FR-004"]}' --json
```

**Individual mode** — register one WP at a time:
```bash
spec-kitty agent tasks map-requirements --wp WP01 --refs FR-001,FR-002 --json
```

The response includes a coverage summary showing which FRs are still unmapped. Keep calling
until `unmapped_functional` is empty. Default mode unions new refs with existing ones in
frontmatter. Use `--replace` to overwrite a WP's refs (e.g., to correct a bad mapping).

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
