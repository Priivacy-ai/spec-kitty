"""Regression tests for scripts/tasks/tasks_cli.py — WP05: Migrate Slice 3: Review & Tasks.

Tests verify that:
- _derive_current_lane() reads from event log (not frontmatter)
- list_command uses _derive_current_lane() for lane authority
- wp_state_for(lane).display_category() is used for display
- All 9 lanes map to the correct display categories
- Canonical status validation is preserved (error if no events)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.reducer import materialize
from specify_cli.status.store import append_event
from specify_cli.status.wp_state import wp_state_for
from tests.utils import REPO_ROOT, run_python_script


pytestmark = pytest.mark.fast

SRC_TASKS_CLI = REPO_ROOT / "src" / "specify_cli" / "scripts" / "tasks" / "tasks_cli.py"


def _load_tasks_cli(module_name: str = "tasks_cli_wp05_test"):
    """Load tasks_cli module from the src/ path."""
    spec = importlib.util.spec_from_file_location(module_name, SRC_TASKS_CLI)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)
    (repo / ".kittify").mkdir()


def _build_feature(
    repo: Path,
    slug: str = "080-tasks-test",
    *,
    to_lane: Lane = Lane.IN_PROGRESS,
    with_events: bool = True,
) -> Path:
    """Build a test feature directory with a single WP."""
    feature_dir = repo / "kitty-specs" / slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-test.md").write_text(
        "---\n"
        'work_package_id: "WP01"\n'
        'title: "Test WP01"\n'
        'agent: "tester"\n'
        'shell_pid: "123"\n'
        "---\n\n"
        "# WP01\n\n"
        "## Activity Log\n"
        "- 2026-04-09T09:00:00Z -- tester -- Prompt created\n",
        encoding="utf-8",
    )
    if with_events:
        event = StatusEvent(
            event_id="01TESTTASKSCLILANE000000000",
            mission_slug=slug,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=to_lane,
            at="2026-04-09T09:00:00+00:00",
            actor="tester",
            force=True,
            execution_mode="direct_repo",
        )
        append_event(feature_dir, event)
        materialize(feature_dir)
    return feature_dir


# ---------------------------------------------------------------------------
# Tests calling live _derive_current_lane() from tasks_cli
# ---------------------------------------------------------------------------


def test_derive_current_lane_returns_lane_from_events(tmp_path: Path) -> None:
    """_derive_current_lane() reads canonical lane from the event log."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, to_lane=Lane.IN_PROGRESS)

    tasks_cli = _load_tasks_cli("tasks_cli_derive_from_events")
    lane = tasks_cli._derive_current_lane(feature_dir, "WP01")

    assert lane == Lane.IN_PROGRESS
    assert lane == "in_progress"


def test_derive_current_lane_returns_planned_when_no_events(tmp_path: Path) -> None:
    """_derive_current_lane() defaults to Lane.PLANNED when event log is empty."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, with_events=False)

    tasks_cli = _load_tasks_cli("tasks_cli_derive_no_events")
    lane = tasks_cli._derive_current_lane(feature_dir, "WP01")

    assert lane == Lane.PLANNED
    assert lane == "planned"


def test_derive_current_lane_returns_planned_when_unknown_wp(tmp_path: Path) -> None:
    """_derive_current_lane() defaults to Lane.PLANNED for a WP with no events."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, to_lane=Lane.DONE)

    tasks_cli = _load_tasks_cli("tasks_cli_derive_unknown_wp")
    lane = tasks_cli._derive_current_lane(feature_dir, "WP99")

    assert lane == Lane.PLANNED


def test_derive_current_lane_tracks_latest_event(tmp_path: Path) -> None:
    """_derive_current_lane() returns the current lane after multiple transitions."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, to_lane=Lane.CLAIMED)

    # Add another transition: claimed → in_progress
    event2 = StatusEvent(
        event_id="01TESTTASKSCLILANE000000002",
        mission_slug=feature_dir.name,
        wp_id="WP01",
        from_lane=Lane.CLAIMED,
        to_lane=Lane.IN_PROGRESS,
        at="2026-04-09T10:00:00+00:00",
        actor="tester",
        force=False,
        execution_mode="direct_repo",
    )
    append_event(feature_dir, event2)
    materialize(feature_dir)

    tasks_cli = _load_tasks_cli("tasks_cli_derive_latest")
    lane = tasks_cli._derive_current_lane(feature_dir, "WP01")

    assert lane == Lane.IN_PROGRESS


# ---------------------------------------------------------------------------
# Tests for display_category() via wp_state_for() — all 9 lanes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lane_str, expected_display",
    [
        # Actual display_category() values from WPState concrete classes:
        ("planned", "Planned"),
        ("claimed", "In Progress"),  # ClaimedState groups under "In Progress"
        ("in_progress", "In Progress"),
        ("for_review", "Review"),  # ForReviewState uses "Review" not "For Review"
        ("in_review", "In Progress"),  # InReviewState groups under "In Progress"
        ("approved", "Approved"),
        ("done", "Done"),
        ("blocked", "Blocked"),
        ("canceled", "Canceled"),
    ],
)
def test_wp_state_for_display_category_all_lanes(lane_str: str, expected_display: str) -> None:
    """wp_state_for(lane).display_category() returns the correct display string for all 9 lanes."""
    state = wp_state_for(lane_str)
    assert state.display_category() == expected_display


def test_wp_state_for_lane_enum_input_works() -> None:
    """wp_state_for() accepts Lane enum values directly."""
    assert wp_state_for(Lane.PLANNED).display_category() == "Planned"
    assert wp_state_for(Lane.IN_PROGRESS).display_category() == "In Progress"
    assert wp_state_for(Lane.FOR_REVIEW).display_category() == "Review"
    assert wp_state_for(Lane.DONE).display_category() == "Done"


# ---------------------------------------------------------------------------
# Integration tests calling list_command via subprocess (live tasks_cli)
# ---------------------------------------------------------------------------


def test_list_command_shows_display_category_for_in_progress(tmp_path: Path, isolated_env: dict[str, str]) -> None:
    """list command shows 'In Progress' (display_category) for in_progress WP."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, to_lane=Lane.IN_PROGRESS)

    result = run_python_script(SRC_TASKS_CLI, ["list", feature_dir.name], cwd=repo, env=isolated_env)

    assert result.returncode == 0, result.stderr
    assert "In Progress" in result.stdout


def test_list_command_shows_display_category_for_done(tmp_path: Path, isolated_env: dict[str, str]) -> None:
    """list command shows 'Done' (display_category) for done WP."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, to_lane=Lane.DONE)

    result = run_python_script(SRC_TASKS_CLI, ["list", feature_dir.name], cwd=repo, env=isolated_env)

    assert result.returncode == 0, result.stderr
    assert "Done" in result.stdout


def test_list_command_shows_display_category_for_planned(tmp_path: Path, isolated_env: dict[str, str]) -> None:
    """list command shows 'Planned' (display_category) for planned WP."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, to_lane=Lane.PLANNED)

    result = run_python_script(SRC_TASKS_CLI, ["list", feature_dir.name], cwd=repo, env=isolated_env)

    assert result.returncode == 0, result.stderr
    assert "Planned" in result.stdout


def test_list_command_fails_without_canonical_status(tmp_path: Path, isolated_env: dict[str, str]) -> None:
    """list command fails with clear error when no canonical status events exist."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, with_events=False)

    result = run_python_script(SRC_TASKS_CLI, ["list", feature_dir.name], cwd=repo, env=isolated_env)

    assert result.returncode == 1
    assert "Canonical status not found" in result.stderr
    assert "finalize-tasks" in result.stderr


def test_list_command_shows_wp_id_in_output(tmp_path: Path, isolated_env: dict[str, str]) -> None:
    """list command shows the work package ID in the output table."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, to_lane=Lane.CLAIMED)

    result = run_python_script(SRC_TASKS_CLI, ["list", feature_dir.name], cwd=repo, env=isolated_env)

    assert result.returncode == 0, result.stderr
    assert "WP01" in result.stdout
