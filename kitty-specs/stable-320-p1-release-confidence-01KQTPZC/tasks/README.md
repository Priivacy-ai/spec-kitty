# Tasks Directory

This directory contains flat work package (WP) prompt files for the mission.

## Current Structure

```text
tasks/
|-- WP01-task-board-progress-semantics.md
|-- WP02-dependency-drift-gate.md
|-- WP03-fresh-workflow-smoke-evidence.md
|-- WP04-release-evidence-and-deferrals.md
`-- README.md
```

All WP files stay directly under `tasks/`. Do not create lane or status
subdirectories.

## Source Of Truth

- `../wps.yaml` is the structured WP manifest used by the current planning pipeline.
- `../tasks.md` is generated from `../wps.yaml` by `finalize-tasks`.
- `../status.events.jsonl` and `../status.json` are the canonical status artifacts.
- WP frontmatter carries execution metadata such as dependencies, requirement refs,
  ownership, and branch strategy.

## Required WP Frontmatter Shape

Each WP file must include YAML frontmatter with the current fields used by
`finalize-tasks` and `spec-kitty next`:

```yaml
---
work_package_id: WP01
title: Task Board Progress Semantics
dependencies: []
requirement_refs:
  - FR-001
subtasks:
  - T001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main.
agent_profile: python-pedro
role: implementer
agent: codex
model: ""
execution_mode: code_change
owned_files:
  - src/specify_cli/cli/commands/agent/tasks.py
authoritative_surface: src/specify_cli/
history: []
---
```

Planning-artifact WPs use `execution_mode: planning_artifact` and own paths under
this mission directory. Code-change WPs own source and test paths.

## Lane Model

Current canonical lane values are:

- `planned`
- `claimed`
- `in_progress`
- `for_review`
- `in_review`
- `approved`
- `done`
- `blocked`
- `canceled`

Use workflow commands or `spec-kitty next` for normal progression. If manually
inspecting status, prefer:

```bash
spec-kitty agent tasks status --mission stable-320-p1-release-confidence-01KQTPZC
spec-kitty agent tasks list-tasks --mission stable-320-p1-release-confidence-01KQTPZC --json
```

Do not use legacy lane aliases in new instructions.

## File Naming

- Format: `WP01-kebab-case-slug.md`
- Keep the directory flat.
- Keep `work_package_id` aligned with the filename prefix.
