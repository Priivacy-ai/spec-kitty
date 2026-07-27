---
work_package_id: WP04
title: Slug/state/target resolution seam — merge/resolve.py
dependencies:
- WP03
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
- T014
- T015
- T016
- T017
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/merge/
create_intent:
- src/specify_cli/merge/resolve.py
- tests/merge/test_resolve_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/resolve.py
- tests/merge/test_resolve_seam.py
role: implementer
tags: []
task_type: implement
shell_pid: "3121964"
---

# Work Package Prompt: WP04 – Slug/state/target resolution seam — merge/resolve.py

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Relocate slug extraction, merge-state load/clear/cleanup, and target-branch resolution into `merge/resolve.py` (consuming the existing `merge/state.py`).

- Requirement refs: FR-003, FR-006, C-002.

## Context & Constraints

- Plan IC-04. Members (research §3): `_extract_mission_slug`, `_resolve_mission_slug`, `_merge_state_key_candidates`, `_iter_merge_states_for_slug`, `_load_merge_state_for_mission`, `_load_merge_state_entry_for_mission`, `_load_or_create_merge_state`, `_clear_merge_state_for_mission`, `_cleanup_merge_workspaces_for_state`, `_resolve_target_branch`.
- Strictly-linear chain: this WP depends only on its predecessor WP03.
- Ownership: this WP owns ONLY `src/specify_cli/merge/resolve.py`, `tests/merge/test_resolve_seam.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T014 – Move the resolvers
- **Steps**: Create `src/specify_cli/merge/resolve.py`; move the slug/state/target resolvers, consuming `merge/state.py` for `MergeState` I/O.

### Subtask T015 – Re-export test-imported resolvers
- **Steps**: Re-export `_resolve_mission_slug`, `_resolve_target_branch` (and the state-load helpers tests import) from the shim (FR-006).

### Subtask T016 – Wire the shim
- **Steps**: Out-of-map wiring edit to `merge.py`: import-from + re-export.

### Subtask T017 – Seam test
- **Steps**: [P] Add `tests/merge/test_resolve_seam.py` (≥90%), covering state-key candidate ordering and target-branch resolution branches.

## Definition of Done

- `resolve` imports cleanly; resolvers re-exported.
- State-key candidate ordering preserved.
- ruff + mypy clean; golden test green.

## Risks & Mitigations

- State-key candidate ordering → preserve exactly; cover in seam test.

## Reviewer Guidance

- Diff `_merge_state_key_candidates` ordering against pre-refactor.
- Confirm no behavior change in slug fallback.

## Activity Log

- 2026-06-24T20:52:40Z – claude:opus:randy-reducer:implementer – shell_pid=3088994 – Assigned agent via action command
- 2026-06-24T21:00:03Z – claude:opus:randy-reducer:implementer – shell_pid=3088994 – Resolve seam: 10 resolvers moved to merge/resolve.py; test-imported resolvers re-exported; state-key candidate order (ULID before slug) locked + covered; 22 seam tests + 427 full merge suite green; one-way import enforced; ruff + mypy --strict clean.
- 2026-06-24T21:00:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=3121964 – Started review via action command
- 2026-06-24T21:00:24Z – user – shell_pid=3121964 – Review passed: 10 resolvers moved verbatim; contract-listed importables re-exported; state-key candidate order (ULID before slug, dedup) preserved + tested; internal helpers correctly not re-exported (unused by shim+tests); one-way import enforced; 22 seam + 427 full suite green; ruff + mypy --strict clean; behavior-preserving.
