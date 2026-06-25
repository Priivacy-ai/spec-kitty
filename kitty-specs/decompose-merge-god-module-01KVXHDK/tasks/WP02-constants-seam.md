---
work_package_id: WP02
title: Shared constants seam — merge/_constants.py
dependencies:
- WP01
requirement_refs:
- C-008
- FR-003
- NFR-003
tracker_refs:
- '#2057'
planning_base_branch: prog/2057-merge
merge_target_branch: prog/2057-merge
branch_strategy: Planning artifacts for this mission were generated on prog/2057-merge. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2057-merge unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/merge/
create_intent:
- src/specify_cli/merge/_constants.py
- tests/merge/test_constants_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/_constants.py
- tests/merge/test_constants_seam.py
role: implementer
tags: []
task_type: implement
shell_pid: "3037301"
---

# Work Package Prompt: WP02 – Shared constants seam — merge/_constants.py

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Centralize shared literals / type aliases / module logger into `merge/_constants.py` so later seams import them without S1192 duplication. Foundation for every subsequent move.

- Requirement refs: FR-003, C-008, NFR-003.

## Context & Constraints

- Plan IC-02. Constants to relocate (research §3): `_STATUS_EVENTS_FILENAME`, `_STATUS_FILENAME`, `_SAFE_PATH_SEGMENT_DIAGNOSTIC`, `TARGET_BRANCH_NOT_SYNCHRONIZED`, `TARGET_BRANCH_SYNC_INVARIANT`, `LINEAR_HISTORY_REJECTION_TOKENS`, `MissionBranchBlocker`, `HollowReviewWarnings` aliases, module `logger`.
- Strictly-linear chain: this WP depends only on its predecessor WP01.
- Ownership: this WP owns ONLY `src/specify_cli/merge/_constants.py`, `tests/merge/test_constants_seam.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T006 – Create the constants module
- **Steps**: Create `src/specify_cli/merge/_constants.py` and move the shared literals/type-aliases/logger listed in Context.

### Subtask T007 – Lock the rejection tokens
- **Steps**: Preserve `LINEAR_HISTORY_REJECTION_TOKENS` tuple order and membership byte-for-byte (INV-8 / C-008).

### Subtask T008 – Wire the shim
- **Steps**: Out-of-map wiring edit to `cli/commands/merge.py`: import the constants from `_constants` and re-export so `__all__` stays byte-stable. Document the edit in the WP.

### Subtask T009 – Seam test
- **Steps**: [P] Add `tests/merge/test_constants_seam.py` asserting the exact `LINEAR_HISTORY_REJECTION_TOKENS` tuple and the relocated literals.

## Definition of Done

- `merge/_constants.py` imports cleanly; golden test (WP01) still green.
- `LINEAR_HISTORY_REJECTION_TOKENS` byte-identical.
- ruff + mypy --strict clean; no new suppressions.

## Risks & Mitigations

- Constant drift → assert exact tuple in the seam test.

## Reviewer Guidance

- Diff the rejection-tokens tuple against pre-refactor.
- Confirm the merge.py wiring edit is import/re-export only (no behavior change).

## Activity Log

- 2026-06-24T20:34:08Z – claude:opus:randy-reducer:implementer – shell_pid=3008090 – Assigned agent via action command
- 2026-06-24T20:41:22Z – claude:opus:randy-reducer:implementer – shell_pid=3008090 – Constants seam: merge/_constants.py; shim re-imports+re-exports; LINEAR_HISTORY_REJECTION_TOKENS locked (INV-8); 14 seam tests + golden + full merge suite green; ruff+mypy clean. (--force: lane carries only pre-seeded planning status files, identical pattern to approved WP01; implementation diff is the seam move + wiring only.)
- 2026-06-24T20:41:33Z – claude:opus:reviewer-renata:reviewer – shell_pid=3037301 – Started review via action command
- 2026-06-24T20:42:00Z – user – shell_pid=3037301 – Review passed: pure move+re-export diff (no logic change); LINEAR_HISTORY_REJECTION_TOKENS byte-identical (INV-8); shim re-exports identical objects; one-way import enforced by AST test; logger namespace preserved; golden+full merge suite green; ruff+mypy clean. (--force: lane carries only pre-seeded planning status files.)
