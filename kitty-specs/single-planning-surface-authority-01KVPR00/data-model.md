# Data Model: MissionTopology SSOT + structural planning-surface coherence

This is a seam + convergence mission. It introduces ONE new persisted field (`topology` in
`meta.json`) and ONE new value type (`MissionTopology`); everything else is the existing
surface-resolution concepts re-expressed against the stored topology.

## MissionTopology (NEW enum — `src/mission_runtime/context.py`)

The mission-level shape: the orthogonal **coordination × lanes** 2×2 grid as one value.

| Member | coordination branch? | `lanes.json`? | Meaning |
|--------|----------------------|---------------|---------|
| `SINGLE_BRANCH` | no | no | one branch, no coord, no lanes (a.k.a. "all-on-feature") |
| `LANES` | no | yes | lane worktrees, no coordination branch |
| `COORD` | yes | no | a coordination branch, no lanes |
| `LANES_WITH_COORD` | yes | yes | lanes + a coordination branch |

- **`FLATTENED` is NOT a member.** A mission that *was* coord and had its `coordination_branch`
  dropped is now `SINGLE_BRANCH`/`LANES` with a `flattened` provenance flag (history, not shape).
- The enum is the single place the lanes-vs-coord cross-product is named; it distinguishes
  `LANES` from `SINGLE_BRANCH` (both resolve a PRIMARY ref today and are indistinguishable to
  the per-ref `CommitTargetKind`).

## `meta.json` — NEW `topology` field (FR-002)

| Field | Type | Role | When assigned |
|-------|------|------|---------------|
| `topology` | `MissionTopology` (str value) | the stored, authoritative mission shape — READ, never re-inferred at resolve time | at `mission create` (`core/mission_creation.py`); legacy missions via `migrate backfill-topology` |
| `flattened` (provenance) | bool/flag | records that a coord mission was flattened — history only, does not change `topology` | at flatten time |

- **Invariant (FR-002/C-004):** resolve-time code reads `topology` from `meta.json`; it does
  NOT recompute the shape from `coordination_branch is None` or a worktree `stat`.
- **Backfill (FR-003):** until a legacy mission is backfilled, the shell computes-and-persists
  `topology` exactly once via the legacy derivation, then reads the stored value. THIS mission's
  own `meta.json` is backfilled before any caller reads the field (dogfooding sequencing).

## `resolve_context_for_mission` (NEW pure resolver — `mission_runtime/resolution.py`)

```
resolve_context_for_mission(mission_id: str, topology: MissionTopology) -> ExecutionContext
```

- A **pure** projection over the single construction door `build_execution_context` (no FS/git
  I/O — NFR-005). The imperative shell parses/persists `meta.json` and passes `id + topology`.
- Optional input-assertion: fail-closed on a supplied-vs-resolved mismatch.
- **Retires BOTH live derivations (FR-004):** `_resolve_coordination_branch`/`resolution.py:705-718`
  AND the independent `runtime_bridge.py:144-211` ladder (`_coord_path.exists() ⇒ COORDINATION`).
- Returns the existing **`ExecutionContext`** (a.k.a. `ActionContext`, `context.py:177`) op-composite:
  `BranchRefFragment` (target/coordination/destination ref), `WorkspaceFragment` (primary/coord/exec),
  `StatusSurfaceFragment` (read/write dir), `ArtifactPlacementFragment`, `IdentityFragment`.

## `routes_through_coordination` (NEW predicate, FR-005)

```
routes_through_coordination(target) -> bool   # MissionTopology-derived per-ref projection
```

- Replaces the **9** `.kind is COORDINATION` decision-site reads (commit_router ×2, implement,
  mission.py ×2, tasks.py, orchestrator_api, _substantive, artifacts).
- The `CommitTargetKind` TYPE survives this mission (vestigial constructor field); its eradication
  (~143 value-literal refs / 41 files) is the behavior-neutral Mission B (C-007).

## Planning surface (where an artifact lives)

- **PRIMARY checkout** — `kitty-specs/<slug>-<mid8>/` — authoritative for planning INPUT
  artifacts (`spec.md`, `plan.md`, `tasks/`, `meta.json`) and for `SINGLE_BRANCH`/`LANES` missions.
- **COORDINATION worktree** — `.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/` — the
  commit surface for `COORD`/`LANES_WITH_COORD` missions (staged at commit-time).
- **Invariant (FR-007/FR-008):** planning writes (`spec-commit`, `map-requirements`,
  `finalize-tasks`, status events) resolve their surface through the seam; `map-requirements`
  writes and `finalize-tasks --validate-only` reads WP `requirement_refs` on the SAME surface.

## Read resolution — driven by STORED topology (FR-006), transient states by the probe (C-006)

| Situation | Stored `topology` | Read resolution | Authority |
|-----------|-------------------|-----------------|-----------|
| coord mission, worktree present | `COORD`/`LANES_WITH_COORD` | COORD | stored topology |
| **flattened, stale `-coord` husk on disk** | `SINGLE_BRANCH`/`LANES` | **PRIMARY** | **stored topology (FR-006)** — the husk is NOT consulted (was the #2062 bug) |
| no coord | `SINGLE_BRANCH`/`LANES` | PRIMARY | stored topology |
| **create-window** (coord declared, worktree not yet materialized) | `COORD`/`LANES_WITH_COORD` | PRIMARY | the **probe** discriminates the transient state (#1718) — NOT the enum (C-006) |
| **coord-deleted** (declared branch gone from git) | `COORD`/`LANES_WITH_COORD` | hard-fail `CoordinationBranchDeleted` | the **probe** (#1848 data-loss carve-out) — NOT the enum (C-006) |

- **Key shift (FR-006/C-004):** the read path resolves from stored topology, so `CoordState.MATERIALIZED`
  (a disk `stat`) is NO LONGER the deciding signal. The on-disk husk cannot out-vote the stored shape.
- **Carve-out (C-006):** create-window (#1718) and coord-deleted (#1848) are transient on-disk×git
  states orthogonal to the 4 cells; they stay discriminated by `probe_coord_state` with the branch
  signal — the stored topology does not subsume them.

## Status-event write surface

- **`emit_status_transition(feature_dir=…)`** (`status/emit.py`) — **Invariant (FR-009):**
  `feature_dir` is resolved by the seam at every call site, not passed ad-hoc, so
  dep-gate/kanban/review-claim reads and `move-task` writes converge.

## `is_committed` collapse (FR-011)

- `missions/_substantive.is_committed` (`:317-412`) — once the surface is structurally single
  (FR-006/FR-007 via stored topology), the 3-surface OR reduces to a single-surface check on the
  resolved placement ref. Gated on the FR-010 live convergence proof (NFR-001/C-002).

## Differential equivalence gate (FR-010)

- `tests/missions/test_surface_resolution_equivalence.py` — extended with (a) a **pure** cell:
  `(mission_id, topology)` for all 4 cells → assert `ExecutionContext` fields, zero FS/git fixtures;
  AND (b) the RETAINED on-disk `flattened-stale-coord` row × every handle form → PRIMARY. The
  `type(a) is type(b)` AND `error_code` assertion stays unweakened.
