# Research: 043 Telemetry Foundation

**Date**: 2026-02-15
**Feature**: 043-telemetry-foundation

## R1: Event Model — Build on `spec_kitty_events` vs New Package

**Decision**: Build on `spec_kitty_events.Event` (Pydantic model)

**Rationale**: The vendored `spec_kitty_events` package already provides:

- `Event` Pydantic model with `event_type`, `aggregate_id`, `lamport_clock`, `causation_id`, `node_id`, `payload`
- `EventStore` ABC with `save_event()`, `load_events(aggregate_id)`, `load_all_events()`
- `LamportClock` with `tick()`, `update()`, `current()` for causal ordering
- `InMemoryEventStore` for testing
- CRDT merge functions for future distributed conflict resolution

ExecutionEvent data fits naturally into the `Event.payload` dict with `event_type="ExecutionEvent"`. No new model class needed — the existing `Event` is generic by design.

**Alternatives considered**:

- New `ExecutionEvent` dataclass in `status/models.py` — rejected: would couple telemetry to the status pipeline
- New Pydantic model in `telemetry/models.py` — rejected: duplicates `spec_kitty_events.Event` structure
- Plain dict (like `mission_v1/events.py`) — rejected: loses Pydantic validation and Lamport clock ordering

## R2: Storage — `SimpleJsonStore` implementing `EventStore` ABC

**Decision**: Create `SimpleJsonStore` as a JSONL-backed implementation of `spec_kitty_events.EventStore`

**Rationale**: The `EventStore` ABC requires three methods:

- `save_event(event: Event)` — append-only JSONL write (idempotent by event_id)
- `load_events(aggregate_id: str)` — filtered read, sorted by `(lamport_clock, node_id)`
- `load_all_events()` — full read, sorted

JSONL is the established pattern in the codebase (used by `status/store.py`, `mission_v1/events.py`, `sync/queue.py`). A file-backed adapter completes the missing "WP02" that was never implemented in `events/store.py`.

**Implementation notes**:

- Append mode for writes (single-process CLI, no file locking needed per constitution)
- Stream-parse for reads (handle >100MB files per spec requirement)
- Skip malformed lines with warning (consistent with existing `read_events()` behavior)
- Idempotent: check `event_id` before appending (dedup on write)

**Alternatives considered**:

- SQLite-backed store — rejected: overkill for MVP, deferred per spec's "Out of Scope"
- Extending `status/store.py` — rejected: user decision to keep events in separate files

## R3: Event File Location — Per-Feature Collocation

**Decision**: `kitty-specs/<feature>/execution.events.jsonl`

**Rationale**: Consistent with `status.events.jsonl` and `mission-events.jsonl` per-feature collocation. The `aggregate_id` field in `spec_kitty_events.Event` maps naturally to `feature_slug`. Cross-project queries iterate over all `kitty-specs/*/execution.events.jsonl` files.

**Alternatives considered**:

- Centralized `.kittify/telemetry/events.jsonl` — rejected: breaks per-feature collocation pattern
- Same file as status events — rejected: user decision to keep separate for easier aggregation

## R4: Orchestrator Integration — Enrich `InvocationResult`

**Decision**: Add optional telemetry fields to `InvocationResult` in `orchestrator/agents/base.py`

**Fields to add**:

- `model: str | None = None`
- `input_tokens: int | None = None`
- `output_tokens: int | None = None`
- `cost_usd: float | None = None`

**Hook point**: After `execute_with_logging()` returns in `integration.py`:

- `process_wp_implementation()` — emit after implementation completes
- `process_wp_review()` — emit after review completes

**Pattern**: Follow existing try/except-with-warning pattern from `emit_wp_assigned()`:

```python
try:
    emit_execution_event(feature_dir, result, wp_id, agent_id, ...)
except Exception as e:
    logger.warning(f"Telemetry emission failed for {wp_id}: {e}")
```

**Alternatives considered**:

- Separate telemetry extraction from stdout — rejected: fragile regex parsing, agent-specific formats
- Post-processing step scanning log files — rejected: adds latency, complex

## R5: CLI Command Structure

**Decision**: `spec-kitty agent telemetry cost` following the nested typer pattern

**Registration**: Add `telemetry` sub-command to the `agent` command group in `cli/commands/agent/__init__.py`

**Pattern**: Same as `agent config`, `agent feature` sub-groups:

```python
# cli/commands/agent/telemetry.py
app = typer.Typer(name="telemetry", help="Telemetry and cost tracking")

@app.command("cost")
def cost_cmd(feature: str = None, since: str = None, until: str = None,
             group_by: str = "agent", json_output: bool = False): ...
```

## R6: Pricing Table Location

**Decision**: Co-locate `_pricing.yaml` in `src/specify_cli/telemetry/` package

**Pattern**: Follows `sync/_events_schema.json` — load via `Path(__file__).resolve().parent / "_pricing.yaml"`. No `pyproject.toml` changes needed.

**Default pricing**: Anthropic Claude, OpenAI GPT, Google Gemini current rates. Constitution can override project-level pricing preferences.

## R7: SaaS Fan-Out

**Decision**: Deferred — local JSONL only for MVP

**Rationale**: The `sync/emitter.py` pipeline supports adding new event types to `VALID_EVENT_TYPES` and `_PAYLOAD_RULES`. When SaaS telemetry is needed, adding `"InvocationCompleted"` to the emitter will route through the existing WebSocket/offline-queue infrastructure. This is out of scope for 043 but the architecture supports it.
