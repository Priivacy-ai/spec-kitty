# Contract: Runtime Bridge Dispatch (composition vs. legacy)

**Source file**: `src/specify_cli/next/runtime_bridge.py`
**Spec coverage**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-015, EDGE-002, EDGE-003

## Public Surface

```python
def decide_next_via_runtime(...) -> Decision:
    ...
```

The `Decision` shape (defined in `src/specify_cli/next/decision.py`) is **unchanged** by this mission. No new fields. No removed fields.

## Single-Dispatch Invariant

For every call to `decide_next_via_runtime(...)`:

> Exactly one of {composition path, legacy DAG path} executes per action attempt.

Concretely, when `_should_dispatch_via_composition(action) == True`:
1. `_dispatch_via_composition(...)` runs (composer + guard + advancement helper).
2. The returned `Decision` is yielded immediately.
3. `runtime_next_step(...)` is **NOT** called.

When `_should_dispatch_via_composition(action) == False`:
1. `runtime_next_step(...)` runs (legacy path) exactly as today.
2. `_dispatch_via_composition(...)` is NOT entered.

## State Diagram

```
decide_next_via_runtime(action)
        |
        v
   _should_dispatch_via_composition(action) ?
        |
   yes  v                              no  v
   _dispatch_via_composition(action)        runtime_next_step(action)
        |                                     |
        v                                     v
   StepContractExecutor.execute(...)          (unchanged)
   _check_composed_action_guard(...)          |
   _advance_run_state_after_composition(...)  |
        |                                     |
        v                                     v
        Decision  (composition)               Decision  (legacy)
```

## New Helper

```python
def _advance_run_state_after_composition(
    repo_root: Path,
    action: str,
    ...,
) -> Decision:
    """Advance run state, lane events, and prompt progression for a composition-backed action.

    Reuses the same primitives as runtime_next_step(...) for state/lane/prompt
    progression but does NOT invoke the legacy DAG action handler — that is the
    point of single-dispatch (FR-001).
    """
```

The helper:
- Emits lane status events via the same `SyncRuntimeEventEmitter`.
- Records mission-state advancement via the same primitive that `runtime_next_step(...)` uses.
- Computes the next public step.
- Returns a `Decision` whose shape is identical to what `runtime_next_step(...)` would produce for the same advance — but with no legacy action dispatch performed.

## Ordering Within `_dispatch_via_composition(...)`

The order within the composition path is fixed:

1. `StepContractExecutor.execute(context)` — composer runs the contract steps via `ProfileInvocationExecutor.invoke(...)`.
2. `_check_composed_action_guard(...)` — fixed `tasks` guard (keyed by `legacy_step_id`) runs after composition. **Unchanged.**
3. `_advance_run_state_after_composition(...)` — new step.
4. Return `Decision`.

Step 2 must remain before step 3. Step 3 must run only on a successful step 1 + step 2.

## `tasks` Guard Semantics (FR-003)

The fixed `tasks` guard is keyed by `legacy_step_id`:

| `legacy_step_id` | Required state |
|------------------|----------------|
| `tasks_outline` | `tasks.md` exists |
| `tasks_packages` | `tasks.md` exists AND ≥1 `tasks/WP*.md` exists |
| `tasks_finalize` (and the public `tasks` step) | terminal state including a `dependencies:` block |

**This contract does not change.** Existing tests for these branches must continue to pass without modification.

## Test Surface

| Test name | File | Asserts |
|-----------|------|---------|
| `test_composition_success_skips_legacy_dispatch[<action>]` | `test_runtime_bridge_composition.py` | parametrized over the 5 composed actions; legacy dispatch entry point is **not called** after composition success (FR-001/FR-015) |
| `test_composition_success_advances_run_state_and_lane_events` | `test_runtime_bridge_composition.py` | lane events emitted; `Decision` reflects progression to next public step (FR-002) |
| `test_decision_shape_unchanged_for_composed_action` | `test_runtime_bridge_composition.py` | `Decision` field set is identical to legacy-path baseline (FR-005) |
| existing `test_tasks_*_guard_*` | `test_runtime_bridge_composition.py` | continue to pass unchanged (FR-003) |
| `test_non_composed_action_uses_legacy_runtime_next_step` | `test_runtime_bridge_composition.py` | EDGE-002 — `runtime_next_step(...)` still runs for non-composed actions |
| `test_advancement_helper_failure_propagates_no_legacy_fallback` | `test_runtime_bridge_composition.py` | EDGE-003 — when the helper raises, the error surfaces through the existing `Decision` error shape; legacy dispatch is **not** entered as a fallback |

## Failure Modes

- **Helper raises**: surfaced through the existing `Decision` error shape; no fallback to legacy dispatch (EDGE-003).
- **`StepContractExecutor.execute(...)` raises**: existing behavior — error is propagated/wrapped through the existing `Decision` error shape (no behavioral change vs. current `main`).
- **Guard fails (`tasks` semantics)**: existing behavior — guard returns a structured failure; this is unchanged.

## Non-Goals

- Editing `mission-runtime.yaml` (FR-004).
- Adding a new mission runner or mission step type (NFR-005).
- Changing the public `Decision` shape (FR-005).
- Affecting non-composed actions (EDGE-002).
