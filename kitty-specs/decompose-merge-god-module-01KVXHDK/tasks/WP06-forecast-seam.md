---
work_package_id: WP06
title: Forecast seam — merge/forecast.py
dependencies:
- WP05
requirement_refs:
- FR-001
- FR-003
- FR-004
tracker_refs:
- '#2057'
planning_base_branch: prog/2057-merge
merge_target_branch: prog/2057-merge
branch_strategy: Planning artifacts for this mission were generated on prog/2057-merge. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2057-merge unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/merge/
create_intent:
- src/specify_cli/merge/forecast.py
- tests/merge/test_forecast_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/forecast.py
- tests/merge/test_forecast_seam.py
role: implementer
tags: []
task_type: implement
shell_pid: "3257279"
---

# Work Package Prompt: WP06 – Forecast seam — merge/forecast.py

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Extract the dry-run preview + JSON/human payload build out of the `merge` command body into `merge/forecast.py`, preserving the dry-run JSON key set and the review-artifact gate preview exactly.

- Requirement refs: FR-001, FR-003, FR-004.

## Context & Constraints

- Plan IC-06. Extract from the `merge` body (research §3): lanes-manifest preview, review-artifact gate preview, `would_assign_mission_number` scan, JSON/human payload build. Dry-run JSON keys are frozen in contracts/cli-surface-contract.md.
- Strictly-linear chain: this WP depends only on its predecessor WP05.
- Ownership: this WP owns ONLY `src/specify_cli/merge/forecast.py`, `tests/merge/test_forecast_seam.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T023 – Create forecast
- **Steps**: Create `src/specify_cli/merge/forecast.py`; move the dry-run preview + payload build.

### Subtask T024 – Preserve the schema
- **Steps**: Preserve the dry-run JSON key set and `REJECTED_REVIEW_ARTIFACT_CONFLICT` emission in both human and JSON output (FR-001).

### Subtask T025 – Wire the shim
- **Steps**: Out-of-map wiring edit to `merge.py`: import-from. The dry-run dispatch in the command body delegates to forecast.

### Subtask T026 – Seam test
- **Steps**: [P] Add `tests/merge/test_forecast_seam.py` (≥90%) asserting the exact key set and the review-artifact preview.

## Definition of Done

- Golden test (dry-run JSON) byte-identical.
- `test_merge_dry_run_review_artifact` + `test_merge_strategy` dry-run JSON pass.
- ruff + mypy clean.

## Risks & Mitigations

- Dry-run schema drift → assert exact key set; re-run golden test.

## Reviewer Guidance

- Diff the dry-run JSON key set against the contract.
- Confirm `would_assign_mission_number` scan is unchanged.

## Activity Log

- 2026-06-24T21:23:18Z – claude:opus:randy-reducer:implementer – shell_pid=3215897 – Assigned agent via action command
- 2026-06-24T21:33:35Z – claude:opus:randy-reducer:implementer – shell_pid=3215897 – Forecast seam: dry-run preview/payload build extracted to merge/forecast.py (run_dry_run_forecast + 3 helpers <=15 CC); JSON key set + REJECTED_REVIEW_ARTIFACT_CONFLICT byte-identical; 6 seam tests + golden dry-run + 463 merge suite green; ruff C901 + mypy strict clean.
- 2026-06-24T21:33:37Z – claude:opus:reviewer-renata:reviewer – shell_pid=3257279 – Started review via action command
- 2026-06-24T21:33:50Z – user – shell_pid=3257279 – Review passed: dry-run forecast extracted behavior-preservingly; frozen 10-key JSON payload + REJECTED_REVIEW_ARTIFACT_CONFLICT byte-identical (golden+dry-run regression+seam verify); CC <=15; no type:ignore (real ReviewArtifactPreflightResult type); patches repointed; 463 suite green; ruff+mypy clean.
