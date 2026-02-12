# Data Model: CLI 2.x Readiness Sprint

**Feature**: 039-cli-2x-readiness
**Date**: 2026-02-12

## Entities

### Event (existing — spec_kitty_events.models.Event)

Immutable event envelope for distributed conflict detection.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| event_id | str | 26 chars, ULID format | Unique event identifier |
| event_type | str | min 1 char | e.g., 'WPStatusChanged', 'MissionStarted' |
| aggregate_id | str | min 1 char | Entity being modified (WP ID, mission ID) |
| payload | Dict[str, Any] | - | Event-specific data |
| timestamp | datetime | ISO 8601 | Wall-clock time (not used for ordering) |
| node_id | str | min 1 char | Emitting node identifier |
| lamport_clock | int | >= 0 | Logical clock for causal ordering |
| causation_id | Optional[str] | 26 chars if present | Parent event ID |
| project_uuid | uuid.UUID | - | Project this event belongs to |
| project_slug | Optional[str] | - | Human-readable project identifier |
| correlation_id | str | 26 chars, ULID | Groups events in same execution |
| schema_version | str | semver | Envelope version (default "1.0.0") |
| data_tier | int | 0-4 | Progressive sharing tier |

### QueueEntry (existing — sync/queue.py SQLite)

Persisted event in the offline SQLite queue.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | int | AUTO_INCREMENT | Queue entry ID |
| data | text | JSON | Serialized event envelope |
| retry_count | int | >= 0, default 0 | Number of failed sync attempts |
| created_at | text | ISO 8601 | When event was queued |
| last_attempt_at | text | ISO 8601, nullable | Last sync attempt timestamp |
| status | text | pending/failed/synced | Current queue entry status |

### StatusTransitionPayload (existing — spec_kitty_events.status)

Payload for WPStatusChanged events.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| feature_slug | str | - | Feature identifier |
| wp_id | str | - | Work package ID |
| from_lane | Optional[Lane] | 7-lane enum | Previous lane (None for initial) |
| to_lane | Lane | 7-lane enum | Target lane |
| actor | str | - | Who performed the transition |
| force | bool | - | Whether transition was forced |
| reason | Optional[str] | Required if force=True | Force justification |
| execution_mode | ExecutionMode | WORKTREE/DIRECT_REPO | How the transition was executed |
| review_ref | Optional[str] | - | Git ref for review |
| evidence | Optional[DoneEvidence] | Required if to_lane=DONE | Completion evidence |

### Lane (existing — spec_kitty_events.status.Lane)

7-lane canonical status model.

| Value | 4-Lane Sync Mapping | Terminal? |
|-------|---------------------|-----------|
| PLANNED | planned | No |
| CLAIMED | doing | No |
| IN_PROGRESS | doing | No |
| FOR_REVIEW | for_review | No |
| DONE | done | Yes |
| BLOCKED | doing | No |
| CANCELED | done | Yes |

**Alias**: `doing` → `IN_PROGRESS` (resolved by `LANE_ALIASES`)

### Credentials (existing — sync/auth.py)

TOML file at `~/.spec-kitty/credentials`.

| Section | Field | Type | Description |
|---------|-------|------|-------------|
| tokens | access | str | JWT access token |
| tokens | refresh | str | JWT refresh token |
| expiries | access | str | Access token expiry (ISO 8601) |
| expiries | refresh | str | Refresh token expiry (ISO 8601) |
| user | username | str | Authenticated username |
| user | team_slug | Optional[str] | Team identifier |
| server | url | str | SaaS server base URL |

## State Transitions

### Queue Entry Lifecycle

```
[created] → pending → (sync attempt) → synced (removed from queue)
                    → (sync attempt) → failed (retry_count++)
                                      → (max retries) → dead_letter (stays in queue)
```

### Event Sync Flow

```
Status transition (move-task)
    → emit_status_transition() [emitter.py]
        → emit_wp_status_changed() [7→4 lane mapping]
            → queue event (SQLite) [queue.py]
                → batch send (HTTP POST) [batch.py]
                    → per-event result processing
                        → success: remove from queue
                        → duplicate: remove from queue
                        → rejected: increment retry_count
                        → 400 error: surface details
```

## New Entities (this sprint)

### BatchResult (new — to be added to batch.py)

Per-event result from batch response processing.

| Field | Type | Description |
|-------|------|-------------|
| event_id | str | Event that was processed |
| status | str | "success", "duplicate", "rejected" |
| error | Optional[str] | Error message if rejected |
| error_category | Optional[str] | Grouped category: schema_mismatch, auth_expired, server_error, unknown |

### QueueStats (new — to be added to queue.py)

Aggregate queue statistics for health display.

| Field | Type | Description |
|-------|------|-------------|
| total_pending | int | Count of pending events |
| total_failed | int | Count of failed events |
| oldest_event_age | Optional[timedelta] | Age of oldest pending event |
| retry_distribution | Dict[str, int] | Histogram: retry bucket → count |
| top_event_types | List[Tuple[str, int]] | Most common event types in queue |

### DiagnoseResult (new — to be added to diagnose.py)

Result of local event validation.

| Field | Type | Description |
|-------|------|-------------|
| event_id | str | Event that was validated |
| valid | bool | Whether event passes schema validation |
| errors | List[str] | Specific validation error messages |
| event_type | str | Type of the event |
