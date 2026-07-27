---
work_package_id: WP07
title: Mission-number bake seam — extend merge/ordering.py
dependencies:
- WP06
requirement_refs:
- C-002
- FR-003
- FR-006
tracker_refs:
- '#2057'
planning_base_branch: prog/2057-merge
merge_target_branch: prog/2057-merge
branch_strategy: Planning artifacts for this mission were generated on prog/2057-merge. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2057-merge unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/merge/
create_intent:
- tests/merge/test_ordering_bake_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/ordering.py
- tests/merge/test_ordering_bake_seam.py
role: implementer
tags: []
task_type: implement
shell_pid: "3306284"
---

# Work Package Prompt: WP07 – Mission-number bake seam — extend merge/ordering.py

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Relocate the mission-number bake cluster into the EXISTING `merge/ordering.py` (which already holds `assign_next_mission_number`), keeping lazy imports lazy (C-007).

- Requirement refs: FR-003, FR-006, C-002.

## Context & Constraints

- Plan IC-07. Members (research §3): `_already_baked`, `_mark_mission_number_baked`, `_is_assigned_mission_number`, `_compute_next_mission_number_or_none`, `_write_mission_number_to_branch`(154 LOC, linear), `_bake_mission_number_into_mission_branch`, `_assign_planning_only_mission_number_if_needed`. `_is_git_repo` may live in git_probes.
- Strictly-linear chain: this WP depends only on its predecessor WP06.
- Ownership: this WP owns ONLY `src/specify_cli/merge/ordering.py`, `tests/merge/test_ordering_bake_seam.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T027 – Relocate the bake cluster
- **Steps**: Move the bake cluster into `merge/ordering.py` (behavior-preserving). Keep the git-worktree-heavy `_write_mission_number_to_branch` verbatim.

### Subtask T028 – Re-export
- **Steps**: Re-export `_bake_mission_number_into_mission_branch` (and other test-imported bake fns) from the shim (FR-006).

### Subtask T029 – Wire + lazy imports
- **Steps**: Out-of-map wiring edit to `merge.py`: import-from + re-export. Do NOT hoist in-function imports to module top (C-007/INV-7).

### Subtask T030 – Tests
- **Steps**: [P] Extend `tests/merge/test_mission_number_idempotency.py` / add `tests/merge/test_ordering_bake_seam.py` (≥90% of moved code).

## Definition of Done

- Idempotency + mission-number tests pass.
- `_bake_mission_number_into_mission_branch` re-exported.
- Lazy imports unchanged; ruff + mypy clean.

## Risks & Mitigations

- `_write_mission_number_to_branch` git-worktree heavy → relocate verbatim; lazy imports unchanged.

## Reviewer Guidance

- Run `test_mission_number_idempotency` + `test_merge_time_number_assignment`.
- Confirm no module-top hoist of `lanes.*`/`coordination.*` imports.

## Activity Log

- 2026-06-24T21:34:12Z – claude:opus:randy-reducer:implementer – shell_pid=3262246 – Assigned agent via action command
- 2026-06-24T21:45:05Z – claude:opus:randy-reducer:implementer – shell_pid=3262246 – Ordering bake seam: 7-fn bake cluster relocated verbatim into merge/ordering.py next to assign_next_mission_number; lazy imports kept lazy (C-007, AST-verified); _bake_mission_number_into_mission_branch re-exported; 21 seam tests + idempotency/number-assignment + 484 merge suite green; ruff C901 + mypy strict clean.
- 2026-06-24T21:45:07Z – claude:opus:reviewer-renata:reviewer – shell_pid=3306284 – Started review via action command
- 2026-06-24T21:45:20Z – user – shell_pid=3306284 – Review passed: bake cluster relocated verbatim (incl 154-LOC _write_mission_number_to_branch); lazy imports kept lazy (C-007, AST-verified); merge logger namespace preserved; _bake_mission_number_into_mission_branch + _is_git_repo re-exported; idempotency/number tests + 484 suite green; ruff C901 + mypy strict clean.
