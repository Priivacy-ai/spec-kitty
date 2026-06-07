---
work_package_id: WP03
title: Genesis non-display invariant, enforced everywhere
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-007
- FR-013
- FR-014
tracker_refs:
- '1666'
planning_base_branch: mission/wp-lane-state-machine-fsm
merge_target_branch: mission/wp-lane-state-machine-fsm
branch_strategy: Planning artifacts for this mission were generated on mission/wp-lane-state-machine-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/wp-lane-state-machine-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - Invariant
assignee: ''
agent: claude
history:
- at: '2026-06-07T13:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/reducer.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/reducer.py
- src/specify_cli/status/views.py
- src/specify_cli/status/progress.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/core/task_metadata_validation.py
role: implementer
tags:
- genesis
- non-display-invariant
task_type: implement
---

# Work Package Prompt: WP03 — Genesis non-display invariant

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for profile **`python-pedro`** (role: `implementer`).

## Objective & Success Criteria

`genesis` never surfaces as a board column, summary key, discovery candidate, or
authorable frontmatter lane; a genesis-state WP is never silently dropped from a table.

- FR-007, FR-013, FR-014; US2/US7 (review F4 + paula-2/3 + debbie inert leaks). SC-002.

## Context & Constraints

- Review F4: `reducer.py` builds `summary = {l.value: 0 for l in Lane}` → every snapshot carries `"genesis": 0`, contradicting the non-display invariant; `test_summary_has_all_lane_keys` passes only against a hand-built fixture.
- Paula-3: `tasks.py` `by_lane = {lane: [] for lane in Lane}` includes a genesis bucket that drops genesis WPs from the table.
- Debbie: `get_all_lane_values()` makes `task_metadata_validation` accept/print `genesis` as authorable.
- Depends on WP01.
- **Confirm the path** of `task_metadata_validation` before editing (`grep -rn "must be one of\|get_all_lane_values" src/`); adjust `owned_files` if it differs from `core/task_metadata_validation.py`.

## Branch Strategy
- Base/merge: `mission/wp-lane-state-machine-fsm`; lane worktree per `lanes.json`. `spec-kitty agent action implement WP03 --agent <name>`.

## Subtasks & Detailed Guidance

### T014 — Reducer summary excludes genesis
- `reducer.py`: `summary = {l.value: 0 for l in Lane if l is not Lane.GENESIS}`; mirror in `views.py` board summary. (Existing fixtures that gained `"genesis": 0` get reverted by T018's correction.)

### T015 — `by_lane` excludes genesis
- `cli/commands/agent/tasks.py`: build `by_lane` over display lanes only (`for lane in Lane if lane is not Lane.GENESIS` or `CANONICAL_LANES`); ensure no genesis-state WP is dropped (route to planned-display or assert none exist post-finalize).

### T016 — Frontmatter validation excludes genesis
- `task_metadata_validation`: the authorable-lane set / "must be one of …" message excludes `genesis` (use `CANONICAL_LANES`, not `get_all_lane_values()`).

### T017 [P] — Docstring hygiene
- Fix the stale "7 lanes" / "9-lane" comments in `reducer.py`, `views.py`, `progress.py` to reflect "10 enum members; 9 active/display + genesis".

### T018 — Tests
- Assert the reducer's REAL summary output (not a fixture) has no `genesis` key; assert the board table never drops a genesis WP; correct any fixtures that wrongly carry `"genesis": 0`.

## Test Strategy
- Targeted: `python -m pytest tests/status/test_views.py tests/status/test_models.py tests/test_dashboard/ tests/specify_cli/cli/commands/agent/ -q -k "lane or summary or board or display"`. `ruff`+`mypy` clean.

## Definition of Done
- No display/summary/discovery surface includes genesis; reducer real output asserted; fixtures corrected; docstrings current.

## Risks & Mitigations
- Fixture churn — assert reducer output, not a hand-built fixture (the `test_summary_has_all_lane_keys` trap).

## Review Guidance — **Persona ICs: Paula-Patterns; reviewer: reviewer-renata**
- Paula: the non-display invariant holds across EVERY representation (enum vs CANONICAL_LANES vs summary vs discovery vs frontmatter). Renata: tests assert real output, not fixtures.

## Activity Log
- 2026-06-07 — system — Prompt created.
