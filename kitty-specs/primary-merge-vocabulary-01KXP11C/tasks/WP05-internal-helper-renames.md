---
work_package_id: WP05
title: Internal helper renames (merge + Sense-D)
dependencies:
- WP04
requirement_refs:
- FR-008
- FR-003
tracker_refs: []
planning_base_branch: feat/terminology-primary-merge-disambiguation
merge_target_branch: feat/terminology-primary-merge-disambiguation
branch_strategy: Planning artifacts for this mission were generated on feat/terminology-primary-merge-disambiguation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/terminology-primary-merge-disambiguation unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
phase: Phase 2 - Safe code
assignee: ''
agent: "claude"
shell_pid: "1270649"
shell_pid_created_at: "1784232286.01"
history:
- at: '2026-07-16T18:15:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/lanes/merge.py
- src/specify_cli/merge/executor.py
- src/specify_cli/cli/commands/implement_cores.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/coordination/commit_router.py
- tests/architectural/surface_resolution_audit/write_candidate_classification.yaml
- tests/specify_cli/cli/commands/test_precondition_ref_unification.py
- tests/specify_cli/coordination/test_partition_authority_characterization.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Internal helper renames (merge + Sense-D)

## ⚡ Do This First: Load Agent Profile
Load `python-pedro` via `/ad-hoc-profile-load`.

## Objectives & Success Criteria
- Rename genuinely INTERNAL helpers to canonical-operation names, moving the FULL blast radius in one change.
- `merge_lane_to_mission` → consolidate-sense; `merge_mission_to_target` → integrate-sense (+ clarify their docstrings, FR-003); `_primary_ref_for` → Sense-D internal; optional `_resolve_primary_target_branch`.
- **EXCLUDED**: `is_primary_artifact_kind` (public `mission_runtime.__all__`) — do NOT rename (C-001).

## Context & Constraints
- Squad: these merge helpers are broadly imported (NOT "internal-only"). Source callers: **`merge/executor.py:271,299,470,482`** (the `_run_lane_based_merge` core path — the single most important caller) AND `orchestrator_api/commands.py:533,571`. Plus **13 test importers** (`tests/merge/test_executor_coverage.py`, `tests/integration/{test_post_merge_index_refresh,test_post_merge_unrelated_untracked,test_merge_lane_planning_data_loss,test_merge_resume,test_lanes_core_coord_read}.py`, `tests/integration/sparse_checkout/test_merge_refresh_and_invariant.py`, `tests/cli/commands/{test_merge_strategy,test_merge_status_commit}.py`, `tests/specify_cli/test_specify_topology_flag.py`, `tests/specify_cli/cli/commands/{test_merge_coord_worktree_resync_1826,test_merge_coord_topology_1772}.py`, `tests/lanes/test_merge.py`) and the arch fixture `write_candidate_classification.yaml` — all must move in lockstep or the surface-audit gate reds. Test importers not in `owned_files` are edited under rationale-backed leeway (no other WP owns them; no-overlap holds).
- `_primary_ref_for` is cross-module: `implement.py` imports it from `implement_cores.py`; pinned by `test_precondition_ref_unification.py` + `test_partition_authority_characterization.py`.
- Depends on WP04 (same review area).

## Subtasks & Detailed Guidance
### T017 – Rename the two `lanes/merge.py` helpers (+ docstrings) and update ALL callers: **`merge/executor.py` (source — do not miss)** + `orchestrator_api/commands.py` + the 13 test importers (listed above) + `write_candidate_classification.yaml`. Grep-verify zero residual before green.
### T018 – Rename `_primary_ref_for` in `implement_cores.py`; update `implement.py` + the two pinning tests (`test_precondition_ref_unification.py`, `test_partition_authority_characterization.py`).
### T019 – (optional) Rename `_resolve_primary_target_branch` (`commit_router.py:553`) internal Sense-B/D helper (delegates to `get_feature_target_branch`). **Caveat: NOT a freebie — it is `monkeypatch.setattr`-ed by name in 8 test files** (`tests/coordination/test_commit_router.py`, `tests/specify_cli/coordination/{test_commit_router_partition,test_commit_router_partition_authority,test_commit_router_placement}.py`, `tests/integration/test_protected_primary_spec_commit.py`, `tests/specify_cli/cli/commands/test_wp03_bypass_writers_fr008.py`, `tests/specify_cli/cli/commands/agent/test_finalize_tasks_commit_surface.py`, `tests/mission_runtime/test_read_path_create_window_invariant.py`). Drop T019 if the churn isn't worth it.
### T020 – Green: full suite + surface-audit gate + `ruff`/`mypy --strict`.

## Test Strategy
- `uv run pytest` (targeted: lanes/merge importers, precondition_ref_unification, partition_authority_characterization, surface_resolution_audit). Do NOT weaken exempt-surface pins.

## Risks & Mitigations
- Missed caller / stale arch fixture → surface-audit gate reds. Grep every caller before renaming; move the yaml fixture in the same commit.

## Review Guidance
- Confirm `is_primary_artifact_kind` untouched; every renamed symbol's callers + fixtures moved together.

## Activity Log
- 2026-07-16T18:15:00Z – system – Prompt created.
- 2026-07-16T19:47:03Z – claude – shell_pid=1211554 – Assigned agent via action command
- 2026-07-16T19:59:07Z – claude – shell_pid=1211554 – Internal helpers renamed (T017-T020 incl T019); all callers incl merge/executor.py + orchestrator_api + 13 test importers + 8 monkeypatch sites + arch fixture moved; grep-verified zero residual; ruff+mypy --strict clean; targeted suites + surface-audit gate green
- 2026-07-16T20:04:52Z – claude – shell_pid=1270649 – Started review via action command
- 2026-07-16T20:05:15Z – user – shell_pid=1270649 – APPROVED. FR-008 internal renames complete & coherent. Zero-residual: git grep old names (merge_lane_to_mission/merge_mission_to_target/_primary_ref_for/_resolve_primary_target_branch) over src+tests EMPTY. Blast radius closed in one commit: executor.py imports+calls (consolidate 271/299, integrate 470/482), orchestrator_api, implement/implement_cores cross-module, commit_router, arch fixture, 13 merge test importers, 2 precondition pins, 8 monkeypatch sites (patch.object/setattr byte-exact to new def). Exempt-integrity intact: is_primary_artifact_kind NOT in diff & still in mission_runtime.__all__; resolve_primary_branch/resolve_merge_target_branch/merge_target_branch/MergeStrategy/merge cmd unaltered. Docstrings clarified (FR-003) cross-referencing the two senses. mypy --strict 6 modules: 0 issues; ruff clean. Targeted suite 955 passed/1 skip; sole failure test_profile_charter_e2e transitive-references is PRE-EXISTING on WP04 base (charter profile compile, unrelated to renames) - surface to operator, not a WP05 blocker.
