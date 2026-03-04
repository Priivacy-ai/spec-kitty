# Software Development Mission

The primary mission type for structured feature development. Defines a 6-state
workflow from discovery through review to completion.

## State Machine

```
discovery → specify → plan → implement → review → done
                                           ↑       |
                                           └───────┘ (rework)
```

Transitions are guarded by artifact checks (e.g., `artifact_exists("spec.md")`)
and gate conditions (e.g., `gate_passed("review_approved")`).

## Runtime DAG (v2.1.0)

The runtime DAG splits execution into 9 steps with agent-profile assignments:

| Step | Agent Profile |
|------|---------------|
| `discovery` | researcher |
| `specify` | — |
| `plan` | architect |
| `tasks_outline` | planner |
| `tasks_packages` | planner |
| `tasks_finalize` | planner |
| `implement` | implementer |
| `review` | reviewer |
| `accept` | — |

## Contents

- `mission.yaml` — State machine with guards and transitions
- `mission-runtime.yaml` — Runtime DAG with step ordering and agent-profile refs
- `command-templates/` — Prompt files for each `/spec-kitty.*` command
- `templates/` — Content scaffolds (spec, plan, tasks, task-prompt templates)
