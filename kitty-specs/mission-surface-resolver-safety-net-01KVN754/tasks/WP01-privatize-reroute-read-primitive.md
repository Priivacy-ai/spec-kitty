---
work_package_id: WP01
title: Privatize + reroute the mid8-blind read primitive
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-008
- NFR-001
- NFR-002
- NFR-004
- NFR-005
tracker_refs:
- '2040'
- '1993'
planning_base_branch: feat/mission-surface-resolver-safety-net
merge_target_branch: feat/mission-surface-resolver-safety-net
branch_strategy: Planning artifacts for this mission were generated on feat/mission-surface-resolver-safety-net. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-surface-resolver-safety-net unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Read-path convergence
agent: claude:opus:python-pedro:implementer
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/_read_path_resolver.py
create_intent:
- tests/missions/test_coord_feature_dir_helpers.py
execution_mode: code_change
mission_id: 01KVN754TY9CVJ8G10ERTMPVRH
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/acceptance/__init__.py
- src/mission_runtime/resolution.py
- src/specify_cli/mission_read_path.py
- tests/missions/test_coord_feature_dir_helpers.py
role: implementer
tags: []
wp_code: WP01
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## 🧹 Campsite-Cleaning Directive (#1970) — ACTIVE

While you are inside the surfaces this WP owns, **remediate adjacent issues you find in-slice** (dead code,
stale comments, missed reroutes, lint/type debt, fakeable assertions) — bounded to this mission's goal (the
read-path convergence). Do **not** wave them off as "pre-existing, out of scope". Fix them and note each in
the handoff. (Out-of-mission-scope changes still stay out — campsite is bounded to the touched surface +
the convergence goal.)

## ⚠️ Squad-corrected scope (read first)

The post-tasks adversarial squad re-baselined this WP against live code. **WP01 drains ZERO equivalence
cells** — the read-path `coord-*/bare` divergence was already closed by #2046 (the matrix's
`_XFAIL_READPATH_MID8_OUT_OF_SCOPE` is dead/unused). The gate **stays at 9/4** through this WP. WP01 is a
pure consolidation + the shared-helper foundation. Do NOT touch `test_surface_resolution_equivalence.py`
(WP04/WP05 own its cell edits).

## Objective

Two things: (1) extract the **shared resolution body** the three legs will call (operator chose full
extraction so the legs literally call one body, not just agree); (2) make `resolve_handle_to_read_path` the
single read-path entry and privatize the mid8-blind worker — preserving the back-compat shim.

## Context (verified)

- `resolve_handle_to_read_path` already derives the mid8 (`resolve_declared_mid8`) and is the correct entry.
- The mid8-blind `resolve_mission_read_path` (`_read_path_resolver.py:229`, in `__all__:749`) has **two**
  external callers that pre-compute the mid8 (byte-identical reroute) — `acceptance/__init__.py:614-618`,
  `mission_runtime/resolution.py:166-185` — plus **3 in-module wrappers** (`:509`, `:608`, `:709`) and the
  back-compat shim `mission_read_path.py:14` (re-exports it in `__all__`).
- Coord-candidate compose is hand-built across 6 sites (`_read_path_resolver.py:160-165`, `:356-360`;
  `surface_resolver.py:518-523`, `:545-548`, `:707-708`); the coord-state probe is duplicated 3× (paula C1/C2).
- Research basis: `research/collapse-reduction-map-randy.md` (R1-A..D), `research/collapse-boundary-analysis-alphonso.md`, paula's C1/C2 consolidation call.

## Subtasks

### T001 — Extract `coord_feature_dir()` (shared compose, paula C1)
- Add `coord_feature_dir(repo_root, slug, mid8) -> Path` next to `_compose_mission_dir` in
  `_read_path_resolver.py` (composes `CoordinationWorkspace.worktree_path / KITTY_SPECS_DIR / _compose_mission_dir`).
  Route the **2 in-`_read_path_resolver.py` compose sites** through it (`:160-165`, `:356-360`). Export it so
  WP04 can adopt the `surface_resolver.py` sites. **Pure path; no behavior change; gate unchanged.**

### T002 — Extract `probe_coord_state()` (shared probe, paula C2)
- Add `probe_coord_state(repo_root, slug, mid8) -> CoordState` discriminating
  `MATERIALIZED | EMPTY | UNMATERIALIZED | DELETED`. **Reuse the existing `surface_resolver._coord_branch_exists`
  as the git/DELETED arm — do NOT collapse its `git rev-parse` away** (alphonso §3.3). Route the read-path
  probe sites (`_resolve_existing_for_slug:155-176`, `_resolve_not_found:348-369`) through it. This is the body
  WP04 (coord-empty) and WP05 (coord-deleted) adopt instead of adding a 4th copy.

### T003 — Reroute the two external callers (byte-identical, drop dead derivations)
- `acceptance/__init__.py:614-618` → `resolve_handle_to_read_path(repo_root, feature)`; drop the now-dead
  local `resolve_declared_mid8` import (`:613`); **preserve the lenient `status_dir if status_dir.exists()
  else feature_dir` fallback at `:619` verbatim** (selection-guard-blessed acceptance carve-out — do NOT route
  it through the hard-failing surface).
- `mission_runtime/resolution.py:166-185` → `resolve_handle_to_read_path(repo_root, slug)`; drop the dead
  local `mid8_from_slug` derivation (`:164-166`); keep the `except StatusReadPathNotFound /
  MissionSelectorAmbiguous → ActionContextError` translation (`:186-197`). **Do NOT delete
  `_mid8_from_primary_meta` (`:209`)** — it has dedicated tests (`test_mid8_direct_routing.py`,
  `test_read_path_resolver_validation.py`); leaving it call-dead is fine for this slice (separate tidy).

### T004 — Privatize the worker + preserve the shim
- Rename `resolve_mission_read_path → _resolve_mission_read_path` in `_read_path_resolver.py`; drop from
  `__all__:749`; update the 3 in-module wrappers (`:509`, `:608`, `:709`).
- **Keep the back-compat shim** `mission_read_path.py`: update its `:14` import to the privatized name and
  **re-export it under the OLD public name** (`resolve_mission_read_path = _resolve_mission_read_path`,
  keep `__all__:17`). The shim's importer test (`test_coord_reader_fixes.py`) and the architectural
  allowlists (`test_no_dead_modules.py:282`, `test_no_dead_symbols.py:666`) depend on this public name —
  preserve it. (Deleting the shim is #2048, OUT of scope.)

### T005 — NFR-005 zero-direct-callers
- Assert zero **direct** external callers of `_resolve_mission_read_path` (the only public surface is the
  shim alias). Grep `src/ tests/` for both `resolve_mission_read_path\b` AND `specify_cli.mission_read_path`
  and confirm the only public consumers are the shim + its allowlisted test.
- (The dead `_XFAIL_READPATH_MID8_OUT_OF_SCOPE` constant in the equivalence test is removed by WP04, which
  owns that file — note it for the WP04 handoff if you confirm it is unreferenced by `_MATRIX`.)

### T006 — Zero-mock unit test for the shared helpers
- `tests/missions/test_coord_feature_dir_helpers.py`: `tmp_path` tests for `coord_feature_dir` (path shape)
  and `probe_coord_state` (the 4 states incl. DELETED via a deleted branch) — no mocks.

### T007 — Campsite
- Adjacent debt in the touched files (stale comments about the old public name, dead branches, lint/type).

## Branch Strategy
Planning base / merge target: `feat/mission-surface-resolver-safety-net`. Head of the dependency chain
WP01 → WP04 → WP05 (separate lanes; WP04/WP05 adopt this WP's helpers via cross-lane tip-merge — see those prompts).

## Definition of Done
- `coord_feature_dir` + `probe_coord_state` extracted, exported, unit-tested; read-path sites route through them.
- Two external callers rerouted byte-identically; dead local derivations dropped; `_mid8_from_primary_meta` kept.
- Worker privatized; **shim preserves the old public name**; zero direct external callers of the private worker.
- **Gate UNCHANGED at 9/4** (no cell drained, no XPASS); the only equivalence-test edit is the dead-constant deletion (if unreferenced).
- `ruff` + `mypy` clean. Campsite noted.

## Risks & Reviewer Guidance
- Reviewer: confirm the shim still exports `resolve_mission_read_path` publicly (the allowlists + importer
  test depend on it). Confirm the acceptance lenient fallback is byte-preserved. Confirm `probe_coord_state`
  keeps `_coord_branch_exists`'s `git rev-parse` arm. Confirm the gate is **9/4 unchanged** — WP01 must NOT
  claim a drained cell (the read-path divergence was already closed by #2046).

## Activity Log
- 2026-06-21T14:42:27Z – system – WP01 prompt generated via /spec-kitty.tasks
