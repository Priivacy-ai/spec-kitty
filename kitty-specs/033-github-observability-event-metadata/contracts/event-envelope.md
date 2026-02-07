# Event Envelope Contract

**Feature**: 033-github-observability-event-metadata
**Date**: 2026-02-07
**Supersedes**: 032-identity-aware-cli-event-sync/contracts/event-envelope.md

## Complete Event Envelope Schema

### Current (After Feature 032 + 033)

```json
{
  "event_id": "01HQXYZ...",
  "event_type": "WPStatusChanged",
  "aggregate_id": "WP01",
  "aggregate_type": "WorkPackage",
  "payload": { "wp_id": "WP01", "previous_status": "planned", "new_status": "doing" },
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

## Field Reference

### Core Envelope Fields (Existing)

| Field | Type | Required | Source | Description |
|-------|------|----------|--------|-------------|
| `event_id` | `string` | Yes | ULID generator | 26-char ULID, unique per event |
| `event_type` | `string` | Yes | Event builder | One of 8 valid types |
| `aggregate_id` | `string` | Yes | Event builder | WP ID or feature slug |
| `aggregate_type` | `string` | Yes | Event builder | `"WorkPackage"` or `"Feature"` |
| `payload` | `object` | Yes | Event builder | Event-type-specific data |
| `timestamp` | `string` | Yes | `datetime.now(UTC)` | ISO 8601 wall-clock time |
| `node_id` | `string` | Yes | LamportClock | 12-char hex machine identifier |
| `lamport_clock` | `integer` | Yes | LamportClock.tick() | Monotonic logical clock value |
| `causation_id` | `string\|null` | No | Caller | ULID of parent event (batch correlation) |

### Identity Fields (Feature 032)

| Field | Type | Required | Source | Description |
|-------|------|----------|--------|-------------|
| `team_slug` | `string` | Yes | AuthClient | Team identifier; `"local"` if unauthenticated |
| `project_uuid` | `string\|null` | Yes* | ProjectIdentity | UUID4; required for WebSocket send |
| `project_slug` | `string\|null` | No | ProjectIdentity | Kebab-case project name |

*Events without `project_uuid` are queued locally only (not sent via WebSocket).

### Git Correlation Fields (Feature 033 — NEW)

| Field | Type | Required | Source | Description |
|-------|------|----------|--------|-------------|
| `git_branch` | `string\|null` | No | GitMetadataResolver | Current branch name. `"HEAD"` if detached. `null` if not in git repo. |
| `head_commit_sha` | `string\|null` | No | GitMetadataResolver | Full 40-char SHA of HEAD. `null` if not in git repo. |
| `repo_slug` | `string\|null` | No | GitMetadataResolver | `owner/repo` format. From config override or auto-derived from origin. `null` if no remote. |

**Resolution timing**:
- `git_branch` and `head_commit_sha`: Resolved **per-event** (2s TTL cache for performance)
- `repo_slug`: Resolved **once per session** (stable — remote URL doesn't change mid-session)

**Derivation precedence for `repo_slug`**:
1. Explicit override: `.kittify/config.yaml` → `project.repo_slug`
2. Auto-derived: `git remote get-url origin` → extract `owner/repo`
3. `null` (no override, no remote)

## Backward Compatibility

### CLI → SaaS (Additive Changes)

| Scenario | Behavior |
|----------|----------|
| Old CLI (pre-033) sends event without git fields | SaaS accepts; git fields treated as absent |
| New CLI (033+) sends event with git fields | SaaS uses fields for GitHub correlation |
| Mixed queue (old + new events) replayed via batch sync | All events accepted; SaaS handles presence/absence |

### Validation Rules

The new fields are **NOT validated** by `_validate_event()` — they are envelope metadata outside the Pydantic Event model scope. The emitter sets them to `null` when unavailable; it does not reject events for missing git metadata.

### Field Absence vs. Null

| Value | Meaning |
|-------|---------|
| Field present, value is string | Git metadata resolved successfully |
| Field present, value is `null` | Git unavailable or not in a git repo |
| Field absent (old CLI) | Event predates feature 033; treat as unknown |

Consumers should handle all three cases.
