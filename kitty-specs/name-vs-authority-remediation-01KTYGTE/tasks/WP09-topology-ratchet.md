---
work_package_id: WP09
title: 'Ratchet: test_topology_resolution_boundary (FR-009) — lands last'
dependencies:
- WP03
- WP04
- WP05
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T030
- T031
- T032
phase: Phase 3 - Closure
assignee: ''
agent: ''
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: tests/architectural/test_topology_resolution_boundary.py
execution_mode: code_change
model: ''
owned_files: []
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – Topology resolution ratchet

## ⚡ Do This First: Load Agent Profile
Load the assigned profile via `spec-kitty agent profile show <profile-id> --all` (pick the best implementer match if none assigned) and operate within its boundaries before reading further.

---
## Objectives & Success Criteria
The permanent C-RATCHET enforcement (contracts/authority-seams.md), structure mirroring `tests/architectural/test_safe_commit_import_boundary.py`:
- **T030:** three assertions — (1) coord-predicate idioms (`-coord` suffix checks, `".worktrees" in parts`) allowlisted to the blessed seam module(s) only (enumerate the post-WP03/05 reality precisely); (2) AST scan: `f"kitty/mission-{...}"`-class branch composes outside `lanes/branch_naming.py` fail; (3) zero `+"00000000")[:8]` fabrication idiom occurrences in src/.
- **T031:** strictness proofs — per assertion, temporarily inject a rogue violation, watch the test FAIL with its actionable message, revert; paste all three proofs in the handoff note (mandatory evidence).
- **T032:** full `tests/architectural/ -q` green; pytestmark correct (architectural marker convention).

## Context & Constraints (read before coding)
- Design (absolute): `kitty-specs/name-vs-authority-remediation-01KTYGTE/{spec.md, plan.md, data-model.md, contracts/authority-seams.md}` + the mission `research/` — **`research-authority-seams.md` is NORMATIVE** for seam APIs/site lists/decision table; `research-p0-rootcauses.md` for defect mechanics; `research-fold-cluster.md` for ready deltas.
- NFR-003 binding: fail-closed over fallback — never introduce a silent name-derived fallback.
- ATDD: pinning/contract tests FIRST where the WP names them. New code: ruff + mypy zero issues, zero suppressions. No existing passing test modified (NFR-001; pin-of-defective-behavior exceptions justified per case).
- C-002: in `coordination/status_transition.py` and `cli/commands/merge.py`, touch ONLY the ranges this WP names — upstream coord-merge-stabilization owns adjacent ranges.
- move-task/mark-status: run from the PRIMARY checkout with the FULL mission slug (`name-vs-authority-remediation-01KTYGTE`). No kitty-specs commits on the lane.

## Definition of Done
Ratchet green + strictness-proven ×3; full architectural suite green; allowlists carry rationale comments referencing the seam contracts.

## Review Guidance
reviewer-renata; she runs her OWN rogue-injection proof (the WP10-01KTRC04 review precedent).

## Activity Log
- 2026-06-12T18:32:00Z – system – Prompt created.
