# Implementation Plan: Retire pre-3.0 status/task readers from active runtime

**Branch**: `kitty/mission-retire-pre30-readers-01KW0MJE` | **Date**: 2026-06-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/retire-pre30-readers-01KW0MJE/spec.md`

**Branch contract** (first statement):
- Current branch at plan start: `kitty/mission-retire-pre30-readers-01KW0MJE`
- Planning/base branch: `kitty/mission-retire-pre30-readers-01KW0MJE`
- Completed changes must merge into: `kitty/mission-retire-pre30-readers-01KW0MJE`

## Summary

Relocate `legacy_detector.py` (and its public symbols `is_legacy_format`, `get_legacy_lane_counts`, `LEGACY_LANE_DIRS`) from the active runtime import graph to `specify_cli.upgrade.legacy_detector`, add a single command-boundary guard (`specify_cli.upgrade.pre30_guard`) that hard-rejects pre-3.0 lane-directory projects before any mutation, and remove all `if use_legacy` branches from active command paths (`task_utils/support.py`, `tasks_cli.py`, `acceptance/__init__.py`). The dashboard retains a thin read-only `is_legacy` annotation path imported from the new upgrade namespace. Documentation in `docs/status-model.md` is updated to mark frontmatter `lane` as historical/migration-only.

## Technical Context

**Language/Version**: Python 3.11+ (runtime uses 3.14 in dev)
**Primary Dependencies**: typer (CLI), ruff/mypy (quality gates), pytest (test suite)
**Storage**: File-based (`status.events.jsonl`, flat `tasks/WP*.md`, `meta.json`)
**Testing**: pytest with `--dist loadfile` for parallel runs; `tests/architectural/` for invariant guards; `tests/specify_cli/` for integration; `tests/upgrade/` for migration regression
**Target Platform**: Linux/macOS CLI
**Performance Goals**: Boundary guard check adds ≤5 ms to cold-start path (NFR-003); a single `os.scandir` or `Path.iterdir()` call on `tasks/` is well within budget
**Constraints**: No changes to `status/store.py`, `status/reducer.py` (C-004); no auto-invoke of upgrade (C-002); `spec-kitty upgrade` must continue to work without regression (FR-009)
**Scale/Scope**: ~10 files modified in `src/`; ~8 test files updated; 2 docs pages updated; 1 new guard module; 1 relocated detector module

## Charter Check

Charter file absent — section skipped per guidelines.

## Project Structure

### Documentation (this mission)

```
kitty-specs/retire-pre30-readers-01KW0MJE/
├── plan.md              # This file
├── research.md          # Caller audit, relocation map, design decisions
├── data-model.md        # Post-cutover invariant + namespace relocation map
├── contracts/           # Boundary-guard error contract
│   └── pre30-guard-contract.md
└── quickstart.md        # Developer quickstart for implementing and testing
```

### Source Code (repository root)

```
src/specify_cli/
├── upgrade/
│   ├── legacy_detector.py      # NEW location (relocated from specify_cli/legacy_detector.py)
│   └── pre30_guard.py          # NEW: command-boundary guard module
├── legacy_detector.py          # DELETED after relocation (no callers remain)
├── task_utils/
│   ├── support.py              # MODIFIED: remove is_legacy_format import + use_legacy branch
│   └── __init__.py             # MODIFIED: remove is_legacy_format re-export
├── tasks_support.py            # MODIFIED: remove is_legacy_format re-export
├── scripts/tasks/
│   ├── task_helpers.py         # MODIFIED: remove is_legacy_format re-export + __all__ entry
│   └── tasks_cli.py            # MODIFIED: replace _check_legacy_format with guard call; remove list_command legacy branch
├── acceptance/__init__.py      # MODIFIED: remove use_legacy branch; add pre-3.0 skip/reject log
├── dashboard/
│   ├── scanner.py              # MODIFIED: update import to upgrade.legacy_detector; keep read-only annotation path
│   └── handlers/features.py   # MODIFIED: update import to upgrade.legacy_detector; keep is_legacy annotation

tests/
├── specify_cli/
│   ├── test_standalone_tasks_cli_canonical.py   # MODIFIED: convert legacy-warning test to hard-reject test
│   └── scripts/test_task_helpers.py             # MODIFIED: remove is_legacy_format from __all__ check
├── test_dashboard/
│   ├── test_scanner.py         # MODIFIED: update monkeypatch paths
│   └── test_api_handler.py     # MODIFIED: update patch paths
├── architectural/
│   └── test_no_dead_symbols.py # MODIFIED: remove grandfathered is_legacy_format entry
└── upgrade/                    # NEW: test_pre30_guard.py (NFR-004: ≥2 tests)

docs/
├── status-model.md             # MODIFIED: update FR-011 doc sections
└── reference/cli-commands.md   # MINOR: already largely correct; verify no live-workflow claims
```

**Structure Decision**: Single Python project. No new top-level directories. The relocated `legacy_detector.py` drops into `src/specify_cli/upgrade/` alongside existing migration infrastructure.

## Complexity Tracking

*No charter violations. Complexity ceiling (≤15) maintained: the new `pre30_guard.py` module is a simple 2-function module; `locate_work_package` complexity drops after legacy branch removal.*

## Implementation Concern Map

### IC-01 — Module relocation and import surgery

- **Purpose**: Move `legacy_detector.py` to `specify_cli.upgrade.legacy_detector` and surgically remove all active-runtime imports and re-exports from the shim chain so the symbol is unreachable from the active package surface without explicitly opting into the upgrade namespace.
- **Relevant requirements**: FR-003, FR-008, C-001, C-003, NFR-001
- **Affected surfaces**:
  - `src/specify_cli/legacy_detector.py` (source → relocated/deleted)
  - `src/specify_cli/upgrade/legacy_detector.py` (destination)
  - `src/specify_cli/task_utils/support.py` (remove import + `__all__` entry)
  - `src/specify_cli/task_utils/__init__.py` (remove re-export)
  - `src/specify_cli/tasks_support.py` (remove re-export)
  - `src/specify_cli/scripts/tasks/task_helpers.py` (remove re-export + `__all__` entry)
  - `tests/specify_cli/scripts/test_task_helpers.py` (update `__all__` assertion)
  - `tests/architectural/test_no_dead_symbols.py` (remove grandfathered entry)
- **Sequencing/depends-on**: none (can proceed independently)
- **Risks**: shim chain is four links deep (`legacy_detector` → `support.py` → `__init__.py` / `tasks_support.py` / `task_helpers.py`); must trace all four to avoid import errors. Upgrade migration `m_0_9_0_frontmatter_only_lanes.py` already uses its own private `_is_legacy_format` method and does NOT import from `legacy_detector` — confirmed safe.

### IC-02 — Command-boundary guard

- **Purpose**: Implement `specify_cli.upgrade.pre30_guard` with `check_pre30_layout(feature_path)` that raises a structured `Pre30LayoutError` (or calls `sys.exit(1)`) with the canonical message when pre-3.0 layout is detected; wire it into all affected mutation command entry points.
- **Relevant requirements**: FR-001, FR-002, FR-005, C-002, NFR-003, NFR-004, NFR-006
- **Affected surfaces**:
  - `src/specify_cli/upgrade/pre30_guard.py` (new)
  - `src/specify_cli/scripts/tasks/tasks_cli.py` (replace `_check_legacy_format` + per-command calls with single `check_pre30_layout` call after mission resolution)
  - `src/specify_cli/cli/commands/agent/tasks.py` (add guard call after `mission_slug` resolved + `feature_path` known)
  - `tests/upgrade/test_pre30_guard.py` (new: NFR-004 positive + negative tests)
- **Sequencing/depends-on**: IC-01 (guard imports from the relocated detector)
- **Risks**: `agent/tasks.py` is a ~4500 LOC god-module; guard must be wired at each `@app.command` entry that calls `locate_work_package` or `emit_status_transition`. Identify the right injection point: after `repo_root = locate_project_root()` + `mission_slug` resolved, before any WP load.

### IC-03 — Active runtime legacy branch removal

- **Purpose**: Remove all `if use_legacy` / `if is_legacy_format()` branches from `locate_work_package`, `_iter_work_packages`, `tasks_cli.py::list_command`, and `acceptance/__init__.py::_iter_work_packages` so the active runtime only handles flat `tasks/WP*.md` layout.
- **Relevant requirements**: FR-004, FR-005, FR-007
- **Affected surfaces**:
  - `src/specify_cli/task_utils/support.py` (`locate_work_package` — remove `use_legacy` branch)
  - `src/specify_cli/scripts/tasks/tasks_cli.py` (`list_command` — remove `use_legacy` branch)
  - `src/specify_cli/acceptance/__init__.py` (`_iter_work_packages` — remove `use_legacy` branch; add pre-3.0 skip with log entry)
- **Sequencing/depends-on**: IC-02 (guard provides the safety net that makes branch removal safe)
- **Risks**: `_iter_work_packages` is called from `collect_feature_summary` which is called from `orchestrator_api/commands.py:1498` — the acceptance scanner is more broadly used than just the accept gate. The pre-3.0 skip must log clearly so callers see it. Do NOT change function signatures.

### IC-04 — Dashboard read-only annotation update

- **Purpose**: Update `dashboard/scanner.py` and `dashboard/handlers/features.py` to import `is_legacy_format` from `specify_cli.upgrade.legacy_detector` instead of the retired active-runtime location; preserve the read-only `is_legacy: true` annotation path (FR-006, Assumption 4) without routing through mutation paths.
- **Relevant requirements**: FR-006, C-003
- **Affected surfaces**:
  - `src/specify_cli/dashboard/scanner.py` (update import; remove mutation-branch `use_legacy` from `_get_kanban_task_data_for_feature`; keep annotation-only path in `_build_kanban_stats` and `_process_wp_file`)
  - `src/specify_cli/dashboard/handlers/features.py` (update import; keep `feature["is_legacy"]` annotation)
  - `tests/test_dashboard/test_scanner.py` (update monkeypatch target path)
  - `tests/test_dashboard/test_api_handler.py` (update patch target path)
- **Sequencing/depends-on**: IC-01 (import path changes)
- **Risks**: Dashboard `_get_kanban_task_data_for_feature` has a `use_legacy` branch that iterates lane subdirectories — this is the mutation-adjacent hot path to remove. The `_build_kanban_stats` and `_process_wp_file` use `is_legacy_format` only as an annotation signal — retain these.

### IC-05 — Test cleanup and documentation update

- **Purpose**: Update tests that exercised legacy active-runtime paths to use the guard or upgrade path instead, and update docs so `docs/status-model.md` no longer describes frontmatter `lane` as a live workflow authority.
- **Relevant requirements**: FR-010, FR-011, NFR-002
- **Affected surfaces**:
  - `tests/specify_cli/test_standalone_tasks_cli_canonical.py` (convert `test_src_tasks_cli_check_legacy_format_warns_once` to test hard-reject via `check_pre30_layout`)
  - `tests/architectural/test_no_dead_symbols.py` (remove grandfathered `is_legacy_format` entry — handled in IC-01)
  - `docs/status-model.md` (clarify frontmatter `lane` is historical; point to `spec-kitty upgrade` for pre-3.0 projects)
- **Sequencing/depends-on**: IC-01, IC-02, IC-03
- **Risks**: `test_no_dead_symbols.py` grandfathered list must be pruned carefully — do not remove other entries unrelated to this mission.

**Branch contract** (second statement, before tasks):
- Planning base branch: `kitty/mission-retire-pre30-readers-01KW0MJE`
- Merge target for completed changes: `kitty/mission-retire-pre30-readers-01KW0MJE`
- All WP lane branches will be created from and merged back to this branch.
