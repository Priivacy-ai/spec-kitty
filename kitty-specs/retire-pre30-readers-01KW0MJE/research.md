# Research: Retire pre-3.0 status/task readers from active runtime

**Mission**: retire-pre30-readers-01KW0MJE  
**Date**: 2026-06-26  
**Branch**: `kitty/mission-retire-pre30-readers-01KW0MJE`

---

## Zero-Caller Audit Table (FR-008 / NFR-001 / C-001)

This table is the deletion-safety spine for the mission. Every symbol slated for removal or de-export from the active runtime is audited below with file:line evidence. Classification is **SAFE TO DELETE** (zero live callers in the active runtime, evidence given) or **DE-EXPORT ONLY / RELOCATE** (load-bearing — symbol has callers that must be handled before removal).

### `is_legacy_format` (from `src/specify_cli/legacy_detector.py`)

| # | Caller file | Line(s) | Import path used | Nature | Verdict |
|---|-------------|---------|------------------|--------|---------|
| 1 | `src/specify_cli/task_utils/support.py` | 14 (import), 320 (call in `locate_work_package`) | `from specify_cli.legacy_detector import is_legacy_format` | Direct import; used in `locate_work_package` `use_legacy` branch — branch to be removed (FR-004). Import to be removed after IC-03. | DE-EXPORT (branch removed, import deleted) |
| 2 | `src/specify_cli/task_utils/__init__.py` | 21 (re-export), 47 (`__all__`) | via `task_utils.support` | Shim re-export with zero external callers that consume it via this path. | DE-EXPORT (remove from shim) |
| 3 | `src/specify_cli/tasks_support.py` | 22 (re-export) | via `task_utils.support` | Backward-compat shim re-export; zero callers outside the shim chain that use `is_legacy_format` from this path. | DE-EXPORT (remove from shim) |
| 4 | `src/specify_cli/scripts/tasks/task_helpers.py` | 34 (re-export), 58 (`__all__`) | via `task_utils.support` | Shim re-export; no caller in `src/` invokes it via this path. Tests patch it as `task_helpers.is_legacy_format` but via monkeypatch only. | DE-EXPORT (remove from shim + `__all__`) |
| 5 | `src/specify_cli/scripts/tasks/tasks_cli.py` | 48 (import), 216 (`_check_legacy_format` body), 325–331 (`list_command` `use_legacy` branch) | via `task_helpers` | Used by `_check_legacy_format` (warning path) and `list_command` (legacy iteration branch). Both replaced by `check_pre30_layout` guard call in IC-02/IC-03. | DE-EXPORT (replace with guard) |
| 6 | `src/specify_cli/acceptance/__init__.py` | 36 (import via `task_utils`), 411 (call in `_iter_work_packages`) | via `specify_cli.task_utils` | Used in `_iter_work_packages` `use_legacy` branch. Branch removed in IC-03; pre-3.0 shape handled by skip + log. | DE-EXPORT (branch removed, import deleted) |
| 7 | `src/specify_cli/dashboard/scanner.py` | 16 (direct import from `legacy_detector`), 703 (`_build_kanban_stats`), 796 (`_process_wp_file`), 855 (`_get_kanban_task_data_for_feature`) | `from specify_cli.legacy_detector import is_legacy_format` | Read-only annotation calls in `_build_kanban_stats` and `_process_wp_file`; `_get_kanban_task_data_for_feature` has a mutation-adjacent `use_legacy` branch (to remove). Dashboard retains annotation calls (FR-006). Import path changes to `specify_cli.upgrade.legacy_detector`. | RELOCATE (import path updated; keep annotation calls; remove mutation branch) |
| 8 | `src/specify_cli/dashboard/handlers/features.py` | 30 (direct import from `legacy_detector`), 109 (`handle_features_list`), 162 (`handle_kanban_request`) | `from specify_cli.legacy_detector import is_legacy_format` | Pure read-only annotation: sets `feature["is_legacy"] = True/False` on dashboard feature list and kanban panel. No mutation path. Import path changes to `specify_cli.upgrade.legacy_detector`. | RELOCATE (import path updated; annotation retained) |

**Summary verdict for `is_legacy_format`**: Zero callers that perform mutation or are in the active command hot path after IC-01/IC-03 surgical removal. Dashboard annotation callers (rows 7–8) are explicitly retained per FR-006. Safe to remove from `specify_cli.legacy_detector` (public surface) after relocation; the symbol persists in `specify_cli.upgrade.legacy_detector`.

---

### `get_legacy_lane_counts` (from `src/specify_cli/legacy_detector.py`)

| # | Caller file | Line(s) | Import path used | Nature | Verdict |
|---|-------------|---------|------------------|--------|---------|
| — | — | — | — | Zero external callers. Only referenced internally in `legacy_detector.py` (lines 50, 81 `__all__`). Not re-exported by any shim. Not called by `task_utils`, `dashboard`, `acceptance`, tests, or any `src/` module outside of `legacy_detector.py` itself. | **SAFE TO DELETE** from active runtime surface |

Evidence: `grep -rn "get_legacy_lane_counts" src/ tests/` returns only `legacy_detector.py` lines 50 and 81. The symbol will be preserved in the relocated `specify_cli.upgrade.legacy_detector` (C-003 requires the upgrade namespace to retain full access), but it is not exported from any active-runtime shim.

---

### `LEGACY_LANE_DIRS` (from `src/specify_cli/legacy_detector.py`)

| # | Caller file | Line(s) | Import path used | Nature | Verdict |
|---|-------------|---------|------------------|--------|---------|
| — | — | — | — | Zero external callers. Only referenced internally in `legacy_detector.py` (lines 14, 39, 68, 79 `__all__`). Not re-exported by any shim. Not imported by `task_utils`, `dashboard`, `acceptance`, tests, or any `src/` module outside of `legacy_detector.py` itself. | **SAFE TO DELETE** from active runtime surface |

Evidence: `grep -rn "LEGACY_LANE_DIRS" src/ tests/` returns only `legacy_detector.py` lines.

---

### `use_legacy` branch in `task_utils/support.py::locate_work_package`

| # | Location | Lines | Nature | Verdict |
|---|----------|-------|--------|---------|
| A | `src/specify_cli/task_utils/support.py` | 320–336 | `use_legacy = is_legacy_format(feature_path)` followed by branch that searches `tasks/{lane}/` subdirectories | After the command boundary guard fires for pre-3.0 projects, this branch can never be reached from a live active command. SAFE TO REMOVE from `locate_work_package`. The function becomes flat-layout-only. | **SAFE TO REMOVE** |

---

### `is_legacy_format()` branch sites in `tasks_cli.py`

| # | Location | Lines | Function | Nature | Verdict |
|---|----------|-------|----------|--------|---------|
| B | `src/specify_cli/scripts/tasks/tasks_cli.py` | 212–247 | `_check_legacy_format` | Warning-only helper; prints legacy warning to stderr; does NOT exit. Used by both `update_command` (line 250, which does exit) and `list_command` (line 327). After IC-02, `check_pre30_layout` in `pre30_guard.py` replaces this entire function. | **SAFE TO REMOVE** (replace with guard) |
| C | `src/specify_cli/scripts/tasks/tasks_cli.py` | 325–355 | `list_command` | `use_legacy` branch that iterates lane subdirectories; called only after `_check_legacy_format`. After IC-02/IC-03, the guard fires before `list_command` body is reached. | **SAFE TO REMOVE** |

---

### `is_legacy_format()` branch sites in `dashboard/scanner.py`

| # | Location | Lines | Function | Nature | Verdict |
|---|----------|-------|----------|--------|---------|
| D | `src/specify_cli/dashboard/scanner.py` | 703 | `_build_kanban_stats` | Read-only: routes to `_build_legacy_kanban_stats` or `_build_event_log_kanban_stats`. This is an annotation/routing decision only — no mutation. RETAIN (import path updated to `upgrade.legacy_detector`). | **RETAIN** (read-only path) |
| E | `src/specify_cli/dashboard/scanner.py` | 796 | `_process_wp_file` | `is_legacy_format(feature_candidate)` used to determine `lane = default_lane` annotation vs. raising `CanonicalStatusNotFoundError`. Read-only decision. RETAIN. | **RETAIN** (read-only path) |
| F | `src/specify_cli/dashboard/scanner.py` | 855 | `_get_kanban_task_data_for_feature` | `use_legacy` branch iterates lane subdirectories to build task list — this IS the mutation-adjacent hot path referenced in FR-006. REMOVE this branch; the function should use flat-layout-only iteration for new invocations, or short-circuit with an `is_legacy` annotation without deep iteration. | **REMOVE mutation branch** |

---

### `is_legacy_format()` branch sites in `acceptance/__init__.py`

| # | Location | Lines | Function | Nature | Verdict |
|---|----------|-------|----------|--------|---------|
| G | `src/specify_cli/acceptance/__init__.py` | 411 | `_iter_work_packages` | `use_legacy` branch iterates `tasks/{lane}/` subdirectories. REMOVE branch; instead insert pre-3.0 shape detection at the top of `_iter_work_packages` that raises `AcceptanceError` (or logs a warning and yields nothing) before any iteration. This satisfies FR-007. | **REMOVE** (replace with skip/reject + log) |

---

## Relocation Map

| Symbol | Current path | Post-mission path | Shim re-exported via |
|--------|-------------|-------------------|---------------------|
| `is_legacy_format` | `specify_cli.legacy_detector` | `specify_cli.upgrade.legacy_detector` | None (shim re-exports removed) |
| `get_legacy_lane_counts` | `specify_cli.legacy_detector` | `specify_cli.upgrade.legacy_detector` | None |
| `LEGACY_LANE_DIRS` | `specify_cli.legacy_detector` | `specify_cli.upgrade.legacy_detector` | None |
| `legacy_detector.py` file | `src/specify_cli/legacy_detector.py` | `src/specify_cli/upgrade/legacy_detector.py` | — |

The original `src/specify_cli/legacy_detector.py` is DELETED after all active-runtime callers are removed. The upgrade namespace (`src/specify_cli/upgrade/`) retains full access with identical `__all__`.

---

## Upgrade Migration Caller Audit (FR-009)

`src/specify_cli/upgrade/migrations/m_0_9_0_frontmatter_only_lanes.py` defines its own **private** `_is_legacy_format` method at line 104 and does NOT import from `specify_cli.legacy_detector`. It is self-contained and will NOT be broken by the relocation. Evidence:

```
grep -rn "from specify_cli.legacy_detector\|legacy_detector" src/specify_cli/upgrade/
# Returns: (no output)
```

The migration's private `_is_legacy_format` has its own inline lane-directory logic that is functionally equivalent but implemented independently. It checks for directory existence (not just `.md` files) and is more aggressive than the `legacy_detector.py` implementation (intentional — migration wants to catch partially-migrated projects). No changes needed to any migration file.

---

## Off-Limits Files (NFR-005 / C-004)

The following files are explicitly **outside this mission's scope** and must not be modified:

| File | Reason |
|------|--------|
| `src/specify_cli/status/store.py` | NFR-005/C-004: `feature_slug`/`mission_id=None` tolerance locked |
| `src/specify_cli/status/reducer.py` | NFR-005/C-004: same |
| `src/specify_cli/upgrade/migrations/m_0_9_0_frontmatter_only_lanes.py` | FR-009: upgrade must continue to work without change |
| `src/specify_cli/upgrade/runner.py` | FR-009: upgrade runner must not be changed |
| `src/specify_cli/upgrade/registry.py` | FR-009: upgrade registry must not be changed |

---

## Boundary Guard Design Decision

**Decision**: The command-boundary guard lives in a single module `src/specify_cli/upgrade/pre30_guard.py`. It exports:
- `Pre30LayoutError(Exception)` — structured exception with `feature_path` and `detected_dirs` attributes
- `check_pre30_layout(feature_path: Path) -> None` — raises `Pre30LayoutError` (caught by command handlers to print message + `sys.exit(1)`) or returns cleanly

**Rationale**: Single chokepoint avoids duplication across the ~4500-LOC `agent/tasks.py` god-module and `tasks_cli.py`. The function takes a resolved `feature_path` (after mission slug resolution), so it cannot fire before the command knows which project it is operating on (preserves normal "no kitty-specs found" errors for non-spec-kitty directories, per Scenario A exception path).

**Rejected alternative**: Checking at project root (before mission resolution) would fire incorrectly for non-spec-kitty directories and would conflict with "no kitty-specs found" error handling.

**Rejected alternative**: Per-function guard calls scattered across `task_utils/support.py` internal functions would not satisfy C-002 (no mutation before guard fires) — the guard must be at the command entry boundary.

**Performance**: `is_legacy_format` makes at most 4 `Path.is_dir()` calls on `tasks/{lane}/` — well under the 5 ms NFR-003 budget even on cold filesystem.

---

## Import Surgery Sequence

To avoid circular imports, apply changes in this order:

1. Copy `src/specify_cli/legacy_detector.py` → `src/specify_cli/upgrade/legacy_detector.py` (update module docstring; keep `__all__` identical)
2. Create `src/specify_cli/upgrade/pre30_guard.py` (imports `is_legacy_format` from `specify_cli.upgrade.legacy_detector`)
3. Update `src/specify_cli/dashboard/scanner.py` import: `from specify_cli.upgrade.legacy_detector import is_legacy_format`
4. Update `src/specify_cli/dashboard/handlers/features.py` import: same
5. Remove `is_legacy_format` from `src/specify_cli/task_utils/support.py` (import + branch + `__all__`)
6. Remove `is_legacy_format` from `src/specify_cli/task_utils/__init__.py` (re-export + `__all__`)
7. Remove `is_legacy_format` from `src/specify_cli/tasks_support.py` (re-export)
8. Remove `is_legacy_format` from `src/specify_cli/scripts/tasks/task_helpers.py` (re-export + `__all__`)
9. Remove `is_legacy_format` from `src/specify_cli/acceptance/__init__.py` (import + branch); add pre-3.0 skip
10. Remove `_check_legacy_format` + `is_legacy_format` from `src/specify_cli/scripts/tasks/tasks_cli.py`; add guard wire-in
11. Wire guard into `src/specify_cli/cli/commands/agent/tasks.py` at mutation command entry points
12. Delete `src/specify_cli/legacy_detector.py`
13. Update tests

---

## Test Gap Analysis (NFR-004)

Existing tests that exercise the legacy path and must be updated:

| Test | Current behavior | Required change |
|------|-----------------|-----------------|
| `tests/specify_cli/test_standalone_tasks_cli_canonical.py::test_src_tasks_cli_check_legacy_format_warns_once` | Creates pre-3.0 fixture; asserts `_check_legacy_format` returns `True` and warns | Convert to test `check_pre30_layout` raises `Pre30LayoutError` (or that the command exits non-zero). Positive guard test counts toward NFR-004. |
| `tests/test_dashboard/test_scanner.py::test_build_kanban_stats_handles_absent_and_legacy_paths` | `monkeypatch.setattr(scanner, "is_legacy_format", ...)` | Update monkeypatch target to `specify_cli.upgrade.legacy_detector.is_legacy_format` or patch via `scanner` module attribute. |
| `tests/test_dashboard/test_scanner.py::test_process_wp_file_raises_without_canonical_log_for_nonlegacy` | Same monkeypatch | Update target path |
| `tests/test_dashboard/test_api_handler.py` (3 occurrences) | `patch.object(features_module, "is_legacy_format", ...)` | Update to `specify_cli.upgrade.legacy_detector` import path |
| `tests/architectural/test_no_dead_symbols.py` | Grandfathered `specify_cli.scripts.tasks.task_helpers::is_legacy_format` | Remove this entry from the grandfathered list |
| `tests/specify_cli/scripts/test_task_helpers.py` | Asserts `is_legacy_format` in `__all__` | Remove that assertion |

New tests to add (NFR-004 ≥2 tests):

| Test | Description |
|------|-------------|
| `tests/upgrade/test_pre30_guard.py::test_guard_rejects_pre30_project` | Creates `tasks/planned/WP01.md` fixture; calls `check_pre30_layout`; asserts `Pre30LayoutError` raised with correct message content. |
| `tests/upgrade/test_pre30_guard.py::test_guard_passes_post30_project` | Creates flat `tasks/WP01.md` fixture; calls `check_pre30_layout`; asserts no exception raised (returns cleanly). |

---

## Documentation Update Analysis (FR-011)

`docs/status-model.md` currently reads (line 21):
> "WP frontmatter is for **static definition only** (title, dependencies, subtasks) -- the `lane` field is no longer written or read by active runtime code"

And line 23:
> "Frontmatter `lane` is a **historical/migration-only** concept retained in migration code paths for backward compatibility"

These are already largely correct. The update required for FR-011 is:
1. Add a section (or expand the "Troubleshooting" section at line 358) that explicitly states pre-3.0 lane-directory shapes (`tasks/planned/`, `tasks/doing/`, etc.) are **not tolerated by active commands** — users must run `spec-kitty upgrade` first.
2. Update the migration section at line 180 ("Migration behavior (for pre-3.0 features)") to clarify that `spec-kitty upgrade` is the mandatory first step before any active command will work.

`docs/reference/cli-commands.md` at line 4092 already marks `validate-tasks` as "LEGACY" — no change needed.
