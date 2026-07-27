# Event Envelope Contract

**Feature**: 032-identity-aware-cli-event-sync
**Date**: 2026-02-07

## Updated Event Envelope Schema

This document describes the changes to the event envelope schema.

### Before (Current)

```json
{
  "event_id": "01HQXYZ...",
  "event_type": "WPStatusChanged",
  "aggregate_id": "WP01",
  "aggregate_type": "WorkPackage",
  "payload": { ... },
  "timestamp": "2026-02-07T12:00:00Z",
  "node_id": "node-abc123",
  "lamport_clock": 42,
  "causation_id": null,
  "team_slug": "my-team"
}
```

### After (This Feature)

```json
{
  "event_id": "01HQXYZ...",
  "event_type": "WPStatusChanged",
  "aggregate_id": "WP01",
  "aggregate_type": "WorkPackage",
  "payload": { ... },
  "timestamp": "2026-02-07T12:00:00Z",
  "node_id": "node-abc123",
  "lamport_clock": 42,
  "causation_id": null,
  "team_slug": "my-team",
  
  // NEW FIELDS
  "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "project_slug": "my-project"
}
```

## Field Definitions

### project_uuid (NEW, REQUIRED for WebSocket)

- **Type**: `string` (UUID4 format)
- **Description**: Unique identifier for the project that emitted this event
- **Format**: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
- **Generation**: Created once during `spec-kitty init` or on first event emission
- **Persistence**: Stored in `.kittify/config.yaml`

**Validation**:
- MUST be present for WebSocket transmission
- If missing, event is queued locally only (not sent via WebSocket)
- Warning logged when event lacks project_uuid

### project_slug (NEW, OPTIONAL)

- **Type**: `string | null`
- **Description**: Human-readable identifier for the project
- **Format**: Kebab-case, derived from directory name or git remote
- **Example**: `"my-awesome-project"`, `"spec-kitty"`

**Derivation Logic**:
1. If git remote `origin` exists: Extract repo name from URL
2. Otherwise: Use directory name, converted to kebab-case

## Backward Compatibility

### CLI → SaaS

- **Old CLI (without project_uuid)**: Events will be stored but not attributed to a project
- **New CLI**: Events include project_uuid, SaaS can materialize Projects

### SaaS Processing

The SaaS should handle events with/without project_uuid:

```python
# In batch sync handler
if event.get("project_uuid"):
    project = get_or_create_project(event["project_uuid"], event.get("project_slug"))
    event.project = project
else:
    logger.warning(f"Event {event['event_id']} missing project_uuid")
    # Store event but don't attribute to project
```

## Migration

No migration needed. New fields are:
- Generated on first CLI access (graceful backfill)
- Optional in existing events (backward compatible)
- Required only for new WebSocket transmissions
