# Phase 1 Data Model: Single Mission-Surface Resolver

This mission is a behavioral consolidation; the "model" is the resolution contract,
the topology states, and the typed-error vocabulary — single-sourced on the canonical
resolver.

## Topology states (the selection input)

| State | Condition | Canonical resolution |
|-------|-----------|----------------------|
| `no-coord` | mission has no `coordination_branch` | primary checkout is authoritative (create→first-write window included) |
| `coord-fresh` | coord branch declared, worktree materialized + populated | coord surface authoritative |
| `coord-behind` | coord exists but primary is ahead/diverged | per the canonical cascade (coord preferred unless empty) |
| `coord-empty` | coord worktree materialized but **no status surface yet** | **HARD-FAIL** `STATUS_READ_PATH_NOT_FOUND` (FR-006) — message: collapse OR recreate/populate |
| `coord-deleted` | coordination_branch set but branch gone | `CoordinationBranchDeleted` (#1848) |

## Value concepts

- **Mission handle** — `mission_id` (ULID) / `mid8` (8-char) / `mission_slug`; resolved by the single canonical handle resolver (no silent first-match — FR-008).
- **Mission-surface directory** — the resolved `kitty-specs/<slug>[-mid8]/` (primary) or `.worktrees/<slug>-coord/kitty-specs/<slug>/` (coord).
- **Composition grammar** — `_compose_mission_dir` (the single `<slug>[-mid8]` composer, T5); `compose_meta_json_path` and the unified `primary_feature_dir_for_mission` (FR-009) route through it.

## The canonical resolver contract (single source)

| Function | Module | Role |
|----------|--------|------|
| `resolve_status_surface_with_anchor` | `coordination/surface_resolver.py` | **the** selection authority (topology → dir or typed error) |
| `primary_feature_dir_for_mission` | `missions/_read_path_resolver.py` (unified) | topology-blind-by-design primary read (mid8-composing) |
| shared `resolve-dir-or-typed-error` delegator (T4) | (extracted) | the one wrapper both `aggregate` and `mission_runtime/resolution` re-point to |

## Typed errors (must survive caller flattening — FR-005)

| Error | Raised when | Must NOT flatten to |
|-------|-------------|---------------------|
| `STATUS_READ_PATH_NOT_FOUND` | coord-empty / surface missing | `MISSION_NOT_FOUND` |
| `MISSION_AMBIGUOUS_SELECTOR` | ambiguous `mid8` handle | `MISSION_NOT_FOUND` |
| `CoordinationBranchDeleted` | coord branch gone | (subclass of the above; preserved) |

## Validation rules

- VR-1 (FR-001): no mission-surface read composes `repo_root/KITTY_SPECS_DIR/<slug>` itself; all route the canonical resolver or a blessed delegator.
- VR-2 (FR-002): for the same (slug, mid8, topology), all entry points return identical dir OR identical typed error.
- VR-3 (FR-006): coord-empty → hard-fail with the two-path message; no silent primary fallback.
- VR-4 (FR-008): ambiguous mid8 → `MISSION_AMBIGUOUS_SELECTOR`, never silent first-match.
- VR-5 (FR-009): exactly one `primary_feature_dir_for_mission` definition, mid8-composing.
- VR-6 (FR-005): typed errors preserved through `next`/`mission_runtime`.

## Equivalence matrix (FR-002 / NFR-003 — the deletion gate)

Rows = topology states above × handle classes {bare-slug, `<slug>-<mid8>`, ambiguous-mid8}.
Each cell: every resolution entry point MUST agree on the dir or the typed error.
A disagreement in any cell blocks deletion of the corresponding duplicate (C-004).
