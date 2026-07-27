# Implementation Plan: State Architecture Cleanup Phase 2

**Branch**: `054-state-architecture-cleanup-phase-2` | **Date**: 2026-03-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/054-state-architecture-cleanup-phase-2/spec.md`
**Evidence**: [007-spec-kitty-2x-state-architecture-audit](vault notes) — refresh findings 2026-03-20

## Summary

Complete the state-architecture cleanup identified by the Obsidian evidence vault audit refresh. Seven cleanup areas: remove active-mission project-level fallback from verification/diagnostics/manifest, delete dead mission code, extend atomic-write discipline to 9 stateful write paths via a shared utility extracted from `feature_metadata.py`, enforce hybrid Git policy for constitution state (commit answers + library, ignore references), deduplicate acceptance implementations, harden `legacy_bridge` import handling, and update the vault notes.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: pathlib, Rich, ruamel.yaml, typer, pytest, tempfile, os
**Storage**: Filesystem only (YAML frontmatter, JSON state files, TOML config, JSONL event logs)
**Testing**: pytest (PWHEADLESS=1 pytest tests/)
**Target Platform**: macOS, Linux (cross-platform via pathlib + os.replace)
**Project Type**: Single Python CLI package
**Performance Goals**: N/A (developer tooling, no latency requirements)
**Constraints**: Ruff compliance, Python 3.11+, no behavior regressions
**Scale/Scope**: ~15 source files modified, ~9 write paths converted, ~5 dead code paths removed

## Constitution Check

*Constitution file absent in this project. Skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/054-state-architecture-cleanup-phase-2/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0 output (decisions, no unknowns)
├── data-model.md        # Phase 1 output (state contract changes)
├── quickstart.md        # Phase 1 output (verification guide)
└── checklists/
    └── requirements.md
```

### Source Code (files modified)

```
src/specify_cli/
├── core/
│   └── atomic.py                    # NEW: shared atomic_write() utility
├── feature_metadata.py              # MODIFIED: import from core.atomic
├── mission.py                       # MODIFIED: delete set_active_mission()
├── manifest.py                      # MODIFIED: remove _detect_active_mission(), require feature context
├── verify_enhanced.py               # MODIFIED: accept feature_dir for mission resolution
├── acceptance.py                    # MODIFIED: absorb unique standalone functions
├── core/
│   └── project_resolver.py          # MODIFIED: delete get_active_mission_key()
├── dashboard/
│   ├── diagnostics.py               # MODIFIED: accept feature_dir for mission resolution
│   └── lifecycle.py                 # MODIFIED: use atomic_write
├── constitution/
│   └── context.py                   # MODIFIED: use atomic_write
├── next/
│   └── runtime_bridge.py            # MODIFIED: use atomic_write
├── workspace_context.py             # MODIFIED: use atomic_write
├── sync/
│   ├── clock.py                     # MODIFIED: replace inline atomic write with shared utility
│   ├── auth.py                      # MODIFIED: add atomic_write (keep file lock)
│   └── config.py                    # MODIFIED: use atomic_write
├── tracker/
│   └── config.py                    # MODIFIED: use atomic_write
├── upgrade/
│   └── metadata.py                  # MODIFIED: use atomic_write
├── status/
│   └── emit.py                      # MODIFIED: remove silent ImportError catch, remove WP06 comment
├── state_contract.py                # MODIFIED: reclassify constitution surfaces
└── scripts/tasks/
    └── acceptance_support.py        # MODIFIED: thin wrapper delegating to acceptance.py

tests/
├── specify_cli/
│   ├── test_atomic_write.py         # NEW: shared utility tests
│   ├── test_state_contract.py       # MODIFIED: validate new classifications
│   └── test_acceptance_regressions.py  # MODIFIED: update for thin wrapper pattern
├── status/
│   └── test_emit.py                 # MODIFIED: test ImportError raises, not silently passes
└── [per-module tests as needed]

.gitignore                           # MODIFIED: add .kittify/constitution/references.yaml
```

**Structure Decision**: All changes are within the existing `src/specify_cli/` package. One new module (`core/atomic.py`) and one new test file (`test_atomic_write.py`). No structural changes to the project layout.

## Complexity Tracking

*No constitution violations to justify.*

## Design Decisions

### D1: Shared Atomic Write Utility

**Decision**: Extract `_atomic_write()` from `feature_metadata.py` into `src/specify_cli/core/atomic.py` as a public function.

**API**:
```python
def atomic_write(path: Path, content: str | bytes, *, mkdir: bool = False) -> None:
    """Write content atomically via write-to-temp-then-rename.

    If mkdir=True, creates parent directories before writing.
    Content can be str (encoded to UTF-8) or bytes (written raw).
    Temp file is created in the same directory as target for same-filesystem rename.
    """
```

**Rationale**: The pattern in `feature_metadata.py` is already correct and battle-tested. Making it importable avoids 9 copies of the same logic. The `mkdir` parameter handles the common `path.parent.mkdir(parents=True, exist_ok=True)` pattern seen in 6 of the 9 write paths.

**Migration for existing callers**:
- `feature_metadata.py`: Replace private `_atomic_write()` with import from `core.atomic`
- `sync/clock.py`: Replace its own inline implementation with the shared utility
- `sync/auth.py`: Wrap `toml.dump()` output through shared utility (keep file lock)
- All others: Replace direct `write_text()` / `json.dump()` / `yaml.dump()` with shared utility

### D2: Active-Mission Removal Strategy

**Decision**: Hard removal, no deprecation period. The migration `m_0_8_0_remove_active_mission.py` already declared this "no longer used" — yet production code still reads it. That contradiction must end cleanly.

**Changes**:

1. **`manifest.py`**: Remove `_detect_active_mission()` entirely. `FileManifest` will no longer carry an `active_mission` property. Callers that need mission context must resolve it from feature `meta.json`.

2. **`verify_enhanced.py`**: Add a `feature_dir: Path | None` parameter to `run_enhanced_verify()`. When provided, resolve mission from `meta.json`. When absent, skip mission-sensitive file checks (or report "no feature context").

3. **`dashboard/diagnostics.py`**: Same pattern — accept `feature_dir` and resolve mission per-feature.

4. **`cli/commands/mission.py`**: The `current_cmd()` fallback to project-level mission when no feature is detected becomes an explicit "no active feature detected" message.

5. **`mission.py`**: Delete `set_active_mission()` entirely.

6. **`core/project_resolver.py`**: Delete `get_active_mission_key()` entirely. Remove from `__init__.py` exports.

7. **`state_contract.py`**: Change `active_mission_marker` from `DEPRECATED` to fully removed from the registry (or keep as `DEPRECATED` with `notes="Removed in 054"`).

### D3: Constitution Git Policy

**Decision**: Hybrid policy — commit shared team knowledge, ignore local machine state.

| Path | Classification | Git Status | Rationale |
|------|---------------|------------|-----------|
| `constitution.md` | AUTHORITATIVE | TRACKED | Source document, defines project way of working |
| `interview/answers.yaml` | AUTHORITATIVE | TRACKED | Team decisions |
| `library/*.md` | AUTHORITATIVE | TRACKED | Shared knowledge references |
| `references.yaml` | LOCAL_RUNTIME | IGNORED | Contains local machine paths, causes merge conflicts |

**Implementation**:
1. Add `.kittify/constitution/references.yaml` to `.gitignore`
2. Update `state_contract.py`: `references` → `LOCAL_RUNTIME` / `IGNORED`; `library` → `AUTHORITATIVE` / `TRACKED`
3. Remove the "Git boundary decision deferred" notes from state contract entries
4. No migration needed — `.gitignore` change is sufficient. Existing tracked `references.yaml` will stop being updated in Git but won't be force-removed from history.

### D4: Acceptance Deduplication

**Decision**: Make `acceptance.py` the single canonical implementation. Move the 3 unique standalone features into it. Reduce `acceptance_support.py` to pure re-exports.

**What moves from standalone → canonical**:
- `ArtifactEncodingError` exception class
- `normalize_feature_encoding()` function
- `_read_text_strict()` function

**What `acceptance_support.py` becomes**:
```python
"""Thin compatibility wrapper for standalone tasks_cli.py usage.

All logic lives in specify_cli.acceptance. This module re-exports
the public API for backwards compatibility with standalone scripts.
"""
from specify_cli.acceptance import (
    AcceptanceError,
    AcceptanceSummary,
    AcceptanceResult,
    ArtifactEncodingError,
    WorkPackageState,
    collect_feature_summary,
    choose_mode,
    detect_feature_slug,
    normalize_feature_encoding,
    perform_acceptance,
)

__all__ = [
    "AcceptanceError",
    "AcceptanceSummary",
    "AcceptanceResult",
    "ArtifactEncodingError",
    "WorkPackageState",
    "collect_feature_summary",
    "choose_mode",
    "detect_feature_slug",
    "normalize_feature_encoding",
    "perform_acceptance",
]
```

**`detect_feature_slug` divergence**: The standalone copy has its own implementation without `announce_fallback`. Move the superset implementation to canonical and support both call signatures via an optional parameter.

### D5: Legacy Bridge Hardening

**Decision**: Remove the `ImportError` catch. Keep the broad `Exception` catch for actual bridge update failures (those are non-critical — canonical state is persisted first).

**Before**:
```python
try:
    from specify_cli.status.legacy_bridge import update_all_views
    update_all_views(feature_dir, snapshot)
except ImportError:
    pass  # WP06 not yet available
except Exception:
    logger.warning(...)
```

**After**:
```python
from specify_cli.status.legacy_bridge import update_all_views  # top-level import

try:
    update_all_views(feature_dir, snapshot)
except Exception:
    logger.warning(
        "Legacy bridge update failed for event %s; "
        "canonical log and snapshot are unaffected",
        event.event_id,
    )
```

**Rationale**: `legacy_bridge.py` is in-tree, tested, and required on 2.x. A missing import is a packaging regression that must surface immediately, not be silently swallowed. Moving to a top-level import makes this a hard failure at module load time.

## Implementation Approach

### Dependency Graph

```
WP01: Shared atomic_write utility (no deps)
WP02: Active-mission fallback removal (no deps)
WP03: Dead mission code deletion (depends on WP02)
WP04: Atomic write conversion of 9 paths (depends on WP01)
WP05: Constitution Git policy (no deps)
WP06: Acceptance deduplication (no deps)
WP07: Legacy bridge hardening (no deps)
WP08: Vault notes update (depends on WP01-WP07)
```

### Parallelization Opportunities

```
Wave 1 (parallel): WP01, WP02, WP05, WP06, WP07
Wave 2 (parallel): WP03 (after WP02), WP04 (after WP01)
Wave 3: WP08 (after all)
```

### Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| `FileManifest` callers break when `active_mission` removed | High | Grep all callers, update each to pass feature context |
| Atomic write changes file permissions on some platforms | Medium | Preserve original file permissions in atomic_write() via `shutil.copymode()` or `os.fchmod()` |
| `acceptance_support.py` standalone users break | Medium | Keep re-export wrapper, test both import paths |
| `legacy_bridge` hard import breaks CI | Low | Module is in-tree and tested; only real packaging regressions fail |

## Testing Strategy

| Cleanup Area | Test Location | What to Test |
|-------------|---------------|-------------|
| Atomic write utility | `tests/specify_cli/test_atomic_write.py` | Successful write, interrupted write (mock os.replace), temp file cleanup, mkdir behavior, bytes vs str |
| Active-mission removal | `tests/cross_cutting/packaging/test_manifest_cli_filtering.py` | Manifest without active_mission, verify with feature context |
| Dead mission code | `tests/runtime/test_project_resolver.py` | Remove tests for deleted functions, add test confirming deletion |
| Atomic write conversion | Per-module test files | Each converted path writes atomically (mock-interrupt test) |
| Constitution Git policy | `tests/specify_cli/test_state_contract.py` | Validate new classifications match .gitignore reality |
| Acceptance dedup | `tests/specify_cli/test_acceptance_regressions.py` | Thin wrapper imports work, parity test still passes |
| Legacy bridge | `tests/status/test_emit.py` | ImportError is NOT caught (raises), bridge exceptions ARE caught |
