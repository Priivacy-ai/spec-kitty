# Missions

**Missions** are workflow definitions that configure phases, templates, and guardrails
for structured work. Each mission subdirectory contains a state machine definition,
an optional runtime DAG, command templates, and content templates.

## Available Missions

| Mission              | Directory        | Domain       | States                                                        |
|----------------------|------------------|--------------|---------------------------------------------------------------|
| Software Development | `software-dev/`  | software-dev | discovery → specify → plan → implement → review → done        |
| Documentation        | `documentation/` | other        | discover → audit → design → generate → validate → publish     |
| Plan                 | `plan/`          | planning     | goals → research → structure → draft → review → done          |
| Research             | `research/`      | research     | scoping → methodology → gathering → synthesis → output → done |

## Structure Convention

Each mission directory contains:

- `mission.yaml` — State machine definition (states, transitions, guards)
- `mission-runtime.yaml` — Runtime DAG (steps, dependencies, agent-profile assignments)
- `command-templates/` — Markdown prompt files for each slash command step
- `templates/` — Content scaffolds for output artifacts (spec, plan, tasks, etc.)

## Python Utilities

This directory also contains shared mission primitives:

- `primitives.py` — `PrimitiveExecutionContext` dataclass with glossary middleware fields
- `glossary_hook.py` — `execute_with_glossary()` for wiring glossary checks into mission execution

## Glossary Reference

See [Mission](../../../glossary/contexts/orchestration.md#mission) and
[Command Template](../../../glossary/contexts/orchestration.md#command-template)
in the orchestration glossary context.
