# Contract: Placement Seam API

The seam is the **single access point** for "where do I write/read artifact kind K under
my mission's topology?" It is the public face of the existing `resolve_action_context`
root — a thin authority the leaf resolvers delegate to (FR-001, C-001). This is an
internal Python contract, not an HTTP API.

## Authority

One authority object per mission operation, exposing two kind-aware projections plus the
classifier already in `artifacts.py`.

### `write_target(kind: MissionArtifactKind) -> CommitTarget`

- **Given** the mission's stored topology and `kind`.
- **Returns** the `CommitTarget` (branch ref + worktree root) the write must commit to.
- **Rules**:
  - Coordination-partition kind AND `routes_through_coordination(stored_topology)` → coord surface / coordination branch.
  - Otherwise → primary surface / target branch.
  - The result is derived from stored topology + `artifact_home_for`; **never** from the current checkout.
- **Forbidden for callers**: `CommitTarget(ref=<current_checkout>)`, `safe_commit(destination_ref=current_branch)`, or inline `coord_branch if coord_branch else planning_branch`.

### `read_dir(kind: MissionArtifactKind) -> Path | ResolvedSurface`

- **Given** the mission's stored topology and `kind`.
- **Returns** the directory/surface to read this kind from.
- **Rules**: symmetric to `write_target`. Coordination reads on an `UNMATERIALIZED` coord
  branch resolve via the branch ref (not a worktree requirement); a flattened mission
  reads all kinds from primary (T-2).
- **Consolidation**: the four duplicate `_planning_read_dir` wrappers collapse to one
  shared helper that delegates here (FR-001).

### `artifact_home_for(kind, placement_ref) -> MissionArtifactHome` (existing classifier)

- Sole constructor of a `MissionArtifactHome`. `write_target` and `read_dir` are thin
  projections over it. Call sites consume the home; they do not assemble placement (H-1).

## Consumer contract (what strangled sites must do)

| Site | Before (bypass) | After (routed) |
|------|-----------------|----------------|
| `mission_creation.py:176` | `CommitTarget(ref=current_branch)` for SPEC | `seam.write_target(SPEC)` |
| `implement.py:885` | `coord_branch if coord_branch else planning_branch` | `seam.write_target(kind)` |
| `implement.py:1462` | `_get_cur_branch() or planning_branch` | `seam.write_target(kind)` |
| `workflow.py:487/503/549/1694` | `if coord_branch … else target_branch` | `seam.write_target(kind)` |
| `tasks.py` move-task/mark-status | inline lane/coord selection | `seam.write_target(STATUS_STATE)` (reconcile with #2438 gate) |
| kind-blind reads via `resolve_feature_dir_for_mission` | kind-blind dir | `seam.read_dir(kind)` |

## Invariants (contract-level)

- **I-1 (C-001)**: no lifecycle/planning site computes placement outside the seam — including when the seam returns primary.
- **I-2 (T-1)**: coord-routing = `routes_through_coordination(stored_topology)`; no inline `== COORD` / `coordination_branch is not None`.
- **I-3 (M-1)**: composition with empty `mid8` fails loudly (FR-007).
- **I-4**: no behavior change to *which* surface a kind resolves to — this is a routing/consolidation change, not a partition change (C-002).
