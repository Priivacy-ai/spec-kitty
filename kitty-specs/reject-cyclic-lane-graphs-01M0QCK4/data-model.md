# Phase 1 Data Model: Reject Cyclic Lane Graphs

## Existing entities

### ExecutionLane

An accepted execution grouping with `lane_id`, ordered `wp_ids`, ownership/surface metadata, `depends_on_lanes`, and `parallel_group`.

**Invariant added by this mission**: the dependency graph formed by all `ExecutionLane.depends_on_lanes` values in a returned `LanesManifest` is acyclic.

### LanesManifest

The persisted accepted execution plan. Its serialized shape is unchanged.

**State rule**: a manifest is constructed and eligible for persistence only after final post-collapse graph validation succeeds.

## New diagnostic value objects

### CycleLane

| Field | Type | Rules |
|---|---|---|
| `lane_id` | `str` | Existing execution-lane identifier; unique within this diagnostic. |
| `wp_ids` | immutable sequence of `str` | Sorted lexically; contains every WP assigned to the named lane. |

### LaneDependencyCycleError

A typed domain rejection derived from `LaneComputationError`.

| Field | Type | Rules |
|---|---|---|
| `error_code` | constant `str` | Always `LANE_DEPENDENCY_CYCLE`. |
| `cycle_path` | immutable sequence of `str` | At least two entries; closed (`first == last`); every adjacent pair is a directed dependency edge; starts at the smallest lane ID in that cycle. |
| `cycle_lanes` | immutable sequence of `CycleLane` | One entry per unique lane in path order; excludes the repeated closing lane. |
| message | `str` | Human-readable remediation context; never the source of structured facts. |

## Relationships

```text
Work packages + ownership
          │
          ▼
    lane assignment ───────► lane_deps
                                  │
                         deterministic validation
                           ┌──────┴──────┐
                           │             │
                         acyclic       cyclic
                           │             │
                           ▼             ▼
                    LanesManifest   LaneDependencyCycleError
                           │             │
                           ▼             ▼
                      persistence    CLI diagnostic only
```

## Validation rules

1. Validate only after all ownership collapse and `lane-planning` dependency edges are complete.
2. Traverse root lane IDs and dependency IDs lexically.
3. Select the first directed cycle encountered by that traversal.
4. Preserve edge direction when rotating the selected cycle to its smallest ID.
5. Repeat the first lane at the end of `cycle_path`.
6. List each cycle lane once in `cycle_lanes`, in first-path-appearance order.
7. Sort every diagnostic lane's `wp_ids`.
8. Never calculate accepted parallel groups, return a manifest, or invoke persistence after rejection.

## State transitions

```text
dependencies assembled
        │
        ▼
    validating
     ├── no cycle ──► depths assigned ──► manifest accepted ──► optional persistence
     └── cycle ─────► structured rejection ──► nonzero CLI exit
```

There is no stored rejected state and no change to the lifecycle state of an existing valid `lanes.json`.

## Atomicity boundary

The governed atomicity boundary is the lane manifest only. A cyclic result cannot create or replace `lanes.json`; prior non-lane effects from canonical finalization are explicitly outside this mission's rollback contract.
