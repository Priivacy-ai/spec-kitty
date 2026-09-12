# Phase 1 Data Model — Coord Write-Placement Closure & Birth-Cutover

No new persisted schemas; the mission tightens routing + invariants over existing entities.

## Entities & invariants

### MissionArtifactKind → MissionArtifactHome (the placement port)
- **Fields**: `kind` (enum), `read_surface` (PRIMARY|COORD), `write_surface` (PRIMARY|COORD), `commit_target` (ref | None).
- **Change (FR-002, D-05)**: `PRIMARY_METADATA.commit_target` moves from `None` (port-blind) to a partition-aware write target so meta writes route through the port.
- **Change (FR-003/FR-006, D-01)**: `decisions.events.jsonl` and `traces/` gain explicit classification in `_MISSION_FILE_KIND_BY_BASENAME` / `_COORD_RESIDUE_DIRS` (both currently classify to `None`).
- **Invariant**: `assert_partition_invariant()` stays exhaustive + disjoint after the additions.

### CommitTarget / PlacementSeam
- **Invariant (FR-001, NFR-001)**: every `safe_commit(target=…)` / `CommitTarget(ref=…)` / `write_meta(...)` for a mission-artifact path is **seam-derived** — asserted whole-tree, not per-module.
- **Read authority (FR-004)**: `placement_seam(...).read_dir(kind)` resolves the read surface; a read of a coord-homed kind against a primary substitute **raises a typed partition-mismatch error** (no silent fallback).

### Runtime cutover state (unchanged shape, new producer)
- **`meta.json.status_phase`**: `"1"` after a fail-closed `verify_backfill().ok`. Sole writer `_flip_phase` (C-004). New producer: the birth seam (D-02).
- **Deterministic seed events** in `status.events.jsonl`: `InnerStateChanged` quartet + a seed `planned→claimed`, ids namespaced on immutable `mission_id` (idempotent, NFR-003).
- **Eligibility (FR-010)**: re-keyed to "event log carries runtime", excluding the self-referential cutover mission.

### Repair operation (FR-005) — state machine
- **States**: `clean` (no divergence) → no-op; `ff-candidate` (strict-ancestor + clean worktree) → forward; `divergent` (non-ancestor) → **refuse + emit unified diff**, zero mutation.
- **Invariant (NFR-005)**: never force-overwrites; forward-only.

## State transitions (birth cutover, FR-009)
```
mission merged → target commit durable → bake mission_number (meta→PRIMARY)
                                       → cutover_mission (reconcile + status_phase→PRIMARY, seed events→COORD)
                                       → [re-run] idempotent no-op (seeds 0, phase stable)
```

## Externally visible events / surfaces
- New CLI surface: `spec-kitty agent mission repair` (FR-005).
- No new network/webhook surface; all local git + JSONL.
