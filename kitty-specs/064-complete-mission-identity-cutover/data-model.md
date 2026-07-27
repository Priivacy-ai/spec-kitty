# Data Model: Complete Mission Identity Cutover

**Feature**: 064-complete-mission-identity-cutover
**Date**: 2026-04-06

## Entity Changes

### 1. ProjectIdentity

**Current state**: Already carries `build_id`. No field changes needed on the dataclass itself.

**Verification required**: Ensure `build_id` is read from and written to `.kittify/config.yaml` under the `build` section, and that it flows through all serialization paths.

### 2. NamespaceRef (body sync namespace)

**Current fields** (`src/specify_cli/sync/namespace.py:24-35`):
```
project_uuid: str
feature_slug: str        ← RENAME
target_branch: str
mission_key: str          ← RENAME
manifest_version: str
```

**Target fields**:
```
project_uuid: str
mission_slug: str         ← was feature_slug
target_branch: str
mission_type: str          ← was mission_key
manifest_version: str
```

**Downstream impact**: All code constructing or destructuring `NamespaceRef` must use new field names. Key call sites:
- `body_queue.py` (enqueue, dequeue)
- `body_transport.py` (_build_request_body)
- Anywhere `NamespaceRef` is constructed from mission metadata

### 3. BodyUploadTask (body upload queue)

**Current fields** (`src/specify_cli/sync/body_queue.py:33-49`):
```
row_id: int
project_uuid: str
feature_slug: str        ← RENAME
target_branch: str
mission_key: str          ← RENAME
manifest_version: str
artifact_path: str
content_hash: str
hash_algorithm: str
content_body: str
size_bytes: int
retry_count: int
next_attempt_at: float
created_at: float
```

**Target fields**:
```
row_id: int
project_uuid: str
mission_slug: str         ← was feature_slug
target_branch: str
mission_type: str          ← was mission_key
manifest_version: str
artifact_path: str
content_hash: str
hash_algorithm: str
content_body: str
size_bytes: int
retry_count: int
next_attempt_at: float
created_at: float
```

**SQLite schema migration**: ALTER TABLE RENAME COLUMN (see research.md Decision 4).

### 4. Body Transport Request Payload

**Current payload** (`src/specify_cli/sync/body_transport.py:72-84`):
```json
{
  "project_uuid": "...",
  "feature_slug": "...",
  "target_branch": "...",
  "mission_key": "...",
  "manifest_version": "...",
  "mission_slug": "...",       // compatibility alias for mission_key
  "artifact_path": "...",
  "content_hash": "...",
  "hash_algorithm": "...",
  "content_body": "..."
}
```

**Target payload**:
```json
{
  "project_uuid": "...",
  "mission_slug": "...",
  "target_branch": "...",
  "mission_type": "...",
  "manifest_version": "...",
  "artifact_path": "...",
  "content_hash": "...",
  "hash_algorithm": "...",
  "content_body": "..."
}
```

Removed: `feature_slug`, `mission_key`, `mission_slug` (as alias).
Added: `mission_slug` (as canonical, was feature_slug), `mission_type` (was mission_key).

### 5. Tracker Bind Payload

**Current payload** (`src/specify_cli/cli/commands/tracker.py:355-360`):
```json
{
  "uuid": "...",
  "slug": "...",
  "node_id": "...",
  "repo_slug": "..."
}
```

**Target payload**:
```json
{
  "uuid": "...",
  "slug": "...",
  "node_id": "...",
  "repo_slug": "...",
  "build_id": "..."
}
```

Added: `build_id` from `ProjectIdentity.build_id`.

### 6. Event Envelope

**Current state**: Already includes `build_id` and `schema_version` in emission paths. Verification required that these fields are preserved through all serialization, queue, replay, and reduction paths.

**Required invariants**:
- `aggregate_type` must be `"Mission"`, never `"Feature"`
- `build_id` must be non-null on every emitted envelope
- `schema_version` must be present on every emitted envelope
- Payload fields must use `mission_slug`, `mission_number`, `mission_type`

### 7. Orchestrator API Response Envelope

**Current payload fields** (injected by `with_tracked_mission_slug_aliases()`):
```json
{
  "feature_slug": "064-my-feature",
  "mission_slug": "064-my-feature",
  ...
}
```

**Target payload fields**:
```json
{
  "mission_slug": "064-my-feature",
  ...
}
```

Removed: `feature_slug` (was injected as alias by `identity_aliases.py`).

### 8. StatusSnapshot

**Current**: `to_dict()` calls `with_tracked_mission_slug_aliases()` which injects `feature_slug`.

**Target**: `to_dict()` emits `mission_slug` only. No alias injection.

### 9. meta.json (Mission Metadata)

**Current scaffolded fields**:
```json
{
  "feature_number": "064",
  "feature_slug": "064-complete-mission-identity-cutover",
  "slug": "064-complete-mission-identity-cutover",
  "friendly_name": "Complete Mission Identity Cutover",
  "mission": "software-dev",
  "target_branch": "main",
  "created_at": "2026-04-06T05:01:28+00:00"
}
```

**Target scaffolded fields**:
```json
{
  "mission_number": "064",
  "mission_slug": "064-complete-mission-identity-cutover",
  "slug": "complete-mission-identity-cutover",
  "friendly_name": "Complete Mission Identity Cutover",
  "mission_type": "software-dev",
  "target_branch": "main",
  "created_at": "2026-04-06T05:01:28+00:00"
}
```

**Field mapping**:
| Legacy | Canonical | Notes |
|--------|-----------|-------|
| `feature_number` | `mission_number` | Same value (e.g., "064") |
| `feature_slug` | `mission_slug` | Same value (e.g., "064-complete-mission-identity-cutover") |
| `mission` | `mission_type` | Same value (e.g., "software-dev") |
| `slug` | `slug` | Unchanged |
| `friendly_name` | `friendly_name` | Unchanged |
| `target_branch` | `target_branch` | Unchanged |
| `created_at` | `created_at` | Unchanged |

### 10. Compatibility Gate Schema

**New entity** — validation primitive for remote-facing paths.

**Input**: A dict representing a payload about to be sent to an external service.

**Validation rules** (derived from upstream 3.0.0 contract):
- Must NOT contain `feature_slug` as a key
- Must NOT contain `feature_number` as a key
- Must NOT contain `mission_key` as a key (legacy body sync field)
- Must NOT contain `aggregate_type: "Feature"`
- If event envelope: must contain `build_id` and `schema_version`
- If event payload: must contain `mission_slug`, not `feature_slug`

**Output**: Pass (no-op) or raise `ContractViolationError` with diagnostic message naming the offending field.

## State Transitions

### Body Upload Queue Migration

```
[Legacy Schema]                    [Canonical Schema]
feature_slug TEXT     ─────────►   mission_slug TEXT
mission_key TEXT      ─────────►   mission_type TEXT
(all other columns unchanged)
```

Transition: Single ALTER TABLE operation within a transaction. Existing row data is preserved; column names change but values remain the same (the values were already correct, just the column names were legacy).

### meta.json Migration (upgrade path only)

```
[Legacy meta.json]                 [Canonical meta.json]
feature_number: "064"  ──────────► mission_number: "064"
feature_slug: "064-x"  ─────────► mission_slug: "064-x"
mission: "software-dev" ────────► mission_type: "software-dev"
```

Transition: Read legacy fields, write canonical fields. Preserve all values. Remove legacy keys from the written output. This is migration-only code, not used by normal runtime paths.
