---
work_package_id: WP06
title: 'Doctrine refinements #1865/#1866/#1867 (FR-010)'
dependencies: []
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: feat/name-vs-authority-remediation-01KTYGTE
merge_target_branch: feat/name-vs-authority-remediation-01KTYGTE
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC (mission retargeted to feat/name-vs-authority-remediation-01KTYGTE on 2026-06-12 — PR #1895 branch frozen for review). During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/name-vs-authority-remediation-01KTYGTE unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T020
- T021
- T022
phase: Phase 1 - Independent lanes
assignee: ''
agent: ''
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/doctrine/styleguides/built-in/
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/styleguides/built-in/planning-and-tracking.styleguide.yaml
- src/doctrine/procedures/built-in/tracker-organisation-workflow.procedure.yaml
- src/doctrine/toolguides/built-in/github-tracker.toolguide.yaml
- src/doctrine/toolguides/built-in/GITHUB_TRACKER.md
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Doctrine refinement deltas

## ⚡ Do This First: Load Agent Profile
Load the assigned profile via `spec-kitty agent profile show <profile-id> --all` (pick the best implementer match if none assigned) and operate within its boundaries before reading further.

---
## Objectives & Success Criteria
Apply the READY deltas from `research/research-fold-cluster.md` §1 (drafted + schema-checked there — use them as the base, refine wording only):
- **T020 (#1865 + both addenda):** styleguide — triage-snapshot label reconciliation pattern; secondary-label coexistence clarification; principle-9 names `priority:P2` + `triage:needs-revision` as the canonical provisional defaults.
- **T021 (#1866):** procedure Step-8 canonical-tree carve-out — label-only mutations permitted on protected nodes; type/parent changes recorded as proposals for the tree owner (covers the question priti's triage raised).
- **T022 (#1867 + addendum):** toolguide — pagination rule generalized to ALL gh list surfaces (issue list, label list, search, api list endpoints); bump last_updated. Then: `spec-kitty doctrine validate` on all three; doctrine suite green; if references blocks changed, regenerate graph.yaml deterministically — NOTE graph.yaml is WP08-owned: coordinate via out-of-map rationale OR leave regen to WP08 if your refs are unchanged.

## Context & Constraints (read before coding)
- Design (absolute): `kitty-specs/name-vs-authority-remediation-01KTYGTE/{spec.md, plan.md, data-model.md, contracts/authority-seams.md}` + the mission `research/` — **`research-authority-seams.md` is NORMATIVE** for seam APIs/site lists/decision table; `research-p0-rootcauses.md` for defect mechanics; `research-fold-cluster.md` for ready deltas.
- NFR-003 binding: fail-closed over fallback — never introduce a silent name-derived fallback.
- ATDD: pinning/contract tests FIRST where the WP names them. New code: ruff + mypy zero issues, zero suppressions. No existing passing test modified (NFR-001; pin-of-defective-behavior exceptions justified per case).
- C-002: in `coordination/status_transition.py` and `cli/commands/merge.py`, touch ONLY the ranges this WP names — upstream coord-merge-stabilization owns adjacent ranges.
- move-task/mark-status: run from the PRIMARY checkout with the FULL mission slug (`name-vs-authority-remediation-01KTYGTE`). No kitty-specs commits on the lane.

## Definition of Done
3 artifacts schema-valid; DIRECTIVE_018 additive (no version bump); doctrine tests + terminology guard green; deltas faithful to the dogfood findings they encode.

## Review Guidance
reviewer-renata; content fidelity vs `docs/development/391-doctrine-usage-test.md` + the triage-pass findings on #1865.

## Activity Log
- 2026-06-12T18:32:00Z – system – Prompt created.
