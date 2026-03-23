# How to Review a Work Package

Use this guide to review a completed work package and update its lane.

## Prerequisites

- The WP is in `lane: "for_review"`
- You are in the WP worktree (or the feature worktree containing the implementation)
- In multi-feature repos, you know the feature slug (required for the `--feature` flag)

## Step 1: Discover Reviewable Work Packages

Before claiming a WP for review, check which work packages are waiting:

```bash
spec-kitty agent tasks list-tasks --lane for_review --feature <slug>
```

For machine-readable output:

```bash
spec-kitty agent tasks list-tasks --lane for_review --feature <slug> --json
```

If the `for_review` lane is empty, there is nothing to review. Wait for an
implementing agent to move a WP into that lane.

## Step 2: Load Governance Context

Load the project's review governance context before inspecting any code. This
surfaces constitution rules, acceptance criteria templates, and review guidance
from doctrine:

```bash
spec-kitty constitution context --action review --json
```

The returned `text` field contains governance context that applies to every
review in this project. If governance files are missing (no constitution
configured), the command still works with fallback defaults -- it is not a
blocker.

## Step 3: Claim the Work Package

### Using the slash command

In your agent:

```text
/spec-kitty.review
```

You can also specify a WP ID:

```text
/spec-kitty.review WP01
```

### Using the CLI directly

```bash
spec-kitty agent workflow review WP01 --agent <your-name> --feature <slug>
```

Omit `WP01` to auto-select the first WP in the `for_review` lane:

```bash
spec-kitty agent workflow review --agent <your-name> --feature <slug>
```

The review command:
- Picks the next WP in `for_review` (or the one you specify)
- Moves it to `lane: "doing"` for review
- Prints the path to a generated review prompt file
- Shows the full prompt and the exact commands for passing or requesting changes

## Step 4: Read the Review Prompt

Read the review prompt file whose path was printed in Step 3:

```bash
cat <prompt-file-path>
```

The review prompt contains:

- Acceptance criteria for this specific WP
- Git diff commands with the correct base branch (use those, not hardcoded `main`)
- Dependency warnings if the WP has downstream dependents
- WP isolation rules
- Completion instructions (approve/reject commands)

Follow the review prompt. It is the source of truth for what to check and how
to check it. The review criteria come from doctrine and the WP definition, not
from this guide.

## Step 5: Issue Your Verdict

Take exactly one action -- never "approve with conditions".

### Passing Review

When everything looks good, move the WP to `approved`:

```bash
spec-kitty agent tasks move-task WP01 --to approved --feature <slug> --note "Review passed: <summary>"
```

### Providing Feedback (Rejection)

If changes are required:
1. Write feedback to a temporary file (the review prompt shows a unique suggested path).
2. Move the WP back to `planned` with `--review-feedback-file`.
3. The command persists feedback in shared git common-dir and stores a pointer in frontmatter `review_feedback`.

Every blocking finding must map to a specific, verifiable remediation action.

In your terminal:

```bash
cat > /tmp/spec-kitty-review-feedback-WP01.md <<'EOF'
**Issue 1**: <description and how to fix>
**Issue 2**: <description and how to fix>
EOF

spec-kitty agent tasks move-task WP01 --to planned --force \
  --feature <slug> \
  --review-feedback-file /tmp/spec-kitty-review-feedback-WP01.md \
  --note "Changes requested: <summary>"
```

## Step 6: Check Downstream Impact

After rejecting a WP, check whether it has downstream dependents:

```bash
spec-kitty agent tasks list-dependents WP01 --feature <slug>
```

For machine-readable output:

```bash
spec-kitty agent tasks list-dependents WP01 --feature <slug> --json
```

If the rejected WP has downstream dependents, those WPs will need a rebase once
the rejection is addressed. Include a rebase warning in your feedback so the
implementing agent and any agents working on dependent WPs are aware.

You can also check the full feature status board for broader context:

```bash
spec-kitty agent tasks status --feature <slug>
```

## Review Precedence Rules

1. **Acceptance criteria are the primary gate** -- a WP meeting all criteria passes even if the reviewer would have done it differently.
2. **The review prompt is the source of truth** -- it contains the specific checks, criteria, and doctrine context for this WP.
3. **One clear verdict per review** -- approve or reject, nothing in between.
4. **The reviewer does not implement fixes** -- feedback must be actionable by the original implementing agent.

## Troubleshooting

- **No WPs found**: Confirm at least one WP is in `for_review` using `spec-kitty agent tasks list-tasks --lane for_review --feature <slug>`.
- **"Multiple features found"**: Add `--feature <slug>` to the command. This is required in repos with more than one active feature.
- **Wrong workspace**: Open the WP worktree that contains the implementation.
- **Need more context**: Check the spec and plan for the feature before completing review.
- **Governance context empty**: The constitution may not be configured yet. Review can still proceed using the acceptance criteria in the review prompt.

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
