---
work_package_id: WP02
title: Differential equivalence test (the deletion safety gate)
dependencies: []
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: feat/single-mission-surface-resolver
merge_target_branch: feat/single-mission-surface-resolver
branch_strategy: Planning artifacts for this mission were generated on feat/single-mission-surface-resolver. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-mission-surface-resolver unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
agent: claude
history:
- at: '2026-06-19T17:06:54Z'
  actor: claude
  note: WP authored from plan IC-05 (FR-002, the C-004 deletion gate).
agent_profile: python-pedro
authoritative_surface: tests/missions/
create_intent:
- tests/missions/test_surface_resolution_equivalence.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- tests/missions/test_surface_resolution_equivalence.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` (`src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`); acknowledge its initialization declaration.

## Objective

Build the **differential equivalence test** that feeds the same `(slug, mid8, topology)` matrix to every mission-surface resolution entry point and asserts each returns an **identical directory OR identical typed error**. This is the C-004 **deletion safety gate**: no duplicate resolver may be deleted (WP06/WP07) until the relevant cells are green. (IC-05; FR-002, NFR-003)

## Context

- Entry points to compare: `_read_path_resolver.resolve_mission_read_path` + `primary_feature_dir_for_mission`, `coordination/surface_resolver.resolve_status_surface_with_anchor`, `status/aggregate.MissionStatus.load`/`_resolve_read_dir`, `mission_runtime/resolution` boundary.
- The test goes **RED initially** on the known divergences (that's the point — it documents them); WP03/WP04/WP05/WP06 fixes flip cells green. Mark the known-RED cells with the FR/WP that closes each (xfail-with-reason or a documented expected-divergence list — NOT a silent skip).

## Subtasks

### T005 — Matrix fixtures
- Build fixtures for the topology states (per data-model.md): `no-coord`, `coord-fresh`, `coord-behind`, `coord-empty` (materialized-but-empty), `coord-deleted`; × handle classes `bare-slug`, `<slug>-<mid8>`, `ambiguous-mid8`. Use realistic on-disk shapes (real worktree/registry layout — no toy slugs).

### T006 — Differential assertion
- For each (topology, handle) cell, call every entry point; assert all return the SAME resolved dir OR all raise the SAME typed error class. A disagreement is a recorded divergence (the gate).

### T007 — Cover all input classes
- MUST include `coord-empty` (→ expected `STATUS_READ_PATH_NOT_FOUND` post-FR-006), `ambiguous-mid8` (→ `MISSION_AMBIGUOUS_SELECTOR` post-FR-008), and the `<slug>-<mid8>` handle class (the FR-009/T1 divergence class — a missing column here would hide T1's false-green).

### T008 — Mark initially-RED cells
- The cells that diverge today (e.g. ambiguous-mid8: aggregate silent-picks vs resolver raises; mid8-handle: the two `primary_feature_dir` differ) → mark with the closing FR/WP (e.g. `xfail(reason="closed by WP04/FR-008")`). As each fix lands, the corresponding WP removes the xfail. Document the expected-green-by-WP map in the test module docstring.

## Branch Strategy
Planning/base + merge target: `feat/single-mission-surface-resolver`. Worktree per lane.

## Definition of Done
- [ ] Differential test covers the full (topology × handle) matrix incl. coord-empty, ambiguous-mid8, `<slug>-<mid8>`.
- [ ] Assertions are dir-equality OR same-typed-error (not truthiness).
- [ ] Initially-RED cells are xfail-with-WP-reason (no silent skips); the docstring maps cell→closing WP.
- [ ] ruff + mypy clean; the test runs (green on the cells already equivalent, xfail on the rest).

## Risks / Reviewer guidance
- **Risk**: a too-lenient assertion (truthiness / "both non-None") that passes under divergence. The reviewer must confirm dir-equality / same-error-class.
- **Reviewer**: confirm the matrix has the `<slug>-<mid8>` column (else FR-009 can false-green later); confirm coord-empty expects the hard-fail, not a fallback.
