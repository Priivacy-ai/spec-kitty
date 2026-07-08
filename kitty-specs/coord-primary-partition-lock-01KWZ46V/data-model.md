# Phase 1 Data Model: Coord/Primary Partition Regression Lock

This mission introduces **no new persisted entities**. It formalizes the value objects
and enums that already encode placement, and locks their invariants. "Data model" here
means the in-memory domain types the seam operates over.

## Enum — `MissionArtifactKind` (existing, `src/mission_runtime/artifacts.py:25-50`)

14 members, partitioned by two frozensets. **This mission locks membership; it does not
add, remove, or re-home a member (C-002).**

| Kind | Partition | Notes |
|------|-----------|-------|
| `SPEC` | primary | strangle target (create-time write) |
| `PLAN` | primary | |
| `TASKS_INDEX` | primary | |
| `WORK_PACKAGE_TASK` | primary | |
| `DATA_MODEL` | primary | |
| `RESEARCH` | primary | |
| `CHECKLIST` | primary | |
| `RETROSPECTIVE` | primary | |
| `PRIMARY_METADATA` | primary | |
| `STATUS_STATE` | coordination | carries status transitions / move-task bookkeeping |
| `LANE_STATE` | coordination | |
| `ACCEPTANCE_MATRIX` | coordination | accept-time write |
| `ANALYSIS_REPORT` | coordination | record-analysis write |
| *(self-bookkeeping)* | coordination | op-records / lifecycle, `_SELF_BOOKKEEPING_*` |

**Invariant P-1**: `_PRIMARY_ARTIFACT_KINDS ∪ _PLACEMENT_ARTIFACT_KINDS` = all members;
the two sets are disjoint. (Ratchet-checkable.)

## Enum — `MissionTopology` (existing, `src/mission_runtime/context.py:64-67`)

2×2 grid. Coord-routing is a **predicate**, not an equality test.

| Value | Coord-routing? (`routes_through_coordination`) | Lanes? |
|-------|-----------------------------------------------|--------|
| `SINGLE_BRANCH` | no → all kinds to primary | no |
| `LANES` | no → all kinds to primary | yes |
| `COORD` | yes | no |
| `LANES_WITH_COORD` | yes | yes |

- `FLATTENED` is a **provenance flag**, not a topology value.
- **Invariant T-1**: coord-routing decisions consult `routes_through_coordination(stored_topology)` only — never `topology == COORD` or `coordination_branch is not None` (C-001).
- **Invariant T-2 (FR-012)**: `stored_topology` is read from `meta.json`; a lingering on-disk `-coord` husk is never authoritative (`_husk_is_authoritative_surface`).

## Value Object — `MissionArtifactHome` (existing, `artifacts.py:175-213`)

The canonical output of a placement decision. Carries all three projections so no call
site re-derives placement:

| Field | Type | Meaning |
|-------|------|---------|
| `read_surface` | Path/surface | where to read this kind |
| `write_surface` | Path/surface | where to write this kind |
| `commit_target` | `CommitTarget` | the branch/ref a write commits to |

- **Invariant H-1**: `artifact_home_for(kind, placement_ref)` is the sole constructor of a
  home; call sites consume `MissionArtifactHome`, they do not assemble it (C-001).

## Value Object — `CommitTarget` (existing)

The commit destination for a write. **Invariant C-1 (FR-011)**: a `CommitTarget` for a
lifecycle/planning artifact is produced by the seam (`write_target(kind)`), never
constructed inline as `CommitTarget(ref=<current_checkout>)`. This is the new ratchet
grammar.

## Domain State — Coordination surface state (read-side, `_read_path_resolver.py:663-706`)

The seam must distinguish four states and behave correctly for each (FR-008, FR-012):

| State | Meaning | Correct behavior |
|-------|---------|------------------|
| `never-created` | mission never declared a `coordination_branch` (non-coord topology) | resolve to primary; **no** `COORDINATION_BRANCH_DELETED` |
| `UNMATERIALIZED` | coord branch exists, worktree not yet created | resolve lifecycle reads via the branch ref |
| `DELETED` | coord worktree removed mid-mission | actionable error / re-materialize, not stale-primary fallback |
| `materialized` | coord worktree present | resolve to coord surface |

## Composition input — `mid8` (write-side, `coordination/workspace.py:161-226`, `branch_naming.py:176-207`)

- **Invariant M-1 (FR-007)**: coord branch/worktree composition requires a non-empty
  `mid8`; an empty `mid8` MUST fail loudly at the composition seam, never compose
  `kitty/mission-<slug>-` → `git worktree add` exit-128.

## Relationships

```
MissionTopology --routes_through_coordination()--> {coord | primary} placement
MissionArtifactKind --frozenset membership--> {coordination | primary} partition
(kind, placement_ref) --artifact_home_for()--> MissionArtifactHome{read_surface, write_surface, commit_target}
seam.write_target(kind) --> CommitTarget   (never inline from checkout)
seam.read_dir(kind)     --> read_surface
```
