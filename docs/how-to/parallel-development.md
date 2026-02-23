---
title: How to Develop in Parallel with Multiple Agents
description: Run multiple Spec Kitty agents in parallel while keeping work packages isolated and coordinated.
---

# How to Develop in Parallel with Multiple Agents

Parallel development lets you move independent work packages (WPs) at the same time while keeping each workspace isolated. Spec Kitty's worktree-per-WP model makes this safe and predictable.

## Why Parallel Development?

- Shorten delivery time by running independent WPs concurrently.
- Keep changes isolated to avoid accidental cross-contamination.
- Use the dashboard to coordinate and rebalance work in real time.


## Prerequisites

- A feature with multiple WPs in `lane: "planned"`.
- Multiple terminals or agents available.
- Dependencies defined in WP frontmatter.

## Identifying Parallel Opportunities

1. List WPs and their dependencies.
2. Start WPs that do not depend on each other.
3. Hold any WP that depends on unfinished work.

## Example: Two Independent WPs

### Terminal 1 - Agent A

```bash
spec-kitty agent workflow implement WP01
cd .worktrees/###-feature-WP01
# Agent A implements WP01
```

### Terminal 2 - Agent B (simultaneously)

```bash
spec-kitty agent workflow implement WP02
cd .worktrees/###-feature-WP02
# Agent B implements WP02
```

## Example: Fan-Out Pattern

```
        WP01
      /  |  \
   WP02 WP03 WP04
```

Once WP01 is finished, three agents can work on WP02, WP03, and WP04 in parallel.

## Example: Dependent WPs

```bash
# Agent A completes WP01 first
spec-kitty agent workflow implement WP01
# ... implement and finish WP01

# Agent B starts WP02 after WP01 exists
spec-kitty implement WP02 --base WP01
cd .worktrees/###-feature-WP02
```

## Best Practices

- Start with dependency-free WPs, then fan out.
- Communicate when base WPs complete so dependents can start.
- Keep each agent in its own worktree path.
- Use workflow commands to keep lane history and dashboard accurate.

## Monitoring Parallel Work

In your terminal:

```bash
spec-kitty agent tasks status
```

Or in your agent:

```text
/spec-kitty.status
```

Use the dashboard to monitor lane movement and agent activity in real time.

---

## Command Reference

- [Agent Subcommands](../reference/agent-subcommands.md) - Workflow commands for agents
- [CLI Commands](../reference/cli-commands.md) - Full CLI reference
- [Orchestrator API](../reference/orchestrator-api.md) - Host contract for external automation providers

## See Also

- [Handle Dependencies](handle-dependencies.md) - Managing WP dependencies
- [Implement a Work Package](implement-work-package.md) - Starting a WP
- [Use the Dashboard](use-dashboard.md) - Monitor parallel progress

## Background

- [Multi-Agent Orchestration](../explanation/multi-agent-orchestration.md) - Coordination patterns
- [Workspace-per-WP Model](../explanation/workspace-per-wp.md) - Isolation strategy
- [Git Worktrees](../explanation/git-worktrees.md) - How worktrees work

## Getting Started

- [Multi-Agent Workflow](../tutorials/multi-agent-workflow.md) - Hands-on parallel tutorial
- [Run External Orchestrator](run-external-orchestrator.md) - Automate lane transitions with `spec-kitty-orchestrator`
