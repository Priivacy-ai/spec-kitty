---
description: Generate kanban-friendly task prompt files for the /tasks mini-board.
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

1. Run `{SCRIPT}` from repo root and parse `FEATURE_DIR` and `AVAILABLE_DOCS` (all absolute paths).

2. Load context artifacts needed for prompt generation:
   - `tasks.md` → capture task IDs, titles, phases, ordering.
   - `plan.md` (required) → architecture, tech stack, dependencies.
   - `spec.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md` if available.
   - `.specify/memory/constitution.md` → reference key principles.

3. Prepare the mini-kanban directory (if missing):
   - Ensure `/tasks/` exists at the feature root.
   - Create columns: `/tasks/planned/`, `/tasks/doing/`, `/tasks/for_review/`, `/tasks/done/`.
   - For large features, introduce optional phase subdirectories (e.g. `tasks/planned/phase-1-setup/`). Decide based on task volume and describe the structure in the report.

4. For each task in `tasks.md`:
   - Derive a short slug from the description (kebab case).
   - Name the prompt `TASK_ID-slug.md` (e.g. `T001-configure-linting.md`) so lexical sort preserves task order.
   - Choose the destination directory:
     * Default: `tasks/planned/`
     * Phase folders: `tasks/planned/phase-<n>-<label>/` when grouping is helpful.
   - Use `.specify/templates/task-prompt-template.md` as the skeleton:
     * Fill frontmatter (`task_id`, `title`, `phase`, `lane=planned`, history entry for creation).
     * Populate each section with rich, actionable instructions answering “What would a fresh agent need to deliver this perfectly?”
     * Reference canonical file paths and commands.
     * Include detailed implementation guidance, test strategy, and risks. Reserve summary-only content for `tasks.md`.
   - Save the prompt file to the chosen directory.

5. Cross-link artifacts:
   - Update the corresponding row in `tasks.md` to mention the prompt filename.
   - Add a short paragraph to `tasks.md` explaining that the prompt file holds the execution details (keep `tasks.md` concise).

6. Generate report output covering:
   - Total prompt files created and any skipped (with reason).
   - Directory layout summary (note phase subfolders if used).
   - Any prerequisites or follow-up actions for implementers.
   - Reminders about metadata updates (`lane`, `agent`, `shell_pid`) and `git mv` expectations when moving between kanban lanes.

7. Encourage team usage:
   - Mention helper scripts for capturing shell PID or updating metadata (if available).
   - Remind that agents must update frontmatter + Activity Log whenever they move a prompt.

Context for prompt generation: {ARGS}

The resulting prompt files must equip a brand-new agent with everything needed to implement the task without additional digging.
