# Implementation Plan: Frontmatter-Only Lane Management

**Branch**: `007-frontmatter-only-lane` | **Date**: 2025-12-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/007-frontmatter-only-lane/spec.md`

## Summary

Eliminate directory-based lane management in favor of frontmatter-only lane tracking. All WP files will live in a flat `tasks/` directory, with the `lane:` YAML frontmatter field as the single source of truth. The `move` command is renamed to `update` to reflect metadata-only changes. Migration is all-at-once (main repo + all worktrees) with user confirmation required.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: pathlib, Rich (console output), ruamel.yaml (frontmatter parsing), typer (CLI)
**Storage**: Filesystem only (YAML frontmatter in markdown files)
**Testing**: pytest
**Target Platform**: Linux/macOS/Windows (cross-platform CLI)
**Project Type**: single
**Performance Goals**: Status command returns within 1 second for features with up to 50 WPs
**Constraints**: Must maintain backwards compatibility path via migration; no hybrid mode support
**Scale/Scope**: Typical feature has 5-20 WPs; migration must handle up to 100 WPs across all features

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No project constitution is defined (template only). Proceeding with standard Python development practices:
- Test coverage for all modified functions
- Clear error messages for user-facing failures
- Idempotent operations where applicable

## Project Structure

### Documentation (this feature)

```
kitty-specs/007-frontmatter-only-lane/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── spec.md              # Feature specification
└── tasks/               # Work packages (flat structure after migration)
```

### Source Code (repository root)

```
src/specify_cli/
├── dashboard/
│   └── scanner.py          # MODIFY: Read lanes from frontmatter, not directories
├── tasks_support.py        # MODIFY: locate_work_package() to search flat tasks/
├── task_metadata_validation.py  # MODIFY: Remove directory-based validation
├── acceptance.py           # MODIFY: Group WPs by frontmatter lane
└── commands/
    └── upgrade.py          # NEW: Migration command

scripts/tasks/
├── tasks_cli.py            # MODIFY: Rename move→update, frontmatter-only changes
└── task_helpers.py         # MODIFY: locate_work_package() flat search

tests/
├── test_tasks_cli_commands.py  # UPDATE: Test update command, flat structure
├── test_dashboard/
│   └── test_scanner.py     # UPDATE: Test frontmatter-based scanning
└── test_migration.py       # NEW: Test upgrade command
```

**Structure Decision**: Single project structure. This is a refactoring of existing modules, not new subsystem creation.

## Engineering Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Command rename | `move` → `update` | Reflects metadata change, not file operation |
| Backwards compatibility | None - clean break | Simplifies codebase, avoids hybrid complexity |
| Migration scope | All-at-once | Single `spec-kitty upgrade` migrates everything |
| Legacy detection | Warn but don't block | Detection on any tasks_cli.py command |
| Default lane | `planned` | When `lane:` field missing, default with warning |

## Files to Modify

### Critical Path (must change)

| File | Function/Area | Change |
|------|---------------|--------|
| `scripts/tasks/tasks_cli.py` | `stage_move()` | Remove file move, update frontmatter only |
| `scripts/tasks/tasks_cli.py` | `move_command()` | Rename to `update_command()` |
| `scripts/tasks/task_helpers.py` | `locate_work_package()` | Search flat `tasks/`, read lane from frontmatter |
| `src/specify_cli/tasks_support.py` | `locate_work_package()` | Same as above (duplicate) |
| `src/specify_cli/dashboard/scanner.py` | `scan_feature_kanban()` | Scan flat `tasks/`, group by frontmatter lane |
| `src/specify_cli/dashboard/scanner.py` | `scan_all_features()` | Count WPs by frontmatter lane |
| `src/specify_cli/task_metadata_validation.py` | `detect_lane_mismatch()` | Remove or repurpose (no directory to mismatch) |
| `src/specify_cli/acceptance.py` | Lane collection | Group WPs by frontmatter lane field |

### New Files

| File | Purpose |
|------|---------|
| `src/specify_cli/commands/upgrade.py` | Migration command implementation |
| `src/specify_cli/legacy_detector.py` | Detect old directory-based format |
| `tests/test_migration.py` | Test upgrade command |

### Documentation Updates

| File | Change |
|------|--------|
| `.kittify/AGENTS.md` | Remove "don't edit lane" warning, explain new approach |
| Task prompt templates | Update to reflect flat structure |
| `tasks/README.md` | Explain frontmatter-only lanes |

## Parallel Work Analysis

This feature can be parallelized into 3 independent streams after a small foundation:

### Dependency Graph

```
Foundation (Stream 0) → Stream 1, 2, 3 (parallel) → Integration
```

### Work Distribution

- **Stream 0 (Foundation)**: Shared utilities - `legacy_detector.py`, updated `LANES` constant location
- **Stream 1 (CLI)**: `tasks_cli.py` refactor, `task_helpers.py` updates
- **Stream 2 (Dashboard)**: `scanner.py` refactor, `acceptance.py` updates
- **Stream 3 (Migration)**: `upgrade.py` command, migration tests

### Coordination Points

- All streams share the lane-reading utility (extract from frontmatter)
- Integration testing after all streams complete
- Documentation updates can happen in any stream
