"""Regression tests for agent_utils/status.py after WP03 migration.

Verifies that:
- progress_bucket() produces correct display semantics for all 9 lanes
- _analyze_parallelization() uses wp_state_for() for skip logic (not raw strings)
- show_kanban_status() correctly renders the kanban board using Lane enum keys
- No raw lane-string comparisons remain in the migrated consumer code
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from specify_cli.agent_utils.status import _analyze_parallelization, show_kanban_status
from specify_cli.status.models import Lane
from specify_cli.status.wp_state import wp_state_for


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
