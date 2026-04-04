# How to Implement a Work Package

Use this guide to implement a single work package (WP) in its execution workspace.

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

## Step 2: Create or Resolve the Workspace

In your terminal:

```bash
spec-kitty implement WP01
```

If the WP depends on another WP, branch from the base work package:

```bash
spec-kitty implement WP02 --base WP01
```

## Step 3: Work in the Resolved Worktree

In your terminal:

```bash
cd <path printed by spec-kitty agent workflow implement>
```

Implement the prompt, run required tests, and commit your changes in that workspace. Modern features may place multiple sequential WPs in a shared lane worktree such as `.worktrees/###-feature-lane-a`; legacy features without lanes still use `.worktrees/###-feature-WP##`.

## Step 4: Mark the WP Ready for Review

Use the exact command printed in the prompt. In your terminal:

```bash
spec-kitty agent tasks move-task WP01 --to for_review --note "Ready for review: <summary>"
```

## What Happens

- An execution workspace is created or reused for the WP (`.worktrees/###-feature-lane-a/` for lane-based features, `.worktrees/###-feature-WP01/` for legacy features)
- The WP lane is updated to `doing`
- Dependencies are enforced via `--base`

> **Note**: Modern Spec Kitty creates one git worktree per execution lane. Sequential WPs in the same lane share that workspace and lane branch. Older features without `lanes.json` still use one worktree per WP.

> **Fallback behavior**: If `lanes.json` exists but `lane_for_wp()` returns `None` for the WP you asked for, Spec Kitty does not guess a lane. It falls back to the legacy per-WP workspace contract (`.worktrees/<feature>-WP##`) until the lane metadata is corrected.

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

- [Execution Workspace Model](../explanation/workspace-per-wp.md) - How lane worktrees and legacy WP worktrees coexist
- [Git Worktrees](../explanation/git-worktrees.md) - How worktrees work
- [Kanban Workflow](../explanation/kanban-workflow.md) - Lane transitions

## Getting Started

- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
- [Multi-Agent Workflow](../tutorials/multi-agent-workflow.md) - Parallel development
