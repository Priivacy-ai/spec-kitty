# Quickstart: Namespace-Aware Artifact Body Sync

**Feature**: 047-namespace-aware-artifact-body-sync

## What This Feature Does

When code paths that emit dossier events for a feature run (e.g., feature-aware sync commands), the CLI now uploads the text content of your feature artifacts to SaaS alongside the existing dossier events. SaaS can then render `spec.md`, `plan.md`, `tasks.md`, and other documents without a separate manual push step.

## How It Works

1. The dossier **indexer** scans `kitty-specs/<feature>/` and produces `ArtifactRef` objects with paths and content hashes
2. The **body sync** phase filters those refs by supported format (`.md`, `.json`, `.yaml`, `.yml`, `.csv`) and supported surfaces (`spec.md`, `plan.md`, `tasks.md`, etc.)
3. Each eligible artifact's content is read, size-checked (≤512 KiB), and uploaded to SaaS with the full namespace tuple
4. If SaaS is offline, uploads are queued to a local SQLite table and replayed automatically on next sync

## What Gets Uploaded

| Surface | Pattern | Example |
|---------|---------|---------|
| Top-level feature files | `spec.md`, `plan.md`, `tasks.md`, `research.md`, `quickstart.md`, `data-model.md` | `kitty-specs/047-feature/spec.md` |
| Research directory | `research/**` | `kitty-specs/047-feature/research/analysis.md` |
| Contract files | `contracts/**` | `kitty-specs/047-feature/contracts/api.yaml` |
| Checklists | `checklists/**` | `kitty-specs/047-feature/checklists/requirements.md` |
| Work package prompts | `tasks/WP*.md` | `kitty-specs/047-feature/tasks/WP01.md` |

## What Gets Skipped

- Binary files (images, PDFs, etc.)
- Files larger than 512 KiB
- Non-UTF-8 files
- Files outside supported surfaces (e.g., `meta.json`, status files)
- Files deleted between index scan and body read

Skipped files are logged with an explicit reason code. Sync does not abort.

## Namespace Isolation

Every upload includes five identity fields:

- `project_uuid` — your project's stable UUID
- `feature_slug` — e.g., `047-namespace-aware-artifact-body-sync`
- `target_branch` — e.g., `2.x`
- `mission_key` — e.g., `software-dev`
- `manifest_version` — the artifact manifest definition version

Two features with the same mission type but different slugs or branches cannot overwrite each other's artifacts on SaaS.

## Offline Behavior

- If SaaS is unreachable, upload tasks are persisted to a local `body_upload_queue` SQLite table
- Tasks survive CLI restarts
- On reconnection, `BackgroundSyncService` drains events first, then body uploads
- Per-task exponential backoff (1s → 5 min cap) prevents tight-loop retry
- `404 index_entry_not_found` is treated as retryable (the remote index may not be materialized yet)
- `404 namespace_not_found` is treated as non-retryable (malformed namespace, surfaced as local failure)

## Diagnostics

Upload results are logged per artifact with one of five statuses:

- `uploaded` — SaaS accepted and stored the body (201)
- `already_exists` — SaaS already has this content (200, idempotent no-op)
- `queued` — SaaS was offline; task saved for later replay
- `skipped` — Artifact not eligible (binary, oversized, non-UTF-8)
- `failed` — Non-retryable error (400 validation, 404 namespace_not_found)

## Key Files

| File | Purpose |
|------|---------|
| `src/specify_cli/sync/dossier_pipeline.py` | Orchestration entrypoint: index, emit events, enqueue bodies |
| `src/specify_cli/sync/body_upload.py` | Body upload preparation (filter, read, re-hash, enqueue) |
| `src/specify_cli/sync/body_queue.py` | `OfflineBodyUploadQueue` (sibling SQLite table) |
| `src/specify_cli/sync/body_transport.py` | HTTP transport to `/api/dossier/push-content/` |
| `src/specify_cli/sync/namespace.py` | `NamespaceRef` dataclass |
| `src/specify_cli/sync/background.py` | `BackgroundSyncService` (extended to drain body queue) |
