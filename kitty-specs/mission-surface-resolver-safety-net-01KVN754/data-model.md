# Data Model: Resolution Legs & Typed-Error Convergence

This is a refactor/convergence mission — the "model" is the set of resolution legs, topology states, and
the typed-error taxonomy the collapse converges. No persisted schema changes.

## Resolution legs (the three entry points the gate compares)

| Leg | Entry point | Role after collapse |
|-----|-------------|---------------------|
| read-path | `missions/_read_path_resolver.resolve_handle_to_read_path` | handle → mid8 → surface dir (mid8-aware); the privatized `_resolve_mission_read_path` is its internal worker |
| surface | `coordination/surface_resolver.resolve_status_surface_with_anchor` | canonical selection authority |
| aggregate | `status.aggregate.MissionStatus` (`_resolve_read_dir`) | boundary used by `agent status` CLI |

**Convergence invariant:** for every `(slug, mid8, topology)` the three legs return the **identical
directory** or the **identical typed error** (`type(a) is type(b)` AND equal `error_code`).

## Topology states & target behavior

| State | Today (divergent) | After collapse (converged) |
|-------|-------------------|----------------------------|
| no-coord | agree → primary | unchanged → primary |
| create→first-write window | agree → primary | unchanged → primary (**#1718 preserved**) |
| coord-fresh / coord-behind, `<slug>-<mid8>` | agree → coord | unchanged |
| coord-fresh / coord-behind, **bare slug** | read-path mid8-blind → primary; surface/agg → coord | all → coord (IC-01 reroute) |
| **coord-empty** | read-path → primary; surface → `CoordinationWorktreeEmpty`; agg → `CoordAuthorityUnavailable` | **all → primary + loud warning** (Option B, IC-04) |
| **coord-deleted** | read-path → primary dir; surface → `CoordinationBranchDeleted`; agg → `CoordAuthorityUnavailable` | **all → `CoordinationBranchDeleted` hard-fail** (IC-05) |

## Typed errors

| Error | error_code | Disposition |
|-------|-----------|-------------|
| `CoordinationWorktreeEmpty` (subclass of `StatusReadPathNotFound`) | `STATUS_READ_PATH_NOT_FOUND` | **DELETED** (IC-04) — coord-empty no longer raises |
| `CoordinationBranchDeleted` | `COORDINATION_BRANCH_DELETED` | **canonical coord-deleted hard-fail**, propagated verbatim across all legs (IC-05) |
| `CoordAuthorityUnavailable` (no error_code) | — | **kept exported** (C-003); aggregate stops *raising* it for coord-deleted (propagates `CoordinationBranchDeleted` instead); coord-empty no longer reaches it |
| `StatusReadPathNotFound` | `STATUS_READ_PATH_NOT_FOUND` | unchanged (genuine missing surface) |
| `MissionSelectorAmbiguous` / `MISSION_AMBIGUOUS_SELECTOR` | `MISSION_AMBIGUOUS_SELECTOR` | unchanged (already equivalent + preserved through `next`) |

## Invariants (must hold post-collapse)

- **INV-1** create→first-write window resolves primary on every leg (#1718).
- **INV-2** coord-deleted hard-fails (never a stale primary read) — data loss (C-001).
- **INV-3** the loud coord-empty warning fires and is observable (NFR-003).
- **INV-4** `_resolve_mission_read_path` has zero external callers (NFR-005).
- **INV-5** the gate's `type`-AND-`error_code` assertion is intact; only `_XFAIL_*` entries retire (NFR-002).
