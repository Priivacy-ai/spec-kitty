# Contract: Event Envelope (3.0.0 Conformance)

**Feature**: 064-complete-mission-identity-cutover
**Date**: 2026-04-06
**Upstream**: spec-kitty-events @ 5b8e6dc, spec-kitty-saas @ 3a0e4af

## Envelope Shape

Every event emitted to SaaS (via WebSocket, batch sync, or offline queue) must include:

```json
{
  "schema_version": "3.0.0",
  "build_id": "uuid-of-this-checkout",
  "aggregate_type": "Mission",
  "event_type": "MissionCreated | MissionClosed | WPStatusChanged | ...",
  "payload": {
    "mission_slug": "064-my-mission",
    "mission_number": "064",
    "mission_type": "software-dev",
    ...
  }
}
```

## Required Envelope Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Must be `"3.0.0"` |
| `build_id` | string (UUID) | Unique checkout/worktree identity |
| `aggregate_type` | string | Must be `"Mission"` (never `"Feature"`) |
| `event_type` | string | One of the canonical event types |

## Forbidden Envelope Fields

| Field | Reason |
|-------|--------|
| `feature_slug` | Legacy alias; use `mission_slug` in payload |
| `aggregate_type: "Feature"` | Legacy aggregate type |

## Required Payload Fields (mission-scoped events)

| Field | Type | Description |
|-------|------|-------------|
| `mission_slug` | string | Mission instance identifier (e.g., "064-my-mission") |
| `mission_number` | string | Mission sequence number (e.g., "064") |
| `mission_type` | string | Mission workflow kind (e.g., "software-dev") |

## Forbidden Payload Fields

| Field | Reason |
|-------|--------|
| `feature_slug` | Legacy; replaced by `mission_slug` |
| `feature_number` | Legacy; replaced by `mission_number` |
| `feature_type` | Legacy; replaced by `mission_type` |

## Canonical Event Types

| Event Type | When Emitted |
|------------|-------------|
| `MissionCreated` | New mission scaffolded |
| `MissionClosed` | Mission accepted/completed |
| `WPStatusChanged` | Work package lane transition |
| `WPCreated` | Work package added |
| `WPAssigned` | Work package claimed by actor |
| `HistoryAdded` | Audit log entry appended |
| `ErrorLogged` | Error event recorded |
| `DependencyResolved` | WP dependency resolved |
| `MissionOriginBound` | Tracker origin binding |

## Forbidden Event Types

| Event Type | Reason |
|------------|--------|
| `FeatureCreated` | Legacy; replaced by `MissionCreated` |
| `FeatureCompleted` | Legacy; replaced by `MissionClosed` |

## build_id Invariants

- `build_id` must be present and non-null on every emitted envelope
- `build_id` must be preserved through serialization, queue storage, replay, and reduction
- Different checkouts/worktrees of the same repository must have different `build_id` values
- The same checkout must retain its `build_id` across sessions
