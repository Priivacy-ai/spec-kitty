# Missions

**Missions** are workflow definitions that configure steps (each with its templates) and guardrails
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

The mission **logic modules** are **not** in this directory — this pack ships mission
**data** only (`mission.yaml`, prompts, templates, step contracts). The Python modules
(`primitives.py` with `PrimitiveExecutionContext`, `glossary_hook.py` with
`execute_with_glossary()`, `repository.py`, and the other 8 logic modules) live in the
`charter.offering` package at `src/charter/offering/missions/` and read this data at
runtime; a pack tree cannot host a Python package.

## Glossary Reference

See [Mission](../../../docs/context/orchestration.md#mission) and
[Command Template](../../../docs/context/orchestration.md#command-template)
in the orchestration glossary context.
