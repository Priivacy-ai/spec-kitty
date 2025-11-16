---
description: Perform structured code review and kanban transitions for completed task prompt files.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -IncludeTasks
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check (CRITICAL for AI Agents)

Before proceeding with review, verify you are in the correct working directory by running the shared pre-flight validation:

```python
from specify_cli.guards import validate_worktree_location

# Validate location
result = validate_worktree_location()
if not result.is_valid:
    print(result.format_error())
    print("\nThis command MUST run from a feature worktree, not the main repository.")
    exit(1)
```

**What this validates**:
- Current branch follows the feature pattern like `001-feature-name`
- You're not attempting to run from `main` or any release branch
- The validator prints clear navigation instructions if you're outside the feature worktree

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

## Outline

1. Run `{SCRIPT}` from repo root; capture `FEATURE_DIR`, `AVAILABLE_DOCS`, and `tasks.md` path.

2. Determine the review target:
   - If user input specifies a filename, validate it exists under `tasks/for_review/` (support phase subdirectories).
   - Otherwise, select the oldest file in `tasks/for_review/` (lexical order is sufficient because filenames retain task ordering).
   - Abort with instructional message if no files are waiting for review.

3. Load context for the selected task:
   - Read the prompt file frontmatter (lane MUST be `for_review`); note `task_id`, `phase`, `agent`, `shell_pid`.
   - Read the body sections (Objective, Context, Implementation Guidance, etc.).
   - Consult supporting documents as referenced: constitution, plan, spec, data-model, contracts, research, quickstart, code changes.
   - Review the associated code in the repository (diffs, tests, docs) to validate the implementation.

4. Conduct the review:
   - Verify implementation against the prompt’s Definition of Done and Review Guidance.
   - Run required tests or commands; capture results.
   - Document findings explicitly: bugs, regressions, missing tests, risks, or validation notes.

5. Decide outcome:
  - **Needs changes**:
     * Append a new entry in the prompt’s **Activity Log** detailing feedback (include timestamp, reviewer agent, shell PID).
     * Update frontmatter `lane` back to `planned`, clear `assignee` if necessary, keep history entry.
     * Add/revise a `## Review Feedback` section (create if missing) summarizing action items.
     * Run `.kittify/scripts/bash/tasks-move-to-lane.sh <FEATURE> <TASK_ID> planned --note "Returned for changes"` (use the PowerShell equivalent on Windows) so the move and history update are staged consistently.
  - **Approved**:
     * Append Activity Log entry capturing approval details (capture shell PID via `echo $$` or helper script).
     * Update frontmatter: set `lane=done`, set reviewer metadata (`agent`, `shell_pid`), optional `assignee` for approver.
     * Use helper script to mark the task complete in `tasks.md` (see Step 6).
     * Run `.kittify/scripts/bash/tasks-move-to-lane.sh <FEATURE> <TASK_ID> done --note "Approved for release"` (PowerShell variant available) to transition the prompt into `tasks/done/`.

6. Update `tasks.md` automatically:
   - Run `scripts/bash/mark-task-status.sh --task-id <TASK_ID> --status done` (POSIX) or `scripts/powershell/Set-TaskStatus.ps1 -TaskId <TASK_ID> -Status done` (PowerShell) from repo root.
   - Confirm the task entry now shows `[X]` and includes a reference to the prompt file in its notes.

7. Produce a review report summarizing:
   - Task ID and filename reviewed.
  - Approval status and key findings.
   - Tests executed and their results.
   - Follow-up actions (if any) for other team members.
   - Reminder to push changes or notify teammates as per project conventions.

Context for review: {ARGS}

All review feedback must live inside the prompt file, ensuring future implementers understand historical decisions before revisiting the task.
