# How to Generate Work Packages

Use this guide to turn a plan into work packages with `/spec-kitty.tasks`.

## Prerequisites

- `kitty-specs/<feature>/plan.md` exists
- All `[NEEDS CLARIFICATION]` items are resolved

## The Command

```text
/spec-kitty.tasks
```

## What Gets Created

- `kitty-specs/<feature>/tasks.md` (overview checklist)
- `kitty-specs/<feature>/tasks/WP01-*.md`, `WP02-*.md`, ... (prompt files)

Work packages live in a **flat** `tasks/` directory. Lane status is stored in each prompt file frontmatter via `lane: "planned"`.

## Understanding Work Packages

Each WP file contains:
- A single goal for the agent
- Subtasks and dependencies
- The exact completion command to move the WP to review

## Finalizing Tasks

After reviewing the generated WPs, finalize the task set:

```bash
spec-kitty agent feature finalize-tasks
```

## Example Output

```
kitty-specs/012-feature/tasks.md
kitty-specs/012-feature/tasks/WP01-auth-backend.md
kitty-specs/012-feature/tasks/WP02-auth-ui.md
kitty-specs/012-feature/tasks/WP03-tests.md
```

## Troubleshooting

- **Missing plan**: Run `/spec-kitty.plan` first.
- **Tasks look incomplete**: Resolve clarifications in `plan.md` and rerun `/spec-kitty.tasks`.
- **Wrong directory**: Run from the main repository root.

---

## Command Reference

- [Slash Commands](../reference/slash-commands.md) - All `/spec-kitty.*` commands
- [Agent Subcommands](../reference/agent-subcommands.md) - `finalize-tasks` and more
- [File Structure](../reference/file-structure.md) - Where tasks are stored

## See Also

- [Create a Plan](create-plan.md) - Required before task generation
- [Implement a Work Package](implement-work-package.md) - Next step after tasks
- [Handle Dependencies](handle-dependencies.md) - Managing WP dependencies

## Background

- [Kanban Workflow](../explanation/kanban-workflow.md) - Lane transitions explained
- [Workspace-per-WP Model](../explanation/workspace-per-wp.md) - Why one workspace per WP

## Getting Started

- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
