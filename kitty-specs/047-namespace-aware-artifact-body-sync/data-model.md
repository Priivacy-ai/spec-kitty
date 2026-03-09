# Data Model: Namespace-Aware Artifact Body Sync

**Feature**: 047-namespace-aware-artifact-body-sync
**Date**: 2026-03-09

## Entities

### NamespaceRef

Canonical sender-side representation of the five-field namespace tuple. Constructed once per sync invocation from project identity, feature metadata, and manifest.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `project_uuid` | `UUID` | `ProjectIdentity.project_uuid` | Stable project identifier from `.kittify/config.yaml` |
| `feature_slug` | `str` | Feature metadata (meta.json or indexer context) | e.g., `047-namespace-aware-artifact-body-sync` |
| `target_branch` | `str` | `meta.json → target_branch` | e.g., `2.x` |
| `mission_key` | `str` | `meta.json → mission` | e.g., `software-dev` |
| `manifest_version` | `str` | `ExpectedArtifactManifest.manifest_version` from `expected-artifacts.yaml` | Versions the artifact-definition set, not the CLI binary |

**Validation rules**:
- All five fields are required and non-empty
- `project_uuid` must be a valid UUID4
- `feature_slug` must match pattern `\d{3}-[a-z0-9-]+`

**Serialization**: JSON object with sorted keys for deterministic hashing.

### ArtifactBodyUploadTask

Durable queued unit persisted to `body_upload_queue` SQLite table. Represents one artifact body awaiting upload to SaaS.

| Field | Type | SQLite Column | Description |
|-------|------|---------------|-------------|
| `id` | `int` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Row ID |
| `upload_id` | `str` | `TEXT UNIQUE NOT NULL` | ULID, unique per task |
| `project_uuid` | `str` | `TEXT NOT NULL` | From NamespaceRef |
| `feature_slug` | `str` | `TEXT NOT NULL` | From NamespaceRef |
| `target_branch` | `str` | `TEXT NOT NULL` | From NamespaceRef |
| `mission_key` | `str` | `TEXT NOT NULL` | From NamespaceRef |
| `manifest_version` | `str` | `TEXT NOT NULL` | From NamespaceRef |
| `artifact_path` | `str` | `TEXT NOT NULL` | Feature-relative path (from ArtifactRef.relative_path) |
| `content_hash` | `str` | `TEXT NOT NULL` | SHA-256 hex (from ArtifactRef.content_hash_sha256) |
| `hash_algorithm` | `str` | `TEXT NOT NULL DEFAULT 'sha256'` | Always `sha256` in v1 |
| `content_body` | `str` | `TEXT NOT NULL` | UTF-8 text content (≤512 KiB) |
| `created_at` | `int` | `INTEGER NOT NULL` | Unix timestamp of enqueue |
| `retry_count` | `int` | `INTEGER DEFAULT 0` | Number of failed attempts |
| `next_attempt_at` | `int` | `INTEGER DEFAULT 0` | Unix timestamp of next eligible retry |
| `last_error` | `str` | `TEXT` | Last error message (nullable) |

**Unique constraint**: `UNIQUE(project_uuid, feature_slug, target_branch, mission_key, manifest_version, artifact_path, content_hash)` — prevents duplicate enqueue of the same content for the same artifact in the same namespace. All five `NamespaceRef` fields are included to ensure a manifest-version change with unchanged file content creates a distinct queued task, preserving namespace isolation.

**Indexes**:
- `idx_body_next_attempt ON body_upload_queue(next_attempt_at)` — for efficient drain ordering
- `idx_body_retry ON body_upload_queue(retry_count)` — for stats and diagnostics

### UploadOutcome

Classified result for one attempted body upload. Not persisted; used as in-memory return value.

| Field | Type | Description |
|-------|------|-------------|
| `upload_id` | `str` | Matches `ArtifactBodyUploadTask.upload_id` |
| `artifact_path` | `str` | Feature-relative path |
| `status` | `str` | One of: `uploaded`, `already_exists`, `queued`, `skipped`, `failed` |
| `reason` | `str` | Human-readable explanation |
| `retryable` | `bool` | Whether the task should be retried |

**Status definitions**:
- `uploaded`: SaaS accepted and stored the body (HTTP 201 `stored`)
- `already_exists`: SaaS already has this content_hash for this artifact (HTTP 200 `already_exists`)
- `queued`: SaaS was unreachable; task persisted to body_upload_queue for later replay
- `skipped`: Artifact was not eligible for upload (binary, oversized, non-UTF-8, deleted after scan)
- `failed`: Non-retryable error (e.g., HTTP 400 validation error, HTTP 404 `namespace_not_found`)

### SupportedInlineFormat

Enumeration of file extensions eligible for inline body upload in v1.

| Extension | MIME Type (informational) |
|-----------|--------------------------|
| `.md` | `text/markdown` |
| `.json` | `application/json` |
| `.yaml` | `text/yaml` |
| `.yml` | `text/yaml` |
| `.csv` | `text/csv` |

### BodyUploadQueueStats

Statistics for the body upload queue, analogous to existing `QueueStats`.

| Field | Type | Description |
|-------|------|-------------|
| `total_queued` | `int` | Total pending upload tasks |
| `total_retried` | `int` | Tasks with retry_count > 0 |
| `oldest_task_age` | `timedelta | None` | Age of oldest pending task |
| `retry_distribution` | `dict[str, int]` | Bucketed retry counts |
| `namespace_distribution` | `dict[str, int]` | Tasks per feature_slug |

## Relationships

```
NamespaceRef (value object)
  ├── constructed from: ProjectIdentity + meta.json + ExpectedArtifactManifest
  └── embedded in: ArtifactBodyUploadTask (5 columns)

ArtifactRef (from Indexer)
  ├── filtered by: SupportedInlineFormat + FR-004 surface patterns + 512 KiB limit
  └── provides: artifact_path, content_hash, size_bytes, is_present

ArtifactBodyUploadTask (persisted in SQLite)
  ├── created from: NamespaceRef + filtered ArtifactRef + file content
  ├── drained by: BackgroundSyncService (after event queue)
  └── produces: UploadOutcome (in-memory)
```

## State Transitions

### ArtifactBodyUploadTask Lifecycle

```
[ArtifactRef scanned]
        │
        ▼
   ┌─────────┐    not supported/oversized/missing
   │ Filter  │────────────────────────────────────► UploadOutcome(skipped)
   └────┬────┘
        │ passes filter
        ▼
   ┌─────────┐    hash mismatch (file changed after scan)
   │ Re-hash │────────────────────────────────────► skip, next sync picks up
   └────┬────┘
        │ hash matches
        ▼
   ┌──────────┐   duplicate unique key
   │ Enqueue  │────────────────────────────────────► no-op (idempotent)
   └────┬─────┘
        │ new task
        ▼
   ┌──────────┐   SaaS online + success
   │ Upload   │────────────────────────────────────► UploadOutcome(uploaded)
   │ attempt  │   SaaS returns already_exists
   │          │────────────────────────────────────► UploadOutcome(already_exists)
   │          │   SaaS offline / 5xx / 429 / 404
   │          │────────────────────────────────────► increment retry, set next_attempt_at
   │          │   HTTP 400 / validation error
   └──────────┘────────────────────────────────────► UploadOutcome(failed), remove from queue
```

## SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS body_upload_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id TEXT UNIQUE NOT NULL,
    project_uuid TEXT NOT NULL,
    feature_slug TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    mission_key TEXT NOT NULL,
    manifest_version TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    hash_algorithm TEXT NOT NULL DEFAULT 'sha256',
    content_body TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    retry_count INTEGER DEFAULT 0,
    next_attempt_at INTEGER DEFAULT 0,
    last_error TEXT,
    UNIQUE(project_uuid, feature_slug, target_branch, mission_key, manifest_version, artifact_path, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_body_next_attempt
    ON body_upload_queue(next_attempt_at);

CREATE INDEX IF NOT EXISTS idx_body_retry
    ON body_upload_queue(retry_count);
```
