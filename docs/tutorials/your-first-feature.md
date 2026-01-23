# Your First Feature: Complete Workflow

**Divio type**: Tutorial

This tutorial walks you through the entire Spec Kitty workflow from specification to merge.

**Time**: ~2 hours
**Prerequisites**: Completed [Getting Started](getting-started.md)

> **Note**: This tutorial uses git for version control. Spec Kitty abstracts the VCS operations into simple commands.

## Overview

Workflow path:

```
/spec-kitty.specify → /spec-kitty.plan → /spec-kitty.tasks → /spec-kitty.implement → /spec-kitty.review → /spec-kitty.accept → /spec-kitty.merge
```

You will build a tiny "task list" feature as the concrete example.

## Step 1: Create the Specification

From the project root, in your agent:

```text
/spec-kitty.specify Build a task list app with add, complete, and delete actions.
```

Answer the discovery interview until it completes.

Expected results:

- `kitty-specs/###-task-list/spec.md`
- A git commit on `main` with the new spec

## Step 2: Create the Technical Plan

Stay in the main repository (planning happens in `main` in v0.11.0+).

In your agent:

```text
/spec-kitty.plan Use Python 3.11, SQLite, and a minimal CLI interface.
```

Answer the planning questions and confirm the Engineering Alignment summary.

Expected results:

- `kitty-specs/###-task-list/plan.md`
- A git commit on `main` with the plan

## Step 3: Generate Work Packages

In your agent:

```text
/spec-kitty.tasks
```

This generates `tasks.md` and individual work package files under:

```
kitty-specs/###-task-list/tasks/
```

Each WP file includes frontmatter with its `lane` and dependencies.

## Step 4: Implement a Work Package

Start with the first planned package (example uses `WP01`).

In your agent:

```text
/spec-kitty.implement
```

This moves the WP to `doing` and prints the implementation prompt. Then create the workspace from your terminal:

```bash
spec-kitty implement WP01
```

Expected output (abridged):

```
OK Created workspace: .worktrees/###-task-list-WP01
```

Move into the new worktree and implement the required changes:

```bash
cd .worktrees/###-task-list-WP01
```

When finished, return to the main repo and run the review step.

## Step 5: Review Your Work

From the main repo, ask your agent to review the work package.

In your agent:

```text
/spec-kitty.review
```

Or via CLI:

```bash
spec-kitty agent workflow review WP01
```

Follow the review instructions and address any feedback.

## Step 6: Accept and Merge

Once review passes, validate and accept.

In your agent:

```text
/spec-kitty.accept
```

Or via CLI:

```bash
spec-kitty accept
```

Then merge the feature branches.

In your agent:

```text
/spec-kitty.merge
```

Or via CLI:

```bash
spec-kitty merge
```

You should see the feature merged into `main` and the worktrees cleaned up.

## Troubleshooting

- **"Planning created a worktree"**: In v0.11.0+, planning stays in `main`. If you see a feature worktree, upgrade with `spec-kitty upgrade`.
- **"WP has dependencies"**: If the WP frontmatter lists dependencies, run `spec-kitty implement WP02 --base WP01` as suggested.
- **Review fails validation**: Run `spec-kitty validate-tasks --fix` and re-run `/spec-kitty.review`.

## What's Next?

Continue with [Multi-Agent Workflow](multi-agent-workflow.md) to learn parallel development with multiple agents.

### Related How-To Guides

- [Create a Plan](../how-to/create-plan.md) - Detailed planning guidance
- [Generate Tasks](../how-to/generate-tasks.md) - Work package generation
- [Implement a Work Package](../how-to/implement-work-package.md) - Implementation details
- [Review a Work Package](../how-to/review-work-package.md) - Review process
- [Accept and Merge](../how-to/accept-and-merge.md) - Final merge workflow

### Reference Documentation

- [CLI Commands](../reference/cli-commands.md) - Full command reference
- [Slash Commands](../reference/slash-commands.md) - Agent slash commands
- [File Structure](../reference/file-structure.md) - Project layout explained

### Learn More

- [Workspace-per-WP Model](../explanation/workspace-per-wp.md) - Why one workspace per WP
- [Kanban Workflow](../explanation/kanban-workflow.md) - Lane transitions
- [Spec-Driven Development](../explanation/spec-driven-development.md) - The philosophy
