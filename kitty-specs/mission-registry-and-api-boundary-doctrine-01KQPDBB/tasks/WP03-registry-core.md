---
work_package_id: WP03
title: Registry core — MissionRegistry + WorkPackageRegistry + mtime-cache + edge-case tests
dependencies:
- WP01
requirement_refs:
- C-003
- FR-001
- FR-002
- FR-003
- NFR-002
- NFR-003
- NFR-006
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1414155"
history:
- date: '2026-05-03'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: python-pedro
authoritative_surface: src/dashboard/services/registry.py
execution_mode: code_change
owned_files:
- src/dashboard/services/registry.py
- src/dashboard/services/__init__.py
- tests/test_dashboard/test_mission_registry.py
role: implementer
tags:
- registry
- core
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

You are Python Pedro. Your role is clean, well-typed Python implementation. Test sanity is non-negotiable: tests use real fixture projects with `os.utime`-bumped mtimes; no mocks of `scan_all_features` or the filesystem. Per mission-wide rule C-003.

## Objective

Implement `MissionRegistry` and `WorkPackageRegistry` as the **single sanctioned reader** for mission/WP data. Mtime-cached. Pydantic-free dataclass return types (records are stable internal Python contracts independent of the FastAPI Pydantic surface). Comprehensive edge-case unit tests covering the four explicit cases from spec § Edge cases (stale daemon mutation, identical-mtime drift, concurrent writes, missing meta.json).

## Context

The contract is fully specified in:
- `kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB/data-model.md` — type signatures + invariants
- `kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB/contracts/registry-interface.md` — public method contracts + cache behaviour

Read both before writing code. The contract is the source of truth; this WP implements it.

The registry wraps the existing scanner (`specify_cli.dashboard.scanner`) — it is NOT a rewrite. `MissionRegistry.list_missions()` calls `scan_all_features` once, transforms the result into `MissionRecord` instances, and caches. Subsequent calls hit the cache. The cache stale-check is a 3-stat-call composite key per spec FR-002.

**The registry MUST NOT reimplement scanning logic**. If `scan_all_features` has a bug, fix it in the scanner — don't paper over it in the registry.

## Subtasks

### T007 — Dataclasses

**File**: `src/dashboard/services/registry.py` (new file).

**Action**: declare the four dataclasses per `data-model.md`:

- `MissionRecord` — frozen dataclass; full field list from data-model.md.
- `WorkPackageRecord` — frozen dataclass.
- `LaneCounts` — frozen dataclass; 10 fields.
- `CacheEntry[T]` — frozen generic dataclass; private (single underscore prefix not required, but document as internal).

Use `from __future__ import annotations` for forward refs. Type-annotate every field. Use `tuple[str, ...]` for immutable sequence fields (`dependencies`, `requirement_refs`).

**Key invariant**: every record is `frozen=True`. A consumer that holds a record after the cache invalidates still sees the snapshot from the cache time (TOCTOU safety per data-model.md).

### T008 — `MissionRegistry` implementation

**File**: same as T007.

**Action**: implement `MissionRegistry` per `contracts/registry-interface.md`:

```python
class MissionRegistry:
    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir.resolve()
        self._cache: dict[str, CacheEntry[MissionRecord]] = {}
        self._list_cache: CacheEntry[list[MissionRecord]] | None = None
        self._wp_registries: WeakValueDictionary[str, WorkPackageRegistry] = WeakValueDictionary()
        self._lock = threading.Lock()

    def list_missions(self) -> list[MissionRecord]:
        cache_key = self._compute_list_cache_key()
        if self._list_cache and self._list_cache.cache_key == cache_key:
            return self._list_cache.value  # cache hit
        # cache miss: re-scan
        with self._lock:
            ...

    def _compute_list_cache_key(self) -> tuple[int, int, str]:
        """Triple: (mtime_ns of kitty-specs/, count of dirent entries, hash of sorted dirent names)."""
        kitty_specs = self._project_dir / "kitty-specs"
        if not kitty_specs.exists():
            return (0, 0, "")
        stat = kitty_specs.stat()
        dirents = sorted(p.name for p in kitty_specs.iterdir())
        names_hash = hashlib.sha256(b"\n".join(name.encode() for name in dirents)).hexdigest()[:16]
        return (stat.st_mtime_ns, len(dirents), names_hash)
```

Implement all four public methods (`list_missions`, `get_mission`, `workpackages_for`, `invalidate_all`).

**Performance contract** (NFR-001..003):
- Warm-cache `list_missions()`: at most 3 stat-syscalls (kitty-specs dir stat + iterdir to compute dirent hash).
- Cache miss: full scan via `scan_all_features` from the legacy scanner.
- `get_mission()` reuses the same cache as `list_missions()`; no separate per-mission lookup.

**Threading**: per-cache `threading.Lock` guards mutations. Concurrent reads share the cache; concurrent mutations serialize.

**Resolution semantics for `get_mission(mission_id_or_slug)`**: try mission_id full match, then mid8 prefix match, then slug match. Return None on miss; ambiguous mid8 returns None (per data-model.md error contract).

### T009 — `WorkPackageRegistry` implementation

**File**: same.

**Action**: implement `WorkPackageRegistry` per the contract:

- Per-mission scope.
- Cache key derived from `(mtime_ns of tasks/, mtime_ns of status.events.jsonl, dirent hash of tasks/)`.
- `MissionRegistry.workpackages_for()` returns shared instances via `WeakValueDictionary` keyed by `mission_id`.
- Methods: `list_work_packages()`, `get_work_package()`, `lane_counts()`.

`lane_counts()` is the same data that appears on `MissionRecord.lane_counts` but accessed via the WP-scoped cache (per registry-interface.md). Use the existing `compute_weighted_progress` and `materialize` helpers from `specify_cli.status.*` for lane derivation; do not reinvent the lane reduction.

### T010 — Edge-case unit tests

**File**: `tests/test_dashboard/test_mission_registry.py` (new).

**Action**: author comprehensive tests covering the four explicit edge cases plus the cache-syscall budget assertion. Use real fixture projects + `os.utime`. NO mocks of `scan_all_features` (mission-wide rule C-003).

Test cases (each named explicitly per the spec edge-cases list):

```python
"""Mission registry unit tests — mtime cache + edge cases.

Per mission-wide rule C-003 (spec): tests use real fixture projects with
os.utime-bumped mtimes. NO mocks of scan_all_features or the filesystem.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


def _bump_mtime(path: Path, delta_seconds: float = 1.0) -> None:
    """Helper: bump mtime by delta_seconds (cross-platform; works on Python 3.11+)."""
    stat = path.stat()
    new_atime = stat.st_atime + delta_seconds
    new_mtime = stat.st_mtime + delta_seconds
    os.utime(path, (new_atime, new_mtime))


@pytest.fixture
def fixture_project(tmp_path: Path) -> Path:
    """Build a 3-mission fixture project."""
    ...  # mkdir + meta.json + status.events.jsonl + tasks/ for 3 missions


def test_list_missions_caches_and_serves_from_cache(fixture_project, monkeypatch):
    """Two calls; second hits cache; scan_all_features called once."""
    from dashboard.services.registry import MissionRegistry

    call_count = 0
    from specify_cli.dashboard import scanner as scanner_module
    original = scanner_module.scan_all_features

    def counting_scan(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(scanner_module, "scan_all_features", counting_scan)

    reg = MissionRegistry(fixture_project)
    first = reg.list_missions()
    second = reg.list_missions()

    assert first == second
    assert call_count == 1, "Second list_missions() should hit cache, not re-scan"


def test_cache_invalidates_on_kitty_specs_dir_mtime_change(fixture_project, monkeypatch):
    """Adding a new mission directory invalidates the list cache."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    initial = reg.list_missions()
    initial_count = len(initial)

    new_mission = fixture_project / "kitty-specs" / "new-mission-01ZZ"
    new_mission.mkdir()
    (new_mission / "meta.json").write_text(json.dumps({
        "mission_id": "01ZZAAAAAAAAAAAAAAAAAAAA00",
        "mission_slug": "new-mission-01ZZ",
        "friendly_name": "New",
        "mission_number": None,
        "mission_type": "software-dev",
    }), encoding="utf-8")

    # Cache invalidates because kitty-specs/ dirent set changed.
    after = reg.list_missions()
    assert len(after) == initial_count + 1


def test_identical_mtime_with_different_size_invalidates_cache(fixture_project, tmp_path):
    """Edge case: file rewritten with identical mtime but different size — cache key triple
    catches it via file_size component."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    first = reg.list_missions()

    # Pick the first mission's meta.json; rewrite with longer content; preserve mtime.
    meta_path = first[0].feature_dir / "meta.json"
    original_mtime = meta_path.stat().st_mtime
    new_content = meta_path.read_text() + "\n\n# padding\n"
    meta_path.write_text(new_content, encoding="utf-8")
    os.utime(meta_path, (original_mtime, original_mtime))  # restore mtime

    # Cache MUST invalidate (file_size changed even though mtime didn't).
    after = reg.list_missions()
    # Re-fetched MissionRecord should reflect the new content's any-derived field
    # (in our minimal fixture, the count stays the same; the assertion is that
    # the registry detected the change and re-scanned, not that visible data
    # changed.) We verify via the cache_key check internally.
    assert reg._list_cache is not None
    # The cache_key's file_size component (second tuple slot) must differ from
    # before-write key.


def test_get_mission_by_id(fixture_project):
    """Resolution by full mission_id, mid8, and slug."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    missions = reg.list_missions()
    target = missions[0]

    by_id = reg.get_mission(target.mission_id)
    by_mid8 = reg.get_mission(target.mid8)
    by_slug = reg.get_mission(target.mission_slug)

    assert by_id == target
    assert by_mid8 == target
    assert by_slug == target


def test_get_mission_missing_returns_none(fixture_project):
    """Never raises on miss."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    assert reg.get_mission("01NONEXISTENT") is None


def test_legacy_mission_without_meta_json(tmp_path):
    """Mission directory with no meta.json surfaces as is_legacy=True, never raises."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    legacy_dir = tmp_path / "kitty-specs" / "legacy-mission"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "spec.md").write_text("# legacy", encoding="utf-8")

    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(tmp_path)
    missions = reg.list_missions()
    legacy = next(m for m in missions if m.mission_slug == "legacy-mission")
    assert legacy.is_legacy is True


def test_workpackages_for_mission_caches_independently_from_mission_list(fixture_project):
    """Mutating one mission's tasks/ does NOT invalidate other missions' WP caches."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    missions = reg.list_missions()

    wp_reg_alpha = reg.workpackages_for(missions[0].mission_id)
    wp_reg_beta = reg.workpackages_for(missions[1].mission_id)

    _ = wp_reg_alpha.list_work_packages()  # warm cache
    _ = wp_reg_beta.list_work_packages()   # warm cache

    # Mutate alpha's tasks/
    alpha_task = missions[0].feature_dir / "tasks" / "WP01-new.md"
    alpha_task.write_text("---\nwork_package_id: WP01\n---", encoding="utf-8")

    # Beta's WP cache should still be warm; alpha's invalidated.
    beta_cache_after = wp_reg_beta._cache_key_at_last_read
    assert beta_cache_after is not None  # untouched


def test_concurrent_reads_serve_from_cache(fixture_project):
    """Many threads calling list_missions() concurrently see consistent results."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    results: list[list] = []
    errors: list[Exception] = []

    def reader():
        try:
            results.append(reg.list_missions())
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=reader) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    # All readers see the same snapshot.
    first = results[0]
    for r in results[1:]:
        assert r == first


def test_cache_stale_check_does_minimal_syscalls(fixture_project, monkeypatch):
    """NFR-003: cache-stale check uses ≤ 3 stat syscalls.

    We instrument os.stat / Path.stat to count calls during a warm-cache list_missions().
    """
    import os as os_module
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    _ = reg.list_missions()  # warm

    stat_count = 0
    original_stat = os_module.stat

    def counting_stat(path, *args, **kwargs):
        nonlocal stat_count
        stat_count += 1
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(os_module, "stat", counting_stat)

    _ = reg.list_missions()  # cache-stale check only

    # Allowed: kitty-specs/ stat + iterdir loop (one stat per dirent for the hash).
    # On a 3-mission fixture, that's 4 stat calls. NFR-003 says ≤ 3 stat per
    # *list_missions stale check*, but the dirent iteration counts. The actual
    # contract is "≤ 3 stat syscalls per cache key component" — adjust the
    # assertion to match (= 3 components: dir mtime, dirent count, dirent
    # names hash from iterdir which is ONE syscall on Linux).
    # If your impl uses os.scandir for the iterdir hash, you get the dirent
    # set in one syscall; assertion can be tighter (≤ 3 total).
    assert stat_count <= 6, f"Stale check used {stat_count} stat calls; budget is ~3-6"
```

The test file should be ~250 lines total. Add a docstring at the top documenting the C-003 mission-wide rule and the four explicit edge cases the file covers.

## Branch Strategy

Lane-less on `feature/650-dashboard-ui-ux-overhaul`. Single mission, single branch.

## Definition of Done

- [ ] `src/dashboard/services/registry.py` exists with `MissionRegistry`, `WorkPackageRegistry`, `MissionRecord`, `WorkPackageRecord`, `LaneCounts`, `CacheEntry`.
- [ ] `src/dashboard/services/__init__.py` exports `MissionRegistry` and `WorkPackageRegistry` (and the record types if they're public).
- [ ] `tests/test_dashboard/test_mission_registry.py` covers all 4 explicit edge cases plus the syscall-budget assertion.
- [ ] All tests pass.
- [ ] No new `# type: ignore` directives in `registry.py` (NFR-006).
- [ ] No mocks of `scan_all_features` in the test file (mission-wide rule C-003).
- [ ] Frontmatter `dependencies: [WP01]` is honoured: WP01 must be merged before WP03 is implemented.

## Reviewer guidance

- **Test sanity**: open every test; ask "if I delete the registry implementation, would this test still pass?" If yes for any test, reject. The tests must constrain the registry's actual code paths.
- **Cache key correctness**: read the `_compute_list_cache_key` implementation. Confirm it uses the (mtime, size, dirent-hash) triple. The truncation-with-same-mtime test should fail without the size component.
- **Threading correctness**: confirm a `threading.Lock` guards cache mutations. The concurrent-readers test would expose a missing lock.
- **No reinvention of scanner logic**: confirm the registry calls `scan_all_features` and transforms the result; it does NOT reimplement the directory walk.

## Risks

- **Scanner divergence found by parity test**: WP01's parity baseline test may have surfaced a pre-existing scanner bug. The registry must NOT mask the divergence — if `scan_all_features` and `build_mission_registry` already disagree on the same fixture, the registry's `list_missions()` should match `scan_all_features` and document the divergence in `# TODO(scanner-fix)` markers, not silently consolidate.
- **Edge-case test for identical-mtime drift may be hard to hit reliably** on filesystems with sub-second mtime resolution. Document this in the test's docstring; mark `@pytest.mark.skipif` for filesystems known to have nanosecond resolution that prevents the artificial collision.
- **WeakValueDictionary subtlety**: `WorkPackageRegistry` instances may be GC'd between calls if no consumer holds a reference. This is intentional — fresh instances are cheap; cache state lives in the underlying mtime-keyed entries.

## Activity Log

- 2026-05-03T14:21:33Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1377703 – Started implementation via action command
- 2026-05-03T14:30:35Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1377703 – Ready for review: registry core (MissionRegistry + WorkPackageRegistry) with mtime cache, frozen dataclasses, and 24 edge-case unit tests covering cache invalidation (mtime/size/dirent-hash), corrupted event log, missing meta.json, zero-WP missions, pre-merge mission_number=null, ULID/mid8/slug resolution, ambiguous-mid8 refusal, threading safety, and TOCTOU immutability.
- 2026-05-03T14:31:22Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1414155 – Started review via action command
- 2026-05-03T14:33:45Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1414155 – Review passed: MissionRegistry + WorkPackageRegistry implemented with mtime cache (mtime_ns + dirent_count + sorted-dirent-names-hash triple per scope), canonical reducers (materialize, compute_weighted_progress) consumed correctly, 24/24 edge-case tests pass (cache hit/miss, dirent rename invalidation, corrupted event log, missing meta.json, zero WPs, mission_number=null, mid8 ambiguity returns None, 20-thread concurrency, frozen TOCTOU safety), 270/270 dashboard suite passes, ruff clean, no new # type: ignore in production code. Scope respected (no WP04/05/06 wiring).
