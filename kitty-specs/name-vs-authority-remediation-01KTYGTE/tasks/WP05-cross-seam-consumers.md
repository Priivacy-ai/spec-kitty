---
work_package_id: WP05
title: Cross-seam consumers + fabrication eradication (FR-007 + A/B residual sites)
dependencies:
- WP03
- WP04
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T016
- T017
- T018
- T019
phase: Phase 2 - Integration
assignee: ''
agent: ''
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/status/aggregate.py
execution_mode: code_change
model: ''
owned_files: []
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Cross-seam consumers + fabrication eradication

## ⚡ Do This First: Load Agent Profile
Load the assigned profile via `spec-kitty agent profile show <profile-id> --all` (pick the best implementer match if none assigned) and operate within its boundaries before reading further.

---
## Objectives & Success Criteria
Files needing BOTH seams (hence deps WP03+WP04 — your lane must contain both):
- **T016:** `status/aggregate.py` — migrate its cluster-A topology predicate (`:278-280`) to WP03's classifier AND its cluster-B site (`:669`) to WP04's grammar.
- **T017 (FR-007):** `coordination/status_transition.py:265` — the fabrication idiom names the ON-DISK transaction dir; route through WP04's authority or fail closed. C-002: touch ONLY this range + its topology predicate (`:114-125`) — upstream coord-merge-stab owns adjacent ranges; also preserve the #1848 deleted-branch carve-out (`:432-437`) exactly.
- **T018 (FR-007):** `cli/commands/implement.py:395` — same eradication.
- **T019:** integration tests: transaction-dir naming for a bare-slug mission (pre-fix would fabricate; post-fix resolves-or-raises); grep-zero fabrication idiom in owned files.

## Context & Constraints (read before coding)
- Design (absolute): `kitty-specs/name-vs-authority-remediation-01KTYGTE/{spec.md, plan.md, data-model.md, contracts/authority-seams.md}` + the mission `research/` — **`research-authority-seams.md` is NORMATIVE** for seam APIs/site lists/decision table; `research-p0-rootcauses.md` for defect mechanics; `research-fold-cluster.md` for ready deltas.
- NFR-003 binding: fail-closed over fallback — never introduce a silent name-derived fallback.
- ATDD: pinning/contract tests FIRST where the WP names them. New code: ruff + mypy zero issues, zero suppressions. No existing passing test modified (NFR-001; pin-of-defective-behavior exceptions justified per case).
- C-002: in `coordination/status_transition.py` and `cli/commands/merge.py`, touch ONLY the ranges this WP names — upstream coord-merge-stabilization owns adjacent ranges.
- move-task/mark-status: run from the PRIMARY checkout with the FULL mission slug (`name-vs-authority-remediation-01KTYGTE`). No kitty-specs commits on the lane.

## Definition of Done
Both fabrication sites dead; aggregate/status_transition/implement consume the seams; #1848 carve-out untouched (test proves); suites + architectural green.

## Review Guidance
reviewer-renata. Verify the C-002 range discipline with the diff; adversarial bare-slug transaction test.

## Activity Log
- 2026-06-12T18:32:00Z – system – Prompt created.
