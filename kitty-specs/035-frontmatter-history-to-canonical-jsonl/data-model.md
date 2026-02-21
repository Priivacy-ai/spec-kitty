# Data Model: Frontmatter History to Canonical JSONL

**Feature**: 035-frontmatter-history-to-canonical-jsonl
**Date**: 2026-02-09

## Entities

### NormalizedHistoryEntry (new, internal to history_parser.py)

Intermediate representation after normalizing a raw Format A history entry.

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `str` | ISO 8601 UTC timestamp (from entry, or `datetime.now(UTC)` if missing) |
| `lane` | `str` | Canonical lane name (after alias resolution) |
| `actor` | `str` | Agent identifier (from entry, or `"migration"` if missing) |

**Invariants**:

- `lane` is always a canonical lane (never an alias like `doing`)
- `timestamp` is always a non-empty ISO 8601 string

### Transition (new, internal to history_parser.py)

A single lane transition derived from adjacent history entries.

| Field | Type | Description |
|-------|------|-------------|
| `from_lane` | `str` | Canonical source lane |
| `to_lane` | `str` | Canonical target lane |
| `timestamp` | `str` | Timestamp of the transition (from the target entry) |
| `actor` | `str` | Actor who caused this transition |
| `evidence` | `DoneEvidence \| None` | Extracted evidence for done transitions |

### TransitionChain (new, return type from history_parser)

| Field | Type | Description |
|-------|------|-------------|
| `transitions` | `list[Transition]` | Ordered list of transitions for one WP |
| `history_entries` | `int` | Number of raw history entries parsed |
| `has_evidence` | `bool` | Whether any transition has DoneEvidence |

### WPMigrationDetail (modified, in migrate.py)

Expanded from existing dataclass.

| Field | Type | Change | Description |
|-------|------|--------|-------------|
| `wp_id` | `str` | unchanged | Work package ID |
| `original_lane` | `str` | unchanged | Raw lane from frontmatter |
| `canonical_lane` | `str` | unchanged | After alias resolution |
| `alias_resolved` | `bool` | unchanged | True if alias was resolved |
| `events_created` | `int` | **new** (replaces `event_id`) | Number of events created |
| `event_ids` | `list[str]` | **new** (replaces `event_id`) | All ULID event IDs |
| `history_entries` | `int` | **new** | Raw history entry count |
| `has_evidence` | `bool` | **new** | Whether DoneEvidence was extracted |

**Migration note**: The old `event_id: str` field is replaced by `event_ids: list[str]` and `events_created: int`. Existing test assertions that check `event_id` will need updating.

## Existing Entities (unchanged)

These entities are used by the migration but not modified:

- **StatusEvent** (`models.py`): Immutable event record. Fields: `event_id`, `feature_slug`, `wp_id`, `from_lane`, `to_lane`, `at`, `actor`, `force`, `execution_mode`, `reason`, `review_ref`, `evidence`.
- **DoneEvidence** (`models.py`): Evidence payload. Contains `ReviewApproval`, optional `RepoEvidence` and `VerificationResult`.
- **ReviewApproval** (`models.py`): Reviewer approval record. Fields: `reviewer`, `verdict`, `reference`.
- **Lane** (`models.py`): StrEnum with 7 canonical lanes.
- **StatusSnapshot** (`models.py`): Materialized state from event log.

## State Transitions

### Migration Idempotency States

```
                    ┌─────────────────┐
                    │  No events file │
                    └────────┬────────┘
                             │ migrate_feature()
                             ▼
                    ┌─────────────────────┐
                    │ Events with marker  │
                    │ (full history)      │◄────── TERMINAL: re-run skips
                    └─────────────────────┘

                    ┌─────────────────────┐
                    │ Events: migration   │
                    │ actors only         │
                    │ (legacy bootstrap)  │
                    └────────┬────────────┘
                             │ backup + replace
                             ▼
                    ┌─────────────────────┐
                    │ Events with marker  │
                    │ (full history)      │◄────── TERMINAL: re-run skips
                    └─────────────────────┘

                    ┌─────────────────────┐
                    │ Events: live actors │
                    │ (non-migration)     │◄────── TERMINAL: always skip
                    └─────────────────────┘
```

### Event Generation Flow per WP

```
frontmatter.history[]
        │
        ▼
  normalize_entries()
        │ resolve aliases, extract (ts, lane, actor)
        ▼
  collapse_duplicates()
        │ remove consecutive same-lane entries
        ▼
  pair_transitions()
        │ adjacent entry pairing: N entries → N-1 transitions
        ▼
  gap_fill()
        │ if last_lane != current_lane: add one transition
        ▼
  extract_evidence()
        │ for done transitions: check review_status/reviewed_by
        ▼
  TransitionChain
        │
        ▼
  [StatusEvent, StatusEvent, ...]
```

## File Formats

### Backup File

Path: `<feature_dir>/status.events.jsonl.bak.<ISO-timestamp>`
Content: Exact copy of the original `status.events.jsonl` before replacement.
Naming: ISO timestamp uses safe filename characters (e.g., `2026-02-09T120000Z`).

### Migration Marker

Present in `StatusEvent.reason` field:

```
"historical_frontmatter_to_jsonl:v1"
```

This marker is set on the **first event** of each migrated WP's transition chain. Subsequent events for the same WP use `"historical migration"` as the reason.
