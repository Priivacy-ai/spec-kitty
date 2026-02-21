# Data Model: 043 Telemetry Foundation

**Date**: 2026-02-15
**Feature**: 043-telemetry-foundation

## Entities

### ExecutionEvent (via `spec_kitty_events.Event`)

Not a new class — uses the existing `Event` Pydantic model with `event_type="ExecutionEvent"` and structured `payload`.

**Event envelope** (from `spec_kitty_events.Event`):

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `str` (ULID, 26 chars) | Unique identifier |
| `event_type` | `str` | `"ExecutionEvent"` |
| `aggregate_id` | `str` | Feature slug (e.g., `"043-telemetry-foundation"`) |
| `timestamp` | `datetime` | Wall-clock timestamp (ISO 8601 UTC) |
| `node_id` | `str` | Emitting node identity (agent key or "cli") |
| `lamport_clock` | `int` | Logical clock value for causal ordering |
| `causation_id` | `str | None` | Parent event ID (e.g., the StatusEvent that triggered this invocation) |

**Payload** (execution-specific data in `Event.payload`):

| Field | Type | Description |
|-------|------|-------------|
| `wp_id` | `str` | Work package ID (e.g., `"WP01"`) |
| `agent` | `str` | Agent key (e.g., `"claude"`, `"codex"`) |
| `role` | `str` | `"implementer"` or `"reviewer"` |
| `model` | `str | None` | Model identifier (e.g., `"claude-sonnet-4-20250514"`) |
| `input_tokens` | `int | None` | Input token count |
| `output_tokens` | `int | None` | Output token count |
| `cost_usd` | `float | None` | Reported cost in USD |
| `duration_ms` | `int` | Invocation duration in milliseconds |
| `success` | `bool` | Whether invocation succeeded |
| `error` | `str | None` | Error message if failed |
| `exit_code` | `int` | Process exit code |

**JSONL representation** (one line in `execution.events.jsonl`):

```json
{"aggregate_id":"043-telemetry","causation_id":null,"event_id":"01HXYZ...","event_type":"ExecutionEvent","lamport_clock":42,"node_id":"claude","payload":{"agent":"claude","cost_usd":0.15,"duration_ms":12500,"error":null,"exit_code":0,"input_tokens":1500,"model":"claude-sonnet-4-20250514","output_tokens":800,"role":"implementer","success":true,"wp_id":"WP01"},"timestamp":"2026-02-15T10:00:00+00:00"}
```

### SimpleJsonStore

JSONL-backed implementation of `spec_kitty_events.EventStore` ABC.

| Attribute | Type | Description |
|-----------|------|-------------|
| `file_path` | `Path` | Path to the JSONL file |

**Methods** (from ABC):

| Method | Signature | Behavior |
|--------|-----------|----------|
| `save_event` | `(event: Event) -> None` | Append to JSONL; skip if `event_id` already exists (idempotent) |
| `load_events` | `(aggregate_id: str) -> list[Event]` | Stream-parse, filter by `aggregate_id`, sort by `(lamport_clock, node_id)` |
| `load_all_events` | `() -> list[Event]` | Stream-parse all, sort by `(lamport_clock, node_id)` |

**Additional methods**:

| Method | Signature | Behavior |
|--------|-----------|----------|
| `query` | `(filters: EventFilter) -> list[Event]` | Filtered read with stream-parsing |

### EventFilter

Query parameters for the telemetry query layer.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `event_type` | `str | None` | `None` | Filter by event type |
| `wp_id` | `str | None` | `None` | Filter by work package ID (in payload) |
| `agent` | `str | None` | `None` | Filter by agent key (in payload) |
| `model` | `str | None` | `None` | Filter by model identifier (in payload) |
| `since` | `datetime | None` | `None` | Events after this timestamp |
| `until` | `datetime | None` | `None` | Events before this timestamp |
| `success` | `bool | None` | `None` | Filter by success flag (in payload) |

### CostSummary

Aggregated cost report.

| Field | Type | Description |
|-------|------|-------------|
| `group_key` | `str` | Grouping value (agent name, model ID, or feature slug) |
| `group_by` | `str` | Grouping dimension (`"agent"`, `"model"`, `"feature"`) |
| `total_input_tokens` | `int` | Sum of input tokens |
| `total_output_tokens` | `int` | Sum of output tokens |
| `total_cost_usd` | `float` | Sum of reported + estimated costs |
| `estimated_cost_usd` | `float` | Portion of total that was estimated from pricing table |
| `event_count` | `int` | Number of ExecutionEvents aggregated |

### PricingTable

Model-to-cost mapping shipped as `_pricing.yaml`.

```yaml
# src/specify_cli/telemetry/_pricing.yaml
models:
  claude-sonnet-4-20250514:
    input_per_1k: 0.003
    output_per_1k: 0.015
  claude-opus-4-20250514:
    input_per_1k: 0.015
    output_per_1k: 0.075
  gpt-4.1:
    input_per_1k: 0.03
    output_per_1k: 0.06
  gemini-2.5-pro:
    input_per_1k: 0.00125
    output_per_1k: 0.01
  # ... more models
```

**Loading precedence**:

1. Constitution pricing overrides (`.kittify/memory/constitution.md` → future `.kittify/constitution/governance.yaml`)
2. Default `_pricing.yaml` shipped with spec-kitty

### InvocationResult (enrichment)

**Existing fields** (unchanged):

- `success`, `exit_code`, `stdout`, `stderr`, `duration_seconds`, `files_modified`, `commits_made`, `errors`, `warnings`

**New optional fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model` | `str | None` | `None` | Model used for this invocation |
| `input_tokens` | `int | None` | `None` | Input token count |
| `output_tokens` | `int | None` | `None` | Output token count |
| `cost_usd` | `float | None` | `None` | Reported cost in USD |

## Relationships

```
InvocationResult ──enriched──→ emit_execution_event() ──creates──→ Event(type="ExecutionEvent")
                                                                        │
                                                          SimpleJsonStore.save_event()
                                                                        │
                                                                        ▼
                                              kitty-specs/<feature>/execution.events.jsonl

SimpleJsonStore.query(EventFilter) ──reads──→ execution.events.jsonl ──returns──→ list[Event]
                                                                                      │
                                                               cost_summary(events, pricing)
                                                                                      │
                                                                                      ▼
                                                                              list[CostSummary]
```

## State Transitions

ExecutionEvents are append-only — no state machine. The `success` field in the payload records the terminal outcome:

- `success=True` — invocation completed successfully
- `success=False` — invocation failed (with `error` and `exit_code`)

No retry or transition logic — each invocation attempt produces one event.
