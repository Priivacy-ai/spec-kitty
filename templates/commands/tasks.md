---
description: Generate grouped work packages with actionable subtasks and matching prompt files for the feature in one pass.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -IncludeTasks
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Setup**: Run `{SCRIPT}` from repo root and capture `FEATURE_DIR` plus `AVAILABLE_DOCS`. All paths must be absolute.

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

5. **Write `tasks.md`** using `.specify/templates/tasks-template.md`:
   - Populate the Work Package sections (setup, foundational, per-story, polish) with the `WPxx` entries.
   - Under each work package include:
     - Summary (goal, priority, independent test)
     - Included subtasks (checkbox list referencing `Txxx`)
     - Implementation sketch (high-level sequence)
     - Parallel opportunities, dependencies, and risks
   - Preserve the checklist style so implementers can mark progress.

6. **Generate prompt files (one per work package)**:
   - Ensure `/tasks/planned/` exists (create `/tasks/doing/`, `/tasks/for_review/`, `/tasks/done/` if missing). Create optional phase subfolders when teams will benefit.
   - For each work package:
     - Derive a kebab-case slug from the title; filename: `WPxx-slug.md`.
     - Use `.specify/templates/task-prompt-template.md` (now tailored for bundles) to capture:
       - Frontmatter with `work_package_id`, an ordered `subtasks` array listing each `Txxx`, `lane=planned`, and a history entry marking creation via `/speckitty.tasks`.
       - Objective, context, and detailed guidance broken down by subtask.
       - Consolidated test strategy (only when requested).
       - Explicit Definition of Done, risks, reviewer guidance.
     - Update the corresponding section in `tasks.md` to reference the prompt filename.
   - Keep prompts exhaustive enough that a new agent can complete the entire work package unaided.

7. **Report**: Provide a concise outcome summary:
   - Path to `tasks.md`
   - Work package count and per-package subtask tallies
   - Parallelization highlights
   - MVP scope recommendation (usually Work Package 1)
  - Prompt generation stats (files written, directory structure, any skipped items with rationale)
   - Next suggested command (e.g., `/speckitty.analyze` or `/speckitty.implement`)

Context for work-package planning: {ARGS}

The combination of `tasks.md` and the bundled prompt files must enable a new engineer to pick up any work package and deliver it end-to-end without further specification spelunking.

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
