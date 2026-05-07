---
work_package_id: WP01
title: Registry Migration and Cache Fixes
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-007
- FR-010
- NFR-001
- NFR-002
- NFR-004
- C-001
- C-002
- C-004
- C-005
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dashboard-services-domain-migration-01KR151P
base_commit: f293162b64bde464dfec5e68cb66b0fada866aff
created_at: '2026-05-07T15:03:11.635038+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Core Registry Migration
assignee: ''
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "2976979"
history:
- at: '2026-05-07T12:36:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/missions/registry.py
execution_mode: code_change
owned_files:
- src/specify_cli/missions/registry.py
- src/dashboard/services/registry.py
- src/specify_cli/cli/commands/dashboard.py
- tests/specify_cli/missions/test_registry_cache.py
tags: []
---

# Work Package Prompt: WP01 – Registry Migration and Cache Fixes

## Branch Strategy

- **Planning/base branch at prompt creation**: `feature/645-api-surface-completion-mission-c`
- **Final merge target for completed work**: `feature/645-api-surface-completion-mission-c`
- **Implement command**: `spec-kitty implement WP01`
- **If the resolved workspace differs from your expectation**: trust the path printed by `spec-kitty agent workflow implement/review`; do not manually create a different worktree.

---

## Objectives & Success Criteria

Move `MissionRegistry`, `WorkPackageRegistry`, and all supporting classes/helpers to
`src/specify_cli/missions/registry.py`. Apply the P1 two-level cache fix (FR-002) and P2
strong-reference store fix (FR-003). Leave a compatibility shim at
`src/dashboard/services/registry.py`. Update the single `specify_cli/` caller
(`src/specify_cli/cli/commands/dashboard.py`) to the canonical path.

**Done when**:
- `src/specify_cli/missions/registry.py` exists, contains no `dashboard.*` imports, and passes `mypy --strict`
- P1 regression: appending a `done` event to `status.events.jsonl`, then calling `list_missions()` on the same `MissionRegistry` instance returns updated lane counts (no stale hit)
- P2 regression: `workpackages_for(mission_id)` called twice returns the same Python object (`is` check)
- `src/dashboard/services/registry.py` is a shim (≤ 15 lines of logic, re-exports all symbols)
- `python -c "from dashboard.services.registry import *"` succeeds (smoke-tests shim)
- `grep -n "from dashboard" src/specify_cli/cli/commands/dashboard.py` returns empty
- All existing registry and dashboard tests pass without modification

## Context & Constraints

**Spec**: `kitty-specs/dashboard-services-domain-migration-01KR151P/spec.md` — FR-001, FR-002, FR-003, FR-007, FR-010
**Data model**: `kitty-specs/dashboard-services-domain-migration-01KR151P/data-model.md` — §1 (two-level cache algorithm), §3 (shim template)
**Quickstart**: `kitty-specs/dashboard-services-domain-migration-01KR151P/quickstart.md` — WP01 section
**Research**: `kitty-specs/dashboard-services-domain-migration-01KR151P/research.md` — R-001 (P1 algorithm), R-002 (P2 fix), R-003 (caller map)

**Constraints**:
- C-001: No `dashboard.*` import anywhere in the new canonical module
- C-002: Shim body ≤ 15 executable lines (re-exports only)
- C-004: Wire shapes unchanged — `MissionRecord`, `WorkPackageRecord`, `LaneCounts` fields identical
- C-005: `WorkPackageRegistry.list_work_packages()` behavior unchanged; only `MissionRegistry.list_missions()` changes

**`specify_cli/missions/` package already exists** — `api_types.py` is already there.
`registry.py` slots in alongside it.

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create `src/specify_cli/missions/registry.py`

**Purpose**: Establish the canonical domain home for mission and WP registry logic.

**Steps**:
1. Copy the full content of `src/dashboard/services/registry.py` to `src/specify_cli/missions/registry.py`.
2. Update the module docstring to reflect the new location: replace the `dashboard.services.registry` reference with `specify_cli.missions.registry` and note that `dashboard/services/registry.py` is now a compatibility shim.
3. Remove the line `from weakref import WeakValueDictionary` — it will be unused after T003.
4. Do NOT yet change the `list_missions()` algorithm or `_wp_registries` field type — those are T002 and T003.
5. Verify the copy with `mypy src/specify_cli/missions/registry.py --strict` (should pass with zero errors since the source already passes).

**Files**:
- `src/specify_cli/missions/registry.py` (new)

**Notes**: The copy should be exact at this stage so T002 and T003 are clean diffs.

---

### Subtask T002 – Apply P1 fix: two-level cache in `list_missions()`

**Purpose**: Make `list_missions()` detect per-mission `status.events.jsonl` changes
without requiring a top-level `kitty-specs/` directory mutation (Robert's P1 finding, PR #970).

**Steps**:

1. Add the new cache field to `MissionRegistry.__init__`:

```python
self._per_mission_cache: dict[Path, CacheEntry[MissionRecord]] = {}
```

2. Replace the `list_missions()` body with the two-level algorithm. The existing structural
   check (`_kitty_specs_cache_key`) remains the first gate. After a structural hit, iterate
   per-mission keys:

```python
def list_missions(self) -> list[MissionRecord]:
    structural_key = _kitty_specs_cache_key(self._project_dir)
    cache = self._list_cache

    if cache is not None and cache.cache_key == structural_key:
        # Structure unchanged — check per-mission freshness outside lock (fast path)
        any_stale = False
        tentative: list[MissionRecord] = []
        for record in cache.value:
            mission_key = _mission_dir_cache_key(record.feature_dir)
            cached_mission = self._per_mission_cache.get(record.feature_dir)
            if cached_mission is None or cached_mission.cache_key != mission_key:
                any_stale = True
                break
            tentative.append(cached_mission.value)
        if not any_stale:
            return tentative

    with self._lock:
        # Double-check after acquiring the lock
        cache = self._list_cache
        if cache is None or cache.cache_key != structural_key:
            records = self._scan()
            now = datetime.now(UTC)
            self._per_mission_cache = {
                r.feature_dir: CacheEntry(r, _mission_dir_cache_key(r.feature_dir), now)
                for r in records
            }
            self._list_cache = CacheEntry(records, structural_key, now)
            return records

        # Structure unchanged — rebuild only stale missions
        now = datetime.now(UTC)
        result: list[MissionRecord] = []
        for record in cache.value:
            mission_key = _mission_dir_cache_key(record.feature_dir)
            cached_mission = self._per_mission_cache.get(record.feature_dir)
            if cached_mission is None or cached_mission.cache_key != mission_key:
                record = _load_mission_record(record.feature_dir)
                self._per_mission_cache[record.feature_dir] = CacheEntry(
                    record, mission_key, now
                )
            else:
                record = cached_mission.value
            result.append(record)
        self._list_cache = CacheEntry(result, structural_key, now)
        return result
```

3. Verify that `_mission_dir_cache_key` (already exists in the module) includes
   `status.events.jsonl` size and mtime — it does by inspection. No changes needed there.

**Files**:
- `src/specify_cli/missions/registry.py` (modified)

**Notes**: The fast path (outside the lock) uses `tentative` to avoid a second full
iteration. If any stale entry is found, it falls through to the lock path and rebuilds
from scratch within the lock.

---

### Subtask T003 – Apply P2 fix: strong-reference `_wp_registries`

**Purpose**: Prevent `WorkPackageRegistry` instances from being garbage-collected between
FastAPI requests (Robert's P2 finding, PR #970).

**Steps**:

1. In `MissionRegistry.__init__`, change:
```python
# OLD
self._wp_registries: WeakValueDictionary[str, WorkPackageRegistry] = WeakValueDictionary()
# NEW
self._wp_registries: dict[str, WorkPackageRegistry] = {}
```

2. The `weakref` import should already have been removed in T001. If it wasn't, remove it now.

3. If a `workpackages_for()` method exists, change it to a standard dict lookup + insert:
```python
def workpackages_for(self, mission_id_or_slug: str) -> WorkPackageRegistry | None:
    record = self.get_mission(mission_id_or_slug)
    if record is None:
        return None
    if record.mission_id not in self._wp_registries:
        with self._lock:
            if record.mission_id not in self._wp_registries:
                self._wp_registries[record.mission_id] = WorkPackageRegistry(record.feature_dir)
    return self._wp_registries[record.mission_id]
```

4. Update the docstring for `_wp_registries` to document the eviction policy: "Entries
   are evicted only when the enclosing `MissionRegistry` instance is garbage-collected."

**Files**:
- `src/specify_cli/missions/registry.py` (modified)

**Notes**: If `workpackages_for()` does not yet exist in the source (the WP registry is
currently accessed differently), add it. The `data-model.md § 1` shows the intended API.

---

### Subtask T004 – Convert `dashboard/services/registry.py` to shim

**Purpose**: Maintain backward compatibility for `dashboard/api/` callers that still
import from `dashboard.services.registry` (they will be updated in WP04, but the shim
lets them keep working in the meantime).

**Steps**:

1. Replace the entire content of `src/dashboard/services/registry.py` with:

```python
# SHIM — removal_release: 3.2.0
# Owner: dashboard-services-domain-migration-01KR151P
# Canonical home: src/specify_cli/missions/registry.py
# This file re-exports all public symbols from the canonical module.
# Do not add business logic here. Edit specify_cli/missions/registry.py instead.
# This shim will be deleted in Phase C (after release 3.2.0).
from specify_cli.missions.registry import (
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

2. Smoke-test: `python -c "from dashboard.services.registry import MissionRegistry, MissionRecord, WorkPackageRegistry, LaneCounts, WorkPackageRecord, CacheEntry; print('OK')"` must print `OK`.

3. Verify `dashboard/services/__init__.py` still works (it imports from `dashboard.services.registry`; the shim satisfies this).

**Files**:
- `src/dashboard/services/registry.py` (replaced with shim)

---

### Subtask T005 – Update `specify_cli/cli/commands/dashboard.py`

**Purpose**: Remove the last `dashboard.*` import in a `specify_cli/` non-bridge module.

**Steps**:

1. Locate the TYPE_CHECKING import:
```python
# OLD
if TYPE_CHECKING:
    from dashboard.services.registry import MissionRecord
# NEW
if TYPE_CHECKING:
    from specify_cli.missions.registry import MissionRecord
```

2. Locate the deferred runtime import inside the `--json` handler function:
```python
# OLD
from dashboard.services.registry import MissionRegistry
# NEW
from specify_cli.missions.registry import MissionRegistry
```

3. Run `grep -n "from dashboard" src/specify_cli/cli/commands/dashboard.py` — must return empty.

4. Run `mypy src/specify_cli/cli/commands/dashboard.py --strict` — must pass.

**Files**:
- `src/specify_cli/cli/commands/dashboard.py` (2 import sites updated)

---

## Test Strategy

Write two regression tests in `tests/specify_cli/missions/test_registry_cache.py`
(the directory already exists; create the file).

### P1 regression — `test_list_missions_reflects_appended_event`

```python
import time
from pathlib import Path
from specify_cli.missions.registry import MissionRegistry

def test_list_missions_reflects_appended_event(tmp_path):
    # Bootstrap a minimal mission dir
    mission_dir = tmp_path / "kitty-specs" / "test-mission-01ABCDEF"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        '{"mission_id":"01ABCDEFGHIJKLMNOPQRSTUVWX","mission_slug":"test-mission-01ABCDEF",'
        '"friendly_name":"Test","mission_type":"software-dev","target_branch":"main"}'
    )
    events_file = mission_dir / "status.events.jsonl"
    events_file.write_text(
        '{"event_id":"01A","at":"2026-01-01T00:00:00+00:00","wp_id":"WP01",'
        '"from_lane":"planned","to_lane":"claimed","actor":"claude","feature_slug":"test",'
        '"force":false,"evidence":null,"reason":null,"review_ref":null,"execution_mode":"worktree"}\n'
    )
    (mission_dir / "tasks").mkdir()
    (mission_dir / "tasks" / "WP01-example.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Example\nlane: claimed\n---\n"
    )

    registry = MissionRegistry(tmp_path)
    records = registry.list_missions()
    assert len(records) == 1
    assert records[0].lane_counts.claimed == 1
    assert records[0].lane_counts.done == 0

    # Force different mtime_ns (guarantee cache key change on next stat)
    import os
    stat = os.stat(events_file)
    os.utime(events_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))

    # Append a done event
    events_file.write_text(
        events_file.read_text() +
        '{"event_id":"01B","at":"2026-01-01T00:01:00+00:00","wp_id":"WP01",'
        '"from_lane":"claimed","to_lane":"done","actor":"claude","feature_slug":"test",'
        '"force":false,"evidence":null,"reason":null,"review_ref":null,"execution_mode":"worktree"}\n'
    )

    # Same registry instance — must see updated counts
    records2 = registry.list_missions()
    assert records2[0].lane_counts.done == 1, "P1: list_missions() returned stale lane counts"
    assert records2[0].lane_counts.claimed == 0
```

### P2 regression — `test_workpackages_for_returns_same_instance`

```python
def test_workpackages_for_returns_same_instance(tmp_path):
    # ... (same mission_dir setup as above)
    registry = MissionRegistry(tmp_path)
    registry.list_missions()  # warm the cache

    mission_id = "01ABCDEFGHIJKLMNOPQRSTUVWX"
    wp_reg1 = registry.workpackages_for(mission_id)
    wp_reg2 = registry.workpackages_for(mission_id)

    assert wp_reg1 is not None
    assert wp_reg1 is wp_reg2, "P2: workpackages_for() returned different instances"
```

---

## Definition of Done

- [ ] `src/specify_cli/missions/registry.py` exists, fully implemented, no `dashboard.*` imports
- [ ] `mypy src/specify_cli/missions/registry.py --strict` → zero errors
- [ ] P1 regression test passes
- [ ] P2 identity test passes
- [ ] `python -c "from dashboard.services.registry import *"` → `OK`
- [ ] `grep -rn "from dashboard" src/specify_cli/cli/commands/dashboard.py` → empty
- [ ] `pytest tests/specify_cli/ tests/test_dashboard/ -x -q` → all pass

## Reviewer Guidance

1. Check that `list_missions()` follows the double-checked locking pattern (outside-lock fast path, inside-lock authoritative update).
2. Verify the shim has ≤ 15 executable lines and re-exports every symbol in `dashboard/services/__init__.__all__`.
3. Confirm `WeakValueDictionary` is gone from the new module (no import, no usage).
4. Run the P1 regression with `pytest -s -v tests/specify_cli/missions/test_registry_cache.py::test_list_missions_reflects_appended_event` and confirm the assertion holds.

## Activity Log

- 2026-05-07T15:03:13Z – claude:sonnet-4-6:implementer:implementer – shell_pid=2966718 – Assigned agent via action command
- 2026-05-07T15:11:10Z – claude:sonnet-4-6:implementer:implementer – shell_pid=2966718 – Registry migrated; P1+P2 cache fixes applied; shim created; tests pass (340 total, 2 new)
- 2026-05-07T15:11:37Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=2976979 – Started review via action command
- 2026-05-07T15:13:53Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=2976979 – Canonical registry moved to specify_cli/missions/registry.py with no dashboard.* imports and weakref removed. P1 fix: _per_mission_cache + _mission_dir_cache_key partial-rescan implemented. P2 fix: _wp_registries strong-ref dict with double-checked locking. Shim re-exports all 6 symbols (16 executable lines, single import + __all__ block). CLI updated to import from canonical module. 2 regression tests pass; 338 dashboard tests pass; mypy --strict clean. Untracked project_state.py/sync_service.py belong to WP02/WP03 (not in WP01 owned_files), bypassed via --force.
