# Data Model: State Architecture Cleanup Phase 2

**Feature**: 054-state-architecture-cleanup-phase-2
**Date**: 2026-03-20

## State Contract Changes

This feature modifies the state contract (`src/specify_cli/state_contract.py`) to align classifications with enforced Git policy and removal of deprecated surfaces.

### Constitution Surfaces (reclassified)

| Surface | Before | After | Change |
|---------|--------|-------|--------|
| `constitution_interview_answers` | AUTHORITATIVE / INSIDE_REPO_NOT_IGNORED | AUTHORITATIVE / TRACKED | Git class → TRACKED (enforced by .gitignore absence) |
| `constitution_references` | DERIVED / INSIDE_REPO_NOT_IGNORED | LOCAL_RUNTIME / IGNORED | Authority → LOCAL_RUNTIME, Git → IGNORED (added to .gitignore) |
| `constitution_library` | DERIVED / INSIDE_REPO_NOT_IGNORED | AUTHORITATIVE / TRACKED | Authority → AUTHORITATIVE, Git → TRACKED |

### Active-Mission Marker (removed)

| Surface | Before | After | Change |
|---------|--------|-------|--------|
| `active_mission_marker` | DEPRECATED / INSIDE_REPO_NOT_IGNORED | REMOVED from registry | Entry deleted — no production code reads it |

### Atomic Write Flag (new metadata)

Surfaces that gain atomic-write discipline will have `atomic_write=True` set in their `StateSurface` entry:

| Surface | Path Pattern | Atomic Before | Atomic After |
|---------|-------------|---------------|--------------|
| `feature_metadata` | `meta.json` | True | True (unchanged) |
| `runtime_feature_runs` | `.kittify/runtime/feature-runs.json` | False | True |
| `workspace_context` | `.kittify/workspaces/*.json` | False | True |
| `constitution_context_state` | `.kittify/constitution/context-state.json` | False | True |
| `dashboard_metadata` | `.kittify/.dashboard` | False | True |
| `lamport_clock` | `~/.spec-kitty/clock.json` | True (inline) | True (shared) |
| `sync_credentials` | `~/.spec-kitty/credentials` | False | True |
| `sync_config` | `~/.spec-kitty/config.toml` | False | True |
| `tracker_config` | `.kittify/config.yaml` (tracker section) | False | True |
| `project_metadata` | `.kittify/metadata.yaml` | False | True |

## Entity: AtomicWriter

New shared utility at `src/specify_cli/core/atomic.py`.

### API

```
atomic_write(path, content, *, mkdir=False)
  path:    Target file path (Path)
  content: File content (str → UTF-8 encoded, or bytes → raw)
  mkdir:   If True, create parent directories before writing

  Guarantees:
  - Temp file created in same directory as target (same-filesystem rename)
  - os.replace() is atomic on all supported platforms
  - On failure: temp file cleaned up, original file untouched
  - On success: target file contains complete new content
```

### Invariants

1. Temp file prefix: `.atomic-` (distinguishable from `.meta-` used by legacy `feature_metadata.py`)
2. Temp file suffix: `.tmp`
3. Exception handling: `BaseException` catch ensures cleanup even on `KeyboardInterrupt`
4. File descriptor lifecycle: `os.fdopen()` wraps fd, context manager closes it

## .gitignore Changes

### Added

```
.kittify/constitution/references.yaml
```

### Unchanged (already present)

```
.kittify/constitution/context-state.json
.kittify/constitution/directives.yaml
.kittify/constitution/governance.yaml
.kittify/constitution/metadata.yaml
```

### Unchanged (deliberately NOT ignored)

```
.kittify/constitution/constitution.md          # Source document
.kittify/constitution/interview/answers.yaml   # Team decisions
.kittify/constitution/library/*.md             # Shared knowledge
```

## Acceptance Module Consolidation

### Before

```
acceptance.py          → 657 lines, 10 public functions
acceptance_support.py  → 758 lines, 13 public functions (superset)
```

### After

```
acceptance.py          → ~720 lines, 13 public functions (absorbed 3 unique standalone functions)
acceptance_support.py  → ~25 lines, pure re-export wrapper
```

### Functions moved from standalone → canonical

| Function | Purpose |
|----------|---------|
| `ArtifactEncodingError` | Custom exception for UTF-8 decode failures |
| `normalize_feature_encoding()` | Windows-1252/Latin-1 → UTF-8 conversion |
| `_read_text_strict()` | Encoding-strict file reader |

### AcceptanceSummary alignment

The `path_violations` field (present in `acceptance.py`, missing in `acceptance_support.py`) will be the single canonical definition after consolidation.
