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
1. Write feedback to a temporary file (the review prompt shows a unique suggested path).
2. Move the WP back to `planned` with `--review-feedback-file`.
3. The command archives feedback to `kitty-specs/<feature>/feedback/` and stores that path in frontmatter `review_feedback`.

In your terminal:

```bash
cat > /tmp/spec-kitty-review-feedback-WP01.md <<'EOF'
**Issue 1**: <description and how to fix>
**Issue 2**: <description and how to fix>
EOF

spec-kitty agent tasks move-task WP01 --to planned --review-feedback-file /tmp/spec-kitty-review-feedback-WP01.md --note "Changes requested: <summary>"
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
