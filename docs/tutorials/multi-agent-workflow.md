# Multi-Agent Parallel Development

**Divio type**: Tutorial

Learn how to coordinate multiple AI agents working on different work packages simultaneously.

**Time**: ~1 hour
**Prerequisites**: Completed [Your First Feature](your-first-feature.md)

## Why Parallel Development?

- Shorter delivery time by splitting work packages
- Clear isolation with dedicated worktrees
- Reduced merge conflicts


## Understanding Work Package Dependencies

Common dependency patterns:

- **Linear**: WP02 depends on WP01
- **Fan-out**: WP01 unblocks multiple packages
- **Diamond**: WP02 and WP03 depend on WP01, then WP04 depends on both

Dependencies are declared in each WP frontmatter.

## Hands-On: Two Agents, Two WPs

### Setup

Generate work packages for your feature.

In your agent:

```text
/spec-kitty.tasks
```

Confirm two independent packages are `lane: "planned"`.

### Terminal 1: Agent A on WP01

```bash
spec-kitty agent workflow implement WP01
cd .worktrees/###-feature-WP01
# Agent A works here
```

### Terminal 2: Agent B on WP02

```bash
spec-kitty agent workflow implement WP02
cd .worktrees/###-feature-WP02
# Agent B works here simultaneously
```

Each agent updates only their own worktree. Do not edit another agent's worktree.

## Handling Dependencies with --base

If WP02 depends on WP01, create WP02 from the WP01 base:

```bash
spec-kitty implement WP02 --base WP01
```

Expected output (abridged):

```
OK Created workspace: .worktrees/###-feature-WP02
```

## Git Worktrees, Briefly

Each work package is a Git worktree on its own branch. This keeps changes isolated and lets agents work in parallel without merge conflicts. For details, see [Workspace-per-WP](../explanation/workspace-per-wp.md) and [Git Worktrees](../explanation/git-worktrees.md).

## Tips for Coordinating Agents

- Run `spec-kitty agent tasks list-tasks` to see current lanes.
- Use `spec-kitty agent tasks add-history WP## --note "..."` to share progress.
- Avoid overlapping file edits across WPs.

## Troubleshooting

- **"WP has dependencies"**: Re-run with `spec-kitty implement WP## --base WPXX`.
- **Worktree already exists**: Run `git worktree list` and reuse the existing folder.
- **Agent edits the wrong WP**: Stop and switch to the correct worktree before continuing.

## What's Next?

You've completed the core tutorials. Explore how-to guides for specific tasks or explanations for deeper understanding.

### Related How-To Guides

- [Parallel Development](../how-to/parallel-development.md) - Run multiple agents simultaneously
- [Handle Dependencies](../how-to/handle-dependencies.md) - Manage WP dependencies
- [Implement a Work Package](../how-to/implement-work-package.md) - Detailed implementation steps
- [Use the Dashboard](../how-to/use-dashboard.md) - Monitor progress in real time

### Reference Documentation

- [Agent Subcommands](../reference/agent-subcommands.md) - Agent workflow commands
- [CLI Commands](../reference/cli-commands.md) - Full command reference
- [File Structure](../reference/file-structure.md) - Worktree layout

### Learn More

- [Multi-Agent Orchestration](../explanation/multi-agent-orchestration.md) - Coordination patterns
- [Workspace-per-WP Model](../explanation/workspace-per-wp.md) - Isolation strategy
- [Git Worktrees](../explanation/git-worktrees.md) - How worktrees work
