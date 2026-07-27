---
work_package_id: WP08
title: Done-bookkeeping seam — merge/done_bookkeeping.py
dependencies:
- WP07
requirement_refs:
- FR-003
- FR-005
- FR-006
tracker_refs:
- '#2057'
planning_base_branch: prog/2057-merge
merge_target_branch: prog/2057-merge
branch_strategy: Planning artifacts for this mission were generated on prog/2057-merge. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2057-merge unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/merge/
create_intent:
- src/specify_cli/merge/done_bookkeeping.py
- tests/merge/test_done_bookkeeping_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/done_bookkeeping.py
- tests/merge/test_done_bookkeeping_seam.py
role: implementer
tags: []
task_type: implement
shell_pid: "3368994"
---

# Work Package Prompt: WP08 – Done-bookkeeping seam — merge/done_bookkeeping.py

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Relocate done/approved transition emission + done asserts + resume reconcile into `merge/done_bookkeeping.py`; split `_mark_wp_merged_done` (CC22) and `_assert_merged_wps_done_on_target` (CC16) into helpers each ≤15 CC (FR-005).

- Requirement refs: FR-003, FR-005, FR-006.

## Context & Constraints

- Plan IC-08. Members (research §3): `_mark_wp_merged_done`(split), `_has_transition_to`, `_assert_merged_wps_reached_done`, `_assert_merged_wps_done_on_target`(split), `_reconcile_completed_wps_for_resume`, `_record_merged_wps_done_for_merge`, `_resolve_merge_actor`. `_mark_wp_merged_done` is consumed by orchestrator_api/commands.py:482.
- Strictly-linear chain: this WP depends only on its predecessor WP07.
- Ownership: this WP owns ONLY `src/specify_cli/merge/done_bookkeeping.py`, `tests/merge/test_done_bookkeeping_seam.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T031 – Create done-bookkeeping
- **Steps**: Create `src/specify_cli/merge/done_bookkeeping.py`; move the done/approved emission + asserts + reconcile.

### Subtask T032 – Split _mark_wp_merged_done
- **Steps**: Split the CC22 `_mark_wp_merged_done` (PLANNED-fallback / force-done / dedup-guard branching) into focused helpers, each ≤15 CC, preserving behavior exactly.

### Subtask T033 – Split the assert
- **Steps**: Split `_assert_merged_wps_done_on_target` (CC16) into helpers ≤15 CC.

### Subtask T034 – Re-export for orchestrator_api
- **Steps**: Re-export `_mark_wp_merged_done` + `_assert_merged_wps_reached_done` + `_assert_merged_wps_done_on_target` from the shim so orchestrator_api/commands.py + tests import unchanged (FR-006).

### Subtask T035 – Wire the shim
- **Steps**: Out-of-map wiring edit to `merge.py`: import-from + re-export.

### Subtask T036 – Seam test
- **Steps**: [P] Add `tests/merge/test_done_bookkeeping_seam.py` (≥90%) exercising the split branches directly (force-done, PLANNED fallback, dedup).

## Definition of Done

- `_mark_wp_merged_done` re-exported; orchestrator_api importer green.
- `test_merge_done_recording` + the mark/assert tests pass.
- Both split functions and their helpers ≤15 CC; ruff + mypy clean.

## Risks & Mitigations

- Intricate dedup/force branching → focused tests per branch; preserve behavior exactly.

## Reviewer Guidance

- Run `test_merge_done_recording` + orchestrator_api import smoke.
- Confirm each split branch has a dedicated test.

## Activity Log

- 2026-06-24T21:45:43Z – claude:opus:randy-reducer:implementer – shell_pid=3310009 – Assigned agent via action command
- 2026-06-24T21:58:50Z – claude:opus:randy-reducer:implementer – shell_pid=3310009 – Done-bookkeeping seam: emission+asserts+reconcile+recording moved to merge/done_bookkeeping.py; _mark_wp_merged_done CC22->11 + _assert_merged_wps_done_on_target CC16->9 via focused helpers (all <=15); _mark_wp_merged_done + asserts re-exported (orchestrator_api green); 20 seam + 34 done-recording + 504 merge suite green; stale read_wp_frontmatter assertion repointed to seam; ruff C901 + mypy strict clean.
- 2026-06-24T21:58:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=3368994 – Started review via action command
- 2026-06-24T21:59:07Z – user – shell_pid=3368994 – Review passed: done-bookkeeping moved behavior-preservingly; _mark_wp_merged_done CC22->11 + _assert_merged_wps_done_on_target CC16->9 (radon-verified all helpers <=15), branching preserved + per-branch tested; orchestrator_api re-exports green; stale read_wp_frontmatter assertion repointed to seam; 504 suite + 20 seam + 34 done-recording green; ruff C901 + mypy strict clean (TYPE_CHECKING, no type:ignore).
