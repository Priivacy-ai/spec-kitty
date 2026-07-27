# Contract: Placement Bifurcation by Artifact Class

Behavioral contract for `resolve_placement_only` / `commit_for_mission` after this
mission. (Internal API contract — no HTTP surface.)

## Contract

For a mission `M` with topology `T` and target branch `B`:

```
# kind-aware placement (reuses the existing MissionArtifactKind model)
resolve_placement(M, kind: MissionArtifactKind) -> CommitTarget:
    if kind in _PRIMARY_ARTIFACT_KINDS:          # the swappable partition (NFR-004)
        return CommitTarget(ref = M.target_branch)   # primary, ALL topologies
    # else: status/bookkeeping — existing topology routing
    if routes_through_coordination(T):
        return CommitTarget(ref = M.coordination_branch)
    return CommitTarget(ref = M.target_branch)

_PRIMARY_ARTIFACT_KINDS = {SPEC, DATA_MODEL, RESEARCH, CHECKLIST,
                           FINALIZED_EXECUTION_PLAN, TASKS_INDEX,
                           WORK_PACKAGE_TASK, LANE_STATE,
                           PRIMARY_METADATA}   # flip = move a kind
```

## Guarantees

- **G-1**: A PLANNING commit always lands on the primary `target_branch`,
  regardless of topology. (FR-002)
- **G-2**: A STATUS commit on a coord-topology mission always lands on the
  coordination branch. (FR-004, C-001)
- **G-3**: For a flattened/single-branch mission, PLANNING and STATUS both land on
  `target_branch` — identical to pre-mission behavior. (NFR-001)
- **G-4**: A PLANNING commit whose `target_branch` is a protected branch is
  **refused** (`ProtectedBranchRefused`-class), with guidance to start a feature
  branch. (FR-008)
- **G-5**: The PLANNING-vs-coordination partition is decided by the single
  inline `if kind in _PRIMARY_ARTIFACT_KINDS` check (the frozenset IS the
  locus). Flipping a kind's membership changes neither the returned
  `CommitTarget` shape nor the `resolve_placement_only`/`commit_for_mission`
  signatures — callers and the context object are blind to the choice. (NFR-004)

## Negative / anti-mutant assertions (for the IC-06 guard)

- A coord-topology fixture MUST show: planning-commit ref == `target_branch`
  **AND** status-commit ref == `coordination_branch`. (Kills the "always coord" and
  "always primary" mutants — the structural single-count guard cannot.)
- Removing the artifact-class branch (regressing to "always coord for coord
  topology") MUST turn the planning-ref assertion red.

## Caller obligations

Every `commit_for_mission` caller declares its `ArtifactClass`:

| Caller | ArtifactClass |
|--------|---------------|
| `spec-commit`, `setup-plan`, `map-requirements`, finalize-tasks tail, record-analysis, analyze/tasks/accept artifact commits | PLANNING |
| `status_transition` event commits, WP transitions | STATUS |
