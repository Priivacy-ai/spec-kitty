---
work_package_id: WP07
title: finalize_tasks seam + mega-function decomposition
dependencies:
- WP06
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
- T027
- T028
- T029
- T030
- T031
phase: Phase 3 - Command seams
assignee: ''
agent: "claude:opus:randy-reducer:implementer"
shell_pid: "3482333"
history:
- timestamp: '2026-06-24T19:52:40Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/mission_finalize.py
create_intent:
- src/specify_cli/cli/commands/agent/mission_finalize.py
- tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_finalize.py
- tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py
tags: []
---

# Work Package Prompt: WP07 – finalize_tasks seam + mega-function decomposition

## Do This First

1. Confirm WP06 merged; golden test green.
2. Read research.md §2 (`finalize_tasks` 1227 LOC — the worst offender, phases enumerated), R-3 (the
   `--validate-only` zero-mutation invariant INV-6 MUST survive), and §5 (existing finalize test files).
3. `finalize_tasks` is imported by `lifecycle.py` — stays re-exportable at `mission.<name>` (WP09).
4. Do NOT move `_stage_finalize_artifacts_in_coord_worktree` here — it relocates to commit_router in WP08.

## Objective

Move `finalize_tasks` + its finalize helpers into `mission_finalize.py`, decomposing the 1227-LOC body into
≤15-CC phase helpers each with a focused test, preserving the `--validate-only` zero-mutation invariant.

## Implementation

### T027 — Create the seam module
Move `finalize_tasks` + `_collect_finalize_artifacts`, `_extract_wp_ids_from_task_files`,
`_branch_tree_relative_path` into `mission_finalize.py`. Keep `commit_for_mission` lazy.

### T028 — Decompose finalize_tasks
Extract phase helpers (each ≤15 CC):
- boundary/SaaS preflight (`run_preflight`)
- feature-dir resolution (Seam D)
- target-branch resolution (`_resolve_planning_branch`)
- pre-loop frontmatter read for conflict detection (T004 in source)
- dependency-conflict "disagree-loud" detection
- charter-activation gate (FR-017)
- dependency resolution preserve-existing
- 8-field bootstrap-mutation loop (dependencies, planning_base_branch, merge_target_branch,
  branch_strategy, requirement_refs, execution_mode, owned_files, authoritative_surface),
  writes guarded by `frontmatter_changed and not validate_only`
- manifest build + ownership/overlap validation
- commit via `commit_for_mission`
- SaaS WPCreated/TasksCompleted emit + dossier sync

### T029 — Preserve INV-6
Add an explicit assertion that the write phase is unreachable when `validate_only`; extend
`test_finalize_tasks_validate_only_readonly.py`.

### T030 — Phase-helper tests
Author `test_mission_finalize_phases.py` with focused tests per extracted phase helper (the Seam C parsers
now get direct + phase coverage).

### T031 — Gates
Golden test + full finalize suite (`test_mission_finalize_tasks.py`,
`test_finalize_tasks_owned_files_validation.py`, `test_finalize_tasks_validate_only_readonly.py`,
`test_finalize_tasks_explicit_empty_owned_files.py`, `test_feature_finalize_bootstrap.py`,
`test_finalize_coord_staging.py`, `test_finalize_clobber_e2e.py`, `tests/tasks/test_finalize_*`) green;
ruff (C901 ≤15 — every phase helper) + mypy --strict clean.

## Acceptance

- `finalize_tasks` body fully ≤15 CC via phase helpers, each tested; INV-6 reinforced; golden + full
  finalize suite green.

## Out-of-map edits

- `src/specify_cli/cli/commands/agent/mission.py`: import-line edits only.

## Activity Log

- 2026-06-24T22:51:16Z – claude:opus:randy-reducer:implementer – shell_pid=3482333 – Assigned agent via action command
- 2026-06-24T22:52:34Z – claude:opus:randy-reducer:implementer – shell_pid=3482333 – Driver stopping at clean WP06/approved boundary before the WP07 finalize_tasks decomposition (1227 LOC, worst offender). WP07 claim is in_progress on lane-g (rebased on WP06 chain, mission.py at 1742 LOC, finalize_tasks at lines 517-1743). Next driver: relocate finalize_tasks + _collect_finalize_artifacts/_extract_wp_ids_from_task_files/_branch_tree_relative_path into mission_finalize.py, route ~12 test-patched cross-cutting symbols (bootstrap_canonical_state, emit_wp_created, _find_feature_directory, get_emitter, locate_project_root, read_wp_frontmatter, _resolve_planning_branch, run_command, _show_branch_context, validate_ownership, get_current_branch) via the mission module, decompose to <=15 CC preserving the --validate-only zero-mutation invariant (INV-6); do NOT move _stage_finalize_artifacts_in_coord_worktree (WP08 relocates it). PRE-EXISTING FAILURE to ignore: tests/integration/test_protected_primary_spec_commit.py::*[record_analysis] fails on mission._resolve_record_analysis_placement_ref (WP04 shim gap, deferred to WP09's re-export sweep; confirmed failing on pristine WP04 tip).
- 2026-06-24T23:23:01Z – claude:opus:randy-reducer:implementer – shell_pid=3482333 – Moved to for_review
- 2026-06-24T23:23:23Z – user – shell_pid=3482333 – Moved to approved
