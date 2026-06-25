---
work_package_id: WP10
title: Executor seam + CC-102 decomposition — merge/executor.py
dependencies:
- WP09
requirement_refs:
- FR-003
- FR-005
- FR-006
- FR-007
tracker_refs:
- '#2057'
planning_base_branch: prog/2057-merge
merge_target_branch: prog/2057-merge
branch_strategy: Planning artifacts for this mission were generated on prog/2057-merge. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2057-merge unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
- T045
- T046
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/merge/
create_intent:
- src/specify_cli/merge/executor.py
- tests/merge/test_executor_phase_boundary.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/executor.py
- tests/merge/test_executor_phase_boundary.py
role: implementer
tags: []
task_type: implement
shell_pid: "3758628"
---

# Work Package Prompt: WP10 – Executor seam + CC-102 decomposition — merge/executor.py

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Relocate `_run_lane_based_merge` + `_run_lane_based_merge_locked` into `merge/executor.py` and internally decompose the CC-102 driver into ~9 phase helpers (each ≤15 CC) via a `_MergeRunState` dataclass; preserve #1827 ordering (INV-5) and the ~6 snapshot-restore-on-exception sites exactly (INV-6). THE high-risk WP.

- Requirement refs: FR-003, FR-005, FR-006, FR-007.

## Context & Constraints

- Plan IC-10. Proposed phases (research §6.1): `_phase_gates_and_state`, `_phase_merge_lanes`, `_phase_bake_and_pre_target_done`, `_phase_mission_to_target`, `_phase_capture_and_baseline`, `_phase_record_done_and_project`, `_phase_porcelain_invariant`, `_phase_commit_and_assert`, `_phase_cleanup_and_summary`. `_MergeRunState` fields: data-model 'Phase-state object'. Executor consumes every prior seam (WP02–WP09).
- Strictly-linear chain: this WP depends only on its predecessor WP09.
- Ownership: this WP owns ONLY `src/specify_cli/merge/executor.py`, `tests/merge/test_executor_phase_boundary.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T041 – Define _MergeRunState
- **Steps**: Define the `_MergeRunState` dataclass threading shared mutable state (snapshots, baseline SHA, mission_number_meta_path, done-marked flags, paths) per data-model 'Phase-state object'.

### Subtask T042 – Move the executor
- **Steps**: Create `merge/executor.py`; move `_run_lane_based_merge` (lock wrapper) + `_run_lane_based_merge_locked`, consuming the prior seams. Keep lazy imports lazy (C-007).

### Subtask T043 – Decompose into phases
- **Steps**: Decompose `_run_lane_based_merge_locked` into the ~9 phase helpers in Context, each taking `_MergeRunState`, mutating documented fields, returning None — each ≤15 CC (FR-005).

### Subtask T044 – Preserve #1827 ordering
- **Steps**: Preserve baseline record (post-target-merge / pre-bookkeeping-commit) → safe_commit → baseline assert (post-commit) ordering and the restore-on-`BaselineMergeCommitError` rollback EXACTLY across phase boundaries (INV-5/INV-6).

### Subtask T045 – Re-export
- **Steps**: Re-export `_run_lane_based_merge` + `_run_lane_based_merge_locked` from the shim (tests + integration import them) (FR-006).

### Subtask T046 – Phase-boundary regression test
- **Steps**: [P] Add `tests/merge/test_executor_phase_boundary.py`: assert the record→commit→assert ordering and that `BaselineMergeCommitError` triggers restore-then-reraise (FR-007).

## Definition of Done

- Every executor function (incl. phase helpers) ≤15 CC.
- #1827 phase-boundary regression test + `test_1827_baseline_regression` pass.
- Recovery/resume/coord-topology/post-merge-invariant suites green; re-exports green; ruff + mypy clean.

## Risks & Mitigations

- THE mission risk → thread state via the dataclass, never closures; keep lazy imports lazy; add the phase-boundary test BEFORE claiming done; preserve all ~6 restore-on-exception sites verbatim.

## Reviewer Guidance

- Diff phase ordering against the pre-refactor line ranges (research §6.1).
- Confirm each restore-on-exception site keeps identical exception-class scoping.
- Run the full merge integration suite.

## Activity Log

- 2026-06-24T22:16:21Z – claude:opus:randy-reducer:implementer – shell_pid=3434929 – Assigned agent via action command
- 2026-06-24T23:58:16Z – claude:opus:randy-reducer:implementer – shell_pid=3434929 – Executor seam + CC-102 decomposition: _run_lane_based_merge[_locked] moved to merge/executor.py, driver decomposed into 13 phase helpers (<=15 CC each) via _MergeRunState dataclass; #1827 ordering (INV-5) + ~6 restore-on-exception sites (INV-6) preserved exactly + phase-boundary regression test (7 tests) green; review-artifact gate kept pre-state; core merge gate (562) + integration (71) + #1827 regression green; ruff C901 + mypy --strict clean; ~14 test files repointed to seam patch targets (behavior-preserving).
- 2026-06-24T23:58:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=3758628 – Started review via action command
- 2026-06-24T23:58:43Z – user – shell_pid=3758628 – Review passed (HIGH-RISK): CC-102 driver decomposed into 13 phase helpers (<=15 CC, radon-verified) via _MergeRunState (no closures); INV-5 #1827 record->commit->assert ordering + INV-6 ~6 restore-on-exception sites preserved exactly (phase-boundary regression test + test_1827_baseline_regression green); review-artifact gate kept pre-state (no state.json on rejection); lazy imports lazy; one-way import; shim re-exports complete; 562 core gate + 71 integration + golden green; ruff C901 + mypy strict clean (no type:ignore); ~14 test files repointed to seam patch targets behavior-preservingly.
