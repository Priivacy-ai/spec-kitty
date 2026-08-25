# Phase 1 Data Model: Finalization Eligibility

This Mission adds an in-memory projection only. It does not change append-only event schemas, work-package prompt schemas, or the persisted `LanesManifest` schema.

## Entity: `FinalizationEligibility`

Immutable value returned by the pure projector.

| Field | Type | Meaning |
|---|---|---|
| `known_wp_ids` | ordered tuple of `WP##` strings | All structurally validated work packages in the current Mission definition. |
| `eligible_wp_ids` | ordered tuple of `WP##` strings | Known work packages whose current canonical lifecycle lane is not `canceled`. |
| `canceled_wp_ids` | ordered tuple of `WP##` strings | Known work packages whose current canonical lifecycle lane is exactly `canceled`. |
| `eligible_dependencies` | immutable/read-only mapping of WP ID to ordered prerequisite IDs | Dependency graph after canceled source nodes are removed; no prerequisite may be canceled. |
| `stale_dependencies` | ordered tuple of `StaleCanceledDependency` | Every direct edge from an eligible work package to a canceled prerequisite. |

### Invariants

- Eligible and canceled IDs are disjoint and their union is the known IDs.
- Only exact current `canceled` lifecycle state affects membership.
- Every key in `eligible_dependencies` is eligible.
- A successful projection has no canceled prerequisite in `eligible_dependencies`.
- Ordering is lexical by normalized work-package ID and stable across runs.
- Missing lifecycle entries for known, not-yet-bootstrapped work packages are eligible.
- Status read errors occur before construction; the entity never represents guessed state.

## Entity: `StaleCanceledDependency`

Immutable diagnostic record created before graph filtering.

| Field | Type | Meaning |
|---|---|---|
| `dependent_wp_id` | `WP##` string | Eligible work package declaring the dependency. |
| `canceled_dependency_wp_id` | `WP##` string | Direct prerequisite whose current lifecycle lane is canceled. |
| `recovery` | constant string | Instruction to remove or repoint the dependency. |

Records sort by `(dependent_wp_id, canceled_dependency_wp_id)` and are rendered completely in human and JSON modes.

## Existing entity: Canonical lifecycle state

The current lifecycle lane remains derived from `status.events.jsonl` through the coordination-aware status surface. This Mission adds no transition and does not mutate state while deciding eligibility.

| Current state | Eligible? | Reason |
|---|---:|---|
| `canceled` | No | Exact exclusion state introduced by this Mission. |
| `done` | Yes | C-002 forbids generalizing cancellation to terminal states. |
| Other valid lifecycle lanes | Yes | Existing execution behavior is preserved. |
| Missing per-WP entry on first finalize | Yes | Canonical bootstrap has not seeded it yet. |
| Unreadable/corrupt event authority | No projection | Finalization fails closed. |

## Existing entity: Execution-lane manifest

The persisted schema is unchanged. A mixed Mission contains only eligible work packages and surviving execution-lane dependencies. An all-canceled Mission contains zero execution lanes using the allocator's existing empty representation. Canceled definitions and events remain in Mission history.

## State and projection flow

```text
Definitions + direct dependencies with valid IDs/references
                 |
Canonical current lifecycle map (one read)
                 |
                 v
       FinalizationEligibility
          |               |
  stale edges exist   no stale edges
          |               |
 explicit refusal     validate eligible DAG cycles
                          |
                  filter ownership/body/frontmatter maps
                          |
                   pure compute_lanes
                          |
              normal or zero-lane manifest
```

## Validation rules

1. Raw dependency ID format and unknown-reference integrity run before projection; raw cycles do not, because canceled-only nodes are not executable DAG input.
2. Status authority must resolve and parse successfully.
3. All stale direct edges are collected before any node is removed.
4. A nonempty stale set blocks all finalization writers.
5. DAG cycle validation runs on `eligible_dependencies`; canceled-only or isolated canceled cycles do not block, while every surviving eligible cycle does.
6. Ownership and execution consumers receive maps keyed only by eligible IDs.
7. Empty eligible input is accepted only when known IDs are nonempty and all are canceled.
8. Missing ownership for remaining eligible code work retains existing failure behavior.
