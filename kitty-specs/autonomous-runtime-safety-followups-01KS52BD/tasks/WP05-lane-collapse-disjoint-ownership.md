---
work_package_id: WP05
title: Lane-collapse disjoint ownership
dependencies: []
requirement_refs:
- FR-012
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
agent: ''
history:
- at: '2026-05-21T10:53:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: runtime-riley
authoritative_surface: src/specify_cli/lanes/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/lanes/**
- tests/lanes/**
- tests/tasks/test_finalize_tasks_lanes_disjoint_fan_in.py
role: implementer
tags: []
---

# Work Package Prompt: WP05 - Lane-collapse disjoint ownership

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load runtime-riley
```

## Objective

Refine lane computation so disjoint upstream workstreams stay parallel and the
downstream fan-in WP becomes the synchronization point.

## Context

Issue #1236 reports PR #1251 planned six lanes but current finalization collapsed
all 14 WPs into `lane-a` because dependency edges alone drove collapse.

## Subtasks & Detailed Guidance

### T021 - Add fan-in fixture

Create a test fixture with six disjoint upstream workstreams and one final fan-in
WP.

### T022 - Refine collapse algorithm

Change lane collapse to consider `owned_files` overlap and lane dependency
ordering, not dependency existence alone.

### T023 - Preserve overlap collapse

Add regression coverage proving overlapping ownership still collapses.

### T024 - Improve report evidence

Update `collapse_report` to make dependency/overlap reasons understandable.

### T025 - Verify

Run:

```bash
uv run pytest tests/lanes tests/tasks/test_finalize_tasks_lanes_disjoint_fan_in.py
uv run mypy --strict src/specify_cli/lanes
```

## Branch Strategy

Planning/base branch: `main`. Final merge target: `main`. Use the runtime
resolved lane workspace.

## Definition of Done

- Disjoint fan-in fixture produces parallel lanes.
- Overlap fixture still collapses.
- Existing merge flow can still consume the generated `lanes.json`.

## Reviewer Guidance

Confirm lane dependencies express synchronization and no write-conflict safety is
lost.

## Activity Log

- 2026-05-21T10:53:40Z -- system -- Prompt created.
