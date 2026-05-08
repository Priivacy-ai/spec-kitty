# Data Model: Dashboard Services Domain Migration (Phase B)

*Mission: `dashboard-services-domain-migration-01KR151P`*
*Date: 2026-05-07*

---

## 1 — MissionRegistry (post-migration)

The `MissionRegistry` class gains a second cache field for per-mission content
invalidation (P1 fix) and changes its WP-registry store from `WeakValueDictionary`
to `dict` (P2 fix).

```python
# src/specify_cli/missions/registry.py

class MissionRegistry:
    _project_dir: Path                                    # unchanged
    _list_cache: CacheEntry[list[MissionRecord]] | None   # unchanged — structural key
    _per_mission_cache: dict[Path, CacheEntry[MissionRecord]]  # NEW — per-mission content key
    _wp_registries: dict[str, WorkPackageRegistry]        # CHANGED: was WeakValueDictionary
    _lock: threading.Lock                                 # unchanged
```

### Cache key semantics

| Field | Key type | Invalidates when |
|---|---|---|
| `_list_cache` | `_kitty_specs_cache_key(project_dir)` — `(mtime_ns, dirent_count, dirent_hash)` of `kitty-specs/` | Mission directory added or deleted |
| `_per_mission_cache[feature_dir]` | `_mission_dir_cache_key(feature_dir)` — `(max_mtime_ns, total_size, tasks_dirent_hash)` over `meta.json + status.events.jsonl + tasks/` | Event-log append, `meta.json` edit, WP file addition |

### `list_missions()` algorithm (P1 fix)

```
def list_missions() -> list[MissionRecord]:
    structural_key = _kitty_specs_cache_key(project_dir)
    cache = _list_cache

    # Fast path: check structural key outside lock
    if cache is not None and cache.cache_key == structural_key:
        result, any_stale = _check_per_mission_freshness(cache.value)
        if not any_stale:
            return result
        # Some missions stale — update under lock

    with _lock:
        # Double-check after lock acquisition
        cache = _list_cache
        if cache is None or cache.cache_key != structural_key:
            records = _scan()  # full walk
            _per_mission_cache = {r.feature_dir: CacheEntry(r, _mission_dir_cache_key(r.feature_dir), now) for r in records}
            _list_cache = CacheEntry(records, structural_key, now)
            return records

        # Structure unchanged; rebuild stale missions only
        result = []
        for record in cache.value:
            mission_key = _mission_dir_cache_key(record.feature_dir)
            cached = _per_mission_cache.get(record.feature_dir)
            if cached is None or cached.cache_key != mission_key:
                record = _load_mission_record(record.feature_dir)
                _per_mission_cache[record.feature_dir] = CacheEntry(record, mission_key, now)
            else:
                record = cached.value
            result.append(record)
        _list_cache = CacheEntry(result, structural_key, now)
        return result
```

### `workpackages_for()` behaviour (P2 fix)

```python
def workpackages_for(self, mission_id_or_slug: str) -> WorkPackageRegistry | None:
    record = self.get_mission(mission_id_or_slug)
    if record is None:
        return None
    # Strong dict — instance survives between requests
    if record.mission_id not in self._wp_registries:
        self._wp_registries[record.mission_id] = WorkPackageRegistry(record.feature_dir)
    return self._wp_registries[record.mission_id]
```

---

## 2 — Module Layout (canonical after migration)

```
src/specify_cli/missions/
├── __init__.py            # existing — no changes
├── api_types.py           # existing — MissionContext, FeaturesListResponse, etc.
├── registry.py            # NEW — MissionRegistry, WorkPackageRegistry, MissionRecord,
│                          #       WorkPackageRecord, LaneCounts, CacheEntry
├── scan_service.py        # NEW — MissionScanService, parse_kanban_path
├── project_state.py       # NEW — ProjectStateService
└── sync_service.py        # NEW — SyncService, SyncTriggerResult, _build_trigger_request
```

---

## 3 — Shim Layout

Each `dashboard/services/*.py` becomes a pure re-export shim with this shape:

```python
# SHIM — removal_release: 3.2.0
# Owner: dashboard-services-domain-migration-01KR151P
# Canonical: specify_cli/missions/<module>.py
from specify_cli.missions.registry import (   # example for registry.py shim
    CacheEntry,
    LaneCounts,
    MissionRecord,
    MissionRegistry,
    WorkPackageRecord,
    WorkPackageRegistry,
)

__all__ = [
    "CacheEntry",
    "LaneCounts",
    "MissionRecord",
    "MissionRegistry",
    "WorkPackageRecord",
    "WorkPackageRegistry",
]
```

`dashboard/services/__init__.py` is **not changed** — it already imports from
`dashboard.services.registry`; after that becomes a shim the facade continues to
work transitively. It is left for Phase C deletion.

---

## 4 — Shim Registry Entries

```yaml
# architecture/2.x/shim-registry.yaml

shims:
  - path: src/dashboard/services/registry.py
    grandfathered: false
    owner_mission: dashboard-services-domain-migration-01KR151P
    removal_release: "3.2.0"
    canonical_path: src/specify_cli/missions/registry.py
    reason: "Phase B service placement — inverted dependency repair (epic #645)"

  - path: src/dashboard/services/mission_scan.py
    grandfathered: false
    owner_mission: dashboard-services-domain-migration-01KR151P
    removal_release: "3.2.0"
    canonical_path: src/specify_cli/missions/scan_service.py
    reason: "Phase B service placement — inverted dependency repair (epic #645)"

  - path: src/dashboard/services/project_state.py
    grandfathered: false
    owner_mission: dashboard-services-domain-migration-01KR151P
    removal_release: "3.2.0"
    canonical_path: src/specify_cli/missions/project_state.py
    reason: "Phase B service placement — inverted dependency repair (epic #645)"

  - path: src/dashboard/services/sync.py
    grandfathered: false
    owner_mission: dashboard-services-domain-migration-01KR151P
    removal_release: "3.2.0"
    canonical_path: src/specify_cli/missions/sync_service.py
    reason: "Phase B service placement — inverted dependency repair (epic #645)"
```

---

## 5 — Architectural Test Changes (FR-014)

```python
# tests/architectural/test_dashboard_boundary.py
# test_no_upstream_dashboard_imports() — BEFORE

_ALLOWED_BOUNDARY_FILES = frozenset({
    src_root / "specify_cli" / "cli" / "commands" / "dashboard.py",  # ← REMOVE after WP01
})
# ... and the broad specify_cli/dashboard/ exclusion covers handlers/  ← NARROW after WP02+WP03

# AFTER (WP04):
# 1. Empty _ALLOWED_BOUNDARY_FILES (dashboard.py no longer imports dashboard.*)
# 2. Change the specify_cli/dashboard/ exclusion to only skip __init__.py
#    (or remove entirely if no remaining legitimate bridge imports exist)
```

---

## 6 — Regression Test Contracts

### P1 test (`test_registry_cache.py::test_list_missions_reflects_appended_event`)

```
Given: a tmp_path with one mission dir containing meta.json, tasks/, status.events.jsonl
       (WP01 in "claimed" lane)
When:  MissionRegistry(tmp_path).list_missions() is called → warm cache
       A "done" event is appended to status.events.jsonl
       list_missions() is called again on the same registry
Then:  returned MissionRecord.lane_counts.done == 1
       returned MissionRecord.lane_counts.claimed == 0
       (no stale cache hit)
```

### P2 test (`test_registry_cache.py::test_workpackages_for_returns_same_instance`)

```
Given: a MissionRegistry with one mission dir
When:  workpackages_for(mission_id) called twice
Then:  both calls return the same WorkPackageRegistry object (assert result1 is result2)
```

---

## 7 — Dependency Direction Diagram (after migration)

```
kernel/api_types.py
    ↑
specify_cli/glossary/types.py       ← GlossaryHealthResponse, GlossaryTermRecord
specify_cli/charter_lint/types.py   ← DecayWatchTileResponse
specify_cli/status/api_types.py     ← KanbanTaskData, KanbanStats, KanbanResponse
specify_cli/missions/api_types.py   ← MissionContext, FeaturesListResponse, ...
    ↑
specify_cli/missions/registry.py    ← MissionRegistry, WorkPackageRegistry (Phase B)
specify_cli/missions/scan_service.py ← MissionScanService (Phase B)
specify_cli/missions/project_state.py ← ProjectStateService (Phase B)
specify_cli/missions/sync_service.py ← SyncService (Phase B)
    ↑
specify_cli/cli/commands/dashboard.py   ← CLI consumer
    ↑
dashboard/api/routers/*.py          ← HTTP transport adapters
dashboard/api/models.py             ← Pydantic DTOs
dashboard/services/*.py             ← shims (→ specify_cli.missions.*) [Phase C: deleted]
```

One-way invariant: `dashboard.*` may import from `specify_cli.*`; `specify_cli.*` and
`kernel.*` must never import from `dashboard.*`. Enforced by
`test_no_upstream_dashboard_imports` with narrowed exemptions after WP04.
