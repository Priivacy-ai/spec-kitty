# SaaS API Integration Contract

**Feature**: 040-mission-collaboration-cli-soft-coordination
**Version**: S1/M1 Step 1
**Base URL**: `https://api.spec-kitty-saas.com` (production) | `https://dev.spec-kitty-saas.com` (development)

## Authentication

**Method:** Bearer Token (API Key)

**Header:**
```
Authorization: Bearer <api-key>
```

**API Key:**
- Issued by SaaS admin
- Scoped to user account (binds to auth_principal)
- Required for all endpoints

**Error Response (401 Unauthorized):**
```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing API key",
  "code": "SAAS_AUTH_FAILED"
}
```

---

## Endpoint: Join Mission

**Method:** `POST`

**Path:** `/api/v1/missions/{mission_id}/participants`

**Purpose:** Join mission and receive SaaS-minted participant_id.

**Path Parameters:**
| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `mission_id` | string | Mission identifier (UUID or slug) | Yes |

**Request Body:**
```json
{
  "role": "developer",
  "auth_principal": "alice@example.com",
  "client_metadata": {
    "cli_version": "0.15.0",
    "platform": "darwin",
    "node_id": "cli-alice-macbook"
  }
}
```

**Request Schema:**
| Field | Type | Description | Required | Constraints |
|-------|------|-------------|----------|-------------|
| `role` | string | Participant role | Yes | ∈ {developer, reviewer, observer, stakeholder} |
| `auth_principal` | string | User email or OAuth subject | Yes | Matches authenticated user |
| `client_metadata` | object | CLI metadata | No | Opaque to SaaS |

**Response (200 OK):**
```json
{
  "participant_id": "01HQRS8ZMBE6XYZ0000000001",
  "mission_id": "mission-abc-123",
  "role": "developer",
  "capabilities": {
    "can_focus": true,
    "can_drive": true,
    "can_execute": true,
    "can_ack_warning": true,
    "can_comment": true,
    "can_decide": true
  },
  "session_token": "sess_01HQRS8ZMBE6XYZABC0123TOK",
  "joined_at": "2026-02-15T10:00:00Z"
}
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| `participant_id` | string | SaaS-minted ULID (26 chars, mission-scoped) |
| `mission_id` | string | Mission identifier (echo of request) |
| `role` | string | Participant role (echo of request) |
| `capabilities` | object | Role-based capabilities (derived from role) |
| `session_token` | string | Session token for subsequent requests (ULID) |
| `joined_at` | string | ISO timestamp of join |

**Error Responses:**

**400 Bad Request (invalid role):**
```json
{
  "error": "BadRequest",
  "message": "Invalid role 'llm_actor'",
  "code": "INVALID_ROLE",
  "details": {
    "valid_roles": ["developer", "reviewer", "observer", "stakeholder"]
  }
}
```

**403 Forbidden (unauthorized mission):**
```json
{
  "error": "Forbidden",
  "message": "User 'alice@example.com' not authorized to join mission-abc-123",
  "code": "MISSION_UNAUTHORIZED"
}
```

**404 Not Found (mission not found):**
```json
{
  "error": "NotFound",
  "message": "Mission 'mission-abc-123' not found",
  "code": "MISSION_NOT_FOUND"
}
```

**409 Conflict (already joined):**
```json
{
  "error": "Conflict",
  "message": "Participant already joined mission-abc-123",
  "code": "ALREADY_JOINED",
  "details": {
    "participant_id": "01HQRS8ZMBE6XYZ0000000001",
    "joined_at": "2026-02-15T09:00:00Z"
  }
}
```

**Idempotency:**
- Multiple join requests for same mission return existing participant_id
- HTTP 409 Conflict with participant_id in details (not an error for CLI)

---

## Endpoint: Replay Events (Batch Upload)

**Method:** `POST`

**Path:** `/api/v1/events/batch/`

**Purpose:** Replay queued events from CLI local queue to SaaS.

**Request Body:**
```json
{
  "events": [
    {
      "event_id": "01HQRS8ZMBE6XYZABC0123001",
      "event_type": "ParticipantJoined",
      "aggregate_id": "mission-abc-123",
      "payload": {
        "participant_id": "01HQRS8ZMBE6XYZ0000000001",
        "role": "developer",
        "participant_type": "human"
      },
      "timestamp": "2026-02-15T10:00:00Z",
      "node_id": "cli-alice-macbook",
      "lamport_clock": 1,
      "causation_id": null
    },
    {
      "event_id": "01HQRS8ZMBE6XYZABC0123002",
      "event_type": "FocusChanged",
      "aggregate_id": "mission-abc-123",
      "payload": {
        "participant_id": "01HQRS8ZMBE6XYZ0000000001",
        "previous_focus": "none",
        "new_focus": "wp:WP01"
      },
      "timestamp": "2026-02-15T10:05:00Z",
      "node_id": "cli-alice-macbook",
      "lamport_clock": 2,
      "causation_id": "01HQRS8ZMBE6XYZABC0123001"
    }
  ]
}
```

**Request Schema:**
| Field | Type | Description | Required | Constraints |
|-------|------|-------------|----------|-------------|
| `events` | array | List of events to replay | Yes | Max 100 events per batch |

**Event Schema (Canonical Envelope):**
| Field | Type | Description | Required | Constraints |
|-------|------|-------------|----------|-------------|
| `event_id` | string | ULID identifier | Yes | 26 chars, unique |
| `event_type` | string | Event type name | Yes | One of 14 canonical types |
| `aggregate_id` | string | Mission identifier | Yes | - |
| `payload` | object | Event-specific data | Yes | Must include participant_id |
| `timestamp` | string | ISO timestamp | Yes | Wall-clock time |
| `node_id` | string | CLI instance identifier | Yes | - |
| `lamport_clock` | integer | Lamport logical clock | Yes | >= 0, monotonic |
| `causation_id` | string | ULID of triggering event | No | 26 chars if present |

**Response (200 OK):**
```json
{
  "accepted_count": 2,
  "rejected_count": 0,
  "accepted_event_ids": [
    "01HQRS8ZMBE6XYZABC0123001",
    "01HQRS8ZMBE6XYZABC0123002"
  ],
  "rejected_events": []
}
```

**Response (207 Multi-Status - partial success):**
```json
{
  "accepted_count": 1,
  "rejected_count": 1,
  "accepted_event_ids": [
    "01HQRS8ZMBE6XYZABC0123001"
  ],
  "rejected_events": [
    {
      "event_id": "01HQRS8ZMBE6XYZABC0123002",
      "error": "UnknownParticipant",
      "message": "Participant '01HQRS8ZMBE6XYZ0000000999' not in mission roster",
      "code": "PARTICIPANT_NOT_IN_ROSTER"
    }
  ]
}
```

**Response Schema:**
| Field | Type | Description |
|-------|------|-------------|
| `accepted_count` | integer | Number of accepted events |
| `rejected_count` | integer | Number of rejected events |
| `accepted_event_ids` | array | List of accepted event_ids (ULIDs) |
| `rejected_events` | array | List of rejection details (error, message, code) |

**Error Responses:**

**400 Bad Request (schema validation failure):**
```json
{
  "error": "BadRequest",
  "message": "Event schema validation failed",
  "code": "INVALID_EVENT_SCHEMA",
  "details": {
    "event_id": "01HQRS8ZMBE6XYZABC0123002",
    "validation_errors": [
      "event_id must be 26 characters (ULID format)",
      "causation_id must be 26 characters if present"
    ]
  }
}
```

**413 Payload Too Large (batch too large):**
```json
{
  "error": "PayloadTooLarge",
  "message": "Batch size exceeds maximum (100 events)",
  "code": "BATCH_TOO_LARGE",
  "details": {
    "max_batch_size": 100,
    "actual_batch_size": 150
  }
}
```

**Validation Rules:**
- `event_id` must be ULID (26 chars)
- `causation_id` must be ULID (26 chars) if present
- `aggregate_id` must match mission roster (mission_id exists)
- `payload.participant_id` must be in mission roster (SaaS validation)
- `event_type` must be one of 14 canonical types (feature 006 contract)
- Lamport clock must be >= 0 and monotonic per node_id

**Participant Roster Validation:**
- SaaS checks `payload.participant_id` against mission roster
- **Accept**: Participant in roster (normal case)
- **Reject**: Participant not in roster (hard error, not advisory)
- **Rejection code**: `PARTICIPANT_NOT_IN_ROSTER`

**Idempotency:**
- Duplicate event_ids are ignored (return 200 OK, no duplicate insertion)
- Replay same batch multiple times is safe (idempotent event_id)

**Rate Limiting:**
- Max 100 events per batch
- Max 10 batches per minute per participant
- HTTP 429 Too Many Requests if rate limit exceeded

---

## Connection Handling

**Timeout:**
- Join endpoint: 5 seconds
- Replay endpoint: 10 seconds (batch processing)

**Retry Policy:**
- Network errors: Exponential backoff (1s, 2s, 4s, 8s, 16s max)
- HTTP 5xx errors: Exponential backoff
- HTTP 4xx errors: No retry (client error, fix request)

**Offline Behavior:**
- Join endpoint: Must be online (hard requirement)
- Replay endpoint: Queue locally, retry on reconnect

---

## Environment Variables

**CLI Configuration:**
- `SAAS_API_URL`: Base URL (default: https://api.spec-kitty-saas.com)
- `SAAS_API_KEY`: API key for authentication
- `SAAS_DEV_URL`: Dev environment URL (for E2E testing)
- `SAAS_DEV_API_KEY`: Dev API key (for E2E testing)

---

## Testing

**Mock SaaS Mode (Local Development):**
```bash
export MOCK_SAAS=true
spec-kitty mission join mission-test-123 --role developer
# Uses mock responses (no actual SaaS call)
```

**Integration Tests:**
- Use `httpx.mock` or `respx` to mock SaaS endpoints
- Validate request schema (method, path, headers, body)
- Test error responses (401, 403, 404, 409, 400, 413)

**E2E Tests:**
- Use real SaaS dev environment
- Requires SAAS_DEV_URL and SAAS_DEV_API_KEY
- Test 3-participant scenario (real API calls)

---

## Backward Compatibility

**API Versioning:**
- Current: `/api/v1/...`
- Breaking changes: New version path (`/api/v2/...`)
- Deprecation: 6 months notice before removal

**S1/M1 Scope:**
- These endpoints are greenfield (2.x branch, no 1.x compatibility)

---

## Questions?

Contact the SaaS team lead or open a GitHub issue.
