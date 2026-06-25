---
work_package_id: WP05
title: Lifecycle families I — branch_context + create_mission + check_prerequisites
dependencies:
- WP04
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
tracker_refs: []
planning_base_branch: prog/2056-mission
merge_target_branch: prog/2056-mission
branch_strategy: Planning artifacts for this mission were generated on prog/2056-mission. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2056-mission unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-decompose-mission-god-module-01KVXHF8
base_commit: cc74304cd7f3ac2d26cc05c3904ff69feb19f276
created_at: '2026-06-24T19:52:40.998893+00:00'
subtasks:
- T017
- T018
- T019
- T020
- T021
phase: Phase 3 - Command seams
assignee: ''
agent: "claude:opus:randy-reducer:implementer"
shell_pid: "3240276"
history:
- timestamp: '2026-06-24T19:52:40Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/mission_create.py
create_intent:
- src/specify_cli/cli/commands/agent/mission_branch_context.py
- src/specify_cli/cli/commands/agent/mission_create.py
- src/specify_cli/cli/commands/agent/mission_check_prerequisites.py
- tests/specify_cli/cli/commands/agent/test_mission_branch_context.py
- tests/specify_cli/cli/commands/agent/test_mission_create_phases.py
- tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_branch_context.py
- src/specify_cli/cli/commands/agent/mission_create.py
- src/specify_cli/cli/commands/agent/mission_check_prerequisites.py
- tests/specify_cli/cli/commands/agent/test_mission_branch_context.py
- tests/specify_cli/cli/commands/agent/test_mission_create_phases.py
- tests/specify_cli/cli/commands/agent/test_mission_check_prerequisites.py
tags: []
---

# Work Package Prompt: WP05 – Lifecycle families I (branch_context + create_mission + check_prerequisites)

## Do This First

1. Confirm WP04 merged; golden test green.
2. Read research.md §2 (`create_mission` mega-function, 281 LOC) and §3 Seam B.
3. `create_mission` is imported by `lifecycle.py` as `agent_feature.create_mission` — must stay
   re-exportable at `mission.<name>` (finalized in WP09). Decompose to ≤15 CC; each phase helper needs a test.

## Objective

Move three lifecycle commands into per-family modules, internally decomposing `create_mission` into ≤15-CC
phase helpers.

## Implementation

### T017 — branch_context family
Create `mission_branch_context.py`; move `branch_context` + `_inject_branch_contract` +
`_resolve_primary_branch_for_recommendation`, `_git_local_or_remote_branch_exists`,
`_switch_to_start_branch`, `_show_branch_context`, `_resolve_planning_branch`,
`_resolve_feature_target_branch`, `_get_current_branch`.

### T018 — create_mission family (decompose)
Create `mission_create.py`; move `create_mission` and decompose its 281 LOC into phase helpers:
scaffold → meta.json write → coordination-branch creation (incl. `--force-recreate-coordination-branch`) →
branch-contract injection → event emit. Each helper ≤15 CC.

### T019 — check_prerequisites family
Create `mission_check_prerequisites.py`; move `check_prerequisites` + `_emit_check_prerequisites_detection_error`,
`_emit_check_prerequisites_result`, `_paths_only_payload`, `_read_meta_for_pr_bound`, `_read_meta_for_emission`.

### T020 — Tests + repoint
Author focused tests for each create_mission phase helper (`test_mission_create_phases.py`) and for
branch_context / check_prerequisites; extend existing `test_mission_create.py`,
`test_create_feature_branch*.py`. Documented import-line edits in `mission.py`.

### T021 — Gates
Golden test green; ruff (C901 ≤15) + mypy --strict clean.

## Acceptance

- Three family modules + tests; `create_mission` fully ≤15 CC with phase-helper tests; golden green.
- `lifecycle.py`'s `create_mission` edge still resolves (temporary `mission.py` import; final re-export WP09).

## Out-of-map edits

- `src/specify_cli/cli/commands/agent/mission.py`: import-line edits only.

## Activity Log

- 2026-06-24T21:26:28Z – claude:opus:randy-reducer:implementer – shell_pid=3231244 – Assigned agent via action command
- 2026-06-24T21:29:21Z – claude:opus:randy-reducer:implementer – shell_pid=3240276 – Assigned agent via action command
- 2026-06-24T21:57:47Z – claude:opus:randy-reducer:implementer – shell_pid=3240276 – Lifecycle families I: branch_context + create (decomposed to phase helpers) + check_prerequisites relocated to per-family leaf modules; mission.py 3431 to 2630 LOC; golden + full agent suite green; ruff C901<=15 + mypy --strict clean. Lane carries pre-existing structural kitty-specs divergence from prog (handled at merge).
- 2026-06-24T21:58:05Z – user – shell_pid=3240276 – Self-review pass: acceptance met (3 family modules + 50 focused tests, create_mission decomposed to 6 phase helpers all <=15 CC); behavior-preserving (golden + 456 agent suite green; only repo-wide failures are pre-existing WP04 record_analysis shim gaps confirmed on pristine WP04 tip, deferred WP09); re-exports verified (mission.<name> patch targets + lifecycle.py create_mission resolve); scope clean. ruff C901<=15 + mypy --strict clean. Lane kitty-specs divergence is pre-existing structural (handled at merge).
