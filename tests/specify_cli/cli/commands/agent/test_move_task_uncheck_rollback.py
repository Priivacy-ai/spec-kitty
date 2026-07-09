"""Unit tests for _mt_uncheck_rollback_subtasks (#2513).

When ``move-task --to planned`` rolls a WP back, the WP's checked subtask
rows in tasks.md must be unchecked — otherwise the lane-transition gate
passes immediately on the next ``for_review`` without the work being re-done.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _make_state(
    tmp_path: Path,
    *,
    task_id: str = "WP01",
    mission_slug: str = "001-test-mission",
    resolved_auto_commit: bool = True,
) -> object:
    """Build a minimal _MoveTaskState for rollback-uncheck tests."""
    from specify_cli.cli.commands.agent.tasks_move_task import _MoveTaskState
    from specify_cli.status import Lane

    return _MoveTaskState(
        task_id=task_id,
        to="planned",
        mission=None,
        agent=None,
        assignee=None,
        shell_pid=None,
        note=None,
        review_feedback_file=None,
        approval_ref=None,
        reviewer=None,
        self_review_fallback=False,
        intended_reviewer=None,
        reviewer_failure_reason=None,
        done_override_reason=None,
        force=False,
        tracker_ref=None,
        skip_review_artifact_check=False,
        auto_commit=None,
        json_output=False,
        target_lane=Lane.PLANNED,
        main_repo_root=tmp_path,
        mission_slug=mission_slug,
        resolved_auto_commit=resolved_auto_commit,
    )


def _make_ports(feature_dir: Path) -> MagicMock:
    """Build a TasksPorts mock whose fs.planning_read_dir returns *feature_dir*."""
    ports = MagicMock()
    ports.fs.planning_read_dir.return_value = feature_dir
    ports.coord.commit_artifact.return_value = MagicMock(status="committed")
    return ports


TASKS_WITH_CHECKED = """\
## WP01 — Build widget

- [x] T001 Design the API
- [x] T002 Implement the handler
- [ ] T003 Write tests

## WP02 — Ship widget

- [x] T004 Ship it
"""


class TestMtUncheckRollbackSubtasks:
    """_mt_uncheck_rollback_subtasks unchecks the target WP's rows in tasks.md."""

    def test_unchecks_checked_rows_in_wp_section(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import _mt_uncheck_rollback_subtasks

        feature_dir = tmp_path / "kitty-specs" / "001-test-mission"
        feature_dir.mkdir(parents=True)
        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text(TASKS_WITH_CHECKED, encoding="utf-8")

        st = _make_state(tmp_path, task_id="WP01")
        ports = _make_ports(feature_dir)

        _mt_uncheck_rollback_subtasks(st, ports)  # type: ignore[arg-type]

        result = tasks_md.read_text(encoding="utf-8")
        assert "- [ ] T001" in result
        assert "- [ ] T002" in result
        assert "- [ ] T003" in result  # already unchecked — preserved
        # WP02 rows must NOT be touched
        assert "- [x] T004" in result

    def test_does_not_write_when_no_checked_rows(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import _mt_uncheck_rollback_subtasks

        feature_dir = tmp_path / "kitty-specs" / "001-test-mission"
        feature_dir.mkdir(parents=True)
        tasks_md = feature_dir / "tasks.md"
        content = "## WP01\n\n- [ ] T001 Not done\n"
        tasks_md.write_text(content, encoding="utf-8")

        st = _make_state(tmp_path, task_id="WP01")
        ports = _make_ports(feature_dir)

        _mt_uncheck_rollback_subtasks(st, ports)  # type: ignore[arg-type]

        # content unchanged; commit not called
        assert tasks_md.read_text(encoding="utf-8") == content
        ports.coord.commit_artifact.assert_not_called()

    def test_skips_silently_when_tasks_md_absent(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import _mt_uncheck_rollback_subtasks

        feature_dir = tmp_path / "kitty-specs" / "001-test-mission"
        feature_dir.mkdir(parents=True)
        # No tasks.md created

        st = _make_state(tmp_path, task_id="WP01")
        ports = _make_ports(feature_dir)

        _mt_uncheck_rollback_subtasks(st, ports)  # type: ignore[arg-type]

        ports.coord.commit_artifact.assert_not_called()

    def test_commits_when_resolved_auto_commit_true(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import _mt_uncheck_rollback_subtasks

        feature_dir = tmp_path / "kitty-specs" / "001-test-mission"
        feature_dir.mkdir(parents=True)
        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text(TASKS_WITH_CHECKED, encoding="utf-8")

        st = _make_state(tmp_path, task_id="WP01", resolved_auto_commit=True)
        ports = _make_ports(feature_dir)
        # Patch ProtectionPolicy.resolve so it doesn't need a real repo
        with patch("specify_cli.cli.commands.agent.tasks.ProtectionPolicy") as mock_pp:
            mock_pp.resolve.return_value = MagicMock()
            _mt_uncheck_rollback_subtasks(st, ports)  # type: ignore[arg-type]

        ports.coord.commit_artifact.assert_called_once()
        call_kwargs = ports.coord.commit_artifact.call_args
        assert call_kwargs.kwargs.get("kind") is not None or call_kwargs.args

    def test_skips_commit_when_resolved_auto_commit_false(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import _mt_uncheck_rollback_subtasks

        feature_dir = tmp_path / "kitty-specs" / "001-test-mission"
        feature_dir.mkdir(parents=True)
        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text(TASKS_WITH_CHECKED, encoding="utf-8")

        st = _make_state(tmp_path, task_id="WP01", resolved_auto_commit=False)
        ports = _make_ports(feature_dir)

        _mt_uncheck_rollback_subtasks(st, ports)  # type: ignore[arg-type]

        # File must still be written (the uncheck itself), but no commit
        result = tasks_md.read_text(encoding="utf-8")
        assert "- [ ] T001" in result
        ports.coord.commit_artifact.assert_not_called()

    def test_commit_failure_is_non_fatal(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import _mt_uncheck_rollback_subtasks

        feature_dir = tmp_path / "kitty-specs" / "001-test-mission"
        feature_dir.mkdir(parents=True)
        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text(TASKS_WITH_CHECKED, encoding="utf-8")

        st = _make_state(tmp_path, task_id="WP01", resolved_auto_commit=True)
        ports = _make_ports(feature_dir)
        ports.coord.commit_artifact.side_effect = RuntimeError("disk full")

        with patch("specify_cli.cli.commands.agent.tasks.ProtectionPolicy") as mock_pp:
            mock_pp.resolve.return_value = MagicMock()
            _mt_uncheck_rollback_subtasks(st, ports)  # type: ignore[arg-type]
        # must not raise — the write still happened
        assert "- [ ] T001" in tasks_md.read_text(encoding="utf-8")
