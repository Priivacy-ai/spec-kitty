# Plan — Canonical Producer Refactor

## Architecture

The CLI has two producer surfaces:

1. **Local-first lifecycle producers** in `src/specify_cli/status/lifecycle_events.py`
   that write append-only JSONL to disk and (optionally) fan out to a SaaS
   outbox via `_lifecycle_saas_fanout_handler` registered by `specify_cli.sync`.
2. **SaaS-direct emitters** in `src/specify_cli/sync/emitter.py` that build
   the canonical wire envelope (`event_id`, `event_type`, `aggregate_id`,
   `payload`, `timestamp`, `project_uuid`, `correlation_id`, …) and route
   through the local outbox + opportunistic WebSocket.

The refactor inserts a canonical-payload construction step at each
producer's payload-build boundary:

```
caller-args -> Canonical*Payload(...).model_dump(mode="json") -> envelope
```

For ergonomics, the producer functions keep their public signatures but
construct the payload via pydantic and `model_dump`. This gives:

- Compile-time-shaped payloads (extra-field rejection via
  `additionalProperties: false` on the schema side; pydantic
  `model_config = ConfigDict(extra="forbid")` on the model side where
  Phase 1 declared it).
- Strict canonical validation at the producer boundary.
- The lint AST rule (CP001/CP002) becomes happy on these sites because
  the dict literal is now `Payload(...).model_dump()` not a bare dict.

## File surfaces

### `src/specify_cli/status/lifecycle_events.py`

- Import canonical models from `spec_kitty_events.project_lifecycle`.
- Convert `emit_project_initialized`, `emit_mission_created_local`,
  `emit_artifact_phase`, `emit_wp_created_local` to build their payload
  via pydantic and `model_dump(mode="json", exclude_none=True)`.
- The `_build_envelope` helper itself remains the local-log envelope
  (not the SaaS wire envelope); it's annotated with a
  `canonical-producer-exempt` since the envelope is local-only and
  documented; OR it returns a typed `LocalLifecycleEnvelope` shape so
  the lint doesn't catch it. Pick whichever the lint allows.
- Tighten `_validate_lifecycle_payload()`: raise on `schema_violations`
  too (not just `model_violations`) for known event types. Local-only
  types (per `LOCAL_ONLY_EVENT_TYPES` from `spec_kitty_events`) skip
  strict validation; today that set is empty.

### `src/specify_cli/sync/emitter.py`

For each of:

- `emit_wp_status_changed` -> `WPStatusChangedPayload` (already in
  `spec_kitty_events.status`)
- `emit_wp_created` -> `WPCreatedPayload`
- `emit_wp_assigned` -> `WPAssignedPayload`
- `emit_build_registered` -> `BuildRegisteredPayload`
- `emit_build_heartbeat` -> `BuildHeartbeatPayload`
- `emit_history_added` -> `HistoryAddedPayload`
- `emit_error_logged` -> `ErrorLoggedPayload`
- `emit_dependency_resolved` -> `DependencyResolvedPayload`
- `emit_mission_origin_bound` -> `MissionOriginBoundPayload`
- `emit_mission_created` -> `MissionCreatedPayload`
- `emit_mission_closed` -> `MissionClosedPayload`
- `emit_mission_started` -> `MissionStartedPayload`
- `emit_phase_entered` -> `PhaseEnteredPayload`
- `emit_mission_completed` -> `MissionCompletedPayload`

build the payload via the canonical model. The wire envelope build in
`_emit()` keeps its current shape (event_id, project_uuid, correlation_id,
timestamp, …) — that's the SaaS wire envelope contract, not a payload.
`_emit()` itself constructs an envelope dict that includes
`event_type`+`payload` keys; we'll route the envelope build via the
`Event` pydantic model from `spec_kitty_events` (already imported) so
the lint sees a canonical constructor.

### `src/specify_cli/status/adapters.py`

Fix `reset_handlers()` test-order pollution. The cause: `_lifecycle_saas_fanout_handler`
is registered at module-import time of `specify_cli.sync`, and tests that
call `adapters.reset_handlers()` wipe it. Re-importing `specify_cli.sync`
doesn't re-run the registration block (the module is already in
`sys.modules`).

Options:

- **Option A (least invasive):** Add a public re-registration entry point,
  e.g. `register_default_handlers()` in `specify_cli.sync` that the
  conftest pytest fixture invokes after `reset_handlers()`. This is the
  cleanest: tests opt in.
- **Option B:** Add a per-test autouse fixture in
  `tests/status/conftest.py` that resets and re-registers.

We'll use **Option B** scoped to the `tests/status/` package, so the
production behavior of `reset_handlers()` stays the same (it's
documented as a test-only utility) and the fix is contained to tests.

### `_validate_lifecycle_payload()` widening

Replace:
```python
result = validate_event(dict(payload), event_type, strict=False)
if result.model_violations:
    raise ValueError(...)
```
with:
```python
if event_type in LOCAL_ONLY_EVENT_TYPES:
    return  # local-only events are not subject to strict canonical contract
if event_type not in _EVENT_TYPE_TO_MODEL:
    return  # unknown types pass; lint catches the producer side
result = validate_event(dict(payload), event_type, strict=True)
if result.model_violations or result.schema_violations:
    details = "; ".join(
        f"{v.field}: {v.message}"
        for v in (*result.model_violations, *result.schema_violations)
    )
    raise ValueError(
        f"Lifecycle payload for {event_type!r} fails canonical contract: {details}"
    )
```

### `emit_artifact_phase` Started/Completed split

Started events (`SpecifyStarted`, `PlanStarted`, `TasksStarted`) must
reject Completed-only extras (`artifact_path`, `summary`, `wp_count`).
The cleanest approach: refuse to populate them in the payload at all
when `event_type.endswith("Started")`. The canonical pydantic models
(`SpecifyStartedPayload` etc.) already enforce this; we just need to
not pass the extras through.

## Test strategy

### New: `tests/status/test_producer_conformance.py`

Enumerate every `emit_*` function on the lifecycle module and the
`EventEmitter` class. For each, build a minimal valid argument set,
invoke the producer (with mocked OfflineQueue/clock/identity), capture
the resulting envelope, and assert:

- `validate_event(envelope["payload"], envelope["event_type"], strict=True)`
  returns a clean result (no model_violations, no schema_violations).
- The pydantic `Event(**envelope)` model accepts the envelope.

### Existing tests

- `tests/status/test_emit_backward_transition.py`
- `tests/status/test_lifecycle_events.py`
- `tests/sync/` package
- `tests/lint/` package

Should continue to pass. New: `tests/status/conftest.py` autouse
fixture that re-registers the default lifecycle handler after any
`reset_handlers()` call.

## Lint burndown

After the refactor, `python scripts/lint_canonical_producers.py
--update-baseline scripts/canonical_producer_lint_baseline.txt` rewrites
the baseline. Remaining entries must:

- Be in a local-only / internal-only / test-only path.
- Carry an inline `# canonical-producer-exempt: #1200 — <reason>` or
  `#1203` comment, OR be left in the baseline file with the reason
  documented in a comment block at the top of the baseline.

Expected drop: from ~172 raw violations to substantially fewer (target
< 80 raw violations) and a meaningfully shrunken baseline.

## Notes for Phase 3 / Phase 4

- Phase 3 (`spec-kitty-saas` legacy adapter) consumes
  `LegacyEnvelopeNormalizer` from `spec_kitty_events.legacy`. Phase 2
  does NOT touch the SaaS side.
- Phase 4 (E2E canary) verifies legacy normalization end-to-end. Phase 2
  ensures the CLI side emits canonical events strictly; Phase 4 covers
  the historical-events path.
- Phase 5 bumps `pyproject.toml` to a pinned `spec-kitty-events` version
  once Phase 1 is published.
