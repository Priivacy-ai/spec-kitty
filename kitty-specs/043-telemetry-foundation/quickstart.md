# Quickstart: 043 Telemetry Foundation

## Emitting Execution Events

```python
from specify_cli.telemetry import emit_execution_event

# After an agent invocation completes:
emit_execution_event(
    feature_dir=feature_dir,
    feature_slug="043-telemetry-foundation",
    wp_id="WP01",
    agent="claude",
    role="implementer",
    model="claude-sonnet-4-20250514",
    input_tokens=1500,
    output_tokens=800,
    cost_usd=0.0165,
    duration_ms=12500,
    success=True,
    error=None,
    exit_code=0,
)
# Fire-and-forget: errors are logged as warnings, never raised
```

## Querying Events

```python
from specify_cli.telemetry import query_execution_events, EventFilter

# All execution events for a feature
events = query_execution_events(feature_dir)

# Filtered query
events = query_execution_events(
    feature_dir,
    filters=EventFilter(agent="claude", success=True),
)

# Project-wide query (across all features)
from specify_cli.telemetry import query_project_events

events = query_project_events(
    repo_root=repo_root,
    filters=EventFilter(model="claude-sonnet-4-20250514"),
)
```

## Cost Summary

```python
from specify_cli.telemetry import cost_summary

# By agent
summaries = cost_summary(events, group_by="agent")
for s in summaries:
    print(f"{s.group_key}: ${s.total_cost_usd:.4f} ({s.event_count} invocations)")

# By model
summaries = cost_summary(events, group_by="model")
```

## CLI Commands

```bash
# Project-wide cost report
spec-kitty agent telemetry cost

# Feature-specific
spec-kitty agent telemetry cost --feature 043-telemetry-foundation

# Grouped by model with timeframe
spec-kitty agent telemetry cost --group-by model --since 2026-02-01

# JSON output for scripting
spec-kitty agent telemetry cost --json
```

## SimpleJsonStore (Direct Usage)

```python
from specify_cli.telemetry.store import SimpleJsonStore
from specify_cli.spec_kitty_events import Event

store = SimpleJsonStore(feature_dir / "execution.events.jsonl")

# Save (idempotent by event_id)
store.save_event(event)

# Load by aggregate
events = store.load_events(aggregate_id="043-telemetry-foundation")

# Load all
all_events = store.load_all_events()
```
