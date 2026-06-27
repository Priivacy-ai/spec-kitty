---
title: 'Your First Feature: Complete Workflow'
description: Walk through a complete Spec Kitty 3.2 mission from specification through plan, tasks, implementation, review, and merge.
doc_status: active
updated: '2026-06-03'
related:
- docs/guides/getting-started.md
- docs/guides/multi-agent-workflow.md
---
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

Before you move on, complete the three post-merge steps:

1. **Mission review** — run `/spec-kitty-mission-review` in your agent to verify spec→code
   fidelity.
2. **Verify the retrospective** — under default policy Spec Kitty already wrote a
   `retrospective.yaml` during merge. Find it at:
   ```bash
   cat .kittify/missions/$(jq -r .mission_id kitty-specs/###-task-list/meta.json)/retrospective.yaml
   ```
   If the file is absent, author it: `spec-kitty retrospect create --mission ###-task-list`.
3. **Surface findings** — review the record's proposals:
   ```bash
   spec-kitty retrospect summary                              # cross-mission aggregation (read-only)
   spec-kitty agent retrospect synthesize --mission <slug>  # inspect proposals (dry-run by default)
   ```

For the full retrospective workflow, see
[How to Use Retrospective Learning](use-retrospective-learning.md).

## Troubleshooting

- **"Planning created a worktree"**: Planning stays in the repository root checkout in the current 3.2 workflow. If you see an unexpected planning worktree, upgrade with `spec-kitty upgrade`.
- **"I want to plan from here but not land on `main`"**: Stay in the repository root checkout and choose the right target branch first. See [How to Keep Main Clean](keep-main-clean.md).
- **"WP has dependencies"**: Keep following the `spec-kitty next` decisions; the runtime will only issue implementation work when its dependencies are satisfied.
- **Review fails validation**: Run `spec-kitty validate-tasks --fix` and re-run `/spec-kitty.review`.

## What's Next?

Continue with [Multi-Agent Workflow](multi-agent-workflow.md) to learn parallel development with multiple agents.

### Related How-To Guides

- [Create a Plan](create-plan.md) - Detailed planning guidance
- [Keep Main Clean](keep-main-clean.md) - Choose a target branch without changing planning location
- [Generate Tasks](generate-tasks.md) - Work package generation
- [Implement a Work Package](implement-work-package.md) - Implementation details
- [Review a Work Package](review-work-package.md) - Review process
- [Accept and Merge](accept-and-merge.md) - Final merge workflow

### Reference Documentation

- [CLI Commands](../api/cli-commands.md) - Full command reference
- [Slash Commands](../api/slash-commands.md) - Agent slash commands
- [File Structure](../api/file-structure.md) - Project layout explained

### Learn More

- [Execution Workspace Model](../architecture/execution-lanes.md) - Why modern features use lane worktrees
- [Kanban Workflow](../architecture/kanban-workflow.md) - Lane transitions
- [Spec-Driven Development](../architecture/spec-driven-development.md) - The philosophy
