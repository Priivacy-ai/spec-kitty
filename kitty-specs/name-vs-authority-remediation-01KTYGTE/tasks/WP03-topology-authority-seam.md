---
work_package_id: WP03
title: Topology authority seam + R3 decision row (FR-005, FR-008)
dependencies: []
requirement_refs:
- FR-005
- FR-008
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 1 - Independent lanes
assignee: ''
agent: ''
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
