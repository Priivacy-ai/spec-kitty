---
title: How to Handle Work Package Dependencies
description: Declare, implement, and maintain dependencies between work packages in Spec Kitty.
---

# How to Handle Work Package Dependencies

Use dependencies to tell Spec Kitty which work packages (WPs) must land before another WP can safely build on them. Dependencies drive lane computation and keep parallel work predictable.

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

When a WP has dependencies, task finalization places it in the correct execution lane:

```bash
spec-kitty implement WP02
```

This resolves the correct lane workspace for WP02 with WP01's changes already present.

## Multiple Dependencies

Task finalization folds multi-dependency work into a lane plan before implementation starts. Agents do not choose a primary dependency or manually merge sibling lane outputs to reconstruct the plan.


## Keeping Dependencies Updated

When a dependency changes after you've started work, use `spec-kitty sync workspace` to update your workspace:

```bash
cd <workspace path printed by spec-kitty implement>
spec-kitty sync workspace
```

You may need to resolve conflicts during sync. See [Sync Workspaces](sync-workspaces.md).

## What Dependencies Do

- Influence lane computation during `finalize_tasks`
- Force dependent work into the same lane or into lanes with explicit ordering
- Ensure `spec-kitty implement WP##` resolves the correct workspace without manual branch selection

## Handling Rebase When Parent Changes

If the parent WP changes after your dependent WP is in progress, rebase the child workspace:

```bash
cd <workspace path printed by spec-kitty implement>

git rebase <base branch printed by spec-kitty>
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
WP02 has dependencies. Use: spec-kitty implement WP02
```

**Fix:** Re-run task finalization so the dependency graph is reflected in `lanes.json`.

## Tips

- Keep dependencies minimal to maximize parallelism.
- Choose the most foundational WP as the base when there are multiple dependencies.
- Use the workflow commands to keep lane changes and dashboards accurate.

---

## Command Reference

- [CLI Commands](../reference/cli-commands.md) - `spec-kitty implement` reference
- [Agent Subcommands](../reference/agent-subcommands.md) - Workflow commands

## See Also

- [Implement a Work Package](implement-work-package.md) - Implementing inside the computed lane workspace
- [Parallel Development](parallel-development.md) - Running multiple agents
- [Generate Tasks](generate-tasks.md) - Where dependencies are declared

## Background

- [Execution Lanes](../explanation/execution-lanes.md) - Why dependencies matter
- [Git Worktrees](../explanation/git-worktrees.md) - Branching mechanics
- [Kanban Workflow](../explanation/kanban-workflow.md) - Lane transitions

## Getting Started

- [Multi-Agent Workflow](../tutorials/multi-agent-workflow.md) - Parallel development tutorial
