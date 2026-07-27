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
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2004354"
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
- **xfail re-attribution (orchestrator finding, WP03 post-impl):** the equivalence test's `coord-fresh/bare` + `coord-behind/bare` cells are tagged `xfail(reason="closed by WP03/FR-009")`, but WP03 (scoped to `primary_feature_dir` disambiguation) does NOT close them — the divergence is `resolve_mission_read_path` mid8-blindness for a bare slug (read_path→primary vs surface/aggregate→coord). These close HERE, at the collapse, when `resolve_mission_read_path` routes through `resolve_status_surface_with_anchor` (which derives mid8). Before draining the xfails in T026: (a) verify the collapse actually makes these cells agree (the bare-slug read_path now resolves to coord like surface/aggregate); (b) update their xfail reasons to cite WP06/FR-001; (c) if the collapse does NOT close them (e.g. bare-slug coord resolution genuinely needs the #1918 mid8-derivation cascade which is OUT OF SCOPE), do NOT force them green — instead mark them as a documented out-of-scope divergence (#1918) and exclude them from the T026 "zero xfail" drain with an explicit allowlist + rationale, rather than a blanket `rg xfail → 0`.
### T022 — Migrate `status_transition.py` predicates (#1900)
- Replace `_is_coordination_feature_dir`/`_is_coord_worktree_feature_dir` with calls to the canonical resolver / `classify_worktree_topology`. No local topology predicate.
### T023 — Drain the C-002 allowlist (#1900, SC-005 proof)
- Remove `status_transition.py` from `tests/architectural/test_topology_resolution_boundary.py`'s allowlist (line ~95); the ratchet now enforces zero parallel selectors there.
### T024 — Coord-empty hard-fail (FR-006)
- Materialized-but-empty coord → raise `STATUS_READ_PATH_NOT_FOUND` whose message names collapse/flatten OR recreate/populate. NO silent primary fallback. Keep no-coord → primary (create→first-write window). Mutation-verified test.
### T025 — ADR (#1716)
- Write `architecture/3.x/adr/2026-06-19-1-coord-empty-surface-fallback.md` recording the hard-fail decision + rationale, bound to the single resolver.
### T026 — Gates (mechanical gate teeth)
- `ruff` + `mypy --strict` clean; the **full WP02 equivalence matrix is GREEN** with mechanical proof: `rg "xfail" tests/missions/test_surface_resolution_equivalence.py` → **0** (every divergence cell closed, none lingering as xfail — this is the CI enforcement of the C-004 gate, not a reviewer eyeball). `tests/status tests/coordination tests/architectural` + a broad run pass (NFR-002 no regression).

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane. **Depends WP02 (equivalence green — hard gate), WP03, WP04, WP05.**

## Definition of Done
- [ ] `resolve_status_surface_with_anchor` is the sole selection authority; status_transition.py predicates migrated; no parallel selector remains.
- [ ] C-002 topology-ratchet allowlist entry for status_transition.py drained (SC-005).
- [ ] Coord-empty hard-fails with the two-path message; no-coord still resolves primary; mutation-verified.
- [ ] ADR committed (#1716 policy).
- [ ] WP02 equivalence matrix fully green, **mechanically proven** (`rg "xfail" tests/missions/test_surface_resolution_equivalence.py` → 0); ruff + mypy --strict clean; no regression.

## Risks / Reviewer guidance
- **Risk**: deleting a duplicate before its equivalence cells are green (C-004 violation). The reviewer MUST confirm the WP02 matrix is fully green (no remaining xfails) before approving.
- **Reviewer**: independently verify the coord-empty message names BOTH recovery paths; confirm the allowlist entry is gone and the ratchet test still passes; confirm no-coord still maps to primary.

## Activity Log

- 2026-06-20T10:03:12Z – claude:opus:python-pedro:implementer – shell_pid=1922249 – Assigned agent via action command
- 2026-06-20T10:52:47Z – claude:opus:python-pedro:implementer – shell_pid=1922249 – Collapse (726d39374): sole-authority documented + #1900 selector migrated + allowlist drained (SC-005); coord-empty hard-fail two-path msg + ADR; equivalence 7pass/6xfail/0XPASS. CRUX for review: 6 xfails = 4 #1918-out-of-scope (authorized) + 2 aggregate-seam (CoordAuthorityUnavailable class vs STATUS_READ_PATH_NOT_FOUND — same error_code, different class). Reviewer must rule the 2-cell allowlist legit vs dodge.
- 2026-06-20T10:52:53Z – claude:opus:reviewer-renata:reviewer – shell_pid=1983507 – Started review via action command
- 2026-06-20T11:07:32Z – user – shell_pid=1983507 – Moved to planned
- 2026-06-20T11:08:20Z – claude:opus:python-pedro:implementer – shell_pid=2000261 – Started implementation via action command
- 2026-06-20T11:11:14Z – claude:opus:python-pedro:implementer – shell_pid=2000261 – Cycle 2: truthful split aggregate-seam xfail reasons (doc-only); gate 0-XPASS, ruff+mypy clean
- 2026-06-20T11:11:23Z – claude:opus:reviewer-renata:reviewer – shell_pid=2004354 – Started review via action command
- 2026-06-20T11:16:54Z – user – shell_pid=2004354 – reviewer-renata APPROVED cycle 2: both new xfail constants verified truthful (live re-observation against lane src — coord-empty subclass-split+no-code-aggregate, coord-deleted multi-way read_path→primary), no stale ref, ADR cross-ref resolves, gate 0-XPASS, ruff+mypy clean, doc-only. Collapse + #1900 drain + FR-006 hard-fail + ADR all approved cycle 1.
