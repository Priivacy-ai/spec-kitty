---
work_package_id: WP03
title: Git primitives seam — merge/git_probes.py
dependencies:
- WP02
requirement_refs:
- C-006
- FR-003
- FR-006
tracker_refs:
- '#2057'
planning_base_branch: prog/2057-merge
merge_target_branch: prog/2057-merge
branch_strategy: Planning artifacts for this mission were generated on prog/2057-merge. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2057-merge unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
phase: Phase 3 - Decompose
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
scope: merge-decomposition
history: []
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/merge/
create_intent:
- src/specify_cli/merge/git_probes.py
- tests/merge/test_git_probes_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/git_probes.py
- tests/merge/test_git_probes_seam.py
role: implementer
tags: []
task_type: implement
shell_pid: "3085104"
---

# Work Package Prompt: WP03 – Git primitives seam — merge/git_probes.py

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

Drive complexity to zero behavior-preservingly. Each relocated seam is a byte-for-byte move plus the focused tests that prove it. Never change behavior to win a complexity point — extract, thread state, and test. The golden CLI test (WP01) is the byte-identity meter; radon `-n B` is the complexity meter.

## Objectives & Success Criteria

Relocate branch/tree/porcelain git primitives into `merge/git_probes.py`, including the PUBLIC `path_is_under_worktrees` symbol (consumed by doctor.py + agent/mission.py).

- Requirement refs: FR-003, FR-006, C-006.

## Context & Constraints

- Plan IC-03. Members (research §2/§3): `_lane_already_integrated`, `_branch_trees_equal`, `path_is_under_worktrees`, `_raw_porcelain_status`, `_classify_porcelain_lines`, `_is_linear_history_rejection`, `_emit_remediation_hint`, `_has_branch_ref`, `_is_git_repo`, `_refresh_primary_checkout_after_merge`, `_paths_have_status_changes`.
- Strictly-linear chain: this WP depends only on its predecessor WP02.
- Ownership: this WP owns ONLY `src/specify_cli/merge/git_probes.py`, `tests/merge/test_git_probes_seam.py`. Edits to `cli/commands/merge.py` (if any) are small documented import/re-export wiring only — `merge.py` is owned solely by WP11.

## Branch Strategy

- **Strategy**: coordination-branch planning; strictly-linear lane nesting.
- **Planning base branch**: prog/2057-merge
- **Merge target branch**: main (program landing); intermediate lane merges flow back into prog/2057-merge.

## Subtasks & Detailed Guidance

### Subtask T010 – Move the primitives
- **Steps**: Create `src/specify_cli/merge/git_probes.py`; move the branch/tree/porcelain primitives listed in Context (behavior-preserving).

### Subtask T011 – Re-export the public symbol
- **Steps**: Re-export `path_is_under_worktrees` from the shim so doctor.py + agent/mission.py keep importing it with zero edits (FR-006).

### Subtask T012 – Wire + one-way check
- **Steps**: Out-of-map wiring edit to `merge.py`: import-from + re-export. Verify no `merge/*` module imports `cli.commands.merge` (C-006/INV-2).

### Subtask T013 – Seam test
- **Steps**: [P] Add `tests/merge/test_git_probes_seam.py` covering ≥90% of moved code (porcelain classification, linear-history detection, worktree path checks).

## Definition of Done

- `git_probes` imports cleanly; `path_is_under_worktrees` re-exported.
- doctor.py + agent/mission.py importers green.
- One-way import preserved; ruff + mypy clean.

## Risks & Mitigations

- Breaking doctor/mission imports → re-export and run those importers' tests.

## Reviewer Guidance

- Run doctor + agent/mission import smoke tests.
- Confirm `_is_linear_history_rejection` uses the locked token tuple from `_constants`.

## Activity Log

- 2026-06-24T20:42:51Z – claude:opus:randy-reducer:implementer – shell_pid=3041790 – Assigned agent via action command
- 2026-06-24T20:51:52Z – claude:opus:randy-reducer:implementer – shell_pid=3041790 – Git probes seam: 11 primitives moved to merge/git_probes.py; path_is_under_worktrees re-exported (doctor+mission importers green); 38 seam+golden tests green; full merge suite (405) green; one-way import enforced; ruff C901 + mypy --strict clean.
- 2026-06-24T20:51:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=3085104 – Started review via action command
- 2026-06-24T20:52:13Z – user – shell_pid=3085104 – Review passed: 11 primitives moved verbatim; path_is_under_worktrees re-exported (importers green); one-way import enforced; _is_linear_history_rejection uses _constants tokens; 38 seam+golden + full merge suite green; ruff C901 + mypy --strict clean; behavior-preserving (bool() wraps are explicit-typing for follow_imports=skip, no logic change).
