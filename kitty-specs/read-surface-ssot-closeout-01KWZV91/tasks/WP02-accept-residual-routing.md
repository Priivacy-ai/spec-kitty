---
work_package_id: WP02
title: Accept residual routing + M2 dirty-surface reconciliation
dependencies:
- WP01
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3045210"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/accept.py
create_intent:
- tests/specify_cli/cli/commands/test_accept_residual_partition.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/accept.py
- tests/specify_cli/cli/commands/test_accept_residual_partition.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile via `/ad-hoc-profile-load` for `python-pedro` (implementer). Then read
`spec.md` (FR-008), `plan.md` (IC-02), and `contracts/partition-aware-commit-seam.md` (§Out of
contract — accept is the separate concern). **Append to `traces/*.md` when relevant.**

## Objective

Route `accept.py::_commit_residual_acceptance_artifacts` through the now-partition-aware
`commit_for_mission` seam (WP01) instead of raw `git commit`, **and reconcile its dirty-detection
surface** with the write-back surface (M2): `write_acceptance_matrix` writes to the **coord**
worktree, but the current dirty-check scans **primary** `git status` — a coord edit never shows
there.

## Context

- `accept.py::_commit_residual_acceptance_artifacts` (~line 76, called ~line 492) currently does a
  raw `run_git(["commit", ...])` (~line 105) — bypasses the seam entirely.
- `_spec_artifact_dirty_paths` (~line 46) scans primary `git_status_lines(repo_root)` (~line 62).
- `write_acceptance_matrix` (`acceptance/matrix.py:182`, called from `acceptance/__init__.py`)
  writes the matrix to the coord `feature_dir` under coord topology.
- **Depends on WP01** — the seam must be partition-aware first.

## Subtasks

### T006 — Red-first
Add `tests/specify_cli/cli/commands/test_accept_residual_partition.py`: on a coord-topology mission,
run the accept residual path; assert (currently RED) the matrix commit lands on **coord**, and that
a coord-worktree edit IS detected by the dirty-check. Prove red pre-fix.

### T007 — Route through the seam
Replace the raw `run_git` commit in `_commit_residual_acceptance_artifacts` with
`commit_for_mission(...)` (single-partition batch → coord for the matrix/issue-matrix/status files).
Do not hand-classify — let the partition-aware seam route.

### T008 — Reconcile dirty-detection (M2)
`_spec_artifact_dirty_paths` must also detect dirt in the coord worktree where
`write_acceptance_matrix` writes (resolve that surface via the placement seam `read_dir`/coord
worktree), not only primary `git status`. Keep PRIMARY-kind residuals working.

### T009 — Regression + quality
FR-008 regression asserting matrix filled+committed via accept lands coord + read back. `ruff`/`mypy`
clean; complexity ≤15; tracer append.

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP02 --agent <name>`.

## Definition of Done
- [ ] Red-first proven; accept residual matrix lands coord.
- [ ] Dirty-detection sees coord-worktree edit (M2 gap closed); PRIMARY residuals unregressed.
- [ ] ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
Confirm the routing goes through `commit_for_mission` (not a new raw commit). Confirm the
dirty-detection now covers the coord write surface. Verify the coord-topology regression.

## Activity Log

- 2026-07-08T08:10:49Z – claude:sonnet:python-pedro:implementer – shell_pid=2800340 – Assigned agent via action command
- 2026-07-08T08:41:51Z – claude:sonnet:python-pedro:implementer – shell_pid=2800340 – Ready: accept residual commit routed through commit_for_mission (coord partition), M2 coord-worktree dirty-detection added, red-first proven green, PRIMARY residuals unregressed
- 2026-07-08T08:43:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=3045210 – Started review via action command
- 2026-07-08T08:48:08Z – user – shell_pid=3045210 – Review passed: FR-008 M2 union-scan (primary+coord via placement_seam.read_dir, existence-gated, no materialization), coord residuals routed through commit_for_mission seam (kind=ACCEPTANCE_MATRIX), primary residuals keep byte-identical raw-git path; split-by-detection-surface avoids commit_for_mission protected-branch refusal on missions with protected target_branch (sound: each partition's dirt is physically in its own worktree). Red-first proven with REAL CoordinationWorkspace worktree (coord dirt invisible pre-fix, lands coord post-fix w/ round-trip read-back, primary+mixed batches correct). 69 accept + 306 acceptance/coordination tests green; ruff/mypy clean.
