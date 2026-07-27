# Data Model: ~/.kittify Runtime Centralization

**Feature**: 036-kittify-runtime-centralization
**Date**: 2026-02-09

## Entities

### GlobalRuntime

Represents the user-global `~/.kittify/` directory and its state.

| Field | Type | Description |
|-------|------|-------------|
| home_path | Path | Absolute path to `~/.kittify/` (or override) |
| version | str | CLI version string from `cache/version.lock` |
| managed_dirs | list[str] | Package-managed directory names (software-dev, research, etc.) |
| managed_files | list[str] | Package-managed file names (AGENTS.md) |
| user_dirs | list[str] | User-owned directory names (custom/) |
| user_files | list[str] | User-owned file names (config.yaml) |

**Invariants**:
- `version` matches CLI version after `ensure_runtime()` completes
- `managed_dirs` are fully overwritten on update
- `user_dirs` and `user_files` are never modified by updates

### VersionLock

Represents the state of `~/.kittify/cache/version.lock`.

| Field | Type | Description |
|-------|------|-------------|
| version | str | CLI version string written after successful update |
| path | Path | Absolute path to the lock file |

**States**:
- **Missing**: `~/.kittify/` not yet populated or interrupted update → trigger full bootstrap
- **Stale**: Version does not match current CLI → trigger update with file lock
- **Current**: Version matches CLI → fast path return

### ResolutionTier

Enum representing the four resolution tiers.

| Value | Priority | Location | Description |
|-------|----------|----------|-------------|
| OVERRIDE | 1 (highest) | `.kittify/overrides/{type}/{name}` | Explicit project customization |
| LEGACY | 2 | `.kittify/{type}/{name}` | Pre-centralization project assets (deprecation window) |
| GLOBAL | 3 | `~/.kittify/missions/{mission}/{type}/{name}` | User-global shared assets |
| PACKAGE_DEFAULT | 4 (lowest) | `PACKAGE_DIR/defaults/{type}/{name}` | Bootstrap before first `ensure_runtime()` |

### AssetDisposition

Represents the classification of a file during `spec-kitty migrate`.

| Value | Action | Condition |
|-------|--------|-----------|
| IDENTICAL | Remove | File is byte-identical to global version |
| CUSTOMIZED | Move to overrides | File differs from global version |
| PROJECT_SPECIFIC | Keep | File is at a project-specific path (config, metadata, memory, etc.) |
| UNKNOWN | Keep + warn | File not in any known category |

### ResolutionResult

Return type from the 4-tier resolver.

| Field | Type | Description |
|-------|------|-------------|
| path | Path | Absolute path to the resolved file |
| tier | ResolutionTier | Which tier resolved the file |
| mission | str | Mission context used for resolution (if applicable) |

### MigrationReport

Return type from `spec-kitty migrate`.

| Field | Type | Description |
|-------|------|-------------|
| removed | list[Path] | Files removed (identical to global) |
| moved | list[tuple[Path, Path]] | Files moved (from, to) to overrides |
| kept | list[Path] | Files kept (project-specific) |
| unknown | list[Path] | Files kept with warnings |
| dry_run | bool | Whether this was a dry-run |

### DoctorCheck

Individual health check result for `spec-kitty doctor`.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Check name (e.g., "global_runtime_exists") |
| passed | bool | Whether the check passed |
| message | str | Human-readable result message |
| severity | str | "error", "warning", or "info" |

## Relationships

```
GlobalRuntime 1──* MissionDirectory (managed or user-custom)
GlobalRuntime 1──1 VersionLock
ResolutionTier 1──* ResolutionResult (one result per resolution)
MigrationReport 1──* AssetDisposition (one per classified file)
DoctorReport 1──* DoctorCheck (one per health check)
```

## State Transitions

### VersionLock States

```
MISSING ──(ensure_runtime)──> CURRENT
STALE   ──(ensure_runtime)──> CURRENT
CURRENT ──(pip upgrade)──> STALE
CURRENT ──(corruption)──> MISSING
```

### ensure_runtime() Flow

```
start
  ├─ version.lock exists AND matches? → return (fast path, <100ms)
  └─ version.lock missing or stale?
       ├─ acquire file lock (non-blocking attempt)
       │   ├─ lock acquired
       │   │   ├─ re-check version.lock → if match, release lock, return
       │   │   └─ build temp dir → merge into ~/.kittify/ → write version.lock → release lock
       │   └─ lock busy (another process updating)
       │       └─ wait for lock → re-check version.lock → return
       └─ (lock always released via context manager)
```
