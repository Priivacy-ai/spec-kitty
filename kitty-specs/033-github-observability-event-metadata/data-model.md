# Data Model: GitHub Observability Event Metadata

**Feature**: 033-github-observability-event-metadata
**Date**: 2026-02-07

## Entities

### GitMetadata (Value Object)

Volatile git state resolved per-event. Not persisted.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `git_branch` | `str \| None` | Current branch name. `"HEAD"` if detached. `None` if not in git repo. | `"2.x"`, `"033-feature-WP01"`, `"HEAD"` |
| `head_commit_sha` | `str \| None` | Full 40-char SHA of HEAD. `None` if not in git repo. | `"68b09b04a1b..."` |
| `repo_slug` | `str \| None` | `owner/repo` from origin remote or config override. `None` if no remote. | `"Priivacy-ai/spec-kitty"` |

**Resolution lifecycle**: Created fresh on each `resolve()` call (subject to 2s TTL cache).

### GitMetadataResolver (Service)

Stateful resolver with TTL cache. One instance per `EventEmitter`.

| Field | Type | Description |
|-------|------|-------------|
| `repo_root` | `Path` | Repository root for subprocess cwd |
| `_cached_branch` | `str \| None` | Cached branch name |
| `_cached_sha` | `str \| None` | Cached HEAD SHA |
| `_cached_repo_slug` | `str \| None` | Cached repo slug (session-level, no TTL) |
| `_cache_time` | `float` | `time.monotonic()` of last branch/SHA resolution |
| `_repo_slug_override` | `str \| None` | Override from config.yaml (validated) |
| `_repo_slug_resolved` | `bool` | Whether repo slug has been resolved this session |
| `ttl` | `float` | Cache TTL in seconds (default: 2.0) |

**Methods**:
- `resolve() -> GitMetadata`: Return current git state (from cache or subprocess)
- `_resolve_branch_and_sha() -> tuple[str | None, str | None]`: Subprocess call
- `_resolve_repo_slug() -> str | None`: Config override > auto-derived > None
- `_derive_repo_slug_from_remote() -> str | None`: Parse origin remote URL
- `_validate_repo_slug(slug: str) -> bool`: Check `owner/repo` format

### ProjectIdentity (Extended)

Existing entity with one new optional field.

| Field | Type | Status | Description |
|-------|------|--------|-------------|
| `project_uuid` | `UUID \| None` | Existing | UUID4 project identifier |
| `project_slug` | `str \| None` | Existing | Kebab-case project name |
| `node_id` | `str \| None` | Existing | 12-char hex machine ID |
| `repo_slug` | `str \| None` | **NEW** | `owner/repo` override from config |

**Persistence**: `repo_slug` stored in `.kittify/config.yaml` under `project.repo_slug`.

### EventEnvelope (Extended)

Existing envelope with three new optional fields.

| Field | Type | Status | Source |
|-------|------|--------|--------|
| `event_id` | `str` | Existing | ULID generator |
| `event_type` | `str` | Existing | Event builder |
| `aggregate_id` | `str` | Existing | Event builder |
| `aggregate_type` | `str` | Existing | Event builder |
| `payload` | `dict` | Existing | Event builder |
| `timestamp` | `str` | Existing | `datetime.now(UTC)` |
| `node_id` | `str` | Existing | LamportClock |
| `lamport_clock` | `int` | Existing | LamportClock.tick() |
| `causation_id` | `str \| None` | Existing | Caller-provided |
| `team_slug` | `str` | Existing | AuthClient |
| `project_uuid` | `str \| None` | Existing | ProjectIdentity |
| `project_slug` | `str \| None` | Existing | ProjectIdentity |
| `git_branch` | `str \| None` | **NEW** | GitMetadataResolver |
| `head_commit_sha` | `str \| None` | **NEW** | GitMetadataResolver |
| `repo_slug` | `str \| None` | **NEW** | GitMetadataResolver |

## State Transitions

### GitMetadata Cache States

```
COLD (no cache)
  │
  ├─ resolve() called ──→ WARM (branch, sha, repo_slug cached)
  │                           │
  │                           ├─ resolve() within 2s TTL ──→ WARM (cache hit)
  │                           │
  │                           └─ resolve() after 2s TTL ──→ WARM (cache refreshed)
  │
  └─ git unavailable ──→ COLD (None values returned, no cache stored)
```

### Repo Slug Resolution States

```
UNRESOLVED
  │
  ├─ config override present + valid ──→ RESOLVED (override value)
  │
  ├─ config override present + invalid ──→ WARN + try auto-derive
  │                                           │
  │                                           ├─ origin remote exists ──→ RESOLVED (auto-derived)
  │                                           │
  │                                           └─ no origin remote ──→ RESOLVED (None)
  │
  ├─ no config override + origin remote ──→ RESOLVED (auto-derived)
  │
  └─ no config override + no remote ──→ RESOLVED (None)
```

## Config Schema Extension

```yaml
# .kittify/config.yaml
project:
  uuid: "550e8400-e29b-41d4-a716-446655440000"
  slug: "spec-kitty"
  node_id: "abc123def456"
  repo_slug: "Priivacy-ai/spec-kitty"  # NEW: optional override
```

**Backward compatibility**: Missing `repo_slug` key treated as `None` (auto-derive from remote). Existing config files work unchanged.
