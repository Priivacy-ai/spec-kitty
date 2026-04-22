# Your First Feature: Complete Workflow

**Divio type**: Tutorial

This tutorial walks you through the entire Spec Kitty workflow from specification to merge.

**Time**: ~2 hours
**Prerequisites**: Completed [Getting Started](getting-started.md)

> **Note**: This tutorial uses git for version control. Spec Kitty abstracts the VCS operations into simple commands.

## Overview

Workflow path:

```
/spec-kitty.specify → /spec-kitty.plan → /spec-kitty.tasks → spec-kitty next → /spec-kitty.accept → /spec-kitty.merge
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
- A new mission directory created under `kitty-specs/`

## Step 2: Create the Technical Plan

Stay in the repository root checkout. Planning happens there, but the mission target branch can be the current branch or an explicit branch you chose before creation.

In your agent:

```text
/spec-kitty.plan Use Python 3.11, SQLite, and a minimal CLI interface.
```

Answer the planning questions and confirm the Engineering Alignment summary.

Expected results:

- `kitty-specs/###-task-list/plan.md`
- Updated planning artifacts in the repository root checkout

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

## Step 4: Enter the Runtime Loop

Start the mission loop from your terminal:

```bash
spec-kitty next --agent claude --mission ###-task-list --json
```

The runtime returns the next action to take. During implementation you will usually see an `implement` decision for a specific WP.

Execute that action with the lower-level command the runtime expects:

```bash
spec-kitty agent action implement WP01 --agent claude
```

That command allocates or reuses the correct lane workspace. Make your code changes there, run the relevant tests, then report the result back to the runtime:

```bash
spec-kitty next --agent claude --mission ###-task-list --result success --json
```

Repeat the loop until the runtime starts issuing review work instead of implementation work.

## Step 5: Review the Work Package

When the runtime points you at review work, run the matching action:

```bash
spec-kitty agent action review WP01 --agent claude
```

Address any review feedback, then continue the `spec-kitty next` loop until the mission is ready for acceptance.

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

You should see the feature merged into the mission's target branch and the worktrees cleaned up.

## Troubleshooting

- **"Planning created a worktree"**: Planning stays in the repository root checkout in `3.1.x`. If you see an unexpected planning worktree, upgrade with `spec-kitty upgrade`.
- **"I want to plan from here but not land on `main`"**: Stay in the repository root checkout and choose the right target branch first. See [How to Keep Main Clean](../how-to/keep-main-clean.md).
- **"WP has dependencies"**: Keep following the `spec-kitty next` decisions; the runtime will only issue implementation work when its dependencies are satisfied.
- **Review fails validation**: Run `spec-kitty validate-tasks --fix` and re-run `/spec-kitty.review`.

## What's Next?

Continue with [Multi-Agent Workflow](multi-agent-workflow.md) to learn parallel development with multiple agents.

### Related How-To Guides

- [Create a Plan](../how-to/create-plan.md) - Detailed planning guidance
- [Keep Main Clean](../how-to/keep-main-clean.md) - Choose a target branch without changing planning location
- [Generate Tasks](../how-to/generate-tasks.md) - Work package generation
- [Implement a Work Package](../how-to/implement-work-package.md) - Implementation details
- [Review a Work Package](../how-to/review-work-package.md) - Review process
- [Accept and Merge](../how-to/accept-and-merge.md) - Final merge workflow

### Reference Documentation

- [CLI Commands](../reference/cli-commands.md) - Full command reference
- [Slash Commands](../reference/slash-commands.md) - Agent slash commands
- [File Structure](../reference/file-structure.md) - Project layout explained

### Learn More

- [Execution Workspace Model](../explanation/execution-lanes.md) - Why modern features use lane worktrees
- [Kanban Workflow](../explanation/kanban-workflow.md) - Lane transitions
- [Spec-Driven Development](../explanation/spec-driven-development.md) - The philosophy
