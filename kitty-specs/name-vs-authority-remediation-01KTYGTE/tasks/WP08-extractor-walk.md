---
work_package_id: WP08
title: 'DRG extractor walks styleguides/toolguides (FR-012, #1863)'
dependencies: []
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/name-vs-authority-remediation-01KTYGTE
merge_target_branch: feat/name-vs-authority-remediation-01KTYGTE
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC (mission retargeted to feat/name-vs-authority-remediation-01KTYGTE on 2026-06-12 — PR #1895 branch frozen for review). During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/name-vs-authority-remediation-01KTYGTE unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T027
- T028
- T029
phase: Phase 1 - Independent lanes
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1591242"
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
- 2026-06-12T19:23:21Z – claude:sonnet:python-pedro:implementer – shell_pid=1470114 – Assigned agent via action command
- 2026-06-12T19:39:10Z – claude:sonnet:python-pedro:implementer – shell_pid=1470114 – T027/T028/T029 complete. _resolve_path_ref() 7-pattern helper + styleguide walk + toolguide schema. Graph delta: +24 suggests edges, +2 nodes (agent_profile:java-implementer stub from stale java-conventions ref + toolguide:rtk-search-tooling from rglob fix in _discover_built_in_artifact_nodes). Idempotency verified (SHA-256). 33 new unit tests. 2195 doctrine tests green. ruff+mypy zero issues.
- 2026-06-12T19:39:52Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1591242 – Started review via action command
- 2026-06-12T19:46:56Z – user – shell_pid=1591242 – Review passed: FR-012 DRG extractor walk implemented correctly. _resolve_path_ref 7-pattern helper (6 doc kinds + agent_profile): clean fail-closed design, returns None for URLs/glossary/_proposed/ADRs. Styleguide and toolguide rglob walks emit suggests edges. Schema change to toolguide.schema.yaml is additive (DIRECTIVE_018 compliant; 219 artifacts pass validation). Graph delta: +24 suggests edges / +2 nodes (234 nodes / 585 edges). Deviation adjudications: (a) agent_profile:java-implementer stub — ACCEPTED: file-existence is not checked by _ensure_node for ANY artifact kind; stub-creation for referenced but missing targets is established extractor behavior (pre-existing in _add_ref_edge for directives/tactics/etc.); the phantom node faithfully surfaces the stale reference in java-conventions.styleguide.yaml rather than hiding it — curation fix (remove/add the profile file) is a separate task, not a WP08 defect; consistent with NFR-003 which governs pattern resolution not file-existence checking. (b) toolguide:rtk-search-tooling — ACCEPTED: file exists at src/doctrine/toolguides/built-in/system_tools/rtk-search-tooling.toolguide.yaml; discovered by rglob fix; genuine pre-existing discovery gap fixed. (c) +24 vs ~27 edges — ACCEPTED: shortfall explained by unresolvable refs correctly dropped (URLs, non-built-in paths, stale refs with no matching node after _resolve_path_ref); no silent loss. Determinism: double-regen byte-identical (SHA 5d1bf42b confirmed). Freshness test passes. 33 new tests all pass. Full doctrine suite 2195/2195 pass. ruff clean. mypy --strict clean on extractor.py. C-002 fence respected (no status_transition.py/merge.py touches). Orphan scope respected (only styleguide reference-walks, no curation orphan edits).
