# Data Model: Annoying Bugs Sweep

## Existing Entities

### LegacyWPRuntime

The pre-event-source witness read from WP frontmatter and `tasks.md`.

| Field | Role in this mission |
|---|---|
| `wp_id` | Per-WP ordering and verification key |
| `shell_pid` | Claim-borne value that must survive |
| `shell_pid_created_at` | Claim-borne value that must survive |
| `agent` | Claim-borne value that must survive |
| `assignee`, `tracker_refs`, `subtasks`, `review` | Annotation values that must not overwrite later legitimate annotations |

### EventStream

Two independently ordered collections:

- `transitions`: folded by `(at, event_id)` to derive lane and claim-borne slots.
- `annotations`: folded after transitions, also by `(at, event_id)`, to derive off-axis slots.

## Planning Value Objects

### WPSeedOrder

| Field | Type | Invariant |
|---|---|---|
| `wp_id` | `str` | Safe WP identifier |
| `existing_transition_keys` | sequence of `(at, event_id)` | Read from the canonical status stream |
| `existing_annotation_keys` | sequence of `(at, event_id)` | Read from the same stream |
| `seed_key` | `(at, event_id)` | Strictly less than every existing key for this WP when history exists |
| `anchor_source` | enum | `existing_history_floor`, `claim_event`, `frontmatter`, or `mission_created_at` |

The implementation may use a helper rather than a persisted dataclass. The value-object model exists
to make the invariant testable.

### ClaimSlotWitness

| Field | Type | Rule |
|---|---|---|
| `wp_id` | `str` | Matches the legacy row |
| `slot` | enum | `shell_pid`, `shell_pid_created_at`, or `agent` |
| `legacy_value` | scalar | Derived directly from `read_legacy_runtime` |
| `raw_seed_value` | scalar | Value persisted in the migration seed evidence |
| `snapshot_value` | scalar | Reduced after seed append |
| `later_legitimate_writer` | bool | Whether non-migration history owns the final slot |
| `matches` | `bool` | Raw seed equals legacy; snapshot equals legacy only without a later writer |

Every non-null legacy claim slot requires a matching raw seed witness. Snapshot equality is required
only when no later legitimate writer exists; otherwise verification proves that later value wins.

### SeedCompatibilityRepair

| Field | Type | Rule |
|---|---|---|
| `repair_id` | ULID | Deterministic namespace distinct from the original seed id |
| `corrupting_seed_id` | ULID | Identifies the persisted pre-fix seed |
| `restored_value` | scalar | Value reduced from legitimate history with migration seeds excluded |
| `slot` | lane or annotation field | Repairs only a value the old seed currently corrupts |

Compatibility repairs are append-only and idempotent. They are not emitted for correctly ordered
seeds or where a later legitimate writer already wins.

### DeadCodeVerdict

| Field | Type | Meaning |
|---|---|---|
| `state` | enum | `clean`, `findings`, `undeterminable` |
| `diagnostic_code` | string or null | Stable code for non-clean structured results |
| `examined_files` | integer | Non-negative denominator |
| `symbols` | list | Discovered public symbols |
| `findings` | list | Unreferenced symbols or diagnostic finding |
| `reason` | string or null | Required for `undeterminable` |

State rules:

- `clean` requires successful discovery and `examined_files > 0` for a supported source change set.
- `findings` requires at least one unreferenced symbol.
- `undeterminable` requires a stable diagnostic code and remediation; it is never rendered as clean.

## State Transitions

### Birth cutover

```text
legacy read -> seed/compatibility plan -> append missing deterministic seeds or repairs
            -> reduce -> independent raw + snapshot verify -> flip status_phase
```

Any append or verification error leaves `status_phase` unchanged.

### Dead-code gate

```text
baseline present -> diff discovery
  -> failed/unsupported -> undeterminable finding
  -> supported -> symbol extraction -> reference scan
       -> unreferenced symbols -> findings
       -> none -> clean
```
