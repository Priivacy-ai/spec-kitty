---
title: Multi-Agent Orchestration
description: Best practices for coordinating multiple AI agents with Spec Kitty's workspace-per-WP model.
---

# Multi-Agent Orchestration

Spec Kitty was designed for **multi-agent development orchestration**—it keeps parallel assistants synchronized while protecting the quality of shared artifacts. This guide outlines patterns that help teams run many AI agents in parallel without incurring merge chaos.

## Core Principles

1. **Planning in main, implementation in worktrees:** All planning (`/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks`) happens in the main repository. Worktrees are created on-demand for each work package during implementation.
2. **One worktree per work package:** Each WP gets its own isolated worktree and branch (e.g., `.worktrees/001-feature-WP01/`), enabling true parallel development.
3. **Command discipline:** Slash commands enforce gated, automated steps so agents cannot skip discovery or validation.
4. **Lane-driven coordination:** Tasks move through `planned → doing → for_review → done` via frontmatter fields, ensuring the dashboard and history stay in sync.

## Orchestration Workflow (0.11.0+)

### 1. Lead Agent Creates the Feature (in main)

```bash
# In main repository
/spec-kitty.specify "Add user authentication system"
```

This creates:

- `kitty-specs/001-user-authentication-system/spec.md` (committed to main)
- NO worktree is created during planning

Share the feature slug (e.g., `001-user-authentication-system`) with all participating agents.

### 2. Planning and Research (in main)

A planning agent executes in the main repository:

```bash
/spec-kitty.plan
/spec-kitty.research  # Optional
```

Output artifacts live under `kitty-specs/<feature>/`:

- `plan.md` - Implementation plan
- `research.md` - Research findings (optional)
- `data-model.md` - Database schema (software-dev mission)

All artifacts are committed to main, visible to all agents.

### 3. Task Decomposition (in main)

```bash
/spec-kitty.tasks
```

Creates:

- `tasks.md` - Work package breakdown with dependencies
- `tasks/WP01-setup.md`, `tasks/WP02-api.md`, etc. - Individual WP prompts

Each WP file has frontmatter tracking status:

```yaml
---
work_package_id: "WP01"
title: "Database Schema"
lane: "planned"
dependencies: []
---
```

### 4. Parallel Implementation (in separate worktrees)

Each agent creates their own worktree for their assigned WP:

```bash
# Agent A implements WP01 (foundation)
spec-kitty implement WP01
# Creates .worktrees/001-user-authentication-system-WP01/

# Agent B implements WP02 (depends on WP01)
spec-kitty implement WP02 --base WP01
# Creates .worktrees/001-user-authentication-system-WP02/

# Agent C implements WP03 (independent)
spec-kitty implement WP03
# Creates .worktrees/001-user-authentication-system-WP03/
```

**Key points:**

- Each agent works in their own isolated worktree
- Each worktree has its own branch
- No conflicts between agents (separate directories)
- Dependencies handled via `--base` flag

When finished, agents move their WP to review:

```bash
spec-kitty agent tasks move-task WP01 --to for_review
```

### 5. Review and Merge

Reviewers examine work packages in `for_review` lane:

```bash
/spec-kitty.review WP01
```

Once all packages are in `done` lane, merge from any WP worktree:

```bash
cd .worktrees/001-user-authentication-system-WP01/
spec-kitty merge
```

The merge command:

- Detects all WP branches for the feature
- Merges them to main in sequence
- Cleans up all worktrees and branches

## Coordinating 10+ Agents

| Challenge | Coordination Technique |
|-----------|-----------------------|
| Work overlap | Each WP has its own worktree—no overlap possible |
| Dependency ordering | Use `--base WP##` to branch from dependencies |
| Review backlog | Assign a dedicated "review agent" for `for_review` lane |
| Status visibility | Use `/spec-kitty.status` or dashboard to see all lanes |

### Parallelization Patterns

**Fan-out pattern** (maximum parallelism):

```
        WP01 (foundation)
       /  |  \
    WP02 WP03 WP04  ← All can run in parallel after WP01
```

```bash
# After WP01 completes:
spec-kitty implement WP02 --base WP01 &  # Agent A
spec-kitty implement WP03 --base WP01 &  # Agent B
spec-kitty implement WP04 --base WP01 &  # Agent C
```

**Diamond pattern** (converging dependencies):

```
        WP01
       /    \
    WP02    WP03
       \    /
        WP04  ← Depends on both WP02 and WP03
```

```bash
# WP04 needs both WP02 and WP03
spec-kitty implement WP04 --base WP03
cd .worktrees/001-feature-WP04/
git merge 001-feature-WP02  # Manual merge of second dependency
```

## Automation Hooks

- **Custom dispatch bot:** Monitor `kitty-specs/<feature>/tasks/` for WPs in `planned` lane and auto-assign to idle agents.
- **Stale task detector:** Poll dashboard or parse WP frontmatter to flag work packages stuck in a lane.
- **CI enforcement:** Reject merges where any WP has `lane: doing` or `lane: for_review` in frontmatter.

## Troubleshooting Parallel Runs

| Issue | Root Cause | Resolution |
|-------|------------|------------|
| Merge conflicts between WPs | WPs editing shared files | Split shared files into dedicated WP or gate via review |
| Dependency not available | Forgot `--base` flag | Re-implement with `spec-kitty implement WP## --base WP##` |
| WP stuck in wrong lane | Manual frontmatter edit | Use `spec-kitty agent tasks move-task WP## --to <lane>` |
| Agent can't find WP | Wrong directory | Ensure agent is in correct worktree for their WP |

## Status Monitoring

Check current state across all WPs:

```bash
# From main repository or any worktree
spec-kitty agent tasks status
```

Output shows kanban board:

```
Feature: 001-user-authentication-system
═══════════════════════════════════════════════════════════════
 PLANNED     │ DOING       │ FOR_REVIEW  │ DONE
─────────────┼─────────────┼─────────────┼─────────────
 WP04        │ WP02 (A)    │ WP03        │ WP01
             │             │             │
─────────────┴─────────────┴─────────────┴─────────────
Progress: ████████░░░░░░░░ 25% (1/4 done)
```

## See Also

### Related Explanations

- [Workspace-per-WP Model](workspace-per-wp.md) - How worktrees enable parallel development
- [Git Worktrees](git-worktrees.md) - How git worktrees work
- [Kanban Workflow](kanban-workflow.md) - How work moves through lanes
- [AI Agent Architecture](ai-agent-architecture.md) - How agents execute commands

### Tutorials

- [Multi-Agent Workflow Tutorial](../tutorials/multi-agent-workflow.md)

### How-To Guides

- [Parallel Development](../how-to/parallel-development.md)
- [Handle Dependencies](../how-to/handle-dependencies.md)
- [Sync Workspaces](../how-to/sync-workspaces.md)
- [Use the Dashboard](../how-to/use-dashboard.md)

### Reference

- [Agent Subcommands](../reference/agent-subcommands.md)
- [CLI Commands](../reference/cli-commands.md)
