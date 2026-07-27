# Data Model: Canonical Status Model Cleanup

## WP Frontmatter Schema (After Cleanup)

### Retained Fields (static definition + operational metadata)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `work_package_id` | `str` | Yes | e.g., "WP01" |
| `title` | `str` | Yes | Human-readable title |
| `dependencies` | `list[str]` | Yes | WP IDs this WP depends on |
| `subtasks` | `list[str]` | Yes | Subtask IDs (T001, T002, ...) |
| `planning_base_branch` | `str` | Yes | Branch to plan from |
| `merge_target_branch` | `str` | Yes | Branch to merge into |
| `branch_strategy` | `str` | Yes | Human-readable branch description |
| `execution_mode` | `str` | Yes | "code_change" or "planning_artifact" |
| `owned_files` | `list[str]` | Yes | Glob patterns for owned files |
| `authoritative_surface` | `str` | Yes | Path prefix for ownership |
| `requirement_refs` | `list[str]` | No | FR-### references |
| `agent` | `str` | No | Assigned agent name (operational) |
| `assignee` | `str` | No | Assigned human (operational) |
| `shell_pid` | `str` | No | Claiming process PID (operational) |
| `history` | `list[HistoryEntry]` | No | Lane-free notes (see below) |

### Removed Fields (no longer in active WP frontmatter)

| Field | Reason |
|-------|--------|
| `lane` | Status lives in `status.events.jsonl` only |
| `review_status` | Status lives in canonical events |
| `reviewed_by` | Status lives in canonical events |
| `review_feedback` | Written to WP body or feedback files, not frontmatter |
| `progress` | Derived from canonical state, not stored in frontmatter |

### HistoryEntry (Lane-Free)

After cleanup, history entries contain:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `at` | `str (ISO 8601)` | Yes | Timestamp |
| `actor` | `str` | Yes | Agent or user name (replaces `agent` in history) |
| `action` | `str` | Yes | Human-readable description |
| `shell_pid` | `str` | No | Process that performed the action |

**Removed from history**: `lane`, `event` (when lane-bearing), any structured status data.

## Canonical Status Entities (Unchanged)

These entities are defined by Feature 034 and are not modified by this cleanup.

### StatusEvent (in status.events.jsonl)

| Field | Type | Notes |
|-------|------|-------|
| `event_id` | `str (ULID)` | Unique event identifier |
| `feature_slug` | `str` | Feature this event belongs to |
| `wp_id` | `str` | Work package ID |
| `from_lane` | `str` | Previous lane |
| `to_lane` | `str` | New lane |
| `actor` | `str` | Who triggered the transition |
| `at` | `str (ISO 8601)` | When it happened |
| `reason` | `str \| null` | Optional reason for transition |
| `force` | `bool` | Whether transition was forced |
| `evidence` | `str \| null` | Optional evidence reference |
| `execution_mode` | `str` | "worktree" or "main" |
| `review_ref` | `str \| null` | Review reference (for review transitions) |

### StatusSnapshot (materialized status.json)

| Field | Type | Notes |
|-------|------|-------|
| `feature_slug` | `str` | Feature identifier |
| `work_packages` | `dict[str, WPState]` | WP ID → current state |
| `last_event_id` | `str` | Most recent event ID |
| `materialized_at` | `str (ISO 8601)` | When snapshot was produced |

### WPState (within snapshot)

| Field | Type | Notes |
|-------|------|-------|
| `lane` | `str` | Current canonical lane |
| `actor` | `str` | Last actor to change state |
| `at` | `str` | When last transition occurred |

## State Transitions

### Canonical Bootstrap (finalize-tasks)

```
[WP file exists, no canonical event]
    │
    └─ finalize-tasks scans WPs
         │
         ├─ event log exists, WP has events → skip (already canonical)
         ├─ event log exists, WP has no events → emit planned event
         └─ event log absent → create file, emit planned event for all WPs
              │
              └─ materialize status.json
```

### Runtime Behavior (after cleanup)

```
[Runtime command needs WP lane]
    │
    ├─ status.events.jsonl exists?
    │     │
    │     ├─ Yes → reduce to snapshot
    │     │     │
    │     │     ├─ WP has state → use it
    │     │     └─ WP has no state → "uninitialized" (reads) or hard-fail (mutations)
    │     │
    │     └─ No → HARD FAIL: "Run finalize-tasks"
    │
    └─ NEVER: read frontmatter lane
```
