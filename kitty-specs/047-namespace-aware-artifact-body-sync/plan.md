# Implementation Plan: Namespace-Aware Artifact Body Sync

**Branch**: `2.x` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)

## Summary

Extend the spec-kitty sync pipeline to upload renderable artifact bodies to SaaS during normal sync. Body uploads consume `ArtifactRef` output from the existing dossier `Indexer`, filter by supported inline formats and size limits, and persist to a sibling `body_upload_queue` SQLite table for durable offline replay. The `BackgroundSyncService` drains events first, then body uploads, preserving the invariant that remote index entries exist before bodies arrive.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, requests, pytest, mypy
**Storage**: SQLite (existing `OfflineQueue` DB file, new sibling table)
**Testing**: pytest with 90%+ coverage for new code, mypy --strict
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+)
**Project Type**: Single (CLI tool)
**Performance Goals**: All supported artifacts uploaded within 10 seconds for a feature with up to 30 artifacts
**Constraints**: 512 KiB per artifact inline limit, 10,000 task queue cap, per-task exponential backoff (1s → 5 min)
**Scale/Scope**: Typical feature has 5-30 text artifacts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Python 3.11+ required | Pass | All new code targets 3.11+ |
| typer CLI framework | Pass | No new CLI commands in v1 (FR-013); body upload is subordinate to existing sync |
| pytest 90%+ coverage | Pass | Required for all new modules |
| mypy --strict | Pass | All new code must pass strict type checking |
| Integration tests for CLI commands | Pass | Integration tests for sync + body upload flow |
| CLI operations < 2 seconds | Pass | Body upload phase is async/background; sync initiation remains fast |
| Cross-platform | Pass | SQLite, requests, pathlib — all cross-platform |
| Git required | Pass | No new git operations introduced |
| 2.x branch (active development) | Pass | This feature targets 2.x |
| Greenfield freedom, no 1.x compat | Pass | No 1.x constraints |
| spec-kitty-events integration | N/A | Body uploads use the sync queue, not the events library directly |
| Mission terminology | Pass | No new user-facing "feature" language introduced; internal code uses `feature_slug` as existing convention |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/047-namespace-aware-artifact-body-sync/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research output
├── data-model.md        # Entity definitions and SQLite schema
├── quickstart.md        # Developer quickstart
├── contracts/
│   └── push-content-api.md  # push_content API contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/sync/
├── namespace.py          # NEW: NamespaceRef dataclass
├── body_queue.py         # NEW: OfflineBodyUploadQueue (sibling SQLite table)
├── body_upload.py        # NEW: Body upload orchestration (filter, read, enqueue)
├── body_transport.py     # NEW: HTTP transport to push_content endpoint
├── queue.py              # MODIFIED: Shared DB infrastructure, schema migration
├── background.py         # MODIFIED: Drain body_upload_queue after event queue
├── emitter.py            # UNCHANGED (body uploads bypass the event emitter)
├── batch.py              # UNCHANGED (body uploads use body_transport, not batch)
├── client.py             # UNCHANGED
├── auth.py               # UNCHANGED (reused by body_transport)
├── runtime.py            # MODIFIED: Wire body queue into SyncRuntime lifecycle
├── config.py             # UNCHANGED
├── project_identity.py   # UNCHANGED (consumed by NamespaceRef construction)
├── diagnose.py           # MODIFIED: Add body upload queue diagnostics
└── events.py             # UNCHANGED

src/specify_cli/dossier/
├── indexer.py            # UNCHANGED (body sync consumes ArtifactRef output)
├── models.py             # UNCHANGED (ArtifactRef is the input interface)
└── ...                   # UNCHANGED

tests/specify_cli/sync/
├── test_namespace.py         # NEW: NamespaceRef construction and validation
├── test_body_queue.py        # NEW: OfflineBodyUploadQueue CRUD, idempotent enqueue
├── test_body_upload.py       # NEW: Filter logic, re-hash guard, integration
├── test_body_transport.py    # NEW: HTTP transport, response classification
├── test_background_body.py   # NEW: BackgroundSyncService body drain ordering
└── test_body_integration.py  # NEW: End-to-end sync + body upload flow
```

**Structure Decision**: All new code lives in `src/specify_cli/sync/` as four new modules plus modifications to three existing modules. No new subpackages. This follows the existing flat structure of the sync package.

## Architecture

### Data Flow

```
Indexer.index_feature()
    │
    ▼
MissionDossier.artifacts: List[ArtifactRef]
    │
    ├──► emit_artifact_indexed() (existing, unchanged)
    │        ▼
    │    EventEmitter → OfflineQueue (event queue)
    │        ▼
    │    BackgroundSyncService → batch_sync() → /api/v1/events/batch/
    │
    └──► body_upload.prepare_body_uploads()  ◄── NEW
             │
             ├── Filter by FR-004 surfaces + FR-005 formats
             ├── Filter by 512 KiB size limit
             ├── Read content, re-hash, compare to ArtifactRef.content_hash
             ├── Skip on mismatch (file changed after scan)
             │
             ▼
         OfflineBodyUploadQueue.enqueue()  ◄── NEW
             │
             ▼
         BackgroundSyncService (drains body queue AFTER event queue)
             │
             ▼
         body_transport.push_content()  ◄── NEW
             │
             ▼
         POST /api/v1/content/push/
             │
             ├── 200 uploaded      → remove from queue
             ├── 200 already_exists → remove from queue
             ├── 400 bad request   → remove from queue (failed)
             ├── 401 unauthorized  → keep (auth refresh)
             ├── 404 not found     → keep, retry (index not materialized)
             ├── 429 rate limited  → keep, retry with backoff
             └── 5xx server error  → keep, retry with backoff
```

### Module Responsibilities

| Module | Responsibility | Dependencies |
|--------|---------------|--------------|
| `namespace.py` | `NamespaceRef` dataclass, construction from `ProjectIdentity` + feature metadata + manifest | `project_identity.py`, `dossier/manifest.py` |
| `body_queue.py` | `OfflineBodyUploadQueue`: SQLite CRUD for `body_upload_queue` table, drain with backoff filtering, stats | `queue.py` (shared DB connection) |
| `body_upload.py` | `prepare_body_uploads()`: filter `ArtifactRef` list, read content, re-hash guard, enqueue via `OfflineBodyUploadQueue` | `body_queue.py`, `namespace.py`, `dossier/models.py` |
| `body_transport.py` | `push_content()`: HTTP POST to SaaS, response classification into `UploadOutcome` | `auth.py`, `requests` |
| `background.py` (mod) | Extended `_sync_once()` to drain `body_upload_queue` after event queue | `body_queue.py`, `body_transport.py` |
| `runtime.py` (mod) | Wire `OfflineBodyUploadQueue` into `SyncRuntime` lifecycle | `body_queue.py` |
| `diagnose.py` (mod) | Body upload queue stats and inspection | `body_queue.py` |

### Key Design Decisions

1. **No event emitter involvement**: Body uploads bypass `EventEmitter` entirely. They are not events in the causal ordering sense — they are content payloads. The event queue handles dossier index events; the body queue handles content delivery. Different concerns, different tables, different transport.

2. **Indexer output as sole input**: Body sync never touches the filesystem directly for artifact discovery. It filters `ArtifactRef` objects from the indexer. The only filesystem access is reading `content_body` for artifacts that pass filtering. This satisfies FR-014 (path form agreement) by construction.

3. **Re-hash guard before enqueue**: After reading file content, the body uploader computes SHA-256 and compares to `ArtifactRef.content_hash_sha256`. On mismatch, the artifact is skipped (file changed between index scan and body read). The next sync cycle will re-index and pick it up with a fresh hash.

4. **Per-task backoff via `next_attempt_at`**: Unlike the event queue (global retry count, timer-based backoff), the body queue stores a per-task `next_attempt_at` timestamp. The drain query filters `WHERE next_attempt_at <= now()`. This prevents a single failing task from blocking the entire queue.

5. **Drain ordering**: Events drain before body uploads. This maximizes the chance that the remote dossier index is materialized before body uploads arrive, reducing 404 `index_entry_not_found` retries.

6. **Idempotent enqueue**: The unique constraint `(project_uuid, feature_slug, target_branch, artifact_path, content_hash)` prevents duplicate tasks for the same content in the same namespace. Changed content (new hash) creates a new task; the old task (if still queued) becomes stale and will get `already_exists` or a new hash replaces it.

7. **No local remote-state cache**: The client always submits. The server returns `already_exists` for content it already has. No client-side pre-skip logic that could go stale.

## Complexity Tracking

No constitution violations. No complexity tracking needed.
