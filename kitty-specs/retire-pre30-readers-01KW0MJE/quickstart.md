# Developer Quickstart: Retire pre-3.0 status/task readers from active runtime

**Mission**: retire-pre30-readers-01KW0MJE  
**Branch**: `kitty/mission-retire-pre30-readers-01KW0MJE`

---

## What this mission does

This mission removes pre-3.0 lane-directory detection from the active runtime command paths and moves it to the migration/upgrade namespace. After this mission:

1. Running any `spec-kitty agent tasks *` or `spec-kitty agent status emit` command against a pre-3.0 project (one with `tasks/planned/`, `tasks/doing/`, etc. subdirectories containing `.md` files) exits non-zero with: `"Pre-3.0 layout detected ... Run spec-kitty upgrade to migrate."`
2. `specify_cli.legacy_detector` is no longer in the active runtime import graph; it moves to `specify_cli.upgrade.legacy_detector`.
3. All `if use_legacy` branches are gone from `locate_work_package`, `_iter_work_packages`, `tasks_cli.py::list_command`.

---

## Key files and their role

| File | Role |
|------|------|
| `src/specify_cli/upgrade/legacy_detector.py` | NEW: relocated from `src/specify_cli/legacy_detector.py` |
| `src/specify_cli/upgrade/pre30_guard.py` | NEW: boundary guard module (`check_pre30_layout`, `Pre30LayoutError`) |
| `src/specify_cli/legacy_detector.py` | DELETED after IC-01 relocation |
| `src/specify_cli/task_utils/support.py` | MODIFIED: remove `is_legacy_format` import + `use_legacy` branch from `locate_work_package` |
| `src/specify_cli/task_utils/__init__.py` | MODIFIED: remove `is_legacy_format` re-export |
| `src/specify_cli/tasks_support.py` | MODIFIED: remove `is_legacy_format` re-export |
| `src/specify_cli/scripts/tasks/task_helpers.py` | MODIFIED: remove `is_legacy_format` re-export + `__all__` entry |
| `src/specify_cli/scripts/tasks/tasks_cli.py` | MODIFIED: replace `_check_legacy_format` with `check_pre30_layout` call; remove `list_command` legacy branch |
| `src/specify_cli/acceptance/__init__.py` | MODIFIED: remove `use_legacy` branch; add pre-3.0 skip with log |
| `src/specify_cli/dashboard/scanner.py` | MODIFIED: update import to `upgrade.legacy_detector`; remove `_get_kanban_task_data_for_feature` legacy branch; retain annotation calls |
| `src/specify_cli/dashboard/handlers/features.py` | MODIFIED: update import to `upgrade.legacy_detector` |
| `src/specify_cli/cli/commands/agent/tasks.py` | MODIFIED: wire `check_pre30_layout` at mutation command entry points |

---

## Implementation sequence

Work through the IC concerns in order — IC-01 unblocks IC-02, IC-02 unblocks IC-03, then IC-04 and IC-05 can proceed in parallel:

### Step 1: Relocate the module (IC-01)

```bash
# Copy the file
cp src/specify_cli/legacy_detector.py src/specify_cli/upgrade/legacy_detector.py

# Update the docstring to say "Migration/upgrade namespace — do not import from active runtime"
# Keep __all__ identical

# Remove from shim chain (4 files):
# - src/specify_cli/task_utils/support.py  (remove import on line 14; remove from __all__)
# - src/specify_cli/task_utils/__init__.py (remove re-export + __all__ entry)
# - src/specify_cli/tasks_support.py       (remove re-export)
# - src/specify_cli/scripts/tasks/task_helpers.py (remove re-export + __all__ entry)
```

Verify nothing is broken yet: `ruff check . && mypy src/specify_cli/task_utils/`

### Step 2: Create boundary guard (IC-02)

Create `src/specify_cli/upgrade/pre30_guard.py`:
- `Pre30LayoutError` exception
- `check_pre30_layout(feature_path: Path) -> None`
- See `contracts/pre30-guard-contract.md` for exact message format

Write `tests/upgrade/test_pre30_guard.py` with T-GUARD-01 through T-GUARD-04.

```bash
pytest tests/upgrade/test_pre30_guard.py -v
```

### Step 3: Remove active-runtime legacy branches (IC-03)

In `src/specify_cli/task_utils/support.py::locate_work_package`:
- Remove `use_legacy = is_legacy_format(feature_path)` and the entire `if use_legacy:` block (keeps only the flat-layout `else:` block)
- Remove `is_legacy_format` from `__all__`

In `src/specify_cli/acceptance/__init__.py::_iter_work_packages`:
- Remove `use_legacy` branch; add pre-3.0 skip (see `data-model.md` for pseudo-code)
- Keep `is_legacy_format` import from `specify_cli.upgrade.legacy_detector` for the skip check

In `src/specify_cli/scripts/tasks/tasks_cli.py`:
- Delete `_check_legacy_format` function entirely
- Delete `_legacy_warning_shown` global
- Delete `is_legacy_format` and `LANES` (if used only by legacy branch) from `task_helpers` import
- In `update_command`: replace `if _check_legacy_format(feature, repo_root): sys.exit(1)` with `check_pre30_layout(feature_path)` call
- In `list_command`: add `check_pre30_layout(feature_path)` before iteration; remove `use_legacy` branch

Wire `check_pre30_layout` in `src/specify_cli/cli/commands/agent/tasks.py` for each `@app.command` that mutates WPs: `move_task`, `mark_status`, `finalize_tasks`, `status`. Call it after `feature_path` is resolved.

```bash
pytest tests/specify_cli/ tests/cross_cutting/ -x --dist loadfile -n auto
```

### Step 4: Update dashboard imports (IC-04)

In `src/specify_cli/dashboard/scanner.py`:
- Line 16: change `from specify_cli.legacy_detector import` → `from specify_cli.upgrade.legacy_detector import`
- Remove the `use_legacy` branch in `_get_kanban_task_data_for_feature` (lines 855–870); return early with a lean `is_legacy: true` annotation
- Keep `is_legacy_format` calls in `_build_kanban_stats` (line 703) and `_process_wp_file` (line 796) — these are read-only annotation paths

In `src/specify_cli/dashboard/handlers/features.py`:
- Line 30: same import path update

Update test patches:
- `tests/test_dashboard/test_scanner.py`: update `monkeypatch.setattr` paths
- `tests/test_dashboard/test_api_handler.py`: update `patch.object` paths

```bash
pytest tests/test_dashboard/ -v
```

### Step 5: Clean up tests and docs (IC-05)

1. `tests/specify_cli/test_standalone_tasks_cli_canonical.py::test_src_tasks_cli_check_legacy_format_warns_once` — rename and rewrite to test hard-reject (`Pre30LayoutError` / non-zero exit).
2. `tests/specify_cli/scripts/test_task_helpers.py` — remove `is_legacy_format` from `__all__` assertion.
3. `tests/architectural/test_no_dead_symbols.py` — remove the `specify_cli.scripts.tasks.task_helpers::is_legacy_format` entry from the grandfathered list.
4. `docs/status-model.md` — add one paragraph under "Troubleshooting" explicitly stating pre-3.0 lane-directory shapes require `spec-kitty upgrade` before any active command will work.

### Step 6: Delete the original module

Only after all import references are removed and tests pass:

```bash
rm src/specify_cli/legacy_detector.py
ruff check . && mypy src/ && pytest tests/ -x --dist loadfile -n auto
```

---

## Quality gates before marking WP done

```bash
# 1. Ruff — zero violations
ruff check .

# 2. mypy — zero issues
mypy src/specify_cli/upgrade/legacy_detector.py src/specify_cli/upgrade/pre30_guard.py

# 3. Terminology guard (touches src/ prose)
pytest tests/architectural/test_no_legacy_terminology.py

# 4. Full test suite
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider

# 5. NFR-004 guard tests
pytest tests/upgrade/test_pre30_guard.py -v

# 6. Upgrade regression
pytest tests/upgrade/ tests/specify_cli/integration/test_migration_e2e.py -v
```

---

## Off-limits files

Do NOT touch:
- `src/specify_cli/status/store.py`
- `src/specify_cli/status/reducer.py`
- `src/specify_cli/upgrade/migrations/m_0_9_0_frontmatter_only_lanes.py`
- `src/specify_cli/upgrade/runner.py`
- `src/specify_cli/upgrade/registry.py`

See `research.md` section "Off-Limits Files" for rationale.
