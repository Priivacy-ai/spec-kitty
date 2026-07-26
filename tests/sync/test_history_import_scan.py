"""Tests for the hybrid SCAN stage of ``sync import-history`` — WP-Y2 (#2262).

The SCAN is *hybrid* (§3.4), so the two mission shapes are driven against real
committed fixtures:

* legacy ``032-identity-aware-cli-event-sync`` — lane transitions only, prefix
  SYNTHESIZED from ``meta.json`` + ``tasks/WP*.md``;
* prefixed ``single-mission-surface-resolver-01KVGCE8`` — ``MissionCreated``/
  ``WPCreated`` read ON_DISK.

The local-only filter and the WPCreated-coverage guard are driven against
synthetic missions so the assertions don't depend on fixture drift.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.models import StatusEvent
from specify_cli.sync.history_import.scan import (
    MissionScan,
    MissionScanError,
    PrefixSource,
    _read_importable_lifecycle,
    scan_mission,
    scan_missions,
)

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPECS = _REPO_ROOT / "kitty-specs"
_LEGACY = _SPECS / "032-identity-aware-cli-event-sync"
_PREFIXED = _SPECS / "single-mission-surface-resolver-01KVGCE8"


# ── legacy shape: prefix SYNTHESIZED from meta.json + tasks/ ──────────────────


@pytest.mark.skipif(not _LEGACY.is_dir(), reason="legacy fixture 032 not present")
def test_legacy_mission_synthesizes_prefix_from_meta_and_tasks():
    scan = scan_mission(_LEGACY)

    assert scan.prefix_source is PrefixSource.SYNTHESIZED
    # Identity + display fields resolve from meta.json (verbatim values).
    assert scan.canonical_mission_id == "01KN2371WRE1E2BH9WR11MAGDG"
    assert scan.mission_slug == "032-identity-aware-cli-event-sync"
    assert scan.name == "Identity-Aware CLI Event Sync"
    assert scan.mission_number == 32
    assert scan.mission_type == "software-dev"
    # Legacy has no purpose_tldr; source_description back-fills it.
    assert scan.purpose_tldr and scan.purpose_tldr.startswith("Make CLI events identity-aware")

    # WPs synthesized from tasks/WP01..WP06.md, each with a non-empty title.
    wp_ids = {wp.wp_id for wp in scan.work_packages}
    assert {"WP01", "WP02", "WP03", "WP04", "WP05", "WP06"} <= wp_ids
    assert all(wp.source is PrefixSource.SYNTHESIZED for wp in scan.work_packages)
    assert all(wp.wp_title for wp in scan.work_packages)

    # Lane transitions are read (and are real StatusEvents), and every wp_id
    # they reference has a WPCreated (INV-3 coverage).
    assert scan.lane_transitions
    assert all(isinstance(event, StatusEvent) for event in scan.lane_transitions)
    lane_wp_ids = {event.wp_id for event in scan.lane_transitions if event.wp_id}
    assert lane_wp_ids <= wp_ids


# ── prefixed shape: prefix read ON_DISK ───────────────────────────────────────


@pytest.mark.skipif(not _PREFIXED.is_dir(), reason="prefixed fixture not present")
def test_prefixed_mission_reads_prefix_from_disk():
    scan = scan_mission(_PREFIXED)

    assert scan.prefix_source is PrefixSource.ON_DISK
    assert scan.canonical_mission_id == "01KVGCE8GSJE3BPCG6K5WNCH9B"
    assert scan.name == "Single Mission-Surface Resolver"

    by_id = {wp.wp_id: wp for wp in scan.work_packages}
    # WP08's on-disk WPCreated payload is read verbatim (title + depends_on).
    assert "WP08" in by_id
    wp08 = by_id["WP08"]
    assert wp08.source is PrefixSource.ON_DISK
    assert wp08.wp_title == "Load-bearing architectural guard"
    assert set(wp08.depends_on) == {"WP01", "WP06"}


# ── local-only lifecycle events are dropped ───────────────────────────────────


def _write_events(mission_dir: Path, rows: list[dict]) -> None:
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "status.events.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_local_only_lifecycle_events_are_filtered(tmp_path):
    mission_dir = tmp_path / "synthetic-filter-01AAAA"
    _write_events(
        mission_dir,
        [
            # canonical-event-exempt(exception-flow): on-disk lifecycle row fed into the drop-filter under test
            {"event_type": "MissionCreated", "aggregate_type": "Mission", "payload": {}},
            # canonical-event-exempt(exception-flow): local-only row the filter must drop
            {"event_type": "MissionReopened", "aggregate_type": "Mission", "payload": {}},
            # canonical-event-exempt(exception-flow): local-only row the filter must drop
            {"event_type": "FollowUpRecorded", "aggregate_type": "Mission", "payload": {}},
            # canonical-event-exempt(exception-flow): on-disk lifecycle row fed into the drop-filter under test
            {"event_type": "WPCreated", "aggregate_type": "WorkPackage", "payload": {"wp_id": "WP01"}},
        ],
    )

    kept = {event["event_type"] for event in _read_importable_lifecycle(mission_dir)}
    assert kept == {"MissionCreated", "WPCreated"}
    assert "MissionReopened" not in kept
    assert "FollowUpRecorded" not in kept


# ── WPCreated coverage guard (INV-3) ──────────────────────────────────────────


def test_wp_coverage_backfills_a_wp_referenced_only_by_a_lane_transition(tmp_path):
    """A lane transition for a WP with no task file / no WPCreated still yields
    a WPCreated, so ``WPStatusChanged`` never precedes ``WPCreated``."""
    mission_dir = tmp_path / "synthetic-cov-01BBBB"
    _write_events(
        mission_dir,
        [
            {
                "actor": "migration",
                "at": "2026-02-07T00:00:00Z",
                "event_id": "01KJ5V38V9HRA67BAXKNQDWP99",
                "evidence": None,
                "execution_mode": "direct_repo",
                "force": False,
                "from_lane": "planned",
                "mission_id": None,
                "mission_slug": "synthetic-cov-01BBBB",
                "policy_metadata": None,
                "reason": None,
                "review_ref": None,
                "to_lane": "in_progress",
                "wp_id": "WP99",
            }
        ],
    )

    scan = scan_mission(mission_dir)

    assert scan.lane_transitions and scan.lane_transitions[0].wp_id == "WP99"
    by_id = {wp.wp_id: wp for wp in scan.work_packages}
    assert "WP99" in by_id, "lane-only WP must be backfilled with a WPCreated"
    assert by_id["WP99"].wp_title == "WP99"
    assert by_id["WP99"].source is PrefixSource.SYNTHESIZED
    assert by_id["WP99"].depends_on == ()


def test_work_packages_are_sorted_by_wp_id(tmp_path):
    # Emit WPCreated out of order via the canonical local emitter (not a
    # hand-rolled event); the scan must return them sorted by wp_id.
    from specify_cli.status.lifecycle_events import emit_wp_created_local

    mission_dir = tmp_path / "synthetic-sort-01CCCC"
    mission_dir.mkdir(parents=True)
    for wp_id in ("WP03", "WP01", "WP02"):
        emit_wp_created_local(mission_dir, mission_slug="synthetic-sort-01CCCC", wp_id=wp_id, wp_title=wp_id)

    scan = scan_mission(mission_dir)
    assert [wp.wp_id for wp in scan.work_packages] == ["WP01", "WP02", "WP03"]


# ── batch helper ──────────────────────────────────────────────────────────────


@pytest.mark.skipif(not (_LEGACY.is_dir() and _PREFIXED.is_dir()), reason="fixtures not present")
def test_scan_missions_preserves_input_order():
    scans = scan_missions([_PREFIXED, _LEGACY])
    assert [scan.mission_slug for scan in scans] == [
        "single-mission-surface-resolver-01KVGCE8",
        "032-identity-aware-cli-event-sync",
    ]
    assert all(isinstance(scan, MissionScan) for scan in scans)


# ── malformed WP frontmatter must not abort the scan (#2883 items 3/4) ────────


def test_corrupt_status_log_raises_named_mission_scan_error(tmp_path):
    """A corrupt status.events.jsonl fails closed as MissionScanError naming the
    mission, not a raw StoreError traceback (Stijn's #2884 review, fix #3)."""
    mission_dir = tmp_path / "synthetic-corrupt-01GGGG"
    mission_dir.mkdir(parents=True)
    # A structurally-broken lane row (not a lifecycle event_type row, so it
    # reaches the lane reader) that read_events rejects with StoreError.
    (mission_dir / "status.events.jsonl").write_text("{ this is not valid json\n", encoding="utf-8")

    with pytest.raises(MissionScanError) as excinfo:
        scan_mission(mission_dir)
    assert "synthetic-corrupt-01GGGG" in str(excinfo.value)


def test_malformed_wp_frontmatter_is_skipped_not_fatal(tmp_path):
    """A WP file whose frontmatter parses to a list (not a dict) raises a
    structural TypeError inside the reader. The scan must skip it, not abort —
    otherwise one bad legacy doc sinks the whole import. The skip is fail-LOUD:
    the scan result carries the skipped file names so the report can surface
    them (B3, #2884 review)."""
    mission_dir = tmp_path / "synthetic-malformed-01FFFF"
    tasks = mission_dir / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "WP01-bad.md").write_text("---\n- a\n- b\n---\nbody\n", encoding="utf-8")
    (tasks / "WP02-good.md").write_text(
        "---\nwork_package_id: WP02\ntitle: Good WP\ndependencies: []\n---\nbody\n",
        encoding="utf-8",
    )

    scan = scan_mission(mission_dir)  # must not raise

    # The skip is counted AND named — never silent.
    assert scan.skipped_wp_files == ("WP01-bad.md",)
    # The good sibling still scans (skip is per-file, not per-mission).
    assert [wp.wp_id for wp in scan.work_packages] == ["WP02"]


def test_malformed_wp_referenced_by_a_lane_transition_is_backfilled_no_orphan(tmp_path):
    """A WP whose task file is malformed (skipped) but which a lane transition
    references must still get a WPCreated via coverage backfill — the exact spot
    an orphan WPStatusChanged would appear if _ensure_wp_coverage regressed."""
    mission_dir = tmp_path / "synthetic-orphan-01HHHH"
    tasks = mission_dir / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "WP01-bad.md").write_text("---\n- a\n- b\n---\nbody\n", encoding="utf-8")  # malformed → skipped
    _write_events(
        mission_dir,
        [
            {
                "actor": "migration",
                "at": "2026-02-07T00:00:00Z",
                "event_id": "01KJ5V38V9HRA67BAXKNQDWP01",
                "evidence": None,
                "execution_mode": "direct_repo",
                "force": False,
                "from_lane": "planned",
                "mission_id": None,
                "mission_slug": "synthetic-orphan-01HHHH",
                "policy_metadata": None,
                "reason": None,
                "review_ref": None,
                "to_lane": "in_progress",
                "wp_id": "WP01",
            }
        ],
    )

    scan = scan_mission(mission_dir)

    by_id = {wp.wp_id: wp for wp in scan.work_packages}
    assert "WP01" in by_id, "malformed-but-referenced WP must be backfilled, not orphaned"
    assert by_id["WP01"].source is PrefixSource.SYNTHESIZED
    # Every wp_id a lane transition references is covered (INV-3).
    assert {event.wp_id for event in scan.lane_transitions} <= set(by_id)


# ── malformed lifecycle rows must be counted, not silently dropped (#2884 A) ──


def test_malformed_event_type_row_is_counted_as_a_skipped_event_row(tmp_path):
    """A row with a null (non-string) ``event_type`` is the genuinely silent
    failure mode named in the review: valid JSON, so ``read_events`` (the
    lane-transition reader) treats it as a skippable non-lane row and does
    NOT fail closed the whole scan — but ``read_lifecycle_events`` also drops
    it (its ``event_type`` isn't a ``str``), so a ``WPCreated`` row shaped
    like this vanishes from BOTH readers with no signal at all. The scan must
    count it (#2884 finding A) so a partial import is loud, not silent."""
    mission_dir = tmp_path / "synthetic-truncated-01JJJJ"
    mission_dir.mkdir(parents=True)
    rows = [
        {"event_type": "MissionCreated", "aggregate_type": "Mission", "payload": {}},
        # canonical-event-exempt(exception-flow): malformed on-disk WPCreated
        # row under test — null event_type is valid JSON but not a lifecycle
        # row `read_lifecycle_events` will keep.
        {"event_type": None, "aggregate_type": "WorkPackage", "payload": {"wp_id": "WP01"}},
    ]
    _write_events(mission_dir, rows)

    scan = scan_mission(mission_dir)

    assert scan.skipped_event_rows == 1
    # The mission still scans successfully (fail-loud, not fail-closed) and
    # the malformed WPCreated row truly never reaches work_packages.
    assert scan.prefix_source is PrefixSource.ON_DISK
    assert scan.work_packages == ()


def test_wp_created_payload_with_no_wp_id_is_counted_not_silently_dropped(tmp_path):
    """``_wps_from_prefix``'s ``if not wp_id: continue`` used to drop the row
    with no log and no count. It must now be counted into
    ``skipped_event_rows`` (#2884 finding A)."""
    mission_dir = tmp_path / "synthetic-no-wpid-01KKKK"
    mission_dir.mkdir(parents=True)
    rows = [
        {"event_type": "MissionCreated", "aggregate_type": "Mission", "payload": {}},
        # canonical-event-exempt(exception-flow): malformed on-disk WPCreated row missing wp_id under test
        {"event_type": "WPCreated", "aggregate_type": "WorkPackage", "payload": {"wp_title": "No id here"}},
        {"event_type": "WPCreated", "aggregate_type": "WorkPackage", "payload": {"wp_id": "WP01", "wp_title": "Good"}},
    ]
    _write_events(mission_dir, rows)

    scan = scan_mission(mission_dir)

    assert scan.skipped_event_rows == 1
    assert [wp.wp_id for wp in scan.work_packages] == ["WP01"]


def test_no_malformed_rows_yields_zero_skipped_event_rows(tmp_path):
    """The common case: a clean lifecycle prefix counts zero skips."""
    mission_dir = tmp_path / "synthetic-clean-01LLLL"
    _write_events(
        mission_dir,
        [
            {"event_type": "MissionCreated", "aggregate_type": "Mission", "payload": {}},
            {"event_type": "WPCreated", "aggregate_type": "WorkPackage", "payload": {"wp_id": "WP01"}},
        ],
    )

    scan = scan_mission(mission_dir)

    assert scan.skipped_event_rows == 0


def test_local_only_event_types_have_one_public_owner() -> None:
    """SSOT (#2884): scan's local-only filter and lifecycle's post-mission set are
    the SAME public owner object — no hand-mirrored frozenset copies to drift."""
    from specify_cli.status import (
        FOLLOW_UP_RECORDED,
        LOCAL_ONLY_LIFECYCLE_EVENT_TYPES,
        MISSION_REOPENED,
    )
    from specify_cli.status.lifecycle import _POST_MISSION_EVENT_TYPES
    from specify_cli.sync.history_import.scan import _LOCAL_ONLY_EVENT_TYPES

    # actual == expected (conventional order, #2884 finding D). Bound to local
    # names first: ruff's SIM300 (Yoda-condition) heuristic treats an ALL_CAPS
    # name compared directly against a set literal as a constant-on-the-left
    # false positive, so the operands are named here instead of inlined.
    actual_local_only_types = LOCAL_ONLY_LIFECYCLE_EVENT_TYPES
    expected_local_only_types = frozenset({MISSION_REOPENED, FOLLOW_UP_RECORDED})
    assert actual_local_only_types == expected_local_only_types
    # Identity (``is``), not just equality: both consumers bind the one owner.
    assert _LOCAL_ONLY_EVENT_TYPES is LOCAL_ONLY_LIFECYCLE_EVENT_TYPES
    assert _POST_MISSION_EVENT_TYPES is LOCAL_ONLY_LIFECYCLE_EVENT_TYPES
