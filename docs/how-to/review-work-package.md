# How to Review a Work Package

Use this guide to review a completed work package and update its lane.

## Prerequisites

- The WP is in `lane: "for_review"`
- You are in the WP worktree (or the feature worktree containing the implementation)

## The Command

In your agent:

```text
/spec-kitty.review
```

You can also specify a WP ID:

```text
/spec-kitty.review WP01
```

## Review Process

The review command:

- Picks the next WP in `for_review` (or the one you specify)
- Moves it to `lane: "doing"` for review
- Shows the full prompt and the exact commands for passing or requesting changes

## Providing Feedback

If changes are required:

1. Add feedback in the **Review Feedback** section of the WP file.
2. Move the WP back to `planned` so the implementer can pick it up again.

In your terminal:

```bash
spec-kitty agent tasks move-task WP01 --to planned --note "Changes requested: <summary>"
```

## Passing Review

When everything looks good, move the WP to `done`.

In your terminal:

```bash
spec-kitty agent tasks move-task WP01 --to done --note "Approved"
```

## Troubleshooting

- **No WPs found**: Confirm at least one WP is in `for_review`.
- **Wrong workspace**: Open the WP worktree that contains the implementation.
- **Need more context**: Check the spec and plan for the feature before completing review.

---

## Command Reference

- [Slash Commands](../reference/slash-commands.md) - All `/spec-kitty.*` commands
- [Agent Subcommands](../reference/agent-subcommands.md) - Workflow commands

## See Also

- [Implement a Work Package](implement-work-package.md) - Required before review
- [Accept and Merge](accept-and-merge.md) - After all WPs pass review
- [Use the Dashboard](use-dashboard.md) - Monitor review status

## Background

- [Kanban Workflow](../explanation/kanban-workflow.md) - Lane transitions explained
- [Multi-Agent Orchestration](../explanation/multi-agent-orchestration.md) - Agent handoffs

## Getting Started

- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
