# How to Create a Feature Specification

Use this guide to capture a new feature specification with `/spec-kitty.specify`.

## When to Use

Run this when you are starting a brand-new feature and need a spec before planning or implementation.

## The Command

```text
/spec-kitty.specify <description>
```

Run it from the main repository root. In v0.11.0+, planning artifacts live in `kitty-specs/` on `main`, and no worktrees are created during specify.

## The Discovery Interview

After the command, the CLI interviews you for missing details. You must answer each question before the spec is generated. Expect the agent to respond with `WAITING_FOR_DISCOVERY_INPUT` until the interview is complete.

## What Gets Created

- `kitty-specs/###-feature/spec.md`
- `kitty-specs/###-feature/meta.json`
- `kitty-specs/###-feature/checklists/requirements.md`

## Example

```text
/spec-kitty.specify Build a photo organizer that groups albums by date and supports drag-and-drop reordering.
```

During discovery, answer follow-up questions (roles, constraints, success criteria). Once complete, the spec is written to `kitty-specs/<feature>/spec.md` on `main`.

## Troubleshooting

- **Stuck on discovery**: Answer the remaining interview questions. The spec will not be created until the interview is complete.
- **Wrong directory**: Run from the main repository root, not from a worktree.
- **Need to revise the spec**: Re-run `/spec-kitty.specify` with the updated description and follow the interview again.

---

## Command Reference

- [Slash Commands](../reference/slash-commands.md) - All `/spec-kitty.*` commands
- [CLI Commands](../reference/cli-commands.md) - Full CLI reference

## See Also

- [Create a Plan](create-plan.md) - Next step after specification
- [Switch Missions](switch-missions.md) - Choose different mission types

## Background

- [Spec-Driven Development](../explanation/spec-driven-development.md) - Why specs come first
- [Mission System](../explanation/mission-system.md) - How missions affect specifications

## Getting Started

- [Getting Started Tutorial](../tutorials/getting-started.md) - Hands-on introduction
- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
