# Data Model — Read-Side Surface-Resolver Adoption (#2046)

No new persisted entities. The mission introduces one resolution seam and reasons over
existing topology/handle classes.

## The seam (the central value object)
`resolve_handle_to_read_path(repo_root: Path, handle: str) -> Path`
- **Input**: `handle` — an operator-supplied mission handle (bare slug, `<slug>-<mid8>`, or full `mission_id`).
- **Invariant (FR-004)**: `handle` is `assert_safe_path_segment`-validated BEFORE any `KITTY_SPECS_DIR` join.
- **Derivation**: primary `meta.json` → `resolve_declared_mid8(meta, handle)` (mid8 or `""`).
- **Topology gate (fail-closed)**: `not mid8 and declares_coordination` → raise (declared coord but no derivable mid8).
- **Routing invariant (FR-005)**: returns `resolve_mission_read_path(repo_root, handle, mid8)` — worktree-existence-gated; NEVER routes through `resolve_status_surface_with_anchor`.
- **Output**: the authoritative read-side mission directory (coord worktree when materialized; primary in the create window or no-coord).
- **Errors**: `MissionSelectorAmbiguous` (ambiguous handle, propagated); the fail-closed gate's typed refusal (declared-coord-empty-mid8).

## Topology × handle classes (the equivalence-matrix axes 01KVGCE8 owns)
| Topology | bare-slug (this mission) | `<slug>-<mid8>` / full id (unaffected) |
|----------|--------------------------|----------------------------------------|
| no-coord | primary (unchanged) | primary |
| coord-fresh | **→ coord (FLIP green)** | coord (already green) |
| coord-behind | **→ coord (FLIP green)** | coord |
| coord-empty | hard-fail read leg; aggregate cell stays out-of-scope (FR-008) | — |
| coord-deleted | read leg fixed; aggregate cell stays out-of-scope (FR-008) | — |
| create→first-write (declared, unmaterialized) | **PRIMARY (must NOT regress — #1718/FR-005)** | primary |

## Sites (state of adoption — 8 direct `resolve_mission_read_path` callers, code-verified)
`routed-through-seam` (target) ← `raw-join-bootstrap` {context:72, mission:1327/1378 (#2046), decision:464 (D-6 consolidation)} ∪ `bespoke-cascade` {workflow:302-324, resolution._mid8_from_primary_meta, runtime_bridge:2431-2450, tasks:4047, acceptance._status_read_feature_dir}.
`seam-source` {orchestrator_api:346} — re-pointed by WP01. No "already-routed, leave-alone" set remains.
