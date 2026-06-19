---
work_package_id: WP06
title: Collapse to one resolver + coord-empty hard-fail (GATED on WP02 green)
dependencies:
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-001
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: feat/single-mission-surface-resolver
merge_target_branch: feat/single-mission-surface-resolver
branch_strategy: Planning artifacts for this mission were generated on feat/single-mission-surface-resolver. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-mission-surface-resolver unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
agent: claude
history:
- at: '2026-06-19T17:06:54Z'
  actor: claude
  note: WP authored from plan IC-06 + IC-08 (FR-001/FR-007/FR-006/#1900). GATED on WP02 equivalence-green.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- tests/coordination/test_surface_resolver_collapse.py
- architecture/3.x/adr/2026-06-19-1-coord-empty-surface-fallback.md
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/coordination/surface_resolver.py
- src/specify_cli/coordination/status_transition.py
- tests/architectural/test_topology_resolution_boundary.py
- tests/coordination/test_surface_resolver_collapse.py
- architecture/3.x/adr/2026-06-19-1-coord-empty-surface-fallback.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
The core collapse: make `coordination/surface_resolver.resolve_status_surface_with_anchor` the **sole** surface-selection authority (FR-001/FR-007), migrate the `status_transition.py` coord predicates to it + drain the C-002 allowlist (#1900), and implement the **coord-empty hard-fail** with an actionable two-path message (FR-006) + an ADR (#1716). (IC-06 + IC-08)

**HARD GATE (C-004): do NOT delete/repoint any resolver until the WP02 equivalence matrix is GREEN for the affected input classes.**

## Context
- `coordination/surface_resolver.py` is the chosen canonical owner (research D1, richest topology logic).
- `coordination/status_transition.py` `_is_coordination_feature_dir`/`_is_coord_worktree_feature_dir` are a 5th parallel selection site (#1900); `tests/architectural/test_topology_resolution_boundary.py:95` allowlists it.
- FR-006 (research D3): a **materialized-but-empty** coord worktree → hard-fail `STATUS_READ_PATH_NOT_FOUND`; message names BOTH recovery paths (collapse/flatten OR recreate/populate). Distinct from no-coord (primary authoritative).

## Subtasks
### T021 — Sole authority (FR-001/FR-007)
- Confirm/route every selection through `resolve_status_surface_with_anchor`; it consumes the WP03 delegator/primitives. No parallel selection logic remains in this surface.
### T022 — Migrate `status_transition.py` predicates (#1900)
- Replace `_is_coordination_feature_dir`/`_is_coord_worktree_feature_dir` with calls to the canonical resolver / `classify_worktree_topology`. No local topology predicate.
### T023 — Drain the C-002 allowlist (#1900, SC-005 proof)
- Remove `status_transition.py` from `tests/architectural/test_topology_resolution_boundary.py`'s allowlist (line ~95); the ratchet now enforces zero parallel selectors there.
### T024 — Coord-empty hard-fail (FR-006)
- Materialized-but-empty coord → raise `STATUS_READ_PATH_NOT_FOUND` whose message names collapse/flatten OR recreate/populate. NO silent primary fallback. Keep no-coord → primary (create→first-write window). Mutation-verified test.
### T025 — ADR (#1716)
- Write `architecture/3.x/adr/2026-06-19-1-coord-empty-surface-fallback.md` recording the hard-fail decision + rationale, bound to the single resolver.
### T026 — Gates
- `ruff` + `mypy --strict` clean; the **full WP02 equivalence matrix is GREEN** (all cells, xfails removed); `tests/status tests/coordination tests/architectural` + a broad run pass (NFR-002 no regression).

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. **Depends WP02 (equivalence green — hard gate), WP03, WP04, WP05.**

## Definition of Done
- [ ] `resolve_status_surface_with_anchor` is the sole selection authority; status_transition.py predicates migrated; no parallel selector remains.
- [ ] C-002 topology-ratchet allowlist entry for status_transition.py drained (SC-005).
- [ ] Coord-empty hard-fails with the two-path message; no-coord still resolves primary; mutation-verified.
- [ ] ADR committed (#1716 policy).
- [ ] WP02 equivalence matrix fully green; ruff + mypy --strict clean; no regression.

## Risks / Reviewer guidance
- **Risk**: deleting a duplicate before its equivalence cells are green (C-004 violation). The reviewer MUST confirm the WP02 matrix is fully green (no remaining xfails) before approving.
- **Reviewer**: independently verify the coord-empty message names BOTH recovery paths; confirm the allowlist entry is gone and the ratchet test still passes; confirm no-coord still maps to primary.
