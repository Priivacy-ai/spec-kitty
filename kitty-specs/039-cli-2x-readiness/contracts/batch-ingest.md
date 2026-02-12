# Contract: Batch Event Ingest

**Feature**: 039-cli-2x-readiness
**Version**: 1.0.0
**Date**: 2026-02-12

## Overview

This document specifies the contract between the spec-kitty CLI (event producer) and the spec-kitty-saas backend (event consumer) for batch event ingestion.

## Authentication

### Login Flow

```
POST /api/v1/token/
Content-Type: application/json

{"username": "<username>", "password": "<password>"}

→ 200 OK
{"access": "<jwt_access_token>", "refresh": "<jwt_refresh_token>"}
```

### Token Refresh

```
POST /api/v1/token/refresh/
Content-Type: application/json

{"refresh": "<jwt_refresh_token>"}

→ 200 OK
{"access": "<new_jwt_access_token>"}
```

### Authorization Header

All authenticated requests use:
```
Authorization: Bearer <jwt_access_token>
```

## Batch Ingest Endpoint

### Request

```
POST /api/v1/events/batch/
Authorization: Bearer <jwt_access_token>
Content-Type: application/json
Content-Encoding: gzip

{
  "events": [
    {
      "event_id": "<26-char ULID>",
      "event_type": "WPStatusChanged",
      "aggregate_id": "<entity_id>",
      "payload": { ... },
      "timestamp": "2026-02-12T10:00:00+00:00",
      "node_id": "<node_identifier>",
      "lamport_clock": 42,
      "causation_id": "<26-char ULID or null>",
      "project_uuid": "<uuid4>",
      "project_slug": "my-project",
      "correlation_id": "<26-char ULID>",
      "schema_version": "1.0.0",
      "data_tier": 0
    }
  ]
}
```

**Batch size**: Up to 1000 events per request.
**Compression**: Body is gzip-compressed.
**Ordering**: Events are sent in FIFO order (timestamp ASC, id ASC).

### Success Response (HTTP 200)

```json
{
  "results": [
    {"event_id": "01HXYZ...", "status": "success"},
    {"event_id": "01HXYZ...", "status": "duplicate"},
    {"event_id": "01HXYZ...", "status": "rejected", "error": "Invalid payload: missing field 'wp_id'"}
  ]
}
```

**Per-event statuses**:
- `success`: Event accepted and stored
- `duplicate`: Event with this `event_id` already exists (treated as success by CLI)
- `rejected`: Event failed validation (CLI retains for retry or diagnosis)

### Error Response (HTTP 400)

```json
{
  "error": "Batch processing failed",
  "details": "Transaction rolled back: 3 events failed schema validation"
}
```

**Required**: The `details` field MUST be present for 400 responses. The CLI depends on it for diagnostics.

### Error Response (HTTP 401)

```json
{
  "error": "Token expired or invalid"
}
```

CLI behavior: Attempt token refresh, retry once. If refresh fails, prompt user to re-authenticate.

### Error Response (HTTP 403)

```json
{
  "error": "Insufficient permissions for team 'my-team' on project 'my-project'"
}
```

CLI behavior: Surface error and suggest checking team membership.

## Event Types

### WPStatusChanged

Emitted when a work package changes lane.

**Payload** (4-lane sync format):
```json
{
  "feature_slug": "039-cli-2x-readiness",
  "wp_id": "WP01",
  "from_lane": "planned",
  "to_lane": "doing",
  "actor": "claude-agent",
  "force": false,
  "reason": null,
  "execution_mode": "WORKTREE",
  "review_ref": null,
  "evidence": null
}
```

**Lane values in sync payload** (4-lane only): `planned`, `doing`, `for_review`, `done`

See [lane-mapping.md](lane-mapping.md) for the 7→4 lane collapse specification.

### MissionStarted

Emitted when a feature workflow begins.

**Payload**:
```json
{
  "feature_slug": "039-cli-2x-readiness",
  "mission_key": "software-dev",
  "started_by": "user@example.com"
}
```

### MissionCompleted

Emitted when all WPs reach terminal state.

**Payload**:
```json
{
  "feature_slug": "039-cli-2x-readiness",
  "mission_key": "software-dev",
  "completed_at": "2026-02-12T18:00:00+00:00",
  "wp_count": 9,
  "done_count": 9
}
```

### PhaseEntered

Emitted when workflow enters a new phase.

**Payload**:
```json
{
  "feature_slug": "039-cli-2x-readiness",
  "phase": "implement",
  "entered_at": "2026-02-12T12:00:00+00:00"
}
```

### ReviewRollback

Emitted when a WP is moved back from for_review.

**Payload**:
```json
{
  "feature_slug": "039-cli-2x-readiness",
  "wp_id": "WP02",
  "rolled_back_from": "for_review",
  "rolled_back_to": "doing",
  "reason": "Changes requested: missing test coverage"
}
```

## Event Envelope Field Reference

| Field | Type | Required | Constraints | Example |
|-------|------|----------|-------------|---------|
| event_id | string | Yes | 26 chars, ULID | "01HXYZ1234567890ABCDEFGH" |
| event_type | string | Yes | min 1 char | "WPStatusChanged" |
| aggregate_id | string | Yes | min 1 char | "039-cli-2x-readiness/WP01" |
| payload | object | Yes | - | (see event type schemas above) |
| timestamp | string | Yes | ISO 8601 with timezone | "2026-02-12T10:00:00+00:00" |
| node_id | string | Yes | min 1 char | "cli-macbook-abc123" |
| lamport_clock | integer | Yes | >= 0 | 42 |
| causation_id | string | No | 26 chars if present | "01HXYZ1234567890ABCDEFGI" |
| project_uuid | string | Yes | UUID v4 | "550e8400-e29b-41d4-a716-446655440000" |
| project_slug | string | No | - | "my-project" |
| correlation_id | string | Yes | 26 chars, ULID | "01HXYZ1234567890ABCDEFJK" |
| schema_version | string | Yes | semver | "1.0.0" |
| data_tier | integer | Yes | 0-4 | 0 |

## Required SaaS Changes

1. **Return `details` field in 400 responses** with per-event failure reasons
2. **Validate team/project authorization** for the authenticated user
3. **Accept only 4-lane sync values** (`planned`, `doing`, `for_review`, `done`) and reject unknown lanes
4. **Return `duplicate` status** for events with previously-seen `event_id` values
5. **Include `error` field in rejected results** with specific validation failure reason
