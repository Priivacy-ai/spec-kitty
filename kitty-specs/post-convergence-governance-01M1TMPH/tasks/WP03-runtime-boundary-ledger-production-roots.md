---
work_package_id: WP03
title: runtime->specify_cli boundary ledger + _PRODUCTION_ROOTS refresh
dependencies: []
requirement_refs:
- FR-008
- FR-009
tracker_refs:
- '3522'
planning_base_branch: tier3/governance-enforcement
merge_target_branch: tier3/governance-enforcement
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Boundary enforcement
agent_profile: architect-alphonso
authoritative_surface: tests/architectural/
role: implementer
task_type: implement
owned_files:
- tests/architectural/test_layer_rules.py
- tests/architectural/test_shared_package_boundary.py
---

# WP03 — runtime->specify_cli boundary ledger + _PRODUCTION_ROOTS refresh

Close the highest-value enforcement hole (#3522): the ~93 `runtime→specify_cli` upward edges are
ungated. Bind them with a shrink-only allowed-exception ledger that mirrors the existing
`_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI` / `TestMissionRuntimeBoundary` pattern verbatim, reusing the
existing helper functions. Refresh `_PRODUCTION_ROOTS` (drop the retired `doctrine` shim; add
`mission_runtime` + `glossary`) so the retired-import scan covers the real roots (D6).

## Requirements
- **FR-008** a new `runtime→specify_cli` edge reds CI (shrink-only ledger; C-003).
- **FR-009** `_PRODUCTION_ROOTS` refreshed (D6).

## Ledger ground-truth (live AST scan of src/runtime/, 2026-09-06)
93 edges / 23 first-level subpackages: `bulk_edit, coordination, core, events, invocation, lanes,
migration, mission, mission_loader, mission_metadata, mission_step_contracts, mission_v1, missions,
requirement_mapping, retrospective, review, runtime, shims, status, status_lanes, task_utils, workspace`
plus a bare-`import specify_cli` sentinel (`""`, 2 edges in `runtime/next/runtime_bridge_io.py`).
`cli`/`next` are absent (they stay hard-forbidden by `TestRuntimeBoundary`).

## Acceptance
- `TestRuntimeSpecifyCliLedger`: within-ledger passes on the live tree; the matcher rejects a synthetic
  `specify_cli.cli` edge (non-vacuity); no stale ledger entries (shrink-only).
- `_PRODUCTION_ROOTS` contains `mission_runtime` + `glossary`, not `doctrine`;
  `test_shared_package_boundary.py` passes.
- Both gates run in ≤5 s.

## Amendment — #3522 scan-root widening + census spelling fix (2026-09-06, second-opinion fold)

The second-opinion architecture check (work/post-convergence/19, PR comment thread) found the ledger
above closes only the ADJACENT half of #3522. The LITERAL ask — the doctrine-facade boundary never
scans `src/runtime/` — required two further test-only changes, folded into this WP:

- `test_runtime_charter_doctrine_boundary.py`: `_RUNTIME_ROOT` → explicit `_SCAN_ROOTS` list
  (`src/specify_cli`, `src/runtime`); `src/runtime`'s two live lazy doctrine reaches
  (`runtime_bridge_composition.py` → `charter.offering.missions.step_contracts`,
  `runtime_bridge_io.py` → `….step_projection`, both census-classified FACADE-ONLY) pinned in the
  shrink-only lazy baseline; failure-message prose updated.
- `test_doctrine_census.py`: same explicit `_SCAN_ROOTS`; the two runtime files recorded as
  documented `ORPHAN_REACHED_EXCEPTIONS` (#2173 owns the future door-routing). **Found and fixed in
  passing: the census matcher recognized only the legacy `doctrine.*` spelling — since the
  `charter.offering` relocation, `reached_doctrine_paths()` returned EMPTY and every census gate
  passed vacuously.** Dual-spelling matcher restored (mirrors the boundary file's
  `_is_doctrine_module`); bare `charter.offering` added to DISPOSITION as INTERNAL-METADATA
  (sibling of the legacy `doctrine` entry); docstring census numbers re-measured
  (6 files / 11 reaches / 10 distinct paths).

Acceptance re-run: `test_doctrine_census.py` + `test_runtime_charter_doctrine_boundary.py` +
`test_layer_rules.py` → 35 passed; `ruff check` clean on both files. With this amendment the WP
delivers BOTH halves of #3522 (layer-rule ledger + doctrine scan-root coverage), and the census gate
is non-vacuous again.
