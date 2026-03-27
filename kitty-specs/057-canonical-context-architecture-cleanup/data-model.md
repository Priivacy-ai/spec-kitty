# Data Model: Canonical Context Architecture Cleanup

**Feature**: 057-canonical-context-architecture-cleanup
**Date**: 2026-03-27

## Entity Overview

```
ProjectIdentity (1) ──────────< MissionIdentity (many)
                                      │
                                      ├──────< WorkPackage (many)
                                      │              │
                                      │              ├── OwnershipManifest (1:1)
                                      │              └── StatusEvent (many) ──▶ StatusSnapshot (derived)
                                      │
                                      ├──────< MissionContext (many, ephemeral)
                                      │
                                      └──────< MergeState (0..1, ephemeral)
```

---

## Core Entities

### ProjectIdentity

Singleton per repository. Assigned at `spec-kitty init`, never changes.

| Field | Type | Description |
|-------|------|-------------|
| `project_uuid` | `str` (ULID) | Immutable project identity |
| `schema_version` | `int` | Monotonically increasing schema version |
| `schema_capabilities` | `list[str]` | Declared capabilities for forward-compat checks |
| `initialized_at` | `str` (ISO 8601) | When project was initialized |
| `last_upgraded_at` | `str` (ISO 8601)` | When last migration ran |

**Storage**: `.kittify/metadata.yaml` (tracked)

```yaml
spec_kitty:
  version: "3.0.0"
  schema_version: 3
  schema_capabilities:
    - canonical_context
    - event_log_authority
    - ownership_manifest
    - thin_shims
  project_uuid: "01HVXYZ..."
  initialized_at: "2026-01-01T00:00:00+00:00"
  last_upgraded_at: "2026-03-27T16:00:00+00:00"
```

---

### MissionIdentity

One per feature/mission. Assigned at `create-feature` time. Stored in `meta.json`.

| Field | Type | Description |
|-------|------|-------------|
| `mission_id` | `str` (ULID) | Immutable mission identity |
| `feature_number` | `str` | Display number (e.g., "057") |
| `slug` | `str` | Kebab-case slug (e.g., "canonical-context-architecture-cleanup") |
| `feature_slug` | `str` | Full slug with number (e.g., "057-canonical-context-architecture-cleanup") |
| `friendly_name` | `str` | Human-readable title |
| `mission` | `str` | Mission type (e.g., "software-dev", "research") |
| `target_branch` | `str` | Branch for final merge |
| `vcs` | `str` | Version control system (e.g., "git") |
| `created_at` | `str` (ISO 8601) | Creation timestamp |

**Storage**: `kitty-specs/<feature_slug>/meta.json` (tracked)

```json
{
  "mission_id": "01HVXYZ...",
  "feature_number": "057",
  "slug": "canonical-context-architecture-cleanup",
  "feature_slug": "057-canonical-context-architecture-cleanup",
  "friendly_name": "Canonical Context Architecture Cleanup",
  "mission": "software-dev",
  "target_branch": "main",
  "vcs": "git",
  "created_at": "2026-03-27T16:49:52+00:00"
}
```

---

### WorkPackage

One per work package. Identity assigned at task finalization.

| Field | Type | Description |
|-------|------|-------------|
| `work_package_id` | `str` (ULID) | Immutable internal identity |
| `wp_code` | `str` | Display alias (e.g., "WP03") |
| `mission_id` | `str` (ULID) | Parent mission reference |
| `title` | `str` | Human-readable WP title |
| `dependencies` | `list[str]` | List of `wp_code` values this WP depends on |
| `execution_mode` | `str` | `"code_change"` or `"planning_artifact"` |
| `owned_files` | `list[str]` | Glob patterns for files this WP owns |
| `authoritative_surface` | `str` | Path prefix for this WP's canonical location |

**Storage**: `kitty-specs/<feature_slug>/tasks/<wp_code>.md` YAML frontmatter (tracked)

All fields are **static metadata** — set at task finalization, never modified by runtime. No mutable status fields exist in frontmatter.

```yaml
---
work_package_id: "01HVXYZ..."
wp_code: "WP03"
mission_id: "01HVXYZ..."
title: "Implement MissionContext resolver"
dependencies: ["WP01", "WP02"]
execution_mode: code_change
owned_files:
  - "src/specify_cli/context/**"
  - "tests/specify_cli/context/**"
authoritative_surface: "src/specify_cli/context/"
---

## Description
[Human-authored WP description and subtask list]
```

### Ownership Manifest (embedded in WorkPackage)

Not a separate entity — these are the `execution_mode`, `owned_files`, and `authoritative_surface` fields on WorkPackage.

**Validation rules**:
- No two WPs within a mission may have overlapping `owned_files` globs
- `authoritative_surface` must be a prefix of at least one `owned_files` entry
- `execution_mode` must be one of: `code_change`, `planning_artifact`
- `planning_artifact` WPs must have `owned_files` that include only `kitty-specs/` paths or documentation paths

---

### MissionContext

Ephemeral bound-identity object. Created by context resolution, consumed by workflow commands.

| Field | Type | Description |
|-------|------|-------------|
| `token` | `str` | Opaque ULID-based token (e.g., "ctx-01HVXYZ...") |
| `project_uuid` | `str` (ULID) | From ProjectIdentity |
| `mission_id` | `str` (ULID) | From MissionIdentity |
| `work_package_id` | `str` (ULID) | From WorkPackage |
| `wp_code` | `str` | Display alias |
| `feature_slug` | `str` | Display alias for mission |
| `target_branch` | `str` | From MissionIdentity |
| `authoritative_repo` | `str` (path) | Absolute path to repo root |
| `authoritative_ref` | `str` | Git ref (branch name) for this WP |
| `owned_files` | `list[str]` | From WorkPackage ownership manifest |
| `execution_mode` | `str` | From WorkPackage |
| `dependency_mode` | `str` | "independent" or "chained" |
| `completion_commands` | `list[str]` | CLI commands to run on WP completion |
| `created_at` | `str` (ISO 8601) | When context was resolved |
| `created_by` | `str` | Agent name that created this context |

**Storage**: `.kittify/runtime/contexts/<token>.json` (gitignored, ephemeral)

```json
{
  "token": "ctx-01HVXYZ...",
  "project_uuid": "01HVXYZ...",
  "mission_id": "01HVXYZ...",
  "work_package_id": "01HVXYZ...",
  "wp_code": "WP03",
  "feature_slug": "057-canonical-context-architecture-cleanup",
  "target_branch": "main",
  "authoritative_repo": "/Users/robert/tmp/big-refactor/spec-kitty",
  "authoritative_ref": "057-canonical-context-architecture-cleanup-WP03",
  "owned_files": ["src/specify_cli/context/**", "tests/specify_cli/context/**"],
  "execution_mode": "code_change",
  "dependency_mode": "chained",
  "completion_commands": ["spec-kitty agent tasks move-task --to for_review"],
  "created_at": "2026-03-27T17:00:00+00:00",
  "created_by": "claude"
}
```

---

### StatusEvent

Immutable event in the append-only log. Existing model preserved with identity fields added.

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `str` (ULID) | Unique event identity |
| `mission_id` | `str` (ULID) | Parent mission (NEW) |
| `work_package_id` | `str` (ULID) | Internal WP identity (NEW) |
| `wp_id` | `str` | Display alias (wp_code) for backward compat in log format |
| `feature_slug` | `str` | Display alias |
| `from_lane` | `str` | Source lane |
| `to_lane` | `str` | Destination lane |
| `at` | `str` (ISO 8601) | Event timestamp |
| `actor` | `str` | Who caused the transition |
| `force` | `bool` | Whether transition was forced |
| `execution_mode` | `str` | WP execution mode at time of event |
| `evidence` | `DoneEvidence \| null` | Required for `done` transitions |
| `reason` | `str \| null` | Human-readable reason |
| `review_ref` | `str \| null` | Reference to review artifact |

**Storage**: `kitty-specs/<feature_slug>/status.events.jsonl` (tracked, append-only)

---

### StatusSnapshot (derived)

Materialized from event log via deterministic `reduce()`. Never read as authoritative input.

| Field | Type | Description |
|-------|------|-------------|
| `mission_id` | `str` (ULID) | Parent mission |
| `work_packages` | `dict[str, WPSnapshot]` | Keyed by `work_package_id` |
| `summary` | `dict[str, int]` | Count per lane |
| `weighted_progress` | `float` | 0.0 to 100.0 |
| `last_event_id` | `str` | Most recent event processed |
| `event_count` | `int` | Total events processed |
| `materialized_at` | `str` (ISO 8601) | When snapshot was generated |

**Storage**: `.kittify/derived/<feature_slug>/status.json` (gitignored, regenerable)

---

### MergeState (ephemeral)

Persisted resume state for merge operations. Scoped per mission.

| Field | Type | Description |
|-------|------|-------------|
| `mission_id` | `str` (ULID) | Mission being merged |
| `feature_slug` | `str` | Display alias |
| `target_branch` | `str` | Branch being merged into |
| `wp_order` | `list[str]` | Ordered WP IDs (work_package_id) to merge |
| `completed_wps` | `list[str]` | WPs successfully merged |
| `current_wp` | `str \| null` | WP currently being merged |
| `has_pending_conflicts` | `bool` | Whether conflicts need resolution |
| `strategy` | `str` | "merge", "squash", or "rebase" |
| `workspace_path` | `str` | Path to merge worktree |
| `started_at` | `str` (ISO 8601) | When merge began |
| `updated_at` | `str` (ISO 8601) | Last state update |

**Storage**: `.kittify/runtime/merge/<mission_id>/state.json` (gitignored, ephemeral)

---

### AgentShim

Template for generated agent command files. Not a persisted entity — the generator produces files from this model.

| Field | Type | Description |
|-------|------|-------------|
| `command_name` | `str` | Slash command name (e.g., "spec-kitty.implement") |
| `cli_command` | `str` | Full CLI command (e.g., "spec-kitty agent shim implement") |
| `agent_name` | `str` | Agent identifier (e.g., "claude", "codex") |
| `is_consumer_facing` | `bool` | Whether this skill appears in consumer installs |

**Storage**: Generated into agent command directories (e.g., `.claude/commands/spec-kitty.implement.md`). Not persisted as data.

---

## State Transitions

### Lane State Machine (unchanged from current)

```
planned → claimed → in_progress → for_review → approved → done
                                                          ↑
                                        (force required to leave done)

blocked ← (reachable from: planned, claimed, in_progress, for_review)
canceled ← (reachable from: all non-done, non-canceled lanes)
```

Alias: `doing` → `in_progress` (resolved at input boundaries, never persisted).

Terminal lanes: `done`, `canceled` (force required to leave).

### MissionContext Lifecycle

```
[raw args from agent]
        │
        ▼
  resolve() ──▶ MissionContext ──▶ persist to .kittify/runtime/contexts/<token>.json
        │                                       │
        ▼                                       ▼
  return token ◀─────────────── lookup by token on subsequent commands
        │
        ▼
  [context expires when WP reaches done/canceled, or on explicit invalidation]
```

### Merge State Machine

```
  IDLE ──▶ PREFLIGHT ──▶ MERGING ──▶ RECONCILING ──▶ COMPLETE
                │              │              │
                ▼              ▼              ▼
             FAILED     CONFLICT_PAUSED    FAILED
                              │
                              ▼
                          RESUMED ──▶ MERGING (continue)
```

---

## Tracked vs Derived Boundary (Definitive)

### Tracked (committed to git)

| Artifact | Location | Authority |
|----------|----------|-----------|
| Human-authored specs, plans, tasks | `kitty-specs/<slug>/*.md` | Human |
| WP frontmatter (static metadata only) | `kitty-specs/<slug>/tasks/*.md` | Task finalization |
| Mission identity | `kitty-specs/<slug>/meta.json` | `create-feature` |
| Canonical event log | `kitty-specs/<slug>/status.events.jsonl` | `emit_status_transition()` |
| Project identity | `.kittify/metadata.yaml` | `spec-kitty init` / `upgrade` |
| Agent configuration | `.kittify/config.yaml` | `spec-kitty agent config` |
| Skills manifest | `.kittify/skills-manifest.json` | `spec-kitty upgrade` |
| Constitution | `.kittify/constitution/constitution.md` | `spec-kitty constitution` |

### Derived (gitignored, regenerable)

| Artifact | Location | Generated from |
|----------|----------|---------------|
| Status snapshot | `.kittify/derived/<slug>/status.json` | Event log via `reduce()` |
| Board summary | `.kittify/derived/<slug>/board-summary.json` | Event log via `reduce()` |
| Weighted progress | `.kittify/derived/<slug>/progress.json` | Event log via `progress.py` |
| Dossier snapshots | `.kittify/derived/dossiers/` | Mission artifacts |
| Generated prompt surfaces | `.kittify/derived/prompt-surfaces/` | Shim templates |
| Cached manifests | `.kittify/derived/manifests/` | WP frontmatter |

### Runtime (gitignored, ephemeral)

| Artifact | Location | Purpose |
|----------|----------|---------|
| Context tokens | `.kittify/runtime/contexts/<token>.json` | Bound identity for agent sessions |
| Merge workspace | `.kittify/runtime/merge/<mid>/workspace/` | Git worktree for merge operations |
| Merge state | `.kittify/runtime/merge/<mid>/state.json` | Resume state for interrupted merges |
| Merge lock | `.kittify/runtime/merge/<mid>/lock` | Prevent concurrent merges |
| WP workspace contexts | `.kittify/runtime/workspaces/<slug>-<wp>.json` | Runtime WP workspace state |
| Operation locks | `.kittify/runtime/locks/` | General operation locks |
