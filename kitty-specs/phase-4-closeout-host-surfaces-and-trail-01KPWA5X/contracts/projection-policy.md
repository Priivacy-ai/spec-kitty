# Contract: `src/specify_cli/invocation/projection_policy.py`

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Covers**: FR-010 (SaaS read-model policy), FR-012 (local-first invariant), NFR-005 (typed + mypy-strict), NFR-007 (propagation-error quiet invariant)

## Purpose

Define the single source of truth for how each `(mode_of_work, event)` pair projects to the SaaS timeline. Consumed by `src/specify_cli/invocation/propagator.py::_propagate_one` after the existing sync-gate. Documented for operators in `docs/trail-model.md`.

## Public API

```python
# Re-exported from projection_policy.py for caller convenience.
from specify_cli.invocation.modes import ModeOfWork

class EventKind(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ARTIFACT_LINK = "artifact_link"
    COMMIT_LINK = "commit_link"

@dataclass(frozen=True)
class ProjectionRule:
    project: bool
    include_request_text: bool
    include_evidence_ref: bool

POLICY_TABLE: dict[tuple[ModeOfWork, EventKind], ProjectionRule]

def resolve_projection(mode: ModeOfWork | None, event: EventKind) -> ProjectionRule: ...
```

The module exports exactly these symbols. Nothing else is public.

## Table authority

`POLICY_TABLE` is the complete enumeration of 4 modes × 4 events = 16 entries. See `data-model.md` §5 for the full table.

**Golden-path invariants (contract tests):**

| Row | Rule |
|-----|------|
| `(TASK_EXECUTION, STARTED)` | `ProjectionRule(True, True, False)` |
| `(TASK_EXECUTION, COMPLETED)` | `ProjectionRule(True, True, True)` |
| `(MISSION_STEP, STARTED)` | `ProjectionRule(True, True, False)` |
| `(MISSION_STEP, COMPLETED)` | `ProjectionRule(True, True, True)` |

Any change to these four rows requires an ADR and a migration note — they govern existing dashboard behaviour for active missions.

**Expected zero-projection rows:**

| Row | Rule |
|-----|------|
| any `(QUERY, *)` | `project=False` |
| `(ADVISORY, ARTIFACT_LINK)` | `project=False` |
| `(ADVISORY, COMMIT_LINK)` | `project=False` |

Query invocations and advisory correlation events produce no SaaS timeline traffic.

## `resolve_projection()` semantics

```python
def resolve_projection(mode: ModeOfWork | None, event: EventKind) -> ProjectionRule:
    effective_mode = mode if mode is not None else ModeOfWork.TASK_EXECUTION
    return POLICY_TABLE.get((effective_mode, event), _DEFAULT_RULE)
```

- `mode is None` → treated as `TASK_EXECUTION`. Rationale: pre-mission records projected under the old unconditional behaviour, which was effectively `(TASK_EXECUTION, event)` projection. Preserving that behaviour on upgrade means no dashboard regression.
- Unknown `(mode, event)` pair → falls back to `_DEFAULT_RULE = ProjectionRule(True, True, True)`. In practice the table is exhaustive for the enums as defined, so this path is only hit if a future `EventKind` value is added without the policy table being extended.

## Consumer contract — `_propagate_one`

Modified sequence (diff from 3.2.0a5):

```python
def _propagate_one(record: InvocationRecord_or_EventDict, repo_root: Path) -> None:
    # 1. Existing sync-gate — unchanged. Short-circuit on sync disabled.
    routing = resolve_checkout_sync_routing(repo_root)
    if routing is not None and not routing.effective_sync_enabled:
        return

    # 2. Existing auth/client lookup — unchanged.
    client = _get_saas_client(repo_root)
    if client is None:
        return

    # 3. NEW: consult policy.
    mode = _extract_mode(record)     # returns ModeOfWork | None
    event = _extract_event(record)   # returns EventKind
    rule = resolve_projection(mode, event)
    if not rule.project:
        return

    # 4. Existing envelope build — now respects include_request_text / include_evidence_ref.
    ...
```

The helper `_extract_mode` reads `record.mode_of_work` for `InvocationRecord` inputs and the `mode_of_work` key from the stored `started` event when the input is a correlation event dict. `_extract_event` maps the `event` field to `EventKind`.

### Envelope field gating

When `rule.include_request_text is False`, the envelope for `started` events **omits** the `request_text` key entirely. Omission, not empty string — this keeps dashboard consumers able to distinguish "advisory started" (no body) from "task_execution started with empty request" (present body, empty).

Same rule for `rule.include_evidence_ref`: omit on `False`, include on `True` (only relevant for `completed` events where `evidence_ref` is present).

## Invariants

- **Policy evaluation is read-only.** It never writes to disk, never raises an uncaught exception, and never blocks.
- **Policy evaluation runs after the sync-gate.** If sync is disabled for the checkout (`effective_sync_enabled=False`), `resolve_projection` is never called — the short-circuit still owns the gate (C-002, FR-012).
- **Policy evaluation runs after authentication.** Unauthenticated checkouts never reach policy evaluation.
- **Type exhaustiveness.** `mypy --strict` passes; `ModeOfWork` and `EventKind` are closed sets.
- **Frozen dataclass.** `ProjectionRule` is frozen so policy rows are shareable and immutable.
- **No operator-configurable override.** This mission does not introduce YAML or env-var overrides (C-009, D4).

## Acceptance tests (selected)

These tests live in `tests/specify_cli/invocation/test_projection_policy.py` (new) and extensions to `test_invocation_e2e.py`:

1. Every `(ModeOfWork, EventKind)` pair has an entry in `POLICY_TABLE`.
2. Golden-path rows match the expected rules (see table above).
3. `resolve_projection(None, EventKind.STARTED)` returns the `TASK_EXECUTION / STARTED` rule (null-tolerance).
4. `_propagate_one` with a mocked connected WebSocket client:
   - Drops advisory `artifact_link` events (no `send_event` call).
   - Emits `task_execution` `started` events (one `send_event` call, envelope includes `request_text`).
   - Emits `task_execution` `completed` events (envelope includes `evidence_ref` when supplied).
5. With sync disabled (`effective_sync_enabled=False`), `resolve_projection` is not called and no envelope is built — verified by mock assertion.
6. With user unauthenticated, `resolve_projection` is not called — verified by mock assertion.
7. `propagation-errors.jsonl` remains empty across 100 invocations under all four modes with sync disabled (NFR-007, SC-008).
