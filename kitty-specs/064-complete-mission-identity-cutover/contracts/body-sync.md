# Contract: Body Sync (Post-Cutover)

**Feature**: 064-complete-mission-identity-cutover
**Date**: 2026-04-06

## Upload Request Payload

POST `/api/dossier/push-content/`

```json
{
  "project_uuid": "uuid",
  "mission_slug": "064-my-mission",
  "target_branch": "main",
  "mission_type": "software-dev",
  "manifest_version": "1.0",
  "artifact_path": "kitty-specs/064-my-mission/spec.md",
  "content_hash": "sha256:...",
  "hash_algorithm": "sha256",
  "content_body": "..."
}
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `project_uuid` | string (UUID) | Project identity |
| `mission_slug` | string | Mission instance identifier |
| `target_branch` | string | Target branch for the mission |
| `mission_type` | string | Mission workflow kind |
| `manifest_version` | string | Artifact manifest version |
| `artifact_path` | string | Relative path to artifact |
| `content_hash` | string | Content hash with algorithm prefix |
| `hash_algorithm` | string | Hash algorithm name |
| `content_body` | string | Artifact content |

## Forbidden Fields

| Field | Reason |
|-------|--------|
| `feature_slug` | Legacy; replaced by `mission_slug` |
| `mission_key` | Legacy intermediate field; replaced by `mission_type` |

## NamespaceRef Fields

The `NamespaceRef` dataclass identifies an artifact's position in the project hierarchy:

| Field | Type | Description |
|-------|------|-------------|
| `project_uuid` | string | Project identity |
| `mission_slug` | string | Mission instance identifier |
| `target_branch` | string | Target branch |
| `mission_type` | string | Mission workflow kind |
| `manifest_version` | string | Artifact manifest version |

## Queue Schema (SQLite)

```sql
CREATE TABLE body_upload_queue (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid TEXT NOT NULL,
    mission_slug TEXT NOT NULL,      -- was: feature_slug
    target_branch TEXT NOT NULL,
    mission_type TEXT NOT NULL,       -- was: mission_key
    manifest_version TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    hash_algorithm TEXT NOT NULL,
    content_body TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL NOT NULL,
    created_at REAL NOT NULL
);
```
