---
title: How to Handle Work Package Dependencies
description: Declare, implement, and maintain dependencies between work packages in Spec Kitty.
---

# How to Handle Work Package Dependencies

Use dependencies to tell Spec Kitty which work packages (WPs) must land before another WP can safely build on them. Dependencies drive the `--base` workflow and keep parallel work predictable.

## Understanding Dependencies

Dependencies are defined in each WP's frontmatter and describe upstream work that must exist for the current WP to compile, test, or merge.

```yaml
---
work_package_id: "WP02"
title: "Build API"
dependencies: ["WP01"]
---
```

## Declaring Dependencies

Declare dependencies as a YAML list in the WP frontmatter:

```yaml
dependencies: ["WP01"]
```

For multiple dependencies:

```yaml
dependencies: ["WP01", "WP03"]
```

## Implementing with Dependencies

When a WP has dependencies, implement it with a base WP so your workspace branches from the correct upstream:

```bash
spec-kitty implement WP02 --base WP01
```

This creates the WP02 workspace with WP01's changes already present.

## Multiple Dependencies

Git can only branch from one base commit, so you choose the primary dependency and merge the others manually:

```bash
spec-kitty implement WP04 --base WP03
cd .worktrees/###-feature-WP04

# Merge the other dependency manually
git merge ###-feature-WP02
```


## Keeping Dependencies Updated

When a dependency changes after you've started work, use `spec-kitty sync workspace` to update your workspace:

```bash
cd .worktrees/###-feature-WP02
spec-kitty sync workspace
```

You may need to resolve conflicts during sync. See [Sync Workspaces](sync-workspaces.md).

## What `--base` Does

- Creates the new WP branch from the base WP branch.
- Includes all code from the base WP in the child workspace.
- Validates the `--base` flag against the declared dependencies and prompts if it does not match.

## Handling Rebase When Parent Changes

If the parent WP changes after your dependent WP is in progress, rebase the child workspace:

```bash
cd .worktrees/###-feature-WP02

git rebase ###-feature-WP01
```

Repeat for each dependent WP that needs the updated base.

## Common Dependency Patterns

### Linear Chain

```
WP01 -> WP02 -> WP03 -> WP04
```

### Fan-Out

```
        WP01
      /  |  \
   WP02 WP03 WP04
```

### Diamond

```
      WP01
     /    \
  WP02   WP03
     \    /
      WP04
```

## Common Errors and Fixes

**Error:**
```
WP02 has dependencies. Use: spec-kitty implement WP02 --base WP01
```

**Fix:** Re-run with the suggested `--base` flag.

## Tips

- Keep dependencies minimal to maximize parallelism.
- Choose the most foundational WP as the base when there are multiple dependencies.
- Use the workflow commands to keep lane changes and dashboards accurate.

---

## Command Reference

- [CLI Commands](../reference/cli-commands.md) - `spec-kitty implement` reference
- [Agent Subcommands](../reference/agent-subcommands.md) - Workflow commands

## See Also

- [Implement a Work Package](implement-work-package.md) - Using `--base` in practice
- [Parallel Development](parallel-development.md) - Running multiple agents
- [Generate Tasks](generate-tasks.md) - Where dependencies are declared

## Background

- [Workspace-per-WP Model](../explanation/workspace-per-wp.md) - Why dependencies matter
- [Git Worktrees](../explanation/git-worktrees.md) - Branching mechanics
- [Kanban Workflow](../explanation/kanban-workflow.md) - Lane transitions

## Getting Started

- [Multi-Agent Workflow](../tutorials/multi-agent-workflow.md) - Parallel development tutorial
