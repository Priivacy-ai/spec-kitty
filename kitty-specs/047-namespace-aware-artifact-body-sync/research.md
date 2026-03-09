# Research: Namespace-Aware Artifact Body Sync

**Feature**: 047-namespace-aware-artifact-body-sync
**Date**: 2026-03-09
**Status**: Complete

## R1: Queue Schema Strategy for Body Uploads

**Decision**: Sibling `body_upload_queue` table in the same SQLite DB file.

**Rationale**: The existing `queue` table schema (`event_id`, `event_type`, `data`, `timestamp`, `retry_count`) is shaped for dossier events. Body upload tasks have different identity (namespace + artifact_path + content_hash), larger payloads (content_body up to 512 KiB), different transport (push_content endpoint, not batch events), and per-task backoff state (next_attempt_at). Mixing these into a polymorphic table would leak complexity into queue stats, drain ordering, retry semantics, and batch replay code that currently assumes everything in the queue is an event.

**Alternatives considered**:
- **(A) Extend existing queue table**: Rejected. Forces polymorphic catch-all, breaks event-shaped assumptions in `drain_queue()`, `process_batch_results()`, and `batch_sync()`.
- **(B) Separate SQLite DB file**: Over-engineered. Two files means two connection pools, two scope-aware path calculations, and more complex cleanup.

**Implementation shape**:
- Split storage classes: `OfflineEventQueue` (existing, renamed conceptually) and `OfflineBodyUploadQueue` (new).
- Single higher-level facade for shared concerns (scope-aware DB path, connection management).
- `BackgroundSyncService` drains events first, body uploads second (ordering matters because body uploads depend on remote index materialization).

## R2: Indexer Integration — ArtifactRef as Source of Truth

**Decision**: Body sync consumes `ArtifactRef` output from `Indexer.index_feature()` directly. No independent filesystem scan.

**Rationale**: The indexer is already the authoritative source for artifact identity (`relative_path`), classification (`artifact_class`), content hash (`content_hash_sha256`), and presence (`is_present`). FR-014 requires path form agreement between body uploader and indexer. An independent scan would duplicate filesystem walking and risk the exact path/hash divergence FR-014 is designed to prevent.

**Alternatives considered**:
- **(B) Independent scan with FR-004 globs**: Rejected. Duplicates work, risks divergence, creates the class of bugs FR-014 exists to prevent.

**Key findings from indexer analysis**:
- `Indexer.index_feature()` returns `MissionDossier` containing `artifacts: List[ArtifactRef]`
- `ArtifactRef.relative_path` is feature-relative (e.g., `spec.md`, `tasks/WP01.md`)
- `ArtifactRef.content_hash_sha256` is SHA-256
- `ArtifactRef.is_present` indicates whether file exists and is readable
- `ArtifactRef.size_bytes` provides size for limit checks
- `ArtifactRef.error_reason` provides skip diagnostics for unreadable files

**Race condition guard**: If a file changes between indexing and body read, the body uploader must re-hash and compare before enqueue. On mismatch, skip and let the next sync cycle pick it up with fresh indexer output.

## R3: Sync Pipeline Integration Point

**Decision**: Body upload preparation runs in an explicit dossier-sync orchestration function (`dossier_pipeline.sync_feature_dossier()`), not in `BackgroundSyncService` and not via a vague "any command that triggers sync" hook.

**Key finding**: The indexer exists but is **not yet called by the sync pipeline**. There is no module in `src/specify_cli/sync/` that invokes `index_feature()`. Dossier event emission happens via `dossier/events.py` functions (`emit_artifact_indexed()` etc.) which call into `sync/emitter.py` directly.

**Why a dedicated orchestration function**:
- Indexing and body enqueue are feature-context work — they require a concrete `feature_dir` and `namespace_ref`
- `BackgroundSyncService` has no reliable "active feature" concept — it only drains already-enqueued work
- Keeping index + event emit + body enqueue in one orchestration preserves path/hash consistency within a single scan

**Orchestration shape** (`dossier_pipeline.sync_feature_dossier()`):
1. Call `Indexer.index_feature(feature_dir, mission_type, step_id)`
2. Emit dossier events from the resulting `MissionDossier`
3. Call `prepare_body_uploads(dossier.artifacts, namespace_ref, ...)`

**Invocation**: Only from code paths that already own dossier emission for a concrete feature directory (feature-aware sync commands). `BackgroundSyncService` remains replay-only: it drains queues, it does not discover artifacts.

## R4: Transport Endpoint for Body Uploads

**Decision**: Body uploads use the SaaS receiver's canonical route `POST /api/dossier/push-content/`, not the existing batch event endpoint (`/api/v1/events/batch/`).

**Rationale**: The existing batch endpoint expects event-shaped payloads (event_id, event_type, aggregate_id, etc.) with gzip compression. Body uploads carry namespace tuple + artifact identity + content body — structurally different. The receiver owns the route contract; the sender targets the canonical route only with no client-side route configuration.

**Transport details**:
- Endpoint: `POST /api/dossier/push-content/` (canonical, owned by SaaS receiver)
- Auth: Same `Bearer` token from `AuthClient` (C-002)
- Payload: JSON with namespace fields + artifact_path + content_hash + hash_algorithm + content_body
- Success: `stored` (201) | `already_exists` (200)
- Retryable failures: `index_entry_not_found` (404), 5xx, 429
- Non-retryable failures: `namespace_not_found` (404), 400 validation error
- No gzip in v1 (bodies are ≤512 KiB; revisit if needed)

**Critical 404 dispatch**: The client MUST inspect the response body `error` field to distinguish retryable `index_entry_not_found` from non-retryable `namespace_not_found`. A bare 404 without a parseable error field defaults to retryable (conservative).

## R5: LocalNamespaceTuple Status

**Decision**: `LocalNamespaceTuple` does not exist in the codebase. The `NamespaceRef` entity from the spec is a new dataclass to create.

**Key finding**: The spec references `LocalNamespaceTuple` as if it exists, but search confirms no such type in `src/specify_cli/dossier/` or anywhere in the codebase. The closest equivalent is the identity fields injected by `EventEmitter._emit()`: `project_uuid`, `project_slug`, `git_branch`, `team_slug`. These are event-level fields, not a reusable namespace tuple.

**Implementation**: Create a `NamespaceRef` dataclass (or Pydantic model) in a new `src/specify_cli/sync/namespace.py` module with the five canonical fields: `project_uuid`, `feature_slug`, `target_branch`, `mission_key`, `manifest_version`. This is constructed once per sync invocation from `ProjectIdentity` + feature metadata + manifest.

## R6: Inline Size Limit

**Decision**: 512 KiB per artifact, measured as UTF-8 encoded byte length of `content_body` before enqueue. Code constant in v1, not user-configurable.

**Rationale**: 1 MB is too generous for queue-backed storage (worst-case 10,000 × 1 MB = 10 GB queue). 256 KB is too tight for legitimate large research or contract documents. 512 KiB provides headroom for normal spec artifacts while bounding queue growth to a reasonable worst case (~5 GB, which is still extreme but bounded).

## R7: Supported Artifact Surfaces and Format Filtering

**Decision**: Body sync uploads artifacts matching FR-004 surface patterns AND FR-005 format extensions.

**Two-stage filter**:
1. **Surface filter**: `ArtifactRef.relative_path` must match one of: `spec.md`, `plan.md`, `tasks.md`, `research.md`, `quickstart.md`, `data-model.md`, `research/**`, `contracts/**`, `checklists/**`, `tasks/WP*.md`
2. **Format filter**: File extension must be `.md`, `.json`, `.yaml`, `.yml`, or `.csv`

**Note**: The indexer may return artifacts outside FR-004 surfaces (e.g., `meta.json`, status files, event logs). These are not uploaded. The surface filter is the gate, not the indexer's artifact classification.
