# Implementation Plan: Mission-Surface Resolver Strangler-Finish

**Branch**: `feat/mission-surface-resolver-safety-net` | **Date**: 2026-06-21 | **Spec**: [spec.md](./spec.md)
**Input**: [spec.md](./spec.md) · **Research**: [randy reduction map](./research/collapse-reduction-map-randy.md), [alphonso boundary analysis](./research/collapse-boundary-analysis-alphonso.md)

## Summary

Finish the #2040 strangler. The single-resolver safety net (audit/guard/differential-equivalence) and the
typed-error pass-through already exist and are green; this mission **converges the three resolution legs**
(read-path, surface, aggregate) so the six documented strict-xfail equivalence cells drain to **31/0**,
applying the operator's coord-empty **Option B** (loud primary fallback) and converging coord-deleted's
exception *spelling* (hard-fail preserved). Plus two disjoint tidies (#2052, #2061). The differential
equivalence gate is the deletion-safety net and stays green at every WP boundary.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich (CLI surface only — this is a refactor/convergence mission, no new deps)
**Storage**: filesystem (mission surfaces under `kitty-specs/` and `.worktrees/<slug>-<mid8>-coord/`); no DB change
**Testing**: pytest; the load-bearing gate is `tests/missions/test_surface_resolution_equivalence.py` (differential), plus `tests/architectural/test_single_mission_surface_resolver.py` (single-resolver guard) and the surface-resolution audit
**Target Platform**: Linux/macOS dev + CI
**Project Type**: single (CLI library, `src/specify_cli` + `src/runtime` + `src/mission_runtime`)
**Performance Goals**: N/A (pure-path resolution; no perf-sensitive change)
**Constraints**: differential gate green at every step (NFR-001); `type(a) is type(b)` + `error_code` assertion not weakened (NFR-002); #1718 create-window preserved; byte-identical reroutes; loud-warning test-asserted
**Scale/Scope**: ~6 source files + the equivalence test + targeted unit tests

### Brownfield-check outcome (standing rule — recorded here)

A pre-planning brownfield reconciliation (the reason for the re-scope) found:
- **Already built + green:** FR-001 audit/inventory, the single-resolver guard, the differential gate
  (27/6), and FR-004-class typed-error pass-through (`runtime_bridge.py` "disease #15") — all from mission
  `01KVGCE8`. **Not rebuilt** here; used as the gate.
- **Stale brief items:** `feature_dir_resolver.py` (the "C-004 shim") **does not exist** (already retired) —
  removed from scope. #2046 read-CLI unification is **closed/fixed** — regression-guarded only (FR-008).
- **Foldable-issue / split-brain / deprecation scan:** the "4 parallel resolvers" are not a deletable pile
  — the collapse is a 3-leg *convergence* with two byte-identical reroutes and small gated deletions
  (`research/collapse-reduction-map-randy.md`). No new deprecations are due for removal in this surface.
- **LOC:** net change is small (delete `CoordinationWorktreeEmpty` + 2 helpers; privatize 1 primitive;
  2 reroutes; 1 aggregate propagation change; 1 read-path discriminator fold; 2 tidies).

## Charter Check

*GATE: must pass before Phase 0. Re-checked after design.*

- **Canonical sources (DIR):** reuse the existing audit/guard/differential and the `resolve_handle_to_read_path`
  / `resolve_declared_mid8` / `_coord_branch_exists` seams — no parallel mechanism. PASS.
- **No legacy terminology:** "Mission" canonical; no `feature*` reintroduced. PASS (terminology guard pre-push).
- **Tidy-First + disjoint ownership:** ICs are surface-disjoint where possible; the shared equivalence test
  + `surface_resolver.py`/`_read_path_resolver.py` edits are **linearized** (IC-01 → IC-04 → IC-05). PASS.
- **No version prescription:** none assigned (PO at release). PASS.
- **Sonar/complexity:** convergence shrinks branching; new helpers get focused tests in the same WP. PASS.

## Project Structure

```
kitty-specs/mission-surface-resolver-safety-net-01KVN754/
├── plan.md            # this file
├── spec.md
├── research/          # randy + alphonso collapse blueprints (Phase 0 basis)
├── data-model.md      # resolution-leg / typed-error model
└── quickstart.md      # how to verify 31/0 + the invariants
```

Source surfaces touched:
```
src/specify_cli/missions/_read_path_resolver.py        # privatize primitive; coord-deleted discriminator (IC-01, IC-05)
src/specify_cli/coordination/surface_resolver.py       # coord-empty Option B + delete CoordinationWorktreeEmpty (IC-04)
src/specify_cli/status/aggregate.py                    # propagate CoordinationBranchDeleted verbatim (IC-05)
src/specify_cli/cli/commands/agent/status.py           # public-contract migration (IC-05)
src/specify_cli/cli/commands/implement.py              # _resolve_lanes_dir extraction (#2052, IC-03)
src/specify_cli/coordination/commit_router.py          # inverted-layering fix (#2061, IC-02)
src/specify_cli/acceptance/__init__.py + src/mission_runtime/resolution.py  # 2 byte-identical reroutes (IC-01)
tests/missions/test_surface_resolution_equivalence.py  # retire _XFAIL_* as cells drain (IC-01/04/05, linearized)
```

## Implementation Concern Map

> Sequencing law (NFR-001): the differential gate is green at every boundary. A WP that changes a leg's
> behavior MUST retire the matching `_XFAIL_*` cell **in the same WP** (a strict-xfail that unexpectedly
> XPASSes is itself a suite failure). Hence the equivalence-test edits are linearized: IC-01 → IC-04 → IC-05.

| IC | Concern (FRs) | Owned surfaces | Depends on | Drains | Risk |
|----|---------------|----------------|------------|--------|------|
| **IC-01** | Privatize + reroute the mid8-blind read primitive (FR-002, NFR-004/005) | `missions/_read_path_resolver.py` (rename to `_resolve_mission_read_path`), `acceptance/__init__.py:618`, `mission_runtime/resolution.py:185`, the read-path `coord-*/bare` cells in the equivalence test | — | read-path mid8-blindness cells (27/6 → 29/4) | LOW (byte-identical reroutes; 2 known callers) |
| **IC-02** | #2061 inverted-layering fix (FR-007, NFR-004) | `coordination/commit_router.py:303/308` + its focused test | — (independent) | — | LOW (byte-identical) |
| **IC-03** | #2052 `_resolve_lanes_dir` pure extraction (FR-006, NFR-004) | `cli/commands/implement.py` (~1019) + a zero-mock unit test | — (independent) | — | LOW (verify-first; may already be behaviorally satisfied) |
| **IC-04** | Coord-empty **Option B** loud primary fallback (FR-003, NFR-003) | `coordination/surface_resolver.py` (coord-empty path; delete `CoordinationWorktreeEmpty` + `_is_coord_empty_condition` + `_canonicalize_or_enrich_coord_empty`; emit loud warning), the coord-empty cells in the equivalence test + a warning-fires test | IC-01 (shared equivalence test) | coord-empty cells | MEDIUM (net-new warning infra; aggregate inherits for free) |
| **IC-05** | Coord-deleted convergence + public-contract migration (FR-004, FR-005) | `missions/_read_path_resolver.py` (`_coord_branch_exists` fold under `require_exists=True`), `status/aggregate.py` (propagate `CoordinationBranchDeleted` verbatim; keep `CoordAuthorityUnavailable` exported), `cli/commands/agent/status.py` (two `except` tuples), the migrated aggregate tests, the coord-deleted cells in the equivalence test | IC-04 (shared equivalence test + surface/read-path ordering) | coord-deleted cells (to 31/0) | HIGH (edits a WP04-frozen public contract; migrate CLI + 3 tests in-slice) |

**Parallelism:** IC-02 and IC-03 are fully independent (disjoint surfaces) and run alongside the IC-01→IC-04→IC-05 chain.

**C-002 fallback (recorded):** if folding `_coord_branch_exists` into the read-path leg (IC-05) reveals a
create→first-write-window regression risk, leave the read-path coord-deleted cell as a documented xfail
(strictly smaller residue than today) rather than risk the #1718 contract.

## Phase 0 — Research

Consolidated in `research/` (the randy + alphonso blueprints). Key decisions:
- **Coord-empty → Option B (loud primary fallback).** Rationale: silent fallback was the rejected hazard;
  loud/observable fallback is acceptable and matches field evidence (strict hard-fail forced flattening).
  ADR `2026-06-19-1` amended. (alphonso Q1/Q2)
- **Coord-deleted → converge exception spelling to `CoordinationBranchDeleted`, hard-fail preserved.**
  Rationale: it is data loss; only the spelling diverged across legs. Keep `CoordAuthorityUnavailable`
  exported (deleting it is a separate API deprecation). (alphonso Q1)
- **Collapse is convergence, not deletion.** Two byte-identical reroutes + privatize one primitive; no
  resolver pile to delete; `feature_dir_resolver.py` already gone. (randy A/B)

## Phase 1 — Design & Contracts

See `data-model.md` (resolution-leg / typed-error model) and `quickstart.md` (verify 31/0 + invariants).
No new API surface; the only "contract" change is the converged `agent status` error behavior, captured in
`data-model.md` and migrated under FR-005.
