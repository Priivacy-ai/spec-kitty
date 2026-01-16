# How to Create a Technical Plan

Use this guide to turn a finished spec into a technical plan with `/spec-kitty.plan`.

## Prerequisites

- `kitty-specs/<feature>/spec.md` exists
- You are in the main repository root (v0.11.0+ keeps planning artifacts in `main`)

## The Command

In your agent:

```text
/spec-kitty.plan
```

Optionally include your stack or architecture preferences in the same message.

## The Planning Interview

The planner asks architecture and non-functional questions. It pauses with `WAITING_FOR_PLANNING_INPUT` until you answer each one.

## What Gets Created

- `kitty-specs/<feature>/plan.md`
- `kitty-specs/<feature>/research.md` (if research is required)
- `kitty-specs/<feature>/data-model.md` (when data is involved)
- `kitty-specs/<feature>/contracts/` (API contracts when applicable)
- Updated agent context files (based on the plan)

## Example

```text
/spec-kitty.plan Use FastAPI + PostgreSQL. Deploy on Fly.io. Use JWTs for auth.
```

## Troubleshooting

- **No plan generated**: Make sure the spec exists and you are running in the main repository root.
- **Planner keeps asking questions**: Provide the missing architectural details; the plan will not generate until the interview is complete.
- **Need to update the plan**: Re-run `/spec-kitty.plan` with the new constraints.

---

## Command Reference

- [Slash Commands](../reference/slash-commands.md) - All `/spec-kitty.*` commands
- [CLI Commands](../reference/cli-commands.md) - Full CLI reference
- [File Structure](../reference/file-structure.md) - Where plans are stored

## See Also

- [Create a Specification](create-specification.md) - Required before planning
- [Generate Tasks](generate-tasks.md) - Next step after planning

## Background

- [Spec-Driven Development](../explanation/spec-driven-development.md) - The philosophy
- [Kanban Workflow](../explanation/kanban-workflow.md) - How work flows after planning

## Getting Started

- [Your First Feature](../tutorials/your-first-feature.md) - Complete workflow walkthrough
