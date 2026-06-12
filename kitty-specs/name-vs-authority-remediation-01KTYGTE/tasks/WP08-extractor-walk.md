---
work_package_id: WP08
title: 'DRG extractor walks styleguides/toolguides (FR-012, #1863)'
dependencies: []
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T027
- T028
- T029
phase: Phase 1 - Independent lanes
assignee: ''
agent: ''
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/doctrine/drg/
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/migration/extractor.py
- src/doctrine/schemas/toolguide.schema.yaml
- src/doctrine/graph.yaml
- tests/doctrine/**
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – DRG extractor artifact walk

## ⚡ Do This First: Load Agent Profile
Load the assigned profile via `spec-kitty agent profile show <profile-id> --all` (pick the best implementer match if none assigned) and operate within its boundaries before reading further.

---
## Objectives & Success Criteria
Per `research/research-fold-cluster.md` §3 (sketch ready):
- **T027:** extend the extractor to walk styleguide `references` — they are plain path STRINGS, not structured dicts: implement the `_resolve_path_ref()` helper (6 path-pattern entries per the research) mapping paths→URNs; emit `suggests` edges. Deterministic (sorted, no timestamps).
- **T028:** add a `references` field to the toolguide schema (currently `additionalProperties: false` blocks it — additive, optional) + walk it identically; DIRECTIVE_018 note in the schema change.
- **T029:** regenerate graph.yaml (expect ≈+27 suggests edges, 0 nodes; ONLY the 7 self-healing legacy orphans gain inbound/outbound edges — the ~20 needing curated references are OUT, comment on #1863 stays authoritative); freshness + shipped-graph-valid + idempotency tests green; new unit tests for the path-ref resolver (hit + each miss-pattern).

## Context & Constraints (read before coding)
- Design (absolute): `kitty-specs/name-vs-authority-remediation-01KTYGTE/{spec.md, plan.md, data-model.md, contracts/authority-seams.md}` + the mission `research/` — **`research-authority-seams.md` is NORMATIVE** for seam APIs/site lists/decision table; `research-p0-rootcauses.md` for defect mechanics; `research-fold-cluster.md` for ready deltas.
- NFR-003 binding: fail-closed over fallback — never introduce a silent name-derived fallback.
- ATDD: pinning/contract tests FIRST where the WP names them. New code: ruff + mypy zero issues, zero suppressions. No existing passing test modified (NFR-001; pin-of-defective-behavior exceptions justified per case).
- C-002: in `coordination/status_transition.py` and `cli/commands/merge.py`, touch ONLY the ranges this WP names — upstream coord-merge-stabilization owns adjacent ranges.
- move-task/mark-status: run from the PRIMARY checkout with the FULL mission slug (`name-vs-authority-remediation-01KTYGTE`). No kitty-specs commits on the lane.

## Definition of Done
regenerate-graph --check fresh; +edges as estimated (report the real number); zero orphan regressions; mypy --strict clean on the DRG path; doctrine suite green.

## Review Guidance
reviewer-renata. Verify determinism (regen twice byte-identical) and that the schema change is genuinely additive (existing toolguides parse unchanged).

## Activity Log
- 2026-06-12T18:32:00Z – system – Prompt created.
