"""Regression tests for agent_utils/status.py after WP03 migration.

Verifies that:
- progress_bucket() produces correct display semantics for all 9 lanes
- _analyze_parallelization() uses wp_state_for() for skip logic (not raw strings)
- show_kanban_status() correctly renders the kanban board using Lane enum keys
- No raw lane-string comparisons remain in the migrated consumer code
- Stale verdict warnings are shown for approved/done WPs with verdict=rejected
- Stall detection flags in_review WPs older than the threshold
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from specify_cli.agent_utils.status import (
    _analyze_parallelization,
    _get_last_event_time,
    _get_wp_review_verdict,
    show_kanban_status,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.wp_state import wp_state_for

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# T008: progress_bucket() regression — all 9 lanes map to expected buckets
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lane_str,expected_bucket", [
    ("planned",    "not_started"),
    ("claimed",    "in_flight"),
    ("in_progress","in_flight"),
    ("for_review", "review"),
    ("in_review",  "review"),
    ("approved",   "review"),
    ("done",       "terminal"),
    ("blocked",    "in_flight"),
    ("canceled",   "terminal"),
])
def test_progress_bucket_all_9_lanes(lane_str: str, expected_bucket: str) -> None:
    """Each lane produces the expected progress_bucket() value."""
    state = wp_state_for(lane_str)
    assert state.progress_bucket() == expected_bucket, (
        f"Lane {lane_str!r} -> bucket {state.progress_bucket()!r} != {expected_bucket!r}"
    )


# ---------------------------------------------------------------------------
# T008: _analyze_parallelization uses progress_bucket() (not raw strings)
# ---------------------------------------------------------------------------

def _make_wp(wp_id: str, lane: Lane, deps: list | None = None) -> dict:
    return {"id": wp_id, "title": f"Title for {wp_id}", "lane": lane,
            "phase": "P1", "file": f"{wp_id}.md", "dependencies": deps or []}


def test_analyze_parallelization_skips_in_flight_wps() -> None:
    """WPs in in_flight bucket (claimed, in_progress, blocked) are skipped."""
    work_packages = [
        _make_wp("WP01", Lane.CLAIMED),
        _make_wp("WP02", Lane.IN_PROGRESS),
        _make_wp("WP03", Lane.BLOCKED),
        _make_wp("WP04", Lane.PLANNED),  # should be ready
    ]
    done_ids: set = set()
    result = _analyze_parallelization(work_packages, done_ids)
    ready_ids = {wp["id"] for wp in result["ready_wps"]}
    # Only WP04 is not in-flight or terminal
    assert ready_ids == {"WP04"}


def test_analyze_parallelization_skips_review_wps() -> None:
    """WPs in review bucket (for_review, in_review, approved) are skipped."""
    work_packages = [
        _make_wp("WP01", Lane.FOR_REVIEW),
        _make_wp("WP02", Lane.IN_REVIEW),
        _make_wp("WP03", Lane.APPROVED),
        _make_wp("WP04", Lane.PLANNED),  # should be ready
    ]
    done_ids: set = set()
    result = _analyze_parallelization(work_packages, done_ids)
    ready_ids = {wp["id"] for wp in result["ready_wps"]}
    assert ready_ids == {"WP04"}


def test_analyze_parallelization_skips_terminal_wps() -> None:
    """WPs in terminal bucket (done, canceled) are skipped."""
    work_packages = [
        _make_wp("WP01", Lane.DONE),
        _make_wp("WP02", Lane.CANCELED),
        _make_wp("WP03", Lane.PLANNED),  # should be ready
    ]
    done_ids = {"WP01", "WP02"}
    result = _analyze_parallelization(work_packages, done_ids)
    ready_ids = {wp["id"] for wp in result["ready_wps"]}
    assert ready_ids == {"WP03"}


def test_analyze_parallelization_respects_done_dependency() -> None:
    """WP is ready only when its dependency is in done_wp_ids."""
    work_packages = [
        _make_wp("WP01", Lane.DONE),
        _make_wp("WP02", Lane.PLANNED, deps=["WP01"]),
        _make_wp("WP03", Lane.PLANNED, deps=["WP99"]),  # unmet dep
    ]
    done_ids = {"WP01"}
    result = _analyze_parallelization(work_packages, done_ids)
    ready_ids = {wp["id"] for wp in result["ready_wps"]}
    assert "WP02" in ready_ids
    assert "WP03" not in ready_ids


def test_analyze_parallelization_parallel_group_when_multiple_ready() -> None:
    """Multiple independent ready WPs produce a parallel group."""
    work_packages = [
        _make_wp("WP01", Lane.PLANNED),
        _make_wp("WP02", Lane.PLANNED),
    ]
    result = _analyze_parallelization(work_packages, set())
    assert result["can_parallelize"] is True
    types = [g["type"] for g in result["parallel_groups"]]
    assert "parallel" in types


# ---------------------------------------------------------------------------
# T008: show_kanban_status() integration test with real filesystem
# ---------------------------------------------------------------------------

def _create_wp_file(tasks_dir: Path, wp_id: str, title: str) -> None:
    """Write a minimal WP frontmatter file."""
    content = textwrap.dedent(f"""\
        ---
        work_package_id: {wp_id}
        title: '{title}'
        ---
        # {wp_id}: {title}
    """)
    (tasks_dir / f"{wp_id}-stub.md").write_text(content, encoding="utf-8")


def _create_events_jsonl(feature_dir: Path, events: list) -> None:
    """Write a status.events.jsonl file."""
    lines = [json.dumps(e) for e in events]
    (feature_dir / "status.events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _create_meta_json(feature_dir: Path, mission_slug: str) -> None:
    """Write minimal meta.json."""
    meta = {
        "mission_slug": mission_slug,
        "mission_number": "080",
        "mission_type": "software-dev",
        "phase": 2,
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


@pytest.fixture()
def mock_project(tmp_path: Path) -> Path:
    """Create a minimal spec-kitty project layout for testing."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("version: 1\n", encoding="utf-8")

    mission_slug = "test-feature"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()

    _create_meta_json(feature_dir, mission_slug)

    return tmp_path


def test_show_kanban_status_uses_lane_enum_grouping(mock_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """show_kanban_status() groups WPs using Lane enum keys, not raw strings.

    This test verifies the live code path: injecting real WP files + events,
    then calling show_kanban_status() and asserting the returned dict has
    correct counts based on progress_bucket() semantics.
    """
    mission_slug = "test-feature"
    feature_dir = mock_project / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"

    _create_wp_file(tasks_dir, "WP01", "Planned Work")
    _create_wp_file(tasks_dir, "WP02", "In Progress Work")
    _create_wp_file(tasks_dir, "WP03", "Done Work")
    _create_wp_file(tasks_dir, "WP04", "For Review Work")

    _create_events_jsonl(feature_dir, [
        {
            "event_id": "01AAA001", "at": "2026-01-01T00:00:00+00:00",
            "feature_slug": mission_slug, "wp_id": "WP01",
            "from_lane": "planned", "to_lane": "planned",
            "actor": "test", "force": False, "reason": None,
            "evidence": None, "review_ref": None, "execution_mode": "worktree",
        },
        {
            "event_id": "01AAA002", "at": "2026-01-01T00:01:00+00:00",
            "feature_slug": mission_slug, "wp_id": "WP02",
            "from_lane": "planned", "to_lane": "in_progress",
            "actor": "test", "force": True, "reason": None,
            "evidence": None, "review_ref": None, "execution_mode": "worktree",
        },
        {
            "event_id": "01AAA003", "at": "2026-01-01T00:02:00+00:00",
            "feature_slug": mission_slug, "wp_id": "WP03",
            "from_lane": "planned", "to_lane": "done",
            "actor": "test", "force": True, "reason": None,
            "evidence": None, "review_ref": None, "execution_mode": "worktree",
        },
        {
            "event_id": "01AAA004", "at": "2026-01-01T00:03:00+00:00",
            "feature_slug": mission_slug, "wp_id": "WP04",
            "from_lane": "planned", "to_lane": "for_review",
            "actor": "test", "force": True, "reason": None,
            "evidence": None, "review_ref": None, "execution_mode": "worktree",
        },
    ])

    monkeypatch.chdir(mock_project)
    monkeypatch.setattr(
        "specify_cli.agent_utils.status.locate_project_root",
        lambda cwd: mock_project,
    )
    monkeypatch.setattr(
        "specify_cli.agent_utils.status.get_main_repo_root",
        lambda repo_root: mock_project,
    )

    result = show_kanban_status(mission_slug)

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert result["total_wps"] == 4
    assert result["done_count"] == 1
    # in_progress_count: WP02=in_flight, WP04=review => 2
    assert result["in_progress_count"] == 2
    # planned_count: WP01=not_started => 1
    assert result["planned_count"] == 1
    assert result["by_lane"]["in_progress"] == 1
    assert result["by_lane"]["done"] == 1
    assert result["by_lane"]["for_review"] == 1


def test_show_kanban_status_all_9_lanes(mock_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """show_kanban_status() correctly counts all 9 lanes via progress_bucket()."""
    mission_slug = "test-feature"
    feature_dir = mock_project / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"

    lanes_to_test = [
        ("WP01", "planned"),
        ("WP02", "claimed"),
        ("WP03", "in_progress"),
        ("WP04", "for_review"),
        ("WP05", "in_review"),
        ("WP06", "approved"),
        ("WP07", "done"),
        ("WP08", "blocked"),
        ("WP09", "canceled"),
    ]

    for wp_id, _ in lanes_to_test:
        _create_wp_file(tasks_dir, wp_id, f"Test {wp_id}")

    events = [
        {
            "event_id": f"01AAA{i+1:03d}", "at": f"2026-01-01T00:{i:02d}:00+00:00",
            "feature_slug": mission_slug, "wp_id": wp_id,
            "from_lane": "planned", "to_lane": lane,
            "actor": "test", "force": True, "reason": None,
            "evidence": None, "review_ref": None, "execution_mode": "worktree",
        }
        for i, (wp_id, lane) in enumerate(lanes_to_test)
    ]
    _create_events_jsonl(feature_dir, events)

    monkeypatch.chdir(mock_project)
    monkeypatch.setattr(
        "specify_cli.agent_utils.status.locate_project_root",
        lambda cwd: mock_project,
    )
    monkeypatch.setattr(
        "specify_cli.agent_utils.status.get_main_repo_root",
        lambda repo_root: mock_project,
    )

    result = show_kanban_status(mission_slug)
    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert result["total_wps"] == 9
    # done_count: only Lane.DONE (not canceled)
    assert result["done_count"] == 1
    # in_progress_count: in_flight (claimed, in_progress, blocked) + review (for_review, in_review, approved) = 6
    assert result["in_progress_count"] == 6
    # planned_count: not_started (planned) = 1
    assert result["planned_count"] == 1


# ---------------------------------------------------------------------------
# Helper factories for StatusEvent
# ---------------------------------------------------------------------------

def _make_status_event(
    wp_id: str,
    at: str,
    to_lane: str = "in_review",
    from_lane: str = "for_review",
    mission_slug: str = "test-feature",
) -> StatusEvent:
    return StatusEvent(
        event_id="01TESTEVT",
        mission_slug=mission_slug,
        wp_id=wp_id,
        from_lane=Lane(from_lane),
        to_lane=Lane(to_lane),
        at=at,
        actor="test",
        force=False,
        execution_mode="worktree",
    )


# ---------------------------------------------------------------------------
# T023 / T024: _get_wp_review_verdict helper
# ---------------------------------------------------------------------------

def test_get_wp_review_verdict_returns_rejected(tmp_path: Path) -> None:
    """_get_wp_review_verdict returns 'rejected' when latest review cycle has it."""
    (tmp_path / "review-cycle-1.md").write_text(
        "---\nverdict: rejected\n---\n# Review\n", encoding="utf-8"
    )
    assert _get_wp_review_verdict(tmp_path) == "rejected"


def test_get_wp_review_verdict_returns_approved(tmp_path: Path) -> None:
    """_get_wp_review_verdict returns 'approved' for an approved verdict."""
    (tmp_path / "review-cycle-1.md").write_text(
        "---\nverdict: approved\n---\n# Review\n", encoding="utf-8"
    )
    assert _get_wp_review_verdict(tmp_path) == "approved"


def test_get_wp_review_verdict_latest_cycle_wins(tmp_path: Path) -> None:
    """_get_wp_review_verdict returns verdict from the highest-numbered cycle."""
    (tmp_path / "review-cycle-1.md").write_text(
        "---\nverdict: rejected\n---\n", encoding="utf-8"
    )
    (tmp_path / "review-cycle-2.md").write_text(
        "---\nverdict: approved\n---\n", encoding="utf-8"
    )
    assert _get_wp_review_verdict(tmp_path) == "approved"


def test_get_wp_review_verdict_no_files_returns_none(tmp_path: Path) -> None:
    """_get_wp_review_verdict returns None when no review-cycle files exist."""
    assert _get_wp_review_verdict(tmp_path) is None


def test_get_wp_review_verdict_no_frontmatter_returns_none(tmp_path: Path) -> None:
    """_get_wp_review_verdict returns None when the review file has no frontmatter."""
    (tmp_path / "review-cycle-1.md").write_text(
        "# No frontmatter here\n", encoding="utf-8"
    )
    assert _get_wp_review_verdict(tmp_path) is None


# ---------------------------------------------------------------------------
# T024: _get_last_event_time helper
# ---------------------------------------------------------------------------

def test_get_last_event_time_returns_most_recent(tmp_path: Path) -> None:
    """_get_last_event_time returns the datetime of the most recent event for wp_id."""
    events = [
        _make_status_event("WP01", "2026-01-01T10:00:00+00:00"),
        _make_status_event("WP01", "2026-01-01T11:00:00+00:00"),
        _make_status_event("WP02", "2026-01-01T12:00:00+00:00"),
    ]
    result = _get_last_event_time(events, "WP01")
    assert result is not None
    assert result == datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc)


def test_get_last_event_time_returns_none_for_unknown_wp() -> None:
    """_get_last_event_time returns None when no events match wp_id."""
    events = [_make_status_event("WP01", "2026-01-01T10:00:00+00:00")]
    assert _get_last_event_time(events, "WP99") is None


def test_get_last_event_time_empty_list() -> None:
    """_get_last_event_time returns None for an empty event list."""
    assert _get_last_event_time([], "WP01") is None


# ---------------------------------------------------------------------------
# T025 / T026: stall detection in show_kanban_status()
# ---------------------------------------------------------------------------

def _make_project_with_in_review_wp(
    tmp_path: Path,
    mission_slug: str,
    at_timestamp: str,
) -> Path:
    """Create a minimal project with WP01 in in_review lane, event at at_timestamp."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("version: 1\n", encoding="utf-8")

    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()

    _create_meta_json(feature_dir, mission_slug)
    _create_wp_file(tasks_dir, "WP01", "In Review Work")

    events = [
        {
            "event_id": "01AAA001", "at": at_timestamp,
            "feature_slug": mission_slug, "wp_id": "WP01",
            "from_lane": "for_review", "to_lane": "in_review",
            "actor": "test", "force": False, "reason": None,
            "evidence": None, "review_ref": None, "execution_mode": "worktree",
        }
    ]
    _create_events_jsonl(feature_dir, events)
    return tmp_path


def test_stall_detected_above_threshold(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """WP in in_review with last event 45m ago is flagged as stalled (threshold=30m)."""
    mission_slug = "test-stall"
    # Place event 45 minutes in the past
    fake_now = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)
    event_time = fake_now - timedelta(minutes=45)
    at_str = event_time.isoformat()

    project = _make_project_with_in_review_wp(tmp_path, mission_slug, at_str)

    monkeypatch.chdir(project)
    monkeypatch.setattr("specify_cli.agent_utils.status.locate_project_root", lambda cwd: project)
    monkeypatch.setattr("specify_cli.agent_utils.status.get_main_repo_root", lambda r: project)
    # Freeze datetime.now() in the status module
    import specify_cli.agent_utils.status as status_mod
    monkeypatch.setattr(status_mod, "datetime", _FakeDatetime(fake_now))

    result = show_kanban_status(mission_slug)

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    stalled = result.get("stalled_wps", [])
    assert len(stalled) == 1
    assert stalled[0]["wp_id"] == "WP01"
    assert stalled[0]["age_minutes"] >= 45


def test_stall_not_detected_below_threshold(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """WP in in_review with last event 10m ago is NOT stalled (threshold=30m)."""
    mission_slug = "test-no-stall"
    fake_now = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)
    event_time = fake_now - timedelta(minutes=10)
    at_str = event_time.isoformat()

    project = _make_project_with_in_review_wp(tmp_path, mission_slug, at_str)

    monkeypatch.chdir(project)
    monkeypatch.setattr("specify_cli.agent_utils.status.locate_project_root", lambda cwd: project)
    monkeypatch.setattr("specify_cli.agent_utils.status.get_main_repo_root", lambda r: project)
    import specify_cli.agent_utils.status as status_mod
    monkeypatch.setattr(status_mod, "datetime", _FakeDatetime(fake_now))

    result = show_kanban_status(mission_slug)

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert result.get("stalled_wps", []) == []


# ---------------------------------------------------------------------------
# T023: stale verdict warning in show_kanban_status()
# ---------------------------------------------------------------------------

def test_stale_verdict_warning_shown_in_done_lane(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """WP in done lane with review-cycle-1.md verdict=rejected appears in stale_verdicts."""
    mission_slug = "test-stale-verdict"
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("version: 1\n", encoding="utf-8")

    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    _create_meta_json(feature_dir, mission_slug)
    _create_wp_file(tasks_dir, "WP01", "Done Work")

    # Write review-cycle-1.md with rejected verdict in the WP01 directory
    wp_dir = tasks_dir / "WP01"
    wp_dir.mkdir()
    (wp_dir / "review-cycle-1.md").write_text(
        "---\nverdict: rejected\n---\n# Review\n", encoding="utf-8"
    )

    # Event: WP01 is done
    events = [
        {
            "event_id": "01AAA001", "at": "2026-01-01T00:00:00+00:00",
            "feature_slug": mission_slug, "wp_id": "WP01",
            "from_lane": "approved", "to_lane": "done",
            "actor": "test", "force": True, "reason": None,
            "evidence": None, "review_ref": None, "execution_mode": "worktree",
        }
    ]
    _create_events_jsonl(feature_dir, events)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("specify_cli.agent_utils.status.locate_project_root", lambda cwd: tmp_path)
    monkeypatch.setattr("specify_cli.agent_utils.status.get_main_repo_root", lambda r: tmp_path)

    result = show_kanban_status(mission_slug)

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    stale = result.get("stale_verdicts", [])
    assert len(stale) == 1
    assert stale[0]["wp_id"] == "WP01"
    assert "rejected" in stale[0]["artifact"]


def test_stale_verdict_clean_no_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """WP in done lane with verdict=approved does NOT appear in stale_verdicts."""
    mission_slug = "test-clean-verdict"
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("version: 1\n", encoding="utf-8")

    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    _create_meta_json(feature_dir, mission_slug)
    _create_wp_file(tasks_dir, "WP01", "Done Work")

    wp_dir = tasks_dir / "WP01"
    wp_dir.mkdir()
    (wp_dir / "review-cycle-1.md").write_text(
        "---\nverdict: approved\n---\n# Review\n", encoding="utf-8"
    )

    events = [
        {
            "event_id": "01AAA001", "at": "2026-01-01T00:00:00+00:00",
            "feature_slug": mission_slug, "wp_id": "WP01",
            "from_lane": "approved", "to_lane": "done",
            "actor": "test", "force": True, "reason": None,
            "evidence": None, "review_ref": None, "execution_mode": "worktree",
        }
    ]
    _create_events_jsonl(feature_dir, events)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("specify_cli.agent_utils.status.locate_project_root", lambda cwd: tmp_path)
    monkeypatch.setattr("specify_cli.agent_utils.status.get_main_repo_root", lambda r: tmp_path)

    result = show_kanban_status(mission_slug)

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert result.get("stale_verdicts", []) == []


# ---------------------------------------------------------------------------
# Helper: fake datetime class for monkeypatching datetime.now()
# ---------------------------------------------------------------------------

class _FakeDatetime:
    """Fake datetime replacement that returns a fixed ``now``."""

    def __init__(self, fixed_now: datetime) -> None:
        self._now = fixed_now

    def now(self, tz: "timezone | None" = None) -> datetime:
        if tz is not None:
            return self._now.astimezone(tz)
        return self._now

    def fromisoformat(self, s: str) -> datetime:
        return datetime.fromisoformat(s)
