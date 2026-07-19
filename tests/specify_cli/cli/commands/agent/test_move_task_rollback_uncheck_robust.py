"""Failure-mode tests for ``_mt_uncheck_rollback_subtasks`` (WP03, #2576).

``_mt_uncheck_rollback_subtasks`` runs OUT-OF-LOCK (C-001) on rollback to
``planned`` and must never let a write failure leave stale ``- [x]`` rows on
disk *silently* — that would let #2513 (gate passes on stale progress)
re-manifest with no signal at all. These tests pin:

- T019: a simulated write failure is SURFACED on ``_MoveTaskState`` and the
  file is left untouched (not partially written) rather than silently
  "succeeding" with stale checked rows.
- T020: the write goes through ``write_text_within_directory`` (the house
  containment guard), not a bare ``Path.write_text``.
- T021: the new failure handler is separate from — and does not touch —
  the pre-existing commit-failure handler; a write failure never reaches the
  commit step at all.
- T022: the out-of-lock ordering from ``_mt_execute`` (uncheck, then release
  the review lock) is preserved even when the uncheck fails — a write
  failure must not propagate past ``_mt_reset_for_planned_rollback`` and
  skip ``_mt_release_review_lock``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

TASKS_WITH_CHECKED = """\
## WP01 — Build widget

- [x] T001 Design the API
- [x] T002 Implement the handler
- [ ] T003 Write tests

## WP02 — Ship widget

- [x] T004 Ship it
"""


def _make_state(
    tmp_path: Path,
    *,
    task_id: str = "WP01",
    mission_slug: str = "001-test-mission",
    resolved_auto_commit: bool = True,
    old_lane: object | None = None,
    target_lane: object | None = None,
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
        target_lane=target_lane if target_lane is not None else Lane.PLANNED,
        old_lane=old_lane if old_lane is not None else Lane.FOR_REVIEW,
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


def _seed_tasks_md(tmp_path: Path, content: str = TASKS_WITH_CHECKED) -> tuple[Path, Path]:
    feature_dir = tmp_path / "kitty-specs" / "001-test-mission"
    feature_dir.mkdir(parents=True)
    tasks_md = feature_dir / "tasks.md"
    tasks_md.write_text(content, encoding="utf-8")
    return feature_dir, tasks_md


class TestWriteFailureSurfaced:
    """T019: a write failure is recorded on state, not silently dropped."""

    def test_write_failure_is_recorded_on_state(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import (
            _mt_uncheck_rollback_subtasks,
        )

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path)
        ports = _make_ports(feature_dir)

        with patch(
            "specify_cli.cli.commands.agent.tasks_move_task.write_text_within_directory",
            side_effect=OSError("disk full"),
        ):
            _mt_uncheck_rollback_subtasks(st, ports)

        assert st.rollback_uncheck_error is not None
        assert "disk full" in st.rollback_uncheck_error

    def test_write_failure_leaves_rows_checked_not_silently(self, tmp_path: Path) -> None:
        """The file is untouched on write failure — rows stay checked — but
        that outcome is SURFACED (state carries the error), not silent."""
        from specify_cli.cli.commands.agent.tasks_move_task import (
            _mt_uncheck_rollback_subtasks,
        )

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path)
        ports = _make_ports(feature_dir)

        with patch(
            "specify_cli.cli.commands.agent.tasks_move_task.write_text_within_directory",
            side_effect=OSError("disk full"),
        ):
            _mt_uncheck_rollback_subtasks(st, ports)

        # The write never landed — rows remain checked on disk...
        result = tasks_md.read_text(encoding="utf-8")
        assert "- [x] T001" in result
        assert "- [x] T002" in result
        # ...but the incomplete rollback is reflected on state, not swallowed.
        assert st.rollback_uncheck_error is not None

    def test_write_failure_does_not_raise(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import (
            _mt_uncheck_rollback_subtasks,
        )

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path)
        ports = _make_ports(feature_dir)

        with patch(
            "specify_cli.cli.commands.agent.tasks_move_task.write_text_within_directory",
            side_effect=OSError("disk full"),
        ):
            # Must not propagate — a caller downstream (_mt_release_review_lock)
            # still needs to run.
            _mt_uncheck_rollback_subtasks(st, ports)

    def test_write_failure_logs_at_error_level(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import (
            _mt_uncheck_rollback_subtasks,
        )

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path)
        ports = _make_ports(feature_dir)

        with (
            caplog.at_level(logging.ERROR),
            patch(
                "specify_cli.cli.commands.agent.tasks_move_task.write_text_within_directory",
                side_effect=OSError("disk full"),
            ),
        ):
            _mt_uncheck_rollback_subtasks(st, ports)

        assert any(record.levelno == logging.ERROR for record in caplog.records)
        assert any("disk full" in record.getMessage() for record in caplog.records)

    def test_read_failure_is_also_surfaced(self, tmp_path: Path) -> None:
        """The read half of the seam is covered by the same guard: a read
        error must not propagate uncaught either."""
        from specify_cli.cli.commands.agent.tasks_move_task import (
            _mt_uncheck_rollback_subtasks,
        )

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path)
        ports = _make_ports(feature_dir)

        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            _mt_uncheck_rollback_subtasks(st, ports)

        assert st.rollback_uncheck_error is not None
        assert "permission denied" in st.rollback_uncheck_error


class TestWriteRoutedThroughHouseGuard:
    """T020: the write path uses write_text_within_directory, not a bare write."""

    def test_write_goes_through_write_text_within_directory(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import (
            _mt_uncheck_rollback_subtasks,
        )

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path, resolved_auto_commit=False)
        ports = _make_ports(feature_dir)

        with patch(
            "specify_cli.cli.commands.agent.tasks_move_task.write_text_within_directory"
        ) as mock_write:
            _mt_uncheck_rollback_subtasks(st, ports)

        mock_write.assert_called_once()
        call_args, call_kwargs = mock_write.call_args
        assert call_args[0] == tasks_md
        assert "- [ ] T001" in call_args[1]
        assert call_kwargs.get("root") == feature_dir

    def test_successful_write_still_lands_on_disk(self, tmp_path: Path) -> None:
        """Non-regression: routing through the house guard still writes for
        real (no mock) — the on-disk contract from #2513 is unchanged."""
        from specify_cli.cli.commands.agent.tasks_move_task import (
            _mt_uncheck_rollback_subtasks,
        )

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path, resolved_auto_commit=False)
        ports = _make_ports(feature_dir)

        _mt_uncheck_rollback_subtasks(st, ports)

        result = tasks_md.read_text(encoding="utf-8")
        assert "- [ ] T001" in result
        assert "- [ ] T002" in result
        assert st.rollback_uncheck_error is None


class TestFailureHandlerSeparateFromCommitHandler:
    """T021: the write-failure handler is distinct from the commit-failure one."""

    def test_write_failure_never_reaches_commit(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks_move_task import (
            _mt_uncheck_rollback_subtasks,
        )

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path, resolved_auto_commit=True)
        ports = _make_ports(feature_dir)

        with patch(
            "specify_cli.cli.commands.agent.tasks_move_task.write_text_within_directory",
            side_effect=OSError("disk full"),
        ):
            _mt_uncheck_rollback_subtasks(st, ports)

        # The write failed before the commit step is ever reached.
        ports.coord.commit_artifact.assert_not_called()
        assert st.rollback_uncheck_error is not None

    def test_commit_failure_still_does_not_set_rollback_uncheck_error(
        self, tmp_path: Path
    ) -> None:
        """Regression: a COMMIT failure (pre-existing #2513 behavior) is a
        separate, still-swallowed warning — it must not be conflated with
        the new write-failure state field."""
        from specify_cli.cli.commands.agent.tasks_move_task import (
            _mt_uncheck_rollback_subtasks,
        )

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path, resolved_auto_commit=True)
        ports = _make_ports(feature_dir)
        ports.coord.commit_artifact.side_effect = RuntimeError("commit backend down")

        with patch("specify_cli.cli.commands.agent.tasks.ProtectionPolicy") as mock_pp:
            mock_pp.resolve.return_value = MagicMock()
            _mt_uncheck_rollback_subtasks(st, ports)

        # The write itself succeeded — only the commit bookkeeping failed —
        # so the new field stays None; this is the pre-existing #2513 leg.
        assert st.rollback_uncheck_error is None
        assert "- [ ] T001" in tasks_md.read_text(encoding="utf-8")


class TestOutOfLockOrderingPreserved:
    """T022: rollback-uncheck failure must not block the review-lock release."""

    def test_reset_then_release_runs_full_sequence_on_uncheck_failure(
        self, tmp_path: Path
    ) -> None:
        """Mirrors the post-lock tail of ``_mt_execute``:
        ``_mt_reset_for_planned_rollback`` then ``_mt_release_review_lock``.
        A write failure in the first call must not raise, so the second call
        is always reached — this is the D2 ordering guarantee.
        """
        from specify_cli.cli.commands.agent.tasks_move_task import (
            _mt_reset_for_planned_rollback,
            _mt_release_review_lock,
        )
        from specify_cli.status import Lane

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(
            tmp_path,
            resolved_auto_commit=True,
            old_lane=Lane.FOR_REVIEW,
            target_lane=Lane.PLANNED,
        )
        ports = _make_ports(feature_dir)

        release_mock = MagicMock()
        with (
            patch(
                "specify_cli.cli.commands.agent.tasks_move_task.write_text_within_directory",
                side_effect=OSError("disk full"),
            ),
            patch("specify_cli.review.lock.ReviewLock.release", release_mock),
            patch(
                "specify_cli.cli.commands.agent.tasks.resolve_workspace_for_wp",
                return_value=MagicMock(worktree_path=str(tmp_path)),
            ),
        ):
            # Simulates the exact post-lock call order in _mt_execute.
            _mt_reset_for_planned_rollback(st, ports)
            _mt_release_review_lock(st)

        # The uncheck failure was recorded...
        assert st.rollback_uncheck_error is not None
        # ...and did NOT prevent the review-lock release from running.
        release_mock.assert_called_once()
