# Quickstart: CLI Event Emission + Sync

**Feature**: 028-cli-event-emission-sync
**Date**: 2026-02-03

## Overview

This guide covers how to work with the event emission system for CLI commands.

## Prerequisites

- Python 3.11+
- spec-kitty-events library installed (via Git dependency)
- Feature 027 auth module available

## Using the EventEmitter

### Basic Event Emission

```python
from specify_cli.sync.events import emit_wp_status_changed

# In your CLI command, after the action succeeds:
emit_wp_status_changed(
    wp_id="WP01",
    previous_status="planned",
    new_status="doing",
    changed_by="user",
    feature_slug="028-cli-event-emission-sync",
)
```

### Getting the Singleton

```python
from specify_cli.sync.events import get_emitter

emitter = get_emitter()

# Check queue status
print(f"Queue size: {emitter.queue.size()}")

# Check connection status
print(f"Status: {emitter.get_connection_status()}")
```

### All Event Types

```python
from specify_cli.sync.events import (
    emit_wp_status_changed,
    emit_wp_created,
    emit_wp_assigned,
    emit_feature_created,
    emit_feature_completed,
    emit_history_added,
    emit_error_logged,
    emit_dependency_resolved,
)

# WP status change
emit_wp_status_changed("WP01", "planned", "doing")

# WP created (typically batch)
emit_wp_created("WP01", "Event Factory", dependencies=[], feature_slug="028-...")

# Agent assigned
emit_wp_assigned("WP01", agent_id="claude", phase="implementation")

# Feature created
emit_feature_created("028-...", feature_number="028", target_branch="2.x", wp_count=7)

# Feature completed
emit_feature_completed("028-...", total_wps=7)

# History entry
emit_history_added("WP01", entry_type="note", content="Implementation started")

# Error logged
emit_error_logged(wp_id="WP01", error_type="runtime", message="Test failed")

# Dependency resolved
emit_dependency_resolved("WP02", dependency_wp_id="WP01", resolution_type="completed")
```

## Wiring into Commands

### Example: implement.py

```python
# src/specify_cli/cli/commands/implement.py

from specify_cli.sync.events import emit_wp_status_changed

def implement(wp_id: str, ...):
    # ... existing workspace creation logic ...

    # After successful workspace creation:
    try:
        emit_wp_status_changed(
            wp_id=wp_id,
            previous_status="planned",
            new_status="doing",
            feature_slug=feature_slug,
        )
    except Exception as e:
        # Non-blocking: log warning but don't fail command
        console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")

    # ... rest of command ...
```

### Example: finalize-tasks (batch events)

```python
# src/specify_cli/cli/commands/agent/feature.py

from specify_cli.sync.events import (
    emit_feature_created,
    emit_wp_created,
    get_emitter,
)

def finalize_tasks(feature_slug: str, work_packages: list):
    # Generate causation_id for batch
    causation_id = get_emitter().generate_causation_id()

    # Emit FeatureCreated
    emit_feature_created(
        feature_slug=feature_slug,
        feature_number=feature_number,
        target_branch=target_branch,
        wp_count=len(work_packages),
        causation_id=causation_id,
    )

    # Emit WPCreated for each WP
    for wp in work_packages:
        emit_wp_created(
            wp_id=wp.id,
            title=wp.title,
            dependencies=wp.dependencies,
            feature_slug=feature_slug,
            causation_id=causation_id,
        )
```

## Testing

### Mocking the Emitter

```python
# tests/test_implement_events.py

from unittest.mock import MagicMock, patch

def test_implement_emits_status_change():
    mock_emitter = MagicMock()

    with patch('specify_cli.sync.events.get_emitter', return_value=mock_emitter):
        # Run implement command
        implement("WP01", feature="028-...")

        # Verify event emitted
        mock_emitter.emit_wp_status_changed.assert_called_once_with(
            wp_id="WP01",
            previous_status="planned",
            new_status="doing",
            feature_slug="028-...",
        )
```

### Testing with Real Queue

```python
# tests/test_offline_queue.py

import tempfile
from pathlib import Path
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.events import get_emitter

def test_events_queue_when_offline():
    with tempfile.TemporaryDirectory() as tmp:
        queue = OfflineQueue(db_path=Path(tmp) / "queue.db")
        emitter = get_emitter()
        emitter.queue = queue
        emitter._ws_client = None  # Simulate offline

        emit_wp_status_changed("WP01", "planned", "doing")

        assert queue.size() == 1
        events = queue.drain_queue()
        assert events[0]["event_type"] == "WPStatusChanged"
```

## Background Sync

### Manual Sync

```bash
# Force immediate sync
spec-kitty sync now

# Check sync status
spec-kitty sync status
```

### Programmatic Sync

```python
from specify_cli.sync.events import get_emitter
from specify_cli.sync.batch import sync_all_queued_events

emitter = get_emitter()

# Trigger batch sync
result = sync_all_queued_events(
    queue=emitter.queue,
    auth_token=emitter.auth.get_access_token(),
    server_url=emitter.config.get_server_url(),
)

print(f"Synced: {result.synced_count}, Errors: {result.error_count}")
```

## Debugging

### Inspect Offline Queue

```python
from specify_cli.sync.queue import OfflineQueue

queue = OfflineQueue()
print(f"Queue size: {queue.size()}")

events = queue.drain_queue(limit=10)
for e in events:
    print(f"{e['event_type']}: {e['aggregate_id']}")
```

### Check Lamport Clock

```python
from specify_cli.sync.events import get_emitter

emitter = get_emitter()
print(f"Current clock: {emitter.clock.value}")
print(f"Node ID: {emitter.clock.node_id}")
```

### View Clock File

```bash
cat ~/.spec-kitty/clock.json
# {"value": 42, "node_id": "alice-laptop-abc123", "updated_at": "..."}
```

## Troubleshooting

### Events Not Syncing

1. Check auth status: `spec-kitty auth status`
2. Check queue: `spec-kitty sync status`
3. Manual sync: `spec-kitty sync now`

### Clock Corruption

```bash
# Reset clock (loses ordering guarantee)
rm ~/.spec-kitty/clock.json

# Next event will start from 1
```

### Queue Full

```bash
# Check queue size
sqlite3 ~/.spec-kitty/queue.db "SELECT COUNT(*) FROM queue"

# Force sync to clear queue
spec-kitty sync now
```

---

**END OF QUICKSTART**
