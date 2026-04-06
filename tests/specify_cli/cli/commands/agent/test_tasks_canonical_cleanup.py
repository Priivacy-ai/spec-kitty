"""Tests for WP03: tasks.py canonical status model cleanup.

Covers:
- finalize-tasks calls bootstrap_canonical_state() and includes stats in output
- move_task body note does NOT contain lane=
- add_note body note does NOT contain lane=
- move_task hard-fails when WP has no canonical event (not bootstrapped)
- move_task succeeds when canonical event exists
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app
from specify_cli.status.store import append_event
from specify_cli.status.models import StatusEvent, Lane

pytestmark = pytest.mark.fast

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_wp_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    """Seed a WP into a specific lane in the event log."""
    _lane_alias = {"doing": "in_progress"}
    canonical_lane = _lane_alias.get(lane, lane)
    event = StatusEvent(
        event_id=f"test-{wp_id}-{canonical_lane}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(canonical_lane),
        at="2026-01-01T00:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def _build_minimal_feature(tmp_path: Path, mission_slug: str = "060-test") -> Path:
    """Create minimal feature structure with tasks.md and one WP file.

    Returns feature_dir.
    """
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tmp_path / ".kittify").mkdir(exist_ok=True)

    (feature_dir / "tasks.md").write_text(
        "## Work Package WP01\n\n## Work Package WP02\n",
        encoding="utf-8",
    )
    for wp_id in ("WP01", "WP02"):
        (tasks_dir / f"{wp_id}-test.md").write_text(
            f"---\n"
            f"work_package_id: {wp_id}\n"
            f"title: Test {wp_id}\n"
            f"execution_mode: code_change\n"
            f"owned_files:\n  - src/{wp_id.lower()}/**\n"
            f"authoritative_surface: src/{wp_id.lower()}/\n"
            f"---\n\n# {wp_id}\n\n## Activity Log\n",
            encoding="utf-8",
        )
    return feature_dir


def _build_wp_file(tmp_path: Path, mission_slug: str, wp_id: str, lane: str = "planned") -> Path:
    """Build a single WP file and return the feature_dir."""
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kittify").mkdir(exist_ok=True)

    wp_file = tasks_dir / f"{wp_id}-test.md"
    wp_file.write_text(
        f"---\n"
        f"work_package_id: {wp_id}\n"
        f"title: Test {wp_id}\n"
        f"lane: {lane}\n"
        f"execution_mode: code_change\n"
        f"owned_files:\n  - src/{wp_id.lower()}/**\n"
        f"authoritative_surface: src/{wp_id.lower()}/\n"
        f"---\n\n# {wp_id}\n\n## Activity Log\n",
        encoding="utf-8",
    )
    return feature_dir


# ---------------------------------------------------------------------------
# T006: finalize-tasks calls bootstrap_canonical_state
# ---------------------------------------------------------------------------


class TestFinalizeTasksBootstrap:
    """finalize-tasks calls bootstrap and includes stats in JSON output."""

    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_mission_slug")
    @patch("specify_cli.cli.commands.agent.tasks.bootstrap_canonical_state")
    def test_finalize_calls_bootstrap(
        self,
        mock_bootstrap: MagicMock,
        mock_slug: MagicMock,
        mock_root: MagicMock,
        mock_branch: MagicMock,
        tmp_path: Path,
    ):
        """finalize-tasks invokes bootstrap_canonical_state after dependency parsing."""
        mission_slug = "060-test"
        feature_dir = _build_minimal_feature(tmp_path, mission_slug)

        mock_root.return_value = tmp_path
        mock_slug.return_value = mission_slug
        mock_branch.return_value = (tmp_path, "main")

        # Mock bootstrap return value
        from specify_cli.status.bootstrap import BootstrapResult
        mock_bootstrap.return_value = BootstrapResult(
            total_wps=2,
            already_initialized=0,
            newly_seeded=2,
            skipped=0,
            wp_details={"WP01": "initialized", "WP02": "initialized"},
        )

        result = runner.invoke(app, ["finalize-tasks", "--mission", mission_slug, "--json"])
        assert result.exit_code == 0, f"CLI error: {result.output}"

        # bootstrap was called
        mock_bootstrap.assert_called_once_with(
            feature_dir, mission_slug, dry_run=False
        )

        # JSON output includes bootstrap stats
        data = json.loads(result.output)
        assert "bootstrap" in data
        assert data["bootstrap"]["total_wps"] == 2
        assert data["bootstrap"]["newly_seeded"] == 2

    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_mission_slug")
    @patch("specify_cli.cli.commands.agent.tasks.bootstrap_canonical_state")
    def test_finalize_validate_only_passes_dry_run(
        self,
        mock_bootstrap: MagicMock,
        mock_slug: MagicMock,
        mock_root: MagicMock,
        mock_branch: MagicMock,
        tmp_path: Path,
    ):
        """--validate-only passes dry_run=True to bootstrap."""
        mission_slug = "060-test"
        _build_minimal_feature(tmp_path, mission_slug)

        mock_root.return_value = tmp_path
        mock_slug.return_value = mission_slug
        mock_branch.return_value = (tmp_path, "main")

        from specify_cli.status.bootstrap import BootstrapResult
        mock_bootstrap.return_value = BootstrapResult(
            total_wps=2, already_initialized=2, newly_seeded=0, skipped=0,
            wp_details={"WP01": "already_exists", "WP02": "already_exists"},
        )

        result = runner.invoke(
            app, ["finalize-tasks", "--mission", mission_slug, "--json", "--validate-only"]
        )
        assert result.exit_code == 0, f"CLI error: {result.output}"

        mock_bootstrap.assert_called_once_with(
            ANY, mission_slug, dry_run=True
        )


# ---------------------------------------------------------------------------
# T007 / T008: Body notes don't contain lane=
# ---------------------------------------------------------------------------


class TestBodyNotesNoLane:
    """Body notes written by move_task and add_history must NOT contain lane=."""

    @patch("specify_cli.cli.commands.agent.tasks.safe_commit")
    @patch("specify_cli.cli.commands.agent.tasks.emit_status_transition")
    @patch("specify_cli.cli.commands.agent.tasks.read_events")
    @patch("specify_cli.cli.commands.agent.tasks.feature_status_lock")
    @patch("specify_cli.cli.commands.agent.tasks._validate_ready_for_review")
    @patch("specify_cli.cli.commands.agent.tasks._check_unchecked_subtasks")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_mission_slug")
    @patch("specify_cli.cli.commands.agent.tasks.locate_work_package")
    def test_move_task_body_note_no_lane(
        self,
        mock_locate_wp: MagicMock,
        mock_slug: MagicMock,
        mock_root: MagicMock,
        mock_branch: MagicMock,
        mock_unchecked: MagicMock,
        mock_review_valid: MagicMock,
        mock_lock: MagicMock,
        mock_read_events: MagicMock,
        mock_emit: MagicMock,
        mock_safe_commit: MagicMock,
        tmp_path: Path,
    ):
        """move_task history entry must not contain 'lane='."""
        mission_slug = "060-test"
        feature_dir = _build_wp_file(tmp_path, mission_slug, "WP01", "claimed")

        mock_root.return_value = tmp_path
        mock_slug.return_value = mission_slug
        mock_branch.return_value = (tmp_path, "main")
        mock_unchecked.return_value = []
        mock_review_valid.return_value = (True, [])
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)

        # Build a mock WP
        wp_file = feature_dir / "tasks" / "WP01-test.md"
        from specify_cli.tasks_support import WorkPackage
        mock_wp = WorkPackage(
            feature=mission_slug,
            path=wp_file,
            current_lane="claimed",
            relative_subpath=Path("tasks/WP01-test.md"),
            frontmatter='work_package_id: WP01\ntitle: Test WP01\nlane: claimed\nagent: testbot\n',
            body="\n# WP01\n\n## Activity Log\n",
            padding="",
        )
        mock_locate_wp.return_value = mock_wp

        # Seed canonical event so hard-fail doesn't trigger
        _seed_wp_lane(feature_dir, "WP01", "claimed")

        # Build a proper mock event for read_events that returns real events
        mock_read_events.return_value = list(
            __import__("specify_cli.status.store", fromlist=["read_events"]).read_events(feature_dir)
        )

        mock_emit.return_value = MagicMock(to_lane=Lane.IN_PROGRESS)
        mock_safe_commit.return_value = True

        result = runner.invoke(
            app,
            [
                "move-task", "WP01",
                "--to", "in_progress",
                "--agent", "testbot",
                "--mission", mission_slug,
                "--force",
                "--json",
                "--no-auto-commit",
            ],
        )
        assert result.exit_code == 0, f"CLI error: {result.output}"

        # Read the WP file and check the activity log
        content = wp_file.read_text(encoding="utf-8")
        assert "lane=" not in content, (
            f"Body note should not contain 'lane=' but got:\n{content}"
        )

    @patch("specify_cli.cli.commands.agent.tasks.emit_history_added")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_mission_slug")
    @patch("specify_cli.cli.commands.agent.tasks.locate_work_package")
    def test_add_history_body_note_no_lane(
        self,
        mock_locate_wp: MagicMock,
        mock_slug: MagicMock,
        mock_root: MagicMock,
        mock_branch: MagicMock,
        mock_emit_history: MagicMock,
        tmp_path: Path,
    ):
        """add_history entry must not contain 'lane='."""
        mission_slug = "060-test"
        feature_dir = _build_wp_file(tmp_path, mission_slug, "WP01", "in_progress")

        mock_root.return_value = tmp_path
        mock_slug.return_value = mission_slug
        mock_branch.return_value = (tmp_path, "main")

        # Seed canonical event for add_history's lane lookup
        _seed_wp_lane(feature_dir, "WP01", "in_progress")

        wp_file = feature_dir / "tasks" / "WP01-test.md"
        from specify_cli.tasks_support import WorkPackage
        mock_wp = WorkPackage(
            feature=mission_slug,
            path=wp_file,
            current_lane="in_progress",
            relative_subpath=Path("tasks/WP01-test.md"),
            frontmatter='work_package_id: WP01\ntitle: Test WP01\nlane: in_progress\nagent: testbot\n',
            body="\n# WP01\n\n## Activity Log\n",
            padding="",
        )
        mock_locate_wp.return_value = mock_wp

        result = runner.invoke(
            app,
            [
                "add-history", "WP01",
                "--note", "Implementation progressing",
                "--agent", "testbot",
                "--mission", mission_slug,
                "--json",
            ],
        )
        assert result.exit_code == 0, f"CLI error: {result.output}"

        content = wp_file.read_text(encoding="utf-8")
        assert "lane=" not in content, (
            f"Body note should not contain 'lane=' but got:\n{content}"
        )
        # Verify note text is present
        assert "Implementation progressing" in content


# ---------------------------------------------------------------------------
# T009: move_task hard-fails when no canonical event
# ---------------------------------------------------------------------------


class TestMoveTaskHardFail:
    """move_task must raise RuntimeError when WP has no canonical status."""

    @patch("specify_cli.cli.commands.agent.tasks.feature_status_lock")
    @patch("specify_cli.cli.commands.agent.tasks.read_events")
    @patch("specify_cli.cli.commands.agent.tasks._validate_ready_for_review")
    @patch("specify_cli.cli.commands.agent.tasks._check_unchecked_subtasks")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_mission_slug")
    @patch("specify_cli.cli.commands.agent.tasks.locate_work_package")
    def test_move_task_hard_fails_no_canonical_event(
        self,
        mock_locate_wp: MagicMock,
        mock_slug: MagicMock,
        mock_root: MagicMock,
        mock_branch: MagicMock,
        mock_unchecked: MagicMock,
        mock_review_valid: MagicMock,
        mock_read_events: MagicMock,
        mock_lock: MagicMock,
        tmp_path: Path,
    ):
        """move_task exits with error when WP has no canonical status events."""
        mission_slug = "060-test"
        feature_dir = _build_wp_file(tmp_path, mission_slug, "WP01", "planned")

        mock_root.return_value = tmp_path
        mock_slug.return_value = mission_slug
        mock_branch.return_value = (tmp_path, "main")
        mock_unchecked.return_value = []
        mock_review_valid.return_value = (True, [])
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)

        # No events = no canonical state
        mock_read_events.return_value = []

        wp_file = feature_dir / "tasks" / "WP01-test.md"
        from specify_cli.tasks_support import WorkPackage
        mock_wp = WorkPackage(
            feature=mission_slug,
            path=wp_file,
            current_lane="planned",
            relative_subpath=Path("tasks/WP01-test.md"),
            frontmatter='work_package_id: WP01\ntitle: Test WP01\nlane: planned\n',
            body="\n# WP01\n\n## Activity Log\n",
            padding="",
        )
        mock_locate_wp.return_value = mock_wp

        result = runner.invoke(
            app,
            [
                "move-task", "WP01",
                "--to", "claimed",
                "--agent", "testbot",
                "--mission", mission_slug,
                "--force",
                "--json",
            ],
        )
        # Should exit with error
        assert result.exit_code != 0, f"Expected failure but got: {result.output}"

        # Error message should mention finalize-tasks
        assert "finalize-tasks" in result.output or "finalize" in result.output.lower(), (
            f"Error should mention finalize-tasks but got:\n{result.output}"
        )
        assert "no canonical status" in result.output.lower() or "has no canonical" in result.output.lower(), (
            f"Error should mention missing canonical status but got:\n{result.output}"
        )

    @patch("specify_cli.cli.commands.agent.tasks.safe_commit")
    @patch("specify_cli.cli.commands.agent.tasks.emit_status_transition")
    @patch("specify_cli.cli.commands.agent.tasks.read_events")
    @patch("specify_cli.cli.commands.agent.tasks.feature_status_lock")
    @patch("specify_cli.cli.commands.agent.tasks._validate_ready_for_review")
    @patch("specify_cli.cli.commands.agent.tasks._check_unchecked_subtasks")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_mission_slug")
    @patch("specify_cli.cli.commands.agent.tasks.locate_work_package")
    def test_move_task_succeeds_with_canonical_event(
        self,
        mock_locate_wp: MagicMock,
        mock_slug: MagicMock,
        mock_root: MagicMock,
        mock_branch: MagicMock,
        mock_unchecked: MagicMock,
        mock_review_valid: MagicMock,
        mock_lock: MagicMock,
        mock_read_events: MagicMock,
        mock_emit: MagicMock,
        mock_safe_commit: MagicMock,
        tmp_path: Path,
    ):
        """move_task succeeds when WP has canonical event."""
        mission_slug = "060-test"
        feature_dir = _build_wp_file(tmp_path, mission_slug, "WP01", "planned")

        mock_root.return_value = tmp_path
        mock_slug.return_value = mission_slug
        mock_branch.return_value = (tmp_path, "main")
        mock_unchecked.return_value = []
        mock_review_valid.return_value = (True, [])
        mock_lock.return_value.__enter__ = MagicMock()
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)

        # Seed canonical state
        _seed_wp_lane(feature_dir, "WP01", "planned")

        # Return real events from the seeded store
        from specify_cli.status.store import read_events as real_read_events
        mock_read_events.return_value = list(real_read_events(feature_dir))

        wp_file = feature_dir / "tasks" / "WP01-test.md"
        from specify_cli.tasks_support import WorkPackage
        mock_wp = WorkPackage(
            feature=mission_slug,
            path=wp_file,
            current_lane="planned",
            relative_subpath=Path("tasks/WP01-test.md"),
            frontmatter='work_package_id: WP01\ntitle: Test WP01\nlane: planned\nagent: testbot\n',
            body="\n# WP01\n\n## Activity Log\n",
            padding="",
        )
        mock_locate_wp.return_value = mock_wp

        mock_emit.return_value = MagicMock(to_lane=Lane.CLAIMED)
        mock_safe_commit.return_value = True

        result = runner.invoke(
            app,
            [
                "move-task", "WP01",
                "--to", "claimed",
                "--agent", "testbot",
                "--mission", mission_slug,
                "--force",
                "--json",
                "--no-auto-commit",
            ],
        )
        assert result.exit_code == 0, f"CLI error: {result.output}"

        data = json.loads(result.output)
        assert data["result"] == "success"
