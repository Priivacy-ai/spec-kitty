---
work_package_id: WP03
title: Topology authority seam + R3 decision row (FR-005, FR-008)
dependencies: []
requirement_refs:
- FR-005
- FR-008
tracker_refs: []
planning_base_branch: feat/name-vs-authority-remediation-01KTYGTE
merge_target_branch: feat/name-vs-authority-remediation-01KTYGTE
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC (mission retargeted to feat/name-vs-authority-remediation-01KTYGTE on 2026-06-12 — PR #1895 branch frozen for review). During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/name-vs-authority-remediation-01KTYGTE unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 1 - Independent lanes
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1685939"
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/coordination/surface_resolver.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/coordination/surface_resolver.py
- src/specify_cli/coordination/status_service.py
- src/specify_cli/dashboard/scanner.py
- src/specify_cli/workspace/root_resolver.py
- src/specify_cli/status/emit.py
- src/specify_cli/status/work_package_lifecycle.py
- tests/specify_cli/coordination/test_worktree_topology*.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Topology authority seam

## ⚡ Do This First: Load Agent Profile
Load the assigned profile via `spec-kitty agent profile show <profile-id> --all` (pick the best implementer match if none assigned) and operate within its boundaries before reading further.

---
## Objectives & Success Criteria
Per `research-authority-seams.md` (NORMATIVE — seam 1):
- **T009 (ATDD FIRST):** `WorktreeTopology` enum + `classify_worktree_topology(path, *, repo_root, registry=None)` + `is_registered_coord_worktree(...)` in `surface_resolver.py`, wrapping the `git worktree list --porcelain` cross-check (exemplar `doctor.py:~3063`); registry injectable/cacheable. Unit tests incl. the F-005 husk case (a `-coord`-NAMED plain dir is classified UNREGISTERED, never COORD).
- **T010 (FR-008):** the #1889 decision table (data-model.md §3) implemented in the classifier path — net-new row R3 (declared + worktree absent + branch DELETED → distinct loud StructuredError; one `git rev-parse --verify`); rows R1/R2/R2′/R4 pinned by tests; composes with upstream #1848's status_transition carve-out (do NOT touch that file here — WP05 migrates it).
- **T011:** migrate the 5 owned consumer sites (`status_service.py:54-56`, `dashboard/scanner.py:328-332`, `workspace/root_resolver.py:72`, `emit.py:388` lock-root, `work_package_lifecycle.py:58`) to the seam. Behavior-preserving except where the old predicate was WRONG (husk-spoofable) — those flips are the point; pin each.
- **T012:** suites green (coordination, dashboard scanner, status emit/lifecycle) + `tests/architectural/ -q`.

## Context & Constraints (read before coding)
- Design (absolute): `kitty-specs/name-vs-authority-remediation-01KTYGTE/{spec.md, plan.md, data-model.md, contracts/authority-seams.md}` + the mission `research/` — **`research-authority-seams.md` is NORMATIVE** for seam APIs/site lists/decision table; `research-p0-rootcauses.md` for defect mechanics; `research-fold-cluster.md` for ready deltas.
- NFR-003 binding: fail-closed over fallback — never introduce a silent name-derived fallback.
- ATDD: pinning/contract tests FIRST where the WP names them. New code: ruff + mypy zero issues, zero suppressions. No existing passing test modified (NFR-001; pin-of-defective-behavior exceptions justified per case).
- C-002: in `coordination/status_transition.py` and `cli/commands/merge.py`, touch ONLY the ranges this WP names — upstream coord-merge-stabilization owns adjacent ranges.
- move-task/mark-status: run from the PRIMARY checkout with the FULL mission slug (`name-vs-authority-remediation-01KTYGTE`). No kitty-specs commits on the lane.

## Definition of Done
Seam is the only topology authority in owned files; husk-spoof test proves the registry disposes; decision-table rows pinned; all suites green.

## Review Guidance
reviewer-renata (+architect-alphonso spot-check on the seam API vs his normative doc). Adversarial: create a fake `-coord` dir and prove every migrated site rejects it.

## Activity Log
- 2026-06-12T18:32:00Z – system – Prompt created.
- 2026-06-12T19:23:05Z – claude:opus:python-pedro:implementer – shell_pid=1470114 – Assigned agent via action command
- 2026-06-12T19:52:03Z – claude:opus:python-pedro:implementer – shell_pid=1470114 – Topology authority seam complete (FR-005/FR-008). Added WorktreeTopology enum + classify_worktree_topology/is_registered_coord_worktree/is_under_worktrees_segment/read_worktree_registry in surface_resolver.py (porcelain-registry backed, fail-closed via WorktreeRegistryUnavailable, injectable cached registry). Implemented #1889 R3: declared+branch-DELETED+worktree-absent raises distinct CoordinationBranchDeleted (subclass of StatusReadPathNotFound, error_code COORDINATION_BRANCH_DELETED, actionable next_step), one git rev-parse --verify disambiguates R2 vs R3; never silent primary fallback. Migrated all 5 A-sites + 2 G-lock sites: status_service (label guard->is_under_worktrees_segment), dashboard/scanner (classify, husk no longer shadows primary), root_resolver (is_registered_coord), emit/work_package_lifecycle (lock root->canonical root for registered worktrees). ATDD: 18 new classifier+R3 tests + scanner husk-rejection pin. Fixtures that declared coord branch without creating it updated to model real ensure_coordination_branch R2 state. Scope fence respected (status_transition/aggregate/merge.py untouched=WP05/C-002). ruff clean, zero NEW mypy errors, 687 owned-area tests + 350 architectural green. Commit 4788a4583. Pre-existing failures (NOT mine): tests/unit/workspace/test_root_resolver.py::test_non_git_directory_raises and ~28 env/ordering failures (charter/README/skills/acceptance) confirmed failing on clean baseline.
- 2026-06-12T19:52:45Z – claude:opus:reviewer-renata:reviewer – shell_pid=1667625 – Started review via action command
- 2026-06-12T20:00:16Z – user – shell_pid=1667625 – Moved to planned
- 2026-06-12T20:01:14Z – claude:opus:python-pedro:implementer – shell_pid=1679127 – Started implementation via action command
- 2026-06-12T20:04:33Z – claude:opus:python-pedro:implementer – shell_pid=1679127 – Cycle 2: unused-ignore fixed; lock-root regression test added (RED-on-mutation proven)
- 2026-06-12T20:05:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=1685939 – Started review via action command
- 2026-06-12T20:07:50Z – user – shell_pid=1685939 – Review passed (cycle 2 re-review, supersedes prior rejected review-cycle-2.md artifact). Both cycle-1 blockers fixed & independently verified. (1) unused-ignore: surface_resolver.py:104 now type:ignore[misc,unused-ignore] w/ expanded dual-invocation rationale; full-package CI mypy (src/specify_cli src/charter src/doctrine) = exactly 82 errors (pre-existing baseline), zero in surface_resolver; single-file run clean. (2) Lock-root flip: two new REAL-worktree regression tests (emit._feature_status_lock_root + lifecycle._repo_root_for_lock) assert canonical-primary lock root + cross-context agreement; mutation check (disabled canonical-root branch via 'if False and' in BOTH emit.py AND work_package_lifecycle.py) turned both tests RED w/ correct failure (lock root = worktree-local instead of canonical), git checkout restored GREEN. Cycle-2 diff 4788a4583..HEAD touches ONLY surface_resolver.py + test_worktree_topology.py; C-002 fence intact (status_transition/aggregate/merge.py = 0 commits whole lane); ruff clean; 20 seam+decision-table tests green. Cycle-1 non-blocking adjudications (fixtures, dead-symbol allowlist, shape idiom, R3) stand.
