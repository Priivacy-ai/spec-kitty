# Data Model: Phase 6 Composition Stabilization

**Mission**: phase6-composition-stabilization-01KQ2JAS
**Created**: 2026-04-25

This mission does not introduce new persistent entities. It tightens invariants on three existing in-process / on-disk shapes.

## Entities

### 1. Invocation lifecycle pair (existing — invariant tightened)

**Storage**: `.kittify/events/profile-invocations/<invocation_id>.jsonl`

| Field on disk | Type | Source |
|---------------|------|--------|
| `event` | `Literal["started", "completed", "failed", "abandoned"]` | first record `started`; second record one of `completed`/`failed`/`abandoned` (here we only emit `completed` or `failed`) |
| `invocation_id` | ULID-26 | `InvocationRecord.invocation_id` (`record.py`) |
| `action` | str | `InvocationRecord.action` — see #794 invariant below |
| `outcome` | `Literal["done", "failed", "abandoned"] | None` | `record.py:34` |
| `... existing fields ...` | n/a | unchanged |

**Invariant (new — tightened by FR-006/FR-007/FR-008)**:

> For every invocation file produced by a composed `software-dev` action, the file contains exactly one `started` record AND exactly one closing record (`completed` with `outcome="done"` for success, or `failed` with `outcome="failed"` for failure).

**State transitions** (existing, made mandatory for composed steps):

```
(no file)
   |
   |  StepContractExecutor.execute(): ProfileInvocationExecutor.invoke(...)
   v
[started]
   |
   |  on success: complete_invocation(id, outcome="done")
   |  on exception: complete_invocation(id, outcome="failed"); raise
   v
[completed | failed]   <-- terminal for this mission
```

`abandoned` exists in the schema but is not produced by composed-step lifecycle close (reserved for user cancellation flows).

### 2. `ProfileInvocationExecutor.invoke(...)` action key (existing — semantic widened)

**Field**: the value passed to `InvocationRecord(action=...)` at `invocation/executor.py:185`.

**Old behavior** (current `main`):

| Branch | Action source |
|--------|---------------|
| `profile_hint` is set | `_derive_action_from_request(request_text, profile.role)` → role-default verb (e.g. `analyze`, `audit`) |
| router-backed | `result.action` from router decision |

**New behavior** (after #794):

| Branch | Action source |
|--------|---------------|
| `profile_hint` is set, `action_hint` truthy | `action_hint` verbatim |
| `profile_hint` is set, `action_hint` falsy/absent | `_derive_action_from_request(request_text, profile.role)` (legacy fallback) |
| router-backed | unchanged — `result.action` from router decision |

**Invariant (new — tightened by FR-013)**:

> When `action_hint` is supplied, governance context assembly reads `action_hint` (via the record). When `action_hint` is not supplied, governance context assembly reads the derived role-default verb. There is no third path.

### 3. Runtime-bridge dispatch decision (existing — single-dispatch invariant)

**Producer**: `runtime_bridge.decide_next_via_runtime(...)`
**Output type**: `Decision` (dataclass at `next/decision.py`)

**Invariant (new — tightened by FR-001/FR-002/FR-005)**:

> For every composition-backed `software-dev` action attempt, exactly one of {composition path, legacy DAG path} executes per call to `decide_next_via_runtime(...)`. Composition success returns a `Decision` directly without calling `runtime_next_step(...)`. The shape of `Decision` is unchanged.

**State transitions** (after fix):

```
decide_next_via_runtime(action)
        |
        |  _should_dispatch_via_composition(action) == True ?
        |  ----- yes -----                                       ----- no -----
        v                                                                v
   _dispatch_via_composition(action)                            runtime_next_step(action)
        |                                                                |
        |  StepContractExecutor.execute(...)                            (unchanged)
        |    -> ProfileInvocationExecutor.invoke(action_hint=...)
        |  _check_composed_action_guard(...)                              v
        |  _advance_run_state_after_composition(...)              Decision (legacy)
        v
   Decision (composition)         <-- returned directly; no fall-through to runtime_next_step
```

## Relationships

- **`StepContractExecutor` → `ProfileInvocationExecutor`** — composer-to-primitive. Composer never bypasses the primitive (C-005/C-006).
- **`ProfileInvocationExecutor` → `InvocationWriter`** — the only path that touches `.kittify/events/profile-invocations/*.jsonl` (FR-008, C-007).
- **`runtime_bridge` → `StepContractExecutor`** — for composed actions only.
- **`runtime_bridge` → `runtime_next_step`** — for non-composed actions only (after fix).

## Validation Rules (testable)

| Rule | Source | Test target |
|------|--------|-------------|
| Every `started` JSONL line for a composed action has a matching `completed` or `failed` line. | FR-006/FR-007 | `test_invocation_e2e.py::test_composed_action_pairs_started_with_completed` |
| The `action` field on a composed-step started record is the contract action when `action_hint` is supplied. | FR-010 | `test_invocation_e2e.py::test_invoke_with_action_hint_and_profile_hint_records_hint` |
| The `action` field falls back to the derived verb when `action_hint` is not supplied. | FR-011 | `test_invocation_e2e.py::test_invoke_profile_hint_only_falls_back_to_derived_action` |
| `decide_next_via_runtime(...)` does NOT call the legacy DAG dispatch handler after composition success. | FR-001/FR-015 | `test_runtime_bridge_composition.py::test_composition_success_skips_legacy_dispatch` |
| The `Decision` field set is unchanged. | FR-005 | `test_runtime_bridge_composition.py::test_decision_shape_unchanged_for_composed_action` |
| The fixed `tasks` guard branches by `legacy_step_id`. | FR-003 | existing `test_tasks_*_guard_*` tests |
