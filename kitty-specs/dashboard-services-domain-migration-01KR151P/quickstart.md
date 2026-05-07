# Quickstart: Dashboard Services Domain Migration (Phase B)

*Mission: `dashboard-services-domain-migration-01KR151P`*

---

## What this mission does

Moves four domain services out of `src/dashboard/services/` into
`src/specify_cli/missions/`, fixes two cache correctness bugs, and leaves thin
re-export shims behind. After this mission, no module inside `specify_cli/` or
`kernel/` imports from `dashboard.*` — enforced at CI level.

---

## WP order and lane layout

```
Lane A: WP01 → WP02 → WP04
Lane B:         WP03
```

- **WP01** must land first: `MissionScanService` (WP02) has a runtime dependency on
  `MissionRegistry` and needs the new path to exist before it can be moved.
- **WP03** is independent: `ProjectStateService` and `SyncService` have no dependency
  on the registry.
- **WP04** is last: it removes the architectural test exemptions (which would fail until
  all callers are updated) and writes the regression tests (which require the canonical
  modules to exist).

---

## WP01 — Registry migration and cache fixes

**New file**: `src/specify_cli/missions/registry.py`

Copy the full implementation from `src/dashboard/services/registry.py`, then apply:

### P1 fix — add `_per_mission_cache` field

```python
# In MissionRegistry.__init__:
self._per_mission_cache: dict[Path, CacheEntry[MissionRecord]] = {}
```

Modify `list_missions()` to:
1. Check `_kitty_specs_cache_key` as before (structural changes)
2. On structural hit, iterate over `_list_cache.value` and compare each
   `_mission_dir_cache_key(record.feature_dir)` against `_per_mission_cache`
3. Rebuild only stale records via `_load_mission_record(feature_dir)`; update
   `_per_mission_cache` and `_list_cache` snapshot

See `data-model.md § 1` for the complete algorithm.

### P2 fix — replace WeakValueDictionary

```python
# Change:
self._wp_registries: WeakValueDictionary[str, WorkPackageRegistry] = WeakValueDictionary()
# To:
self._wp_registries: dict[str, WorkPackageRegistry] = {}
```

Remove the `from weakref import WeakValueDictionary` import.

Update `workpackages_for()` to use a regular dict lookup + insert pattern.

**Convert `src/dashboard/services/registry.py` to shim** (see shim template in
`data-model.md § 3`).

**Update caller**: `src/specify_cli/cli/commands/dashboard.py`
- TYPE_CHECKING import: `from specify_cli.missions.registry import MissionRecord`
- Deferred runtime import: `from specify_cli.missions.registry import MissionRegistry`

---

## WP02 — MissionScanService migration

**New file**: `src/specify_cli/missions/scan_service.py`

Copy from `src/dashboard/services/mission_scan.py`, then fix imports:

```python
# TYPE_CHECKING block — update:
if TYPE_CHECKING:
    from specify_cli.missions.registry import MissionRecord, MissionRegistry

# __init__ method — update the fallback import:
# Change:
from dashboard.services.registry import MissionRegistry
# To:
from specify_cli.missions.registry import MissionRegistry
```

**Convert `src/dashboard/services/mission_scan.py` to shim**.

**Update caller**: `src/specify_cli/dashboard/handlers/features.py`
- Both deferred import sites: `from specify_cli.missions.scan_service import MissionScanService`
- Second site: `from specify_cli.missions.scan_service import MissionScanService, parse_kanban_path`

---

## WP03 — ProjectStateService and SyncService migration

**New files**:
- `src/specify_cli/missions/project_state.py` — copy from `dashboard/services/project_state.py`; no import updates needed (no `dashboard.*` imports in that file)
- `src/specify_cli/missions/sync_service.py` — copy from `dashboard/services/sync.py`; no import updates needed

**Convert both source files to shims**.

**Update caller**: `src/specify_cli/dashboard/handlers/api.py`

```python
# Top-level import — update:
from specify_cli.missions.sync_service import _build_trigger_request as _build_sync_trigger_request
# Deferred imports — update:
from specify_cli.missions.project_state import ProjectStateService
from specify_cli.missions.sync_service import SyncService
```

---

## WP04 — API consumers, shim registry, tests, ADR

### 1. Update `dashboard/api/` consumers (FR-013)

| File | Symbol(s) to update |
|---|---|
| `src/dashboard/api/app.py` | `MissionRegistry` |
| `src/dashboard/api/deps.py` | `MissionRegistry` |
| `src/dashboard/api/routers/missions.py` | `MissionRecord`, `MissionRegistry`, `WorkPackageRecord` |
| `src/dashboard/api/routers/health.py` | `ProjectStateService` |
| `src/dashboard/api/routers/sync.py` | `SyncService` |

Change each import from `dashboard.services.*` → `specify_cli.missions.*`.

### 2. Register shims (`architecture/2.x/shim-registry.yaml`)

Replace `shims: []` with the four entries from `data-model.md § 4`.

Verify with: `spec-kitty doctor shim-registry`

### 3. Tighten `test_no_upstream_dashboard_imports` (FR-014)

In `tests/architectural/test_dashboard_boundary.py`:

```python
# a) Remove dashboard.py from _ALLOWED_BOUNDARY_FILES (now imports from specify_cli.missions)
_ALLOWED_BOUNDARY_FILES = frozenset()   # empty after WP01

# b) Narrow specify_cli/dashboard/ exclusion
# Change the broad skip:
#   py_file.relative_to(src_root / "specify_cli" / "dashboard")
#   continue  # inside specify_cli/dashboard/ — skip
# To a targeted skip of files that still legitimately bridge (inspect what remains):
#   If specify_cli/dashboard/handlers/*.py no longer import from dashboard.*
#   after WP02+WP03, the entire exclusion can be removed.
#   If any file in specify_cli/dashboard/ still legitimately imports dashboard.*,
#   list it explicitly in _ALLOWED_BOUNDARY_FILES instead of skipping the whole tree.
```

Add synthetic violation test:
```python
def test_boundary_check_catches_synthetic_violation(tmp_path):
    # Write a temporary .py file that imports from dashboard
    f = tmp_path / "fake_specify_cli_module.py"
    f.write_text("from dashboard.services.registry import MissionRegistry\n")
    # Run the boundary scan logic against this file and assert it's detected
    ...
```

### 4. Write regression tests (`tests/specify_cli/missions/test_registry_cache.py`)

Follow the test contracts from `data-model.md § 6`.

### 5. File ADR (`architecture/2.x/adr/2026-05-07-1-dashboard-services-phase-b.md`)

Required sections: Context, Decision, Rationale, Consequences, Phase C plan,
Relationship to #992. Cross-link from `architecture/2.x/adr/README.md`.

---

## Verification checklist

After each WP:

```bash
cd src && pytest tests/ -x -q              # all tests pass
mypy src/ --strict --quiet                 # zero new errors
spec-kitty doctor shim-registry            # clean (after WP04)
grep -rn "from dashboard" src/specify_cli/ # should print only specify_cli/dashboard/ bridge files
```

After WP04 (complete):
```bash
# Verify C-009 is now enforced with no remaining exemptions needed
python -m pytest tests/architectural/test_dashboard_boundary.py -v
# Expect: PASSED with no violations
```
