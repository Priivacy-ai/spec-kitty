# Contract — `MissionRegistry` and `WorkPackageRegistry` Public Interface

This is the canonical Python contract for the registry. Every transport-side consumer (FastAPI router, CLI command, future MCP tool) MUST consume mission/WP data exclusively through these methods. Direct scanner imports from transport modules are forbidden by `tests/architectural/test_transport_does_not_import_scanner.py` (FR-009).

## Construction

```python
from pathlib import Path
from dashboard.services.registry import MissionRegistry

registry = MissionRegistry(project_dir=Path("/path/to/spec-kitty/repo"))
```

- `project_dir` MUST be the spec-kitty project root (the directory containing `kitty-specs/`).
- The constructor is cheap — no filesystem reads. The first cache miss happens on the first method call.
- One instance per process is the recommended lifecycle. The dashboard FastAPI app stashes one on `app.state.mission_registry` at startup; the CLI constructs one per invocation.
- Constructing a second instance against the same `project_dir` is supported but each instance has its own cache (no shared state).

## `MissionRegistry.list_missions()`

```python
def list_missions(self) -> list[MissionRecord]:
    """Return every mission under kitty-specs/ in display order.

    Display order: missions with assigned `display_number` come first, sorted
    ascending; missions without (pre-merge) come next, sorted by `created_at`
    descending; legacy missions (no meta.json) come last, sorted by directory
    name.

    Cache behaviour:
    - First call: scans kitty-specs/, opens every meta.json, returns full list.
    - Subsequent calls (warm cache, no mtime change): returns cached list with
      ≤ 3 stat syscalls (one each for kitty-specs/ dirent listing, the
      mission-list cache key file, and the dirent name hash check).
    - mtime change in kitty-specs/ dirent listing (mission added/removed):
      full rescan.
    - mtime change in any individual mission's meta.json: that mission's
      MissionRecord is refreshed from disk; other missions' records served
      from cache.

    Error contract: never raises. A malformed meta.json produces a
    MissionRecord with is_legacy=True and best-effort field values.
    """
```

## `MissionRegistry.get_mission(mission_id_or_slug)`

```python
def get_mission(self, mission_id_or_slug: str) -> MissionRecord | None:
    """Resolve a mission by mission_id (ULID), mid8 (8-char prefix), or slug.

    Resolution precedence: mission_id > mid8 > mission_slug. The same handle
    semantics as `spec-kitty agent context resolve --mission <handle>`.

    Returns None on miss. Never raises.

    Cache behaviour:
    - Reuses the same cache as list_missions(); no separate per-mission lookup.
    - Cache stale-check happens on every call (3 stat syscalls).

    Error contract: an ambiguous handle (e.g., a mid8 that matches two
    missions) returns None. Callers needing strict disambiguation should call
    list_missions() and filter.
    """
```

## `MissionRegistry.workpackages_for(mission_id_or_slug)`

```python
def workpackages_for(self, mission_id_or_slug: str) -> WorkPackageRegistry:
    """Return a WorkPackageRegistry scoped to one mission.

    The returned registry has its own per-mission cache. Mission-level mtime
    changes (e.g. meta.json rewrite) do NOT invalidate the WP cache; only
    changes under kitty-specs/<slug>/tasks/ or kitty-specs/<slug>/status.events.jsonl
    do.

    Raises ValueError if the mission does not exist (use get_mission first if
    you need to handle the missing case gracefully).

    Cache behaviour:
    - Each call returns a NEW WorkPackageRegistry instance (cheap; no
      filesystem reads in the constructor).
    - Multiple instances for the same mission share the same cache via a
      WeakValueDictionary keyed by mission_id.
    """
```

## `MissionRegistry.invalidate_all()`

```python
def invalidate_all(self) -> None:
    """Force a full cache flush across mission-level AND all WP-level caches.

    For test use ONLY. Production consumers MUST rely on mtime-based
    invalidation. Documented here for completeness; flagged with a comment
    in the registry source pointing at the test-only contract.
    """
```

## `WorkPackageRegistry.list_work_packages()`

```python
def list_work_packages(self) -> list[WorkPackageRecord]:
    """Return every WP for the mission this registry is scoped to.

    Order: ascending by wp_id (lexicographic; "WP01" < "WP02" < ... < "WP10").

    Cache behaviour: keyed on the (mtime, dirent set, status.events.jsonl
    mtime) triple for kitty-specs/<slug>/tasks/ and the events log.

    Error contract: never raises. A malformed WP frontmatter produces a
    WorkPackageRecord with best-effort fields (lane="planned" if the events
    log is silent, agent=None, etc.).
    """
```

## `WorkPackageRegistry.get_work_package(wp_id)`

```python
def get_work_package(self, wp_id: str) -> WorkPackageRecord | None:
    """Resolve one WP by ID. Returns None on miss. Never raises."""
```

## `WorkPackageRegistry.lane_counts()`

```python
def lane_counts(self) -> LaneCounts:
    """Aggregate lane counts across this mission's WPs.

    Same data as MissionRecord.lane_counts but accessed via the WP-scoped
    cache (cheaper if the caller already has a WorkPackageRegistry handle).
    """
```

## Threading model

- All registry methods are safe to call from multiple threads concurrently.
- Cache mutations use a per-cache `threading.Lock` to serialise writes; concurrent reads see either the pre-update or the post-update snapshot, never a torn one.
- The dashboard FastAPI app under uvicorn is single-process / single-threaded by default; the lock cost is bounded.

## Forbidden usage patterns

The following patterns are forbidden by `tests/architectural/test_transport_does_not_import_scanner.py` (FR-009):

```python
# ❌ FORBIDDEN — direct scanner import in a transport module
from specify_cli.dashboard.scanner import scan_all_features

# ❌ FORBIDDEN — direct scanner import via the legacy shim
from specify_cli.scanner import build_mission_registry

# ❌ FORBIDDEN — direct filesystem walk in a router body
for mission_dir in (request.app.state.project_dir / "kitty-specs").iterdir():
    ...
```

Allowed:

```python
# ✅ ALLOWED — registry is the canonical reader
from dashboard.services.registry import MissionRegistry

registry = MissionRegistry(project_dir=request.app.state.project_dir)
missions = registry.list_missions()
```

## Migration guide for existing transport code

| Old pattern | New pattern |
|-------------|-------------|
| `from specify_cli.dashboard.scanner import scan_all_features` | `from dashboard.services.registry import MissionRegistry` |
| `scan_all_features(project_dir)` | `registry.list_missions()` |
| `scan_feature_kanban(project_dir, feature_id)` | `registry.workpackages_for(feature_id).list_work_packages()` |
| `build_mission_registry(project_dir)` | `registry.list_missions()` |
| `resolve_active_feature(project_dir)` | (still in `MissionScanService` for active-mission logic; the service itself now uses the registry) |
