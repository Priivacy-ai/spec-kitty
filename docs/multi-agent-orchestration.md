---
title: Multi-Agent Orchestration
description: Best practices for coordinating multiple AI agents with Spec Kitty’s workflow tooling.
---

# Multi-Agent Orchestration

Spec Kitty was designed for **multi-agent development orchestration**—it keeps parallel assistants synchronized while protecting the quality of shared artifacts. This guide outlines patterns that help teams run many AI agents in parallel without incurring merge chaos.

## Core Principles

1. **Single feature branch, multiple work packages:** Every feature gets its own branch and worktree; agents divide the work by package, not by branch.
2. **Command discipline:** `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks`, and `/spec-kitty.implement` enforce gated, automated steps so agents cannot skip discovery or validation.
3. **Lane-driven coordination:** Tasks move through `planned → doing → for_review → done` via helper scripts, ensuring the dashboard and history stay in sync.

## Orchestration Workflow

### 1. Lead Agent Creates the Feature
- Run `/spec-kitty.specify` to generate the spec, branch, and worktree (`.worktrees/<feature>`).
- Share the feature slug (e.g., `001-systematic-recognizer-enhancement`) with all participating agents.

### 2. Planning and Research
- A planning agent executes `/spec-kitty.plan` and `/spec-kitty.research`.
- Output artifacts (plan.md, research.md, data-model.md, quickstart.md) live under `kitty-specs/<feature>/`.

### 3. Task Decomposition
- Run `/spec-kitty.tasks` to build `tasks.md` and prompt files in `tasks/planned/`.
- Each work package receives a structured prompt file containing scope, dependencies, and risks.

### 4. Parallel Implementation
- Assign work packages to agents; each agent moves the prompt to `doing` using `.kittify/scripts/bash/tasks-move-to-lane.sh`.
- Agents work inside the same worktree but edit disjoint files as defined in the prompts to avoid conflicts.
- When finished, move prompts to `for_review` with the same helper script.

### 5. Review and Merge
- Reviewers pull prompts from `for_review` and apply feedback.
- Run `/spec-kitty.merge` once all packages hit `done`—this command merges the feature branch and optionally removes the worktree.

## Coordinating 10+ Agents

| Challenge | Coordination Technique |
|-----------|-----------------------|
| Work overlap | Use prompts to enforce file boundaries; mark parallel-safe tasks with `[P]` |
| Review backlog | Assign a dedicated “review agent” responsible for the `for_review` lane |
| Context drift | Refresh agent context with `.kittify/scripts/bash/update-agent-context.sh __AGENT__` after each plan update |

## Automation Hooks

- **Custom dispatch bot:** Watch `tasks/planned/` for new prompts and auto-assign to idle agents.
- **Stale task detector:** Poll the dashboard API or `tasks.md` to flag work packages stuck in a lane longer than a defined SLA.
- **CI enforcement:** Reject merges where `tasks/for_review/` or `tasks/doing/` still contain prompts.

## Troubleshooting Parallel Runs

| Issue | Root Cause | Resolution |
|-------|------------|------------|
| Frequent merge conflicts | Agents editing shared configuration files | Split configuration into dedicated work packages or gate via review agent |
| Agents overwriting prompts | Lane scripts not used | Require `.kittify` helper scripts; audit git history for manual edits |
| Missing artifacts | Command skipped | Re-run `/spec-kitty.tasks` or `/spec-kitty.plan` to regenerate required files |

## Next Steps

- Study the **dashboard workflow** in [`kanban-dashboard-guide.md`](kanban-dashboard-guide.md).
- Try the real-world scenario [`../examples/multi-agent-feature-development.md`](../examples/multi-agent-feature-development.md).
- Dive into Claude-specific orchestration in [`claude-code-workflow.md`](claude-code-workflow.md).
