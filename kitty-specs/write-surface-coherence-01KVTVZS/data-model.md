# Data Model: Write-Surface Coherence

Internal refactor. The model already exists on the **read** side
(`src/mission_runtime/artifacts.py`, from merged 01KVRJ6P): `MissionArtifactKind`
+ `artifact_home_for` + `_PLACEMENT_ARTIFACT_KINDS`. This mission makes the
**write** side consult the same model and re-partitions which kinds live on
primary.

## The asymmetry being fixed

| Side | Today | Mechanism |
|------|-------|-----------|
| **Read** | kind-aware | `artifact_home_for(kind)` / `is_coordination_artifact_residue_path` — `PRIMARY_METADATA`→primary; everything in `_PLACEMENT_ARTIFACT_KINDS`→placement (coord under coord topology) |
| **Write** | **kind-BLIND** | `resolve_placement_only` routes purely by topology, ignoring `MissionArtifactKind` → planning artifacts written to coord |

The fix: make the write path kind-aware (consult `artifact_home_for`) AND move the
planning + identity kinds out of `_PLACEMENT_ARTIFACT_KINDS` onto primary, so read
and write agree.

## Entities

### MissionArtifactKind (existing — reused, not re-invented)

`src/mission_runtime/artifacts.py`. The partition this mission establishes:

| Partition | Kinds | Destination (all shapes) |
|-----------|-------|--------------------------|
| **PRIMARY** (planning + identity) | `SPEC`, `DATA_MODEL`, `RESEARCH`, `CHECKLIST`, `FINALIZED_EXECUTION_PLAN`, `TASKS_INDEX`, `WORK_PACKAGE_TASK`, `LANE_STATE`†, `PRIMARY_METADATA` | primary `target_branch` |
| **COORD** (status / bookkeeping / verification) | `STATUS_STATE`, `ISSUE_MATRIX`, `ACCEPTANCE_MATRIX`†, `ANALYSIS_REPORT`† | coordination branch (coord topology); `target_branch` (flat) |

† **Partition membership to confirm in tasks** — `LANE_STATE` (finalize output,
travels with `tasks.md` → defaulted PRIMARY), `ACCEPTANCE_MATRIX` (accept-time
verification → defaulted COORD), `ANALYSIS_REPORT` (record-analysis → defaulted
COORD). The mechanism is unaffected by where these three land; only the frozenset
membership differs.

- **Decision (operator)**: `PRIMARY_METADATA` (meta.json) moves to PRIMARY on
  **both** read and write (full symmetry) — currently the read model already says
  primary while the write side commits it to coord; this closes that split.

### The swappable locus (NFR-004)

The PRIMARY-vs-COORD decision is the **frozenset partition** — one place:

```
_PRIMARY_ARTIFACT_KINDS  = {SPEC, DATA_MODEL, RESEARCH, CHECKLIST,
                            FINALIZED_EXECUTION_PLAN, TASKS_INDEX,
                            WORK_PACKAGE_TASK, LANE_STATE, PRIMARY_METADATA}

artifact_home_for(kind, ...):
    if kind in _PRIMARY_ARTIFACT_KINDS:
        return home(write_surface=primary, commit_target=target_branch)
    # else: existing coord-vs-target topology routing
```

- **Invariant (NFR-004)**: flipping a kind's destination = moving it between the
  two sets (one line). The returned `MissionArtifactHome`/`CommitTarget` shape and
  the `artifact_home_for`/`resolve_*_placement` signatures are unchanged; callers
  are blind to the membership.

### CommitTarget / MissionArtifactHome (existing — unchanged shape)

Only *which* surface/ref the home carries changes, by partition membership.

### MissionTopology (existing — unchanged)

After this mission, topology determines only the COORD-partition destination.
The PRIMARY partition is topology-independent.

## Routing table

| Topology | Partition | Destination | Changed? |
|----------|-----------|-------------|----------|
| coord | PRIMARY (planning + meta) | `target_branch` | **YES** (was coordination_branch) |
| coord | COORD (status/bookkeeping) | `coordination_branch` | no |
| flat / single_branch | either | `target_branch` | no |

## Validation rules / invariants

- **INV-1** (C-001): COORD-partition routing for coord topology is unchanged
  (atomic event log stays on coordination).
- **INV-2** (FR-008): a PRIMARY-partition commit whose `target_branch` is protected
  is refused (require a feature branch); no coord transit.
- **INV-3** (NFR-001): flat/single-branch missions are unchanged → behavior-neutral.
- **INV-4** (FR-006): the PRIMARY-partition **read** path resolves from primary and
  does not consult the coord husk (status transients #1718/#1848 keep theirs).
- **INV-5** (full symmetry): read and write resolve the SAME surface for a given
  kind — no read(primary)/write(coord) split for any kind (incl. meta).

## Key surfaces (all must become kind-aware — FR-003)

- `resolve_placement_only` (`mission_runtime/resolution.py`) — kind-blind today;
  must consult the partition (via `artifact_home_for` / a kind input).
- `commit_for_mission` (`coordination/commit_router.py`) — pass the kind.
- `_planning_commit_worktree` (`agent/mission.py:752/775`) — **second routing
  authority** with its own `routes_through_coordination`; must consult the partition.
- `_resolve_mission_aware_target` (`safe_commit_cmd.py`) and `append-history`
  (`orchestrator_api/commands.py:1343`) — direct-`safe_commit` planning writers
  that bypass `commit_for_mission`; must consult the partition.
- `_PLACEMENT_ARTIFACT_KINDS` / `_PRIMARY_ARTIFACT_KINDS` (`artifacts.py`) — the
  swappable partition (NFR-004).
