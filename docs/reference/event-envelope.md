# Event Envelope Reference

Every event emitted by spec-kitty follows a fixed envelope schema with 15 fields.
The canonical contract lives at `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md`.

## Field Reference

### Core Envelope (9 fields)

| Field | Type | Required | Resolved | Description |
|-------|------|----------|----------|-------------|
| `event_id` | `string` | Yes | Per-event | 26-char ULID, unique per event |
| `event_type` | `string` | Yes | Per-event | One of the 8 event types (e.g. `WPStatusChanged`) |
| `aggregate_id` | `string` | Yes | Per-event | WP ID or feature slug |
| `aggregate_type` | `string` | Yes | Per-event | `"WorkPackage"` or `"Feature"` |
| `payload` | `object` | Yes | Per-event | Event-type-specific data |
| `timestamp` | `string` | Yes | Per-event | ISO 8601 UTC wall-clock time |
| `node_id` | `string` | Yes | Per-session | 12-char hex machine identifier from LamportClock |
| `lamport_clock` | `integer` | Yes | Per-event | Monotonic logical clock, incremented each emit |
| `causation_id` | `string\|null` | No | Per-event | ULID of parent event for batch correlation |

### Identity Fields (3 fields -- Feature 032)

| Field | Type | Required | Resolved | Description |
|-------|------|----------|----------|-------------|
| `team_slug` | `string` | Yes | Per-session | Team identifier; `"local"` when unauthenticated |
| `project_uuid` | `string\|null` | Yes* | Per-session | UUID4 from `.kittify/identity.yaml`; required for WebSocket |
| `project_slug` | `string\|null` | No | Per-session | Kebab-case project name |

*Events without `project_uuid` are queued locally only (not sent via WebSocket).

### Git Correlation Fields (3 fields -- Feature 033)

| Field | Type | Required | Resolved | Description |
|-------|------|----------|----------|-------------|
| `git_branch` | `string\|null` | No | Per-event (2s TTL) | Current branch; `"HEAD"` if detached; `null` outside git |
| `head_commit_sha` | `string\|null` | No | Per-event (2s TTL) | Full 40-char SHA of HEAD; `null` outside git |
| `repo_slug` | `string\|null` | No | Per-session | `owner/repo` format; `null` if no remote configured |

**Derivation precedence for `repo_slug`:**
1. Config override: `.kittify/config.yaml` > `project.repo_slug`
2. Auto-derived: `git remote get-url origin` > extract `owner/repo`
3. `null` (no override, no remote)

## Backward Compatibility

| Scenario | Behavior |
|----------|----------|
| Old CLI (pre-033) sends event without git fields | SaaS accepts; fields treated as absent |
| New CLI (033+) sends event with git fields | SaaS uses fields for GitHub correlation |
| Mixed queue (old + new events) replayed | All events accepted; SaaS handles both |

**Field absence vs null:** A `null` value means "resolved but unavailable". An absent field means the event predates feature 033. Consumers should handle both.

## Example Event

```json
{
  "event_id": "01HQXYZ1234567890ABCDEFG",
  "event_type": "WPStatusChanged",
  "aggregate_id": "WP01",
  "aggregate_type": "WorkPackage",
  "payload": {
    "wp_id": "WP01",
    "previous_status": "planned",
    "new_status": "doing",
    "changed_by": "claude-opus",
    "feature_slug": "033-github-observability-event-metadata"
  },
  "timestamp": "2026-02-07T12:00:00+00:00",
  "node_id": "abc123def456",
  "lamport_clock": 42,
  "causation_id": null,
  "team_slug": "my-team",
  "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "project_slug": "spec-kitty",
  "git_branch": "033-github-observability-event-metadata-WP01",
  "head_commit_sha": "68b09b04a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
  "repo_slug": "Priivacy-ai/spec-kitty"
}
```

See the [canonical contract](../kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md) for full details.
