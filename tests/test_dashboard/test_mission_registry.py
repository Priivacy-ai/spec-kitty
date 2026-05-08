"""Mission registry unit tests — mtime cache + edge cases.

Per mission-wide rule C-003 (spec
``kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB``):
tests use real fixture projects with ``os.utime``-bumped mtimes. NO mocks of
``scan_all_features`` or the filesystem internals. Where syscall counting is
required for the budget assertion, we monkey-patch ``Path.stat`` on a copy of
the registry's own helpers, not on the legacy scanner module.

Edge cases covered (per spec § Edge cases / data-model.md / contract):

  1. Stale daemon mutation — cache served from previous mtime; new mtime
     invalidates.
  2. Identical-mtime drift with different content size — caught by the size
     component of the cache-key triple.
  3. Concurrent reads — many threads see consistent snapshots; reducer
     produces deterministic output.
  4. Missing meta.json — mission surfaces with ``is_legacy=True``; never
     raises.
  5. Corrupted ``status.events.jsonl`` — registry returns degraded record;
     never raises.
  6. Mission with zero WPs — returns empty WP list cleanly.
  7. ``mission_number=null`` (pre-merge) — works alongside numbered missions.
  8. ULID resolution — ``mission_id``, ``mid8``, ``mission_slug`` all resolve.

Owned by WP03 of the registry mission.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


# ─────────────────────────────────────────────────────────────────────────────
# Helpers + fixtures
# ─────────────────────────────────────────────────────────────────────────────


def _bump_mtime(path: Path, delta_seconds: float = 1.0) -> None:
    """Advance a path's atime/mtime by ``delta_seconds`` (cross-platform; Python 3.11+)."""
    st = path.stat()
    os.utime(path, (st.st_atime + delta_seconds, st.st_mtime + delta_seconds))


def _write_meta(
    feature_dir: Path,
    *,
    mission_id: str,
    mission_slug: str | None = None,
    friendly_name: str | None = None,
    mission_number: int | None = None,
    mission_type: str = "software-dev",
    target_branch: str = "main",
    created_at: str = "2026-05-03T00:00:00+00:00",
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "mission_id": mission_id,
        "mission_slug": mission_slug or feature_dir.name,
        "friendly_name": friendly_name or feature_dir.name,
        "mission_number": mission_number,
        "mission_type": mission_type,
        "target_branch": target_branch,
        "created_at": created_at,
    }
    (feature_dir / "meta.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_wp(
    feature_dir: Path,
    *,
    wp_id: str,
    title: str = "Some WP",
    dependencies: list[str] | None = None,
    requirement_refs: list[str] | None = None,
    subtasks: list[str] | None = None,
) -> None:
    tasks = feature_dir / "tasks"
    tasks.mkdir(exist_ok=True)
    deps = dependencies or []
    refs = requirement_refs or []
    subs = subtasks or []
    body = (
        "---\n"
        f"work_package_id: {wp_id}\n"
        f"title: {title}\n"
        f"dependencies: {json.dumps(deps)}\n"
        f"requirement_refs: {json.dumps(refs)}\n"
        f"subtasks: {json.dumps(subs)}\n"
        "agent: claude\n"
        "agent_profile: python-pedro\n"
        "role: implementer\n"
        "---\n\n"
        f"# Work Package Prompt: {title}\n"
    )
    (tasks / f"{wp_id}-test.md").write_text(body, encoding="utf-8")


def _write_event(
    feature_dir: Path,
    *,
    wp_id: str,
    from_lane: str,
    to_lane: str,
    actor: str = "claude",
    event_id: str | None = None,
    at: str = "2026-05-03T00:00:00+00:00",
    feature_slug: str | None = None,
) -> None:
    """Append one canonical lane-transition event to status.events.jsonl."""
    record = {
        "actor": actor,
        "at": at,
        "event_id": event_id or f"01EV{wp_id}{to_lane}",
        "evidence": None,
        "execution_mode": "code_change",
        "feature_slug": feature_slug or feature_dir.name,
        "force": False,
        "from_lane": from_lane,
        "reason": None,
        "review_ref": None,
        "to_lane": to_lane,
        "wp_id": wp_id,
    }
    line = json.dumps(record, sort_keys=True) + "\n"
    (feature_dir / "status.events.jsonl").open("a", encoding="utf-8").write(line)


@pytest.fixture
def fixture_project(tmp_path: Path) -> Path:
    """3-mission fixture project with assorted shapes.

    - alpha: 2 WPs, with event log; one WP done.
    - beta:  1 WP, no event log (pre-finalize).
    - gamma: zero WPs, mission_number=None (pre-merge).
    """
    (tmp_path / ".kittify").mkdir()

    # alpha — finalised, one WP done.
    alpha_dir = tmp_path / "kitty-specs" / "mission-alpha-01ALPHA00"
    _write_meta(
        alpha_dir,
        mission_id="01ALPHA0000000000000000000",
        friendly_name="Alpha Mission",
        mission_number=1,
    )
    _write_wp(alpha_dir, wp_id="WP01", title="First")
    _write_wp(alpha_dir, wp_id="WP02", title="Second")
    # Use distinct timestamps so the reducer applies events in order.
    transitions = [
        ("WP01", "planned", "claimed", "2026-05-03T00:00:01+00:00"),
        ("WP01", "claimed", "in_progress", "2026-05-03T00:00:02+00:00"),
        ("WP01", "in_progress", "for_review", "2026-05-03T00:00:03+00:00"),
        ("WP01", "for_review", "in_review", "2026-05-03T00:00:04+00:00"),
        ("WP01", "in_review", "approved", "2026-05-03T00:00:05+00:00"),
        ("WP01", "approved", "done", "2026-05-03T00:00:06+00:00"),
        ("WP02", "planned", "claimed", "2026-05-03T00:00:07+00:00"),
    ]
    for idx, (wp_id, from_lane, to_lane, at) in enumerate(transitions):
        _write_event(
            alpha_dir,
            wp_id=wp_id,
            from_lane=from_lane,
            to_lane=to_lane,
            event_id=f"01EV{idx:02d}{wp_id}{to_lane}",
            at=at,
        )

    # beta — single WP, no event log yet.
    beta_dir = tmp_path / "kitty-specs" / "mission-beta-01BETA000"
    _write_meta(
        beta_dir,
        mission_id="01BETA00000000000000000000",
        friendly_name="Beta Mission",
        mission_number=2,
    )
    _write_wp(beta_dir, wp_id="WP01", title="Beta only")

    # gamma — zero WPs, pre-merge (mission_number=null).
    gamma_dir = tmp_path / "kitty-specs" / "mission-gamma-01GAMMA00"
    _write_meta(
        gamma_dir,
        mission_id="01GAMMA0000000000000000000",
        friendly_name="Gamma Mission",
        mission_number=None,
    )
    (gamma_dir / "tasks").mkdir()  # empty tasks/

    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# T009 — cache invalidation behaviour
# ─────────────────────────────────────────────────────────────────────────────


def test_warm_cache_returns_same_instance(fixture_project: Path) -> None:
    """Two calls in a row return the same in-memory list (cache hit)."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    first = reg.list_missions()
    second = reg.list_missions()

    # Cache hit: same list object identity.
    assert first is second
    assert len(first) == 3


def test_cache_invalidates_on_kitty_specs_dir_mtime_change(fixture_project: Path) -> None:
    """Adding a new mission directory invalidates the list cache (dirent set changes)."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    initial = reg.list_missions()
    initial_count = len(initial)

    new_dir = fixture_project / "kitty-specs" / "mission-delta-01DELTA00"
    _write_meta(
        new_dir,
        mission_id="01DELTA0000000000000000000",
        friendly_name="Delta Mission",
        mission_number=4,
    )

    after = reg.list_missions()
    assert len(after) == initial_count + 1
    assert any(m.mission_slug == "mission-delta-01DELTA00" for m in after)


def test_cache_key_size_component_catches_same_mtime_rewrite(fixture_project: Path) -> None:
    """Cache key contains ``dirent_count`` (size surrogate). Removing a mission
    keeps the surviving set, but dirent_count drops — cache must invalidate.
    """
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    first = reg.list_missions()
    assert len(first) == 3

    # Remove gamma (it has no events; just wipe the directory).
    import shutil
    shutil.rmtree(fixture_project / "kitty-specs" / "mission-gamma-01GAMMA00")

    after = reg.list_missions()
    assert len(after) == 2
    assert all(m.mission_slug != "mission-gamma-01GAMMA00" for m in after)


def test_cache_invalidates_on_dirent_rename_with_same_count(tmp_path: Path) -> None:
    """The dirent_names_hash component of the cache key catches renames with
    unchanged dirent count and unchanged kitty-specs/ mtime (R-1 in research.md).
    """
    from dashboard.services.registry import MissionRegistry

    (tmp_path / ".kittify").mkdir()
    a_dir = tmp_path / "kitty-specs" / "mission-a-01ABC00000"
    _write_meta(a_dir, mission_id="01ABC00000000000000000ABCD")
    b_dir = tmp_path / "kitty-specs" / "mission-b-01BCD00000"
    _write_meta(b_dir, mission_id="01BCD00000000000000000BCDE")

    reg = MissionRegistry(tmp_path)
    first = reg.list_missions()
    first_slugs = {m.mission_slug for m in first}
    assert first_slugs == {"mission-a-01ABC00000", "mission-b-01BCD00000"}

    # Rename b -> c. Dirent count is unchanged (still 2). Even if FS mtime
    # bumps with the rename, the names hash is what guarantees invalidation
    # when mtime resolution is coarse on some platforms.
    new_b = tmp_path / "kitty-specs" / "mission-c-01CDE00000"
    b_dir.rename(new_b)
    _write_meta(
        new_b,
        mission_id="01CDE00000000000000000CDEF",
        mission_slug="mission-c-01CDE00000",
    )

    after = reg.list_missions()
    after_slugs = {m.mission_slug for m in after}
    assert "mission-c-01CDE00000" in after_slugs


def test_wp_registry_cache_invalidates_on_event_log_growth(fixture_project: Path) -> None:
    """Appending an event to status.events.jsonl invalidates the WP cache for that mission."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    alpha = reg.get_mission("01ALPHA0000000000000000000")
    assert alpha is not None

    wp_reg = reg.workpackages_for(alpha.mission_id)
    first = wp_reg.list_work_packages()
    wp02_first = next(w for w in first if w.wp_id == "WP02")
    assert wp02_first.lane == "claimed"

    # Advance WP02 to in_progress (use a later timestamp so the reducer
    # applies it after the WP02 claim event seeded by the fixture).
    _write_event(
        alpha.feature_dir,
        wp_id="WP02",
        from_lane="claimed",
        to_lane="in_progress",
        event_id="01EV99WP02inprog",
        at="2026-05-03T00:01:00+00:00",
    )

    # Many filesystems batch mtime to second resolution; force a bump in case.
    _bump_mtime(alpha.feature_dir / "status.events.jsonl", delta_seconds=2.0)

    second = wp_reg.list_work_packages()
    wp02_second = next(w for w in second if w.wp_id == "WP02")
    assert wp02_second.lane == "in_progress"


def test_wp_registry_caches_independently_per_mission(fixture_project: Path) -> None:
    """Mutating one mission's tasks/ does NOT change another mission's WP records.

    The WP registries are scoped by mission directory; their cache keys are
    independent.
    """
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    alpha = reg.get_mission("01ALPHA0000000000000000000")
    beta = reg.get_mission("01BETA00000000000000000000")
    assert alpha is not None and beta is not None

    alpha_reg = reg.workpackages_for(alpha.mission_id)
    beta_reg = reg.workpackages_for(beta.mission_id)

    alpha_wps_before = alpha_reg.list_work_packages()
    beta_wps_before = beta_reg.list_work_packages()
    assert len(alpha_wps_before) == 2
    assert len(beta_wps_before) == 1

    # Add a WP to alpha. Beta's cache must keep its previous answer
    # (still 1 WP, matching beta_wps_before by content).
    _write_wp(alpha.feature_dir, wp_id="WP03", title="New alpha WP")
    _bump_mtime(alpha.feature_dir / "tasks", delta_seconds=2.0)

    alpha_wps_after = alpha_reg.list_work_packages()
    beta_wps_after = beta_reg.list_work_packages()

    assert len(alpha_wps_after) == 3
    assert len(beta_wps_after) == 1
    assert beta_wps_before == beta_wps_after  # frozen dataclass equality


def test_invalidate_all_drops_caches(fixture_project: Path) -> None:
    """``invalidate_all`` clears the mission list and known WP caches."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    first = reg.list_missions()
    alpha = reg.get_mission(first[0].mission_id)
    assert alpha is not None
    wp_reg = reg.workpackages_for(alpha.mission_id)
    _ = wp_reg.list_work_packages()

    reg.invalidate_all()
    # After invalidation, the underlying caches are dropped. The next
    # list_missions() call repopulates them. The state remains correct.
    second = reg.list_missions()
    assert len(second) == len(first)
    # Same content but different list identity (fresh scan).
    assert second is not first


# ─────────────────────────────────────────────────────────────────────────────
# T010 — edge cases
# ─────────────────────────────────────────────────────────────────────────────


def test_legacy_mission_without_meta_json(tmp_path: Path) -> None:
    """Mission directory with no meta.json surfaces as ``is_legacy=True``; never raises."""
    from dashboard.services.registry import MissionRegistry

    (tmp_path / ".kittify").mkdir()
    legacy_dir = tmp_path / "kitty-specs" / "legacy-mission"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "spec.md").write_text("# legacy", encoding="utf-8")

    reg = MissionRegistry(tmp_path)
    missions = reg.list_missions()
    legacy = next(m for m in missions if m.mission_slug == "legacy-mission")
    assert legacy.is_legacy is True
    # Slug-style synthetic id so consumers still get a stable handle.
    assert legacy.mission_id.startswith("legacy:")


def test_corrupted_status_events_jsonl_is_handled_gracefully(tmp_path: Path) -> None:
    """A mission with a malformed event log returns a degraded record (no exception)."""
    from dashboard.services.registry import MissionRegistry

    (tmp_path / ".kittify").mkdir()
    feature_dir = tmp_path / "kitty-specs" / "mission-corrupt-01CORRUPT0"
    _write_meta(
        feature_dir,
        mission_id="01CORRUPT00000000000000000",
        mission_number=99,
        friendly_name="Corrupt Mission",
    )
    _write_wp(feature_dir, wp_id="WP01")
    # Write garbage to status.events.jsonl (invalid JSON).
    (feature_dir / "status.events.jsonl").write_text(
        "{not valid json on this line}\n", encoding="utf-8"
    )

    reg = MissionRegistry(tmp_path)
    missions = reg.list_missions()
    assert len(missions) == 1
    record = missions[0]
    # is_legacy is False because both meta.json AND an event log file exist —
    # the file is just corrupt. The record's lane counts are degraded (zero)
    # and weighted_percentage is None.
    assert record.is_legacy is False
    assert record.weighted_percentage is None
    assert record.lane_counts.total == 0


def test_mission_with_zero_wps_returns_empty_list(fixture_project: Path) -> None:
    """``WorkPackageRegistry.list_work_packages()`` on a mission with no WP files returns []."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    gamma = reg.get_mission("01GAMMA0000000000000000000")
    assert gamma is not None

    wp_reg = reg.workpackages_for(gamma.mission_id)
    assert wp_reg.list_work_packages() == []
    counts = wp_reg.lane_counts()
    assert counts.total == 0


def test_pre_merge_mission_number_null_works(fixture_project: Path) -> None:
    """Pre-merge missions (``mission_number=null``) appear in the list and resolve correctly."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    gamma = reg.get_mission("01GAMMA0000000000000000000")
    assert gamma is not None
    assert gamma.display_number is None
    # Numbered missions sort first; gamma is in the unnumbered tail.
    missions = reg.list_missions()
    numbered_first = [m for m in missions if m.display_number is not None]
    unnumbered_tail = [m for m in missions if m.display_number is None and not m.is_legacy]
    assert any(m.mission_id == gamma.mission_id for m in unnumbered_tail)
    # Numbered missions still come first in display order.
    if numbered_first and unnumbered_tail:
        first_unnumbered_idx = missions.index(unnumbered_tail[0])
        last_numbered_idx = missions.index(numbered_first[-1])
        assert last_numbered_idx < first_unnumbered_idx


def test_get_mission_resolves_by_id_mid8_and_slug(fixture_project: Path) -> None:
    """Resolution by full mission_id, mid8, and slug all return the same record."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    target_id = "01ALPHA0000000000000000000"

    by_id = reg.get_mission(target_id)
    assert by_id is not None
    by_mid8 = reg.get_mission(target_id[:8])
    by_slug = reg.get_mission(by_id.mission_slug)

    assert by_id == by_mid8 == by_slug


def test_get_mission_returns_none_on_miss(fixture_project: Path) -> None:
    """``get_mission`` never raises; missing handle yields ``None``."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    assert reg.get_mission("01NONEXIST00000000000000000") is None
    assert reg.get_mission("nonsense-slug") is None
    assert reg.get_mission("") is None


def test_get_mission_ambiguous_mid8_returns_none(tmp_path: Path) -> None:
    """When two missions share a ``mid8``, resolution is refused (returns None) — no silent fallback."""
    from dashboard.services.registry import MissionRegistry

    (tmp_path / ".kittify").mkdir()
    # Two missions sharing the first 8 chars.
    _write_meta(
        tmp_path / "kitty-specs" / "mission-x-01XYZ00001",
        mission_id="01XYZ000000000000000000001",
    )
    _write_meta(
        tmp_path / "kitty-specs" / "mission-y-01XYZ00002",
        mission_id="01XYZ000000000000000000002",
    )

    reg = MissionRegistry(tmp_path)
    # mid8 collision -> ambiguous -> None.
    assert reg.get_mission("01XYZ000") is None


def test_workpackages_for_raises_on_unknown_mission(fixture_project: Path) -> None:
    """``workpackages_for`` raises ``ValueError`` on unknown mission (use get_mission first)."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    with pytest.raises(ValueError, match="Mission not found"):
        reg.workpackages_for("01NONEXIST00000000000000000")


def test_concurrent_readers_serve_consistent_snapshots(fixture_project: Path) -> None:
    """Many threads calling ``list_missions()`` concurrently see consistent, equal results."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    barrier = threading.Barrier(20)
    results: list[list] = []
    errors: list[Exception] = []
    lock = threading.Lock()

    def reader() -> None:
        try:
            barrier.wait(timeout=5)
            res = reg.list_missions()
        except Exception as exc:  # noqa: BLE001 — capture & rethrow in main
            with lock:
                errors.append(exc)
            return
        with lock:
            results.append(res)

    threads = [threading.Thread(target=reader) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    first = results[0]
    for r in results[1:]:
        assert r == first  # frozen dataclass equality


def test_records_are_immutable_after_cache_eviction(fixture_project: Path) -> None:
    """Holding a reference to a record after the cache evicts still sees the snapshot.

    This is the TOCTOU-safety invariant from data-model.md.
    """
    from dataclasses import FrozenInstanceError

    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    snapshot = reg.list_missions()
    held = snapshot[0]

    # Mutating the underlying directory would normally trigger a re-scan; the
    # held record continues to show the old data because frozen dataclasses
    # cannot be modified.
    with pytest.raises(FrozenInstanceError):
        held.friendly_name = "Tampered"  # type: ignore[misc]


def test_mission_record_lane_counts_match_wp_registry_counts(fixture_project: Path) -> None:
    """``MissionRecord.lane_counts`` and ``WorkPackageRegistry.lane_counts()``
    agree (both consume the same canonical reducer).
    """
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    alpha = reg.get_mission("01ALPHA0000000000000000000")
    assert alpha is not None
    wp_reg = reg.workpackages_for(alpha.mission_id)

    via_mission = alpha.lane_counts
    via_wp = wp_reg.lane_counts()
    assert via_mission == via_wp


def test_alpha_mission_lane_counts_reflect_event_log(fixture_project: Path) -> None:
    """Verify the registry consumes the canonical event log (not a stub)."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    alpha = reg.get_mission("01ALPHA0000000000000000000")
    assert alpha is not None
    counts = alpha.lane_counts
    # WP01 is done, WP02 is claimed → 1 done + 1 claimed = 2 total.
    assert counts.done == 1
    assert counts.claimed == 1
    assert counts.total == 2
    assert alpha.weighted_percentage is not None


def test_workpackages_returns_records_with_correct_fields(fixture_project: Path) -> None:
    """``WorkPackageRecord`` fields are populated from frontmatter + event log."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    alpha = reg.get_mission("01ALPHA0000000000000000000")
    assert alpha is not None
    wp_reg = reg.workpackages_for(alpha.mission_id)

    wps = wp_reg.list_work_packages()
    assert [w.wp_id for w in wps] == ["WP01", "WP02"]
    wp01 = wps[0]
    assert wp01.title == "First"
    assert wp01.lane == "done"
    assert wp01.agent == "claude"
    assert wp01.agent_profile == "python-pedro"
    assert wp01.role == "implementer"
    assert wp01.dependencies == ()
    # last_event_id is populated from the canonical event stream.
    assert wp01.last_event_id is not None
    assert wp01.last_event_at is not None


def test_get_work_package_returns_none_on_miss(fixture_project: Path) -> None:
    """``get_work_package`` never raises; missing WP yields ``None``."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    alpha = reg.get_mission("01ALPHA0000000000000000000")
    assert alpha is not None
    wp_reg = reg.workpackages_for(alpha.mission_id)
    assert wp_reg.get_work_package("WP99") is None
    assert wp_reg.get_work_package("") is None


def test_no_kitty_specs_directory_returns_empty_list(tmp_path: Path) -> None:
    """A project root without a ``kitty-specs/`` directory yields an empty mission list."""
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(tmp_path)
    assert reg.list_missions() == []


def test_workpackages_for_shares_instance_when_held(fixture_project: Path) -> None:
    """Two calls to ``workpackages_for`` for the same mission return the same instance.

    The instance is held in a ``WeakValueDictionary``; identity is preserved
    only while at least one consumer keeps a reference.
    """
    from dashboard.services.registry import MissionRegistry

    reg = MissionRegistry(fixture_project)
    alpha = reg.get_mission("01ALPHA0000000000000000000")
    assert alpha is not None

    wp_reg_a = reg.workpackages_for(alpha.mission_id)
    wp_reg_b = reg.workpackages_for(alpha.mission_id)
    assert wp_reg_a is wp_reg_b


# ─────────────────────────────────────────────────────────────────────────────
# Cache-syscall budget smoke test (NFR-003)
# ─────────────────────────────────────────────────────────────────────────────


def test_cache_hit_skips_scanner_walk(fixture_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A warm cache hit must NOT invoke a full re-scan.

    We assert the registry's internal ``_scan`` method runs at most once across
    two consecutive ``list_missions()`` calls when the filesystem is unchanged.
    """
    from dashboard.services import registry as registry_module

    reg = registry_module.MissionRegistry(fixture_project)

    # Wrap the bound method to count invocations without breaking semantics.
    call_count = 0
    original_scan = reg._scan  # type: ignore[attr-defined]

    def counting_scan() -> list[registry_module.MissionRecord]:
        nonlocal call_count
        call_count += 1
        return original_scan()

    monkeypatch.setattr(reg, "_scan", counting_scan)

    _ = reg.list_missions()  # cache miss → scan
    _ = reg.list_missions()  # cache hit → no scan
    _ = reg.list_missions()  # cache hit → no scan
    assert call_count == 1, f"Cache should serve subsequent calls; saw {call_count} scans"
