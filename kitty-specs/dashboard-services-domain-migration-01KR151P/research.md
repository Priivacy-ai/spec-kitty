# Phase 0 Research: Dashboard Services Domain Migration (Phase B)

*Mission: `dashboard-services-domain-migration-01KR151P`*
*Date: 2026-05-07*

---

## R-001 — P1 Cache Fix: Two-Level Cache Design (Option A)

**Decision**: Implement Option A — a two-level cache with separate structural and
per-mission content keys.

**Rationale**: Option A ("partial rescan") was selected by stakeholder. The design stores:
1. `_list_cache: CacheEntry[list[MissionRecord]] | None` keyed on `_kitty_specs_cache_key`
   (top-level `kitty-specs/` mtime + dirent count + hash). Detects structural changes:
   new missions added, missions deleted.
2. `_per_mission_cache: dict[Path, CacheEntry[MissionRecord]]` keyed on
   `_mission_dir_cache_key(feature_dir)` per mission. Detects content changes: event-log
   appends, `meta.json` edits.

**list_missions() lookup algorithm**:

```
structural_key = _kitty_specs_cache_key(project_dir)

if _list_cache is None or _list_cache.cache_key != structural_key:
    # Directory structure changed — full rescan; rebuild both caches
    records = _full_scan()
    _per_mission_cache = {r.feature_dir: CacheEntry(r, _mission_dir_cache_key(r.feature_dir)) for r in records}
    _list_cache = CacheEntry(records, structural_key)
    return records

# Structure unchanged — check per-mission freshness
result = []
any_stale = False
for record in _list_cache.value:
    mission_key = _mission_dir_cache_key(record.feature_dir)
    cached = _per_mission_cache.get(record.feature_dir)
    if cached is None or cached.cache_key != mission_key:
        record = _load_mission_record(record.feature_dir)  # targeted rescan
        _per_mission_cache[record.feature_dir] = CacheEntry(record, mission_key)
        any_stale = True
    else:
        record = cached.value
    result.append(record)

if any_stale:
    _list_cache = CacheEntry(result, structural_key)  # refresh list snapshot
return result
```

**Concurrency**: The outer `threading.Lock` already used in `list_missions()` covers
the two-level check atomically; double-checked locking pattern carries over unchanged.

**Performance**: Per-mission cache key computation calls `os.stat()` on `meta.json`,
`status.events.jsonl`, and `tasks/` — 3–4 stat calls per mission. For 150 missions this
is ~450–600 stat calls per `list_missions()` on a warm structural cache but with stale
mission keys. On a fully warm cache (no changes) this reduces to zero stat calls inside
the mission loop (cache hit at structural key short-circuits). NFR-003 (≤ 5 ms overhead)
is achievable because stat calls are O(1) per file and do not involve directory walks.

**Alternatives considered**: Option B (composite key including max mtime of all event
logs) was rejected by stakeholder. It would trigger a full list rescan whenever any single
mission changes, which is acceptable at small scale but wasteful for large projects.

---

## R-002 — P2 Fix: Strong-Reference WorkPackageRegistry Store

**Decision**: Replace `WeakValueDictionary[str, WorkPackageRegistry]` with
`dict[str, WorkPackageRegistry]`.

**Rationale**: `WeakValueDictionary` allows GC to collect `WorkPackageRegistry` instances
between FastAPI requests because the router only holds a local variable reference. The
fix is a one-line change: `dict` has strong references. The eviction policy is documented
as "entries evicted when the enclosing `MissionRegistry` is collected" — suitable because
`MissionRegistry` lives in `app.state` for the FastAPI lifetime, and as a short-lived
object in CLI contexts.

**Memory bound**: A `WorkPackageRegistry` holds a `CacheEntry[list[WorkPackageRecord]]`
(typically < 1 KB per mission; 150 missions ≈ 150 KB). This is negligible.

---

## R-003 — Caller Migration Map

Complete inventory of `dashboard.*` imports in `specify_cli/` and the required updates:

### `specify_cli/cli/commands/dashboard.py`

| Current import | Updated import |
|---|---|
| `from dashboard.services.registry import MissionRecord` (TYPE_CHECKING) | `from specify_cli.missions.registry import MissionRecord` |
| `from dashboard.services.registry import MissionRegistry` (deferred, inside function) | `from specify_cli.missions.registry import MissionRegistry` |

### `specify_cli/dashboard/handlers/api.py`

| Current import | Updated import |
|---|---|
| `from dashboard.services.sync import _build_trigger_request as _build_sync_trigger_request` (top-level) | `from specify_cli.missions.sync_service import _build_trigger_request as _build_sync_trigger_request` |
| `from dashboard.services.project_state import ProjectStateService` (deferred) | `from specify_cli.missions.project_state import ProjectStateService` |
| `from dashboard.services.sync import SyncService` (deferred) | `from specify_cli.missions.sync_service import SyncService` |

### `specify_cli/dashboard/handlers/features.py`

| Current import | Updated import |
|---|---|
| `from dashboard.services.mission_scan import MissionScanService` (deferred, ×2 locations) | `from specify_cli.missions.scan_service import MissionScanService` |
| `from dashboard.services.mission_scan import MissionScanService, parse_kanban_path` (deferred) | `from specify_cli.missions.scan_service import MissionScanService, parse_kanban_path` |

### `dashboard/api/` callers (FR-013 — direct import preferred)

| File | Current import | Updated import |
|---|---|---|
| `dashboard/api/app.py` | `from dashboard.services.registry import MissionRegistry` | `from specify_cli.missions.registry import MissionRegistry` |
| `dashboard/api/deps.py` | `from dashboard.services.registry import MissionRegistry` | `from specify_cli.missions.registry import MissionRegistry` |
| `dashboard/api/routers/missions.py` | `from dashboard.services.registry import MissionRecord, MissionRegistry, WorkPackageRecord` | `from specify_cli.missions.registry import MissionRecord, MissionRegistry, WorkPackageRecord` |
| `dashboard/api/routers/health.py` | `from dashboard.services.project_state import ProjectStateService` | `from specify_cli.missions.project_state import ProjectStateService` |
| `dashboard/api/routers/sync.py` | `from dashboard.services.sync import SyncService` | `from specify_cli.missions.sync_service import SyncService` |

### `specify_cli/missions/scan_service.py` (moved module — internal fix required)

`MissionScanService.__init__` contains a **runtime** (non-TYPE_CHECKING) deferred import:
```python
from dashboard.services.registry import MissionRegistry
```
This is inside `__init__` as the fallback when no `registry` is injected. After the move,
this must become:
```python
from specify_cli.missions.registry import MissionRegistry
```
The `TYPE_CHECKING` import block at module top must also be updated:
```python
if TYPE_CHECKING:
    from specify_cli.missions.registry import MissionRecord, MissionRegistry
```

---

## R-004 — Architectural Test Strategy (FR-014)

**Finding**: `tests/architectural/test_dashboard_boundary.py::test_no_upstream_dashboard_imports`
already implements the C-009 check using AST scanning. It currently has two exemptions:

1. `specify_cli/cli/commands/dashboard.py` — in `_ALLOWED_BOUNDARY_FILES` (line 138)
2. `specify_cli/dashboard/` — entire subpackage skipped by path check (line 150)

**WP04 task** (not "add new assertion" but "tighten existing assertion"):
1. After WP01 fixes `dashboard.py`, **remove** it from `_ALLOWED_BOUNDARY_FILES`.
2. After WP02 and WP03 fix the handlers, **narrow** the `specify_cli/dashboard/`
   exclusion to skip only files that are legitimately bridge code — specifically the
   `__init__.py` and `lifecycle.py` in that package (if they still import from
   `dashboard.*`). Handlers must no longer be in the exclusion.

**Synthetic violation test**: Add a test that temporarily injects a forbidden import
into a fixture file and asserts the boundary check catches it (satisfies the FR-014
requirement to verify the extended assertion catches a synthetic violation).

---

## R-005 — Shim Pattern

**Precedent**: No shims are currently registered in `architecture/2.x/shim-registry.yaml`
(the file reads `shims: []`). These four shims are the first entries under the
`migration-shim-ownership-rules-01KPDYDW` governance framework.

**Shim template** (each of the four `dashboard/services/*.py` files):

```python
# SHIM — removal_release: 3.2.0
# Owner: dashboard-services-domain-migration-01KR151P
# This module re-exports from its canonical home. See architecture/2.x/shim-registry.yaml.
# Do not add business logic here; edit specify_cli/missions/<module>.py instead.
from specify_cli.missions.<module> import *  # noqa: F401,F403
from specify_cli.missions.<module> import (
    # explicit named exports to satisfy mypy --strict (star import insufficient)
    Symbol1,
    Symbol2,
    ...
)
__all__ = ["Symbol1", "Symbol2", ...]
```

**shim-registry.yaml entry shape** (per the schema in `migration-shim-ownership-rules-01KPDYDW`):

```yaml
- path: src/dashboard/services/registry.py
  grandfathered: false
  owner_mission: dashboard-services-domain-migration-01KR151P
  removal_release: "3.2.0"
  canonical_path: src/specify_cli/missions/registry.py
  reason: "Phase B service placement remediation — inverted dependency repair"
```

**Note on `dashboard/services/__init__.py`**: This facade re-exports from
`dashboard.services.registry`. After that module becomes a shim, the facade continues
to work (two-hop re-export). The `__init__.py` itself does NOT need a shim registration
because it imports from a sibling module (not the other way), and it will be deleted
together with the shims in Phase C.

---

## R-006 — WP Sequencing and Lane Assignment

**Dependency graph**:

- WP01 (Registry) → WP02 depends on it (runtime import in `MissionScanService.__init__`)
- WP03 (ProjectState + Sync) has no dependency on WP01 or WP02
- WP04 (Governance + Tests) depends on WP01 + WP02 + WP03

**Recommended lane structure**:

```
Lane A: WP01 → WP02 → WP04
Lane B: WP03
```

WP03 and WP02 can run in parallel (different service classes, different callers).
WP04 must follow all three because it removes the exemptions from the boundary test
and writes the P1/P2 regression tests (which require the canonical modules to exist).

---

## R-007 — Test Directory

`tests/specify_cli/missions/` already exists (confirmed by `ls tests/specify_cli/`).
The P1 and P2 regression tests (`test_registry_cache.py`) can be placed there directly.
No new test directory scaffolding required.

---

## Summary of Resolved Decisions

| Question | Decision |
|---|---|
| P1 cache approach | Option A: two-level cache (`_per_mission_cache: dict[Path, CacheEntry[MissionRecord]]`) |
| P2 fix | `dict[str, WorkPackageRegistry]`; eviction on `MissionRegistry` GC |
| Shim removal_release | `3.2.0` (current: 3.2.0a11) |
| FR-014 implementation | Tighten existing C-009 test exemptions; add synthetic violation fixture |
| `MissionScanService` runtime import | Deferred runtime import (not just TYPE_CHECKING) must also be updated to `specify_cli.missions.registry` |
| WP lane layout | Lane A: WP01→WP02→WP04; Lane B: WP03 (parallel with WP02) |
| Test placement | `tests/specify_cli/missions/test_registry_cache.py` (directory exists) |
