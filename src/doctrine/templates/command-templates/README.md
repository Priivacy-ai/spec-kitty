# Command Templates

Prompt files for `/spec-kitty.*` slash commands. These are the **source templates**
that get deployed to agent directories (`.claude/commands/`, `.codex/prompts/`, etc.)
during `spec-kitty upgrade`.

Each file corresponds to one slash command surface and contains the full prompt that
guides the agent through the workflow step.

## Available Commands

| Template | Slash Command |
|----------|---------------|
| `accept.md` | `/spec-kitty.accept` |
| `analyze.md` | `/spec-kitty.analyze` |
| `checklist.md` | `/spec-kitty.checklist` |
| `clarify.md` | `/spec-kitty.clarify` |
| `constitution.md` | `/spec-kitty.constitution` |
| `dashboard.md` | `/spec-kitty.dashboard` |
| `doctrine.md` | `/spec-kitty.doctrine` (curation workflow) |
| `implement.md` | `/spec-kitty.implement` |
| `merge.md` | `/spec-kitty.merge` |
| `plan.md` | `/spec-kitty.plan` |
| `profile-context.md` | `/spec-kitty.profile-context` (ad-hoc specialist session) |
| `research.md` | `/spec-kitty.research` |
| `review.md` | `/spec-kitty.review` |
| `specify.md` | `/spec-kitty.specify` |
| `status.md` | `/spec-kitty.status` |
| `tasks.md` | `/spec-kitty.tasks` |

## Glossary Reference

See [Command Template](../../../../glossary/contexts/orchestration.md#command-template)
in the orchestration glossary context.
