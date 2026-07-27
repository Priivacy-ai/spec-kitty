---
work_package_id: WP02
title: Feature-dir resolution seam (Seam D)
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-006
- NFR-001
- NFR-005
tracker_refs: []
planning_base_branch: prog/2056-mission
merge_target_branch: prog/2056-mission
branch_strategy: Planning artifacts for this mission were generated on prog/2056-mission. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2056-mission unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-decompose-mission-god-module-01KVXHF8
base_commit: cc74304cd7f3ac2d26cc05c3904ff69feb19f276
created_at: '2026-06-24T19:52:40.998893+00:00'
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 2 - Shared resolution surface
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3078208"
history:
- timestamp: '2026-06-24T19:52:40Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/mission_feature_resolution.py
create_intent:
- src/specify_cli/cli/commands/agent/mission_feature_resolution.py
- tests/specify_cli/cli/commands/agent/test_mission_feature_resolution.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_feature_resolution.py
- tests/specify_cli/cli/commands/agent/test_mission_feature_resolution.py
tags: []
---

# Work Package Prompt: WP02 – Feature-dir resolution seam (Seam D)

## Do This First

1. Confirm WP01's golden test is green — it is your regression net for this WP.
2. Read research.md §3 Seam D and §4 (coupling: `_build_setup_plan_detection_error` is imported by
   `lifecycle.py`; `_find_feature_directory` is patched 39× — both must remain re-exportable at `mission.<name>`).
3. Extract Seam D FIRST so later seams import a stable resolution surface.

## Objective

Extract the shared feature-dir resolution surface into `mission_feature_resolution.py`, keeping every
symbol re-exportable from `mission.<name>` (the shim re-export is finalized in WP09; for now `mission.py`
imports from the seam so patch targets keep resolving).

## Implementation

### T005 — Create the seam module
Move into `mission_feature_resolution.py`: `_find_feature_directory`,
`_resolve_mission_dir_name_primary_anchored`, `_primary_anchored_feature_dir`,
`_list_feature_spec_candidates`, `_sole_mission_slug_or_none`, `_build_setup_plan_detection_error`,
`_safe_load_meta`, `_read_feature_meta`. Seam imports lower layers only
(`missions._read_path_resolver`, `core`, `status`) — never back into `mission`/other seams (INV-8).

### T006 — Repoint references
Update `mission.py` to import these from the seam (out-of-map import edit — documented below).

### T007 — Direct unit tests
Author `test_mission_feature_resolution.py` with DIRECT tests for the resolvers (handle → read path,
ambiguous handle → structured error, sole-mission auto-select, detection-error payload shape). Target ≥90%.

### T008 — Gates
Golden test green; ruff + mypy --strict clean on touched files; confirm one-way imports.

## Acceptance

- New seam + test exist; ≥90% coverage of the seam.
- `lifecycle.py`'s `_build_setup_plan_detection_error` edge still resolves (via the temporary `mission.py`
  import; final shim re-export lands in WP09).
- Golden test green; no function over CC 15.

## Out-of-map edits

- `src/specify_cli/cli/commands/agent/mission.py`: import-line edits only, to point at the new seam.
  (Final shim reduction + re-export sweep is WP09, which solely owns `mission.py`.)

## Activity Log

- 2026-06-24T20:34:15Z – claude:opus:randy-reducer:implementer – shell_pid=3009765 – Assigned agent via action command
- 2026-06-24T20:50:16Z – claude:opus:randy-reducer:implementer – shell_pid=3009765 – Seam D extracted; 22 seam tests + golden green, 90% coverage, ruff/mypy clean, one-way imports verified. --force: kitty-specs contamination is pre-existing mission-branch status-transition bookkeeping (also present on approved lane-a), not WP02 code; merge-base with prog is the pre-mission origin commit.
- 2026-06-24T20:50:24Z – claude:opus:reviewer-renata:reviewer – shell_pid=3078208 – Started review via action command
- 2026-06-24T20:50:38Z – user – shell_pid=3078208 – Review passed: behavior-preserving Seam D extraction; 22 seam tests + 16 golden + 80 patch-target tests + full agent suite (359) green; 90% seam coverage; ruff C901 clean; mypy clean on new files (3 mission.py findings pre-existing); one-way imports verified; scope clean. --force: pre-existing mission-branch status bookkeeping contamination (also on approved lane-a).
