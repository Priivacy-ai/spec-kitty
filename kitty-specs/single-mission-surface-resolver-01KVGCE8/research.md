# Phase 0 Research: Single Mission-Surface Resolver

## Decision 1 — Canonical owner = `coordination/surface_resolver.resolve_status_surface_with_anchor`

- **Decision**: Make `resolve_status_surface_with_anchor` the sole surface-selection authority; all others become thin adapters / topology-blind-by-design / retired.
- **Rationale**: It already holds the richest topology logic (coord→primary cascade, materialization handling, `_coord_mid8`, `CoordinationBranchDeleted` #1848, the #1772 nesting guard). The other resolvers re-implement subsets of it. Picking the superset as owner makes the collapse a re-point, not a rewrite.
- **Alternatives**: `_read_path_resolver.resolve_mission_read_path` (also rich, but the surface_resolver already delegates to its `candidate_*`); a brand-new resolver (rejected — C-002 forbids a new shadow path / #1993).

## Decision 2 — T1 canonical `primary_feature_dir_for_mission` = the mid8-composing form

- **Decision**: The unified `primary_feature_dir_for_mission` composes `<slug>[-mid8]` via the single `_compose_mission_dir` grammar (the `feature_dir_resolver.py` form), NOT the raw-slug form.
- **Rationale**: The mid8-composing form correctly locates backfilled / `<slug>-<mid8>` directories; the raw-slug form silently mislocates them when a handle carries a mid8. "Topology-blind primary read" must still resolve the RIGHT primary dir. Pin with a per-caller-class regression test (bare-slug, `<slug>-<mid8>`, backfilled).
- **Alternatives**: raw-slug form (rejected — mislocates mid8 handles, the divergence we're removing); keep both (rejected — it IS the bug).
- **Note**: this is the FR-009 behavior decision; recorded here so the unification is deliberate, not a blind merge.

## Decision 3 — Coord-empty hard-fail (Q1→B), with an actionable two-path message

- **Decision**: A **materialized-but-empty** coordination worktree → hard-fail `STATUS_READ_PATH_NOT_FOUND`; the message instructs the operator to either **collapse/flatten** (drop `coordination_branch`) OR **recreate/populate** the coordination branch. No silent primary fallback on a divergent surface.
- **Rationale**: A silent fallback is exactly the desync (#1716 root cause) — it hides which surface is authoritative. Hard-fail surfaces the divergence and the two legitimate recoveries. Recorded as an ADR (IC-08), bound to the resolver.
- **Boundary**: the *no-coord* create→first-write window (no coordination branch at all) is NOT this case — primary is the sole authoritative surface there. The resolver must distinguish "no coord" (primary authoritative) from "coord exists but empty" (hard-fail).

## Decision 4 — Typed-error pass-through first (FR-005, #2010 bug #15) — cheapest slice

- **Decision**: Preserve `STATUS_READ_PATH_NOT_FOUND` / `MISSION_AMBIGUOUS_SELECTOR` through `next`/`mission_runtime` instead of flattening to `MISSION_NOT_FOUND`. Land independently of the resolver collapse.
- **Rationale**: Highest-blast-radius desync symptom, no resolver change, error types already exist — the cheapest first behavioral win that de-risks the rest.

## Decision 5 — Equivalence test BEFORE deletion (C-004 safety gate)

- **Decision**: The FR-002 differential test (same (slug, mid8, topology) → same dir or same typed error) MUST be green before any duplicate resolver is deleted.
- **Rationale**: #2010's unification closed without proving behavior-equivalence across input classes — that's why it's reopening here. The equivalence test is the gate that makes deletion safe; deleting first repeats #2010's mistake.

## Decision 6 — T6 import migration = scoped bulk-edit, NOT global change_mode

- **Decision**: Only the T6 shim-retirement WP (migrate 30+ `missions.feature_dir_resolver` import sites) is a bulk edit; produce a scoped `occurrence_map.yaml` (import_paths) for THAT WP at its implement time (after IC-02's audit fixes the site set). Do not set `change_mode: bulk_edit` globally.
- **Rationale**: Globally marking the mission bulk-edit would wrongly gate the non-bulk WPs on an occurrence map. The bulk slice is bounded and post-audit.

## Deprecation check (brownfield)

- `missions/feature_dir_resolver.py` — C-004 strangler shim, due for retirement (T6/IC-06). Confirmed still imported by 30+ sites.
- `mission_read_path.py` — compatibility re-export shim, only `runtime_bridge.py:2442` + 1 test import it (T7, opportunistic).
- No other strangler shim in the resolver surface is past a removal milestone that this mission must additionally drain (the legacy-compose C-002 allowlist already drained per #1900's analysis; only the coord-predicate entry remains, handled by IC-06).

## Out-of-scope confirmations (from the boy-scout squad)

- `WorktreeTopology`/`classify_worktree_topology`/`read_worktree_registry` — correct git-registry authority, reused; NOT a selection duplicate.
- `_mid8_from_primary_meta`/`resolve_declared_mid8` mid8 cascade — separate seam (#1918).
