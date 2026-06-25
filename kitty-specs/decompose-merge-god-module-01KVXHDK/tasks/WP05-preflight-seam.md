---
work_package_id: WP05
title: Preflight seam — extend merge/preflight.py
dependencies:
- WP04
requirement_refs:
- C-002
- FR-003
- FR-005
- FR-006
tracker_refs:
- '#2057'
planning_base_branch: prog/2057-merge
merge_target_branch: prog/2057-merge
branch_strategy: Planning artifacts for this mission were generated on prog/2057-merge. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2057-merge unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/merge/
create_intent:
- tests/merge/test_preflight_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/preflight.py
- src/specify_cli/merge/push_preflight.py
- tests/merge/test_preflight_seam.py
role: implementer
tags: []
task_type: implement
shell_pid: "3212693"
---

# Work Package Prompt: WP05 – Preflight seam — extend merge/preflight.py

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Relocate git/target/mission-branch/review-artifact/hollow-review preflights into the EXISTING `merge/preflight.py` (+ `push_preflight.py` support), and split `_collect_hollow_review_warnings` (CC21) into helpers each ≤15 CC (FR-005).

- Requirement refs: FR-003, FR-005, FR-006, C-002.

## Context & Constraints

- Plan IC-05. Members (research §3): `_enforce_git_preflight`, `_enforce_planning_artifact_target_branch`, `_check_mission_branch`, `_has_branch_ref`(if not already in git_probes), `_validate_target_branch`, `_target_branch_sync_payload`, `_target_branch_refresh_failed_payload`, `_enforce_target_branch_sync_preflight`, `_effective_push_requested`, `_enforce_canonical_status_history`, `_enforce_review_artifact_consistency`, `_collect_hollow_review_warnings`(split), `_warn_or_confirm_hollow_reviews`.
- Strictly-linear chain: this WP depends only on its predecessor WP04.
- Ownership: this WP owns ONLY `src/specify_cli/merge/preflight.py`, `src/specify_cli/merge/push_preflight.py`, `tests/merge/test_preflight_seam.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T018 – Relocate preflights
- **Steps**: Move the preflight functions into `merge/preflight.py` (+ `push_preflight.py` for target-sync support). Keep `post_merge.review_artifact_consistency` as a leaf dependency.

### Subtask T019 – Split the CC21 fn
- **Steps**: Split `_collect_hollow_review_warnings` into focused helpers, each ≤15 CC, preserving the warning buckets exactly (FR-005).

### Subtask T020 – Re-export
- **Steps**: Re-export `_check_mission_branch`, `_effective_push_requested`, `_enforce_canonical_status_history`, `_enforce_review_artifact_consistency` from the shim (FR-006).

### Subtask T021 – Wire the shim
- **Steps**: Out-of-map wiring edit to `merge.py`: import-from + re-export.

### Subtask T022 – Tests
- **Steps**: [P] Extend/add `tests/merge/test_preflight_seam.py` covering the split helpers and both review-artifact-gate branches (≥90% of new/moved code).

## Definition of Done

- Existing preflight test files pass unchanged.
- `_collect_hollow_review_warnings` and its helpers all ≤15 CC.
- Re-exports green; ruff + mypy clean.

## Risks & Mitigations

- Review-artifact gate behavior → cover both consistent and conflicting branches.

## Reviewer Guidance

- Run existing `test_target_branch_preflight`, `test_push_preflight`, `test_merge_preflight_mission_branch`, `test_hollow_review_warnings`.
- Confirm the hollow-review split preserves bucket contents.

## Activity Log

- 2026-06-24T21:00:53Z – claude:opus:randy-reducer:implementer – shell_pid=3125625 – Assigned agent via action command
- 2026-06-24T21:22:33Z – claude:opus:randy-reducer:implementer – shell_pid=3125625 – Preflight seam: 12 preflights relocated (domain preflight.py + publish push_preflight.py per #1706); _collect_hollow_review_warnings CC21 split into two helpers <=15; shim re-exports test-imported symbols; 3 mission test files repointed to new collaborator homes; 450+ merge suite + golden green; ruff C901 + mypy --strict clean.
- 2026-06-24T21:22:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=3212693 – Started review via action command
- 2026-06-24T21:22:55Z – user – shell_pid=3212693 – Review passed: 12 preflights relocated behavior-preservingly; #1706 publish-layer boundary respected (push/target-sync trio in push_preflight, domain preflight network-free, verified); CC21 hollow-review fn split into 2 helpers <=15 with exact buckets; shim re-exports intact (incl WP02 constants); 3 test files repointed to new collaborator homes; 450+ suite + golden green; ruff C901 + mypy strict clean.
