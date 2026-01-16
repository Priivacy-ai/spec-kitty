# How to Implement a Work Package

Use this guide to implement a single work package (WP) in its own workspace.

## Prerequisites

- Tasks have been generated and finalized
- You know the WP ID (for example, `WP01`)

## Step 1: Get the WP Prompt

Use the slash command in your agent (recommended):

```text
/spec-kitty.implement
```

Or run the workflow command directly:

```bash
spec-kitty agent workflow implement WP01 --agent <agent>
```

This moves the WP to `lane: "doing"` and prints the full prompt plus the completion command.

## Step 2: Create the Workspace

In your terminal:

```bash
spec-kitty implement WP01
```

If the WP depends on another WP, branch from the base work package:

```bash
spec-kitty implement WP02 --base WP01
```

## Step 3: Work in the Worktree

In your terminal:

```bash
cd .worktrees/###-feature-WP01
```

Implement the prompt, run required tests, and commit your changes in the WP worktree.

## Step 4: Mark the WP Ready for Review

Use the exact command printed in the prompt. In your terminal:

```bash
spec-kitty agent tasks move-task WP01 --to for_review --note "Ready for review: <summary>"
```

## What Happens

- A dedicated worktree is created for the WP (`.worktrees/###-feature-WP01/`)
- The WP lane is updated to `doing`
- Dependencies are enforced via `--base`

## Troubleshooting

- **"Base workspace does not exist"**: Implement the dependency first.
- **"WP has dependencies"**: Re-run with `--base WPXX`.
- **No prompt shown**: Run `/spec-kitty.implement` or `spec-kitty agent workflow implement` again.

---

## Command Reference

- [Slash Commands](../reference/slash-commands.md) - All `/spec-kitty.*` commands
- [Agent Subcommands](../reference/agent-subcommands.md) - Workflow commands
- [CLI Commands](../reference/cli-commands.md) - Full CLI reference

## See Also

- [Generate Tasks](generate-tasks.md) - Required before implementation
- [Handle Dependencies](handle-dependencies.md) - Using `--base` for dependent WPs
- [Review a Work Package](review-work-package.md) - Next step after implementation

## Background

- [Workspace-per-WP Model](../explanation/workspace-per-wp.md) - Why one workspace per WP
- [Git Worktrees](../explanation/git-worktrees.md) - How worktrees work
- [Kanban Workflow](../explanation/kanban-workflow.md) - Lane transitions

## Getting Started

- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
- [Multi-Agent Workflow](../tutorials/multi-agent-workflow.md) - Parallel development
