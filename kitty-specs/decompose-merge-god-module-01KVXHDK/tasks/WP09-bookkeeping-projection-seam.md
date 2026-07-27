---
work_package_id: WP09
title: Bookkeeping-projection / snapshot seam — merge/bookkeeping_projection.py
dependencies:
- WP08
requirement_refs:
- FR-003
- FR-006
tracker_refs:
- '#2057'
planning_base_branch: prog/2057-merge
merge_target_branch: prog/2057-merge
branch_strategy: Planning artifacts for this mission were generated on prog/2057-merge. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2057-merge unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
- T040
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/merge/
create_intent:
- src/specify_cli/merge/bookkeeping_projection.py
- tests/merge/test_bookkeeping_projection_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/bookkeeping_projection.py
- tests/merge/test_bookkeeping_projection_seam.py
role: implementer
tags: []
task_type: implement
shell_pid: "3429602"
---

# Work Package Prompt: WP09 – Bookkeeping-projection / snapshot seam — merge/bookkeeping_projection.py

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Relocate the status-surface trust + snapshot/restore + projection cluster into `merge/bookkeeping_projection.py`, preserving `_restore_final_bookkeeping_snapshots` signature/behavior for the executor split (INV-6).

- Requirement refs: FR-003, FR-006, INV-6.

## Context & Constraints

- Plan IC-09. Members (research §3): `_validate_mission_slug_path_segment`, `_target_bookkeeping_status_paths`, `_read_optional_bytes`, `_restore_optional_bytes`, `_assert_status_path_within_target_surface`, `_assert_status_surface_path_is_trusted`, `_assert_status_surface_file_path_is_trusted`, `_assert_bookkeeping_snapshot_path_is_trusted`, `_capture_bookkeeping_snapshots`, `_restore_final_bookkeeping_snapshots`, `_target_branch_still_at_baseline`, `_project_status_bookkeeping_to_target`.
- Strictly-linear chain: this WP depends only on its predecessor WP08.
- Ownership: this WP owns ONLY `src/specify_cli/merge/bookkeeping_projection.py`, `tests/merge/test_bookkeeping_projection_seam.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T037 – Create projection seam
- **Steps**: Create `src/specify_cli/merge/bookkeeping_projection.py`; move the trust + snapshot/restore + projection cluster.

### Subtask T038 – Preserve restore signature
- **Steps**: Keep `_restore_final_bookkeeping_snapshots` signature and behavior stable — the executor (WP10) calls it at the ~6 restore-on-exception sites (INV-6).

### Subtask T039 – Wire the shim
- **Steps**: Out-of-map wiring edit to `merge.py`: import-from + re-export where tests import these (e.g. target-bookkeeping-path / trust tests).

### Subtask T040 – Seam test
- **Steps**: [P] Add `tests/merge/test_bookkeeping_projection_seam.py` (≥90%) covering trusted AND rejected path-trust branches and snapshot capture/restore round-trip.

## Definition of Done

- Trust + projection tests pass; `test_merge_residue_gate` green.
- `_restore_final_bookkeeping_snapshots` signature unchanged.
- ruff + mypy clean.

## Risks & Mitigations

- Path-trust assertions are security-sensitive → cover trusted + rejected paths.

## Reviewer Guidance

- Confirm rejected-path assertions still raise.
- Confirm snapshot round-trip is byte-identical.

## Activity Log

- 2026-06-24T21:59:31Z – claude:opus:randy-reducer:implementer – shell_pid=3372502 – Assigned agent via action command
- 2026-06-24T22:15:36Z – claude:opus:randy-reducer:implementer – shell_pid=3372502 – Bookkeeping-projection seam: trust + snapshot/restore + coord->target projection moved verbatim to merge/bookkeeping_projection.py; _restore_final_bookkeeping_snapshots signature stable (INV-6, sig-asserted); trusted+rejected path-trust branches + snapshot round-trip tested; shim re-exports intact; ratchet/spy repointed; 525 merge suite + golden green; ruff + mypy strict clean (no type:ignore).
- 2026-06-24T22:15:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=3429602 – Started review via action command
- 2026-06-24T22:15:53Z – user – shell_pid=3429602 – Review passed: projection/trust/snapshot cluster moved verbatim; path-trust branches (trusted+rejected+topology-mismatch+bad-filename) tested; _restore_final_bookkeeping_snapshots signature stable (INV-6); snapshot round-trip byte-identical; ratchet+spy repointed to seams; 525 suite + golden + residue-gate + coord-topology green; ruff + mypy strict clean.
