---
work_package_id: WP11
title: Mission-identity field-drop fold-in (#1663)
dependencies:
- WP10
requirement_refs:
- FR-025
- FR-026
- FR-027
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T039
- T040
- T041
phase: Phase 5 - Consumption
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2954825"
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: 'src/runtime/next/'
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/runtime_bridge.py
- tests/runtime/**
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP11 – Mission-identity field-drop fold-in (#1663)

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below).

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objectives & Success Criteria

Carry `mission_id`/`mission_slug` through the `runtime_bridge.py` `MissionRunSnapshot` reconstructions that currently drop them; add a regression test; make #1663 closeable.

- FR-025/026/027. SC-006.

## Context & Constraints

- Drop sites: `src/runtime/next/runtime_bridge.py:1723` and `:1860` (all six `engine.py` construction sites already preserve identity — keep them correct).
- Same file as WP04 — sequence after WP04 to avoid edit conflicts.

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T039 – Carry identity through reconstructions
- **Steps**: Add `mission_id=snapshot.mission_id, mission_slug=snapshot.mission_slug` to the two `MissionRunSnapshot(...)` reconstructions at `runtime_bridge.py:1723` and `:1860`.
- **Files**: `src/runtime/next/runtime_bridge.py`.

### Subtask T040 – Regression test
- **Steps**: Add a test asserting a snapshot's `mission_id`/`mission_slug` survive the auto-complete reconstruction path (not reset to `None`).
- **Files**: `tests/runtime/` (or the existing runtime_bridge test module).

### Subtask T041 – Confirm closeable
- **Steps**: Audit all snapshot construction/reconstruction sites; confirm none drop identity. Note #1663 closeable in the WP summary.

## Test Strategy

- New regression test green; existing runtime tests green.

## Risks & Mitigations

- None significant; ensure no other reconstruction site exists beyond the two known + six engine sites.

## Review Guidance — **Persona IC: reviewer-renata**

- Reviewer profile: `reviewer-renata`. Verify both sites carry identity, the regression test actually fails without the fix, and #1663's acceptance is met.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
- 2026-06-08T10:29:20Z – claude:sonnet:python-pedro:implementer – shell_pid=2940673 – Started implementation via action command
- 2026-06-08T10:38:26Z – claude:sonnet:python-pedro:implementer – shell_pid=2940673 – Ready for review: identity carried through both runtime_bridge MissionRunSnapshot reconstruction sites (site-1 autocomplete at line 1737, site-2 final-persist at line 1876) + 2 regression tests with non-vacuity proof. All 8 production construction sites verified. mypy/ruff clean. #1663 closeable.
- 2026-06-08T10:39:01Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2954825 – Started review via action command
