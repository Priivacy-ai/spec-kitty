"""Characterization + focused-helper tests for the WP07 degod (#2649, folds #2604).

Pins BEFORE and AFTER the WP07 decomposition of ``tasks_move_task.py``:

- T032: the ``#2576``/``#2513`` dual-handler contract on
  ``_mt_uncheck_rollback_subtasks`` (a write/read failure is RECORDED on
  state and logged at error level; a commit failure is a SEPARATE, swallowed
  warning) — the two failure modes must never be merged into one handler
  (C-001).
- T032: ``_mt_commit_wp_file``'s degrade-never-crash placement-ref branch —
  when ``_mt_resolve_status_placement_ref`` cannot resolve a placement (any
  internal failure), the WP-file commit still completes without raising.
- T033: ``_do_move_task``'s parameter count stays at or under the local ≤13
  gate now that the 21-parameter signature collapsed to a
  ``_MoveTaskArgs`` param object + ``ports``.
- T034/T035: focused tests for the module-private helpers extracted out of
  ``_mt_commit_wp_file`` (folds #2604) and ``_mt_uncheck_rollback_subtasks``.
"""

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.agent_tasks_ports import CommitArtifactResult
from specify_cli.cli.commands.agent import tasks_move_task
from specify_cli.cli.commands.agent.tasks_move_task import (
    _MoveTaskArgs,
    _MoveTaskState,
    _do_move_task,
    _mt_commit_wp_file,
    _mt_uncheck_rollback_subtasks,
)
from specify_cli.status import Lane

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_MODULE = "specify_cli.cli.commands.agent.tasks_move_task"

TASKS_WITH_CHECKED = """\
## WP01 — Build widget

- [x] T001 Design the API
- [x] T002 Implement the handler
- [ ] T003 Write tests
"""


# --------------------------------------------------------------------------- #
# Shared state/ports builders
# --------------------------------------------------------------------------- #


def _make_state(tmp_path: Path, **overrides: object) -> _MoveTaskState:
    """Build a minimal ``_MoveTaskState``, mirroring the sibling rollback-uncheck
    test files' own builder so this file stays consistent with the established
    fixture shape."""
    kwargs: dict[str, object] = {
        "task_id": "WP01",
        "to": "planned",
        "mission": None,
        "agent": None,
        "assignee": None,
        "shell_pid": None,
        "note": None,
        "review_feedback_file": None,
        "approval_ref": None,
        "reviewer": None,
        "self_review_fallback": False,
        "intended_reviewer": None,
        "reviewer_failure_reason": None,
        "done_override_reason": None,
        "force": False,
        "tracker_ref": None,
        "skip_review_artifact_check": False,
        "auto_commit": None,
        "json_output": False,
        "target_lane": Lane.PLANNED,
        "old_lane": Lane.FOR_REVIEW,
        "main_repo_root": tmp_path,
        "mission_slug": "001-test-mission",
        "resolved_auto_commit": True,
    }
    kwargs.update(overrides)
    return _MoveTaskState(**kwargs)  # type: ignore[arg-type]


def _make_uncheck_ports(feature_dir: Path) -> MagicMock:
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


# --------------------------------------------------------------------------- #
# T032 — #2576/#2513 dual-handler characterization (MUST stay separate, C-001)
# --------------------------------------------------------------------------- #


class TestUncheckRollbackDualHandler:
    """Pins the two independent exception handlers on
    ``_mt_uncheck_rollback_subtasks``: a write/read failure is SURFACED on
    ``st.rollback_uncheck_error`` (never swallowed); a commit failure is a
    SEPARATE, still-swallowed warning. They must never be merged into one
    ``logging.exception`` catch-all."""

    def test_write_failure_is_recorded_and_logged_never_swallowed(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path)
        ports = _make_uncheck_ports(feature_dir)

        with (
            caplog.at_level(logging.ERROR),
            patch(f"{_MODULE}.write_text_within_directory", side_effect=OSError("disk full")),
        ):
            _mt_uncheck_rollback_subtasks(st, ports)

        assert st.rollback_uncheck_error is not None
        assert "disk full" in st.rollback_uncheck_error
        assert any(record.levelno == logging.ERROR for record in caplog.records)
        # The write-failure leg never reaches the commit step at all.
        ports.coord.commit_artifact.assert_not_called()
        # Rows stay checked on disk — the failure is surfaced, not silently fixed.
        assert "- [x] T001" in tasks_md.read_text(encoding="utf-8")

    def test_commit_failure_is_a_separate_swallowed_warning(self, tmp_path: Path) -> None:
        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path, resolved_auto_commit=True)
        ports = _make_uncheck_ports(feature_dir)
        ports.coord.commit_artifact.side_effect = RuntimeError("commit backend down")

        with patch("specify_cli.cli.commands.agent.tasks.ProtectionPolicy") as mock_pp:
            mock_pp.resolve.return_value = MagicMock()
            _mt_uncheck_rollback_subtasks(st, ports)  # must not raise

        # The write itself succeeded (only the commit bookkeeping failed) —
        # this is the DIFFERENT #2513 leg; it must not set rollback_uncheck_error.
        assert st.rollback_uncheck_error is None
        assert "- [ ] T001" in tasks_md.read_text(encoding="utf-8")

    def test_never_raises_regardless_of_which_handler_fires(self, tmp_path: Path) -> None:
        feature_dir, _tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path)
        ports = _make_uncheck_ports(feature_dir)

        with patch(f"{_MODULE}.write_text_within_directory", side_effect=OSError("boom")):
            _mt_uncheck_rollback_subtasks(st, ports)  # a downstream caller still runs


# --------------------------------------------------------------------------- #
# T032 — _mt_commit_wp_file degrade-never-crash placement-ref branch
# --------------------------------------------------------------------------- #


class TestCommitWpFileDegradeNeverCrash:
    """Pins ``_mt_commit_wp_file``'s observable behavior BEFORE extraction:
    when placement resolution degrades (any internal failure inside
    ``_mt_resolve_status_placement_ref``), the WP-file commit still completes
    without crashing the move-task — not just the happy path."""

    def _state(self, tmp_path: Path, wp_path: Path) -> _MoveTaskState:
        from types import SimpleNamespace
        from typing import Any, cast

        st = _make_state(
            tmp_path,
            to="for_review",
            target_lane=Lane.FOR_REVIEW,
            mission_slug="",  # empty slug is the seam's own degrade trigger
        )
        st.wp = cast(Any, SimpleNamespace(path=wp_path))
        st.feature_dir = tmp_path / "kitty-specs" / "001-test-mission"
        st.feature_dir.mkdir(parents=True, exist_ok=True)
        return st

    def test_commit_completes_when_placement_resolution_degrades(self, tmp_path: Path) -> None:
        wp_path = tmp_path / "WP01-x.md"
        wp_path.write_text("original", encoding="utf-8")
        st = self._state(tmp_path, wp_path)

        ports = MagicMock()
        ports.coord.commit_artifact.return_value = CommitArtifactResult(
            status="committed", placement_ref="main"
        )

        with (
            patch("specify_cli.cli.commands.agent.tasks.ProtectionPolicy") as mock_pp,
            patch(f"{_MODULE}._collect_status_artifacts", return_value=[]),
            patch("specify_cli.cli.commands.agent.tasks._primary_bundle_status_artifacts", return_value=[]),
        ):
            mock_pp.resolve.return_value = MagicMock()
            # No exception raised — the degrade-never-crash contract.
            _mt_commit_wp_file(st, ports, "updated", "unknown", skip_target_commit=False)

        assert wp_path.read_text(encoding="utf-8") == "updated"
        ports.coord.commit_artifact.assert_called_once()

    def test_happy_path_commit_success_prints_plain_message(self, tmp_path: Path) -> None:
        """Non-regression baseline: a resolvable placement that matches
        ``target_branch`` reports the ORIGINAL plain message (no divergence)."""
        wp_path = tmp_path / "WP01-x.md"
        wp_path.write_text("original", encoding="utf-8")
        st = self._state(tmp_path, wp_path)
        st.target_branch = "main"

        ports = MagicMock()
        ports.coord.commit_artifact.return_value = CommitArtifactResult(
            status="committed", placement_ref="main"
        )

        with (
            patch("specify_cli.cli.commands.agent.tasks.ProtectionPolicy") as mock_pp,
            patch(f"{_MODULE}._collect_status_artifacts", return_value=[]),
            patch("specify_cli.cli.commands.agent.tasks._primary_bundle_status_artifacts", return_value=[]),
            patch("specify_cli.cli.commands.agent.tasks.console") as console_mock,
        ):
            mock_pp.resolve.return_value = MagicMock()
            _mt_commit_wp_file(st, ports, "updated", "unknown", skip_target_commit=False)

        printed = " ".join(str(call.args[0]) for call in console_mock.print.call_args_list)
        assert "Committed status change to main branch" in printed
        assert "status bookkeeping" not in printed


# --------------------------------------------------------------------------- #
# T034 — focused tests for the helpers extracted out of _mt_commit_wp_file
# --------------------------------------------------------------------------- #


class TestCommitWpFileHelpers:
    def test_wp_commit_message_without_known_agent(self, tmp_path: Path) -> None:
        st = _make_state(tmp_path, task_id="WP03", mission_slug="042-widget", target_lane=Lane.APPROVED)
        msg = tasks_move_task._mt_wp_commit_message(st, "unknown")
        assert msg == f"chore: Move WP03 to {Lane.APPROVED} on spec 042"
        assert "[" not in msg

    def test_wp_commit_message_appends_known_agent(self, tmp_path: Path) -> None:
        st = _make_state(tmp_path, task_id="WP03", mission_slug="042-widget", target_lane=Lane.APPROVED)
        msg = tasks_move_task._mt_wp_commit_message(st, "claude")
        assert msg.endswith(" [claude]")

    def test_report_commit_outcome_success_prints_success_message(self, tmp_path: Path) -> None:
        st = _make_state(tmp_path, json_output=False, target_branch="main")
        with patch("specify_cli.cli.commands.agent.tasks.console") as console_mock:
            tasks_move_task._mt_report_commit_outcome(
                st,
                commit_success=True,
                skip_target_commit=False,
                router_result=CommitArtifactResult(status="committed", placement_ref="main"),
                status_placement_ref="main",
            )
        printed = " ".join(str(call.args[0]) for call in console_mock.print.call_args_list)
        assert "Committed status change" in printed

    def test_report_commit_outcome_failure_warns_without_swallowing(self, tmp_path: Path) -> None:
        """#2155: a router error is surfaced as a warning, never silently dropped."""
        st = _make_state(tmp_path, json_output=False)
        router_result = CommitArtifactResult(status="error", placement_ref="main", diagnostic="boom")
        with patch("specify_cli.cli.commands.agent.tasks.console") as console_mock:
            tasks_move_task._mt_report_commit_outcome(
                st,
                commit_success=False,
                skip_target_commit=False,
                router_result=router_result,
                status_placement_ref=None,
            )
        printed = " ".join(str(call.args[0]) for call in console_mock.print.call_args_list)
        assert "did not land" in printed
        assert "boom" in printed

    def test_report_commit_outcome_skip_arm_prints_nothing(self, tmp_path: Path) -> None:
        st = _make_state(tmp_path, json_output=False)
        with patch("specify_cli.cli.commands.agent.tasks.console") as console_mock:
            tasks_move_task._mt_report_commit_outcome(
                st,
                commit_success=False,
                skip_target_commit=True,
                router_result=None,
                status_placement_ref=None,
            )
        console_mock.print.assert_not_called()


# --------------------------------------------------------------------------- #
# T035 — focused tests for the helpers extracted out of
# _mt_uncheck_rollback_subtasks
# --------------------------------------------------------------------------- #


class TestUncheckRollbackHelpers:
    def test_attempt_uncheck_write_returns_true_and_writes_on_success(self, tmp_path: Path) -> None:
        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path)

        wrote = tasks_move_task._mt_attempt_uncheck_write(st, tasks_md, feature_dir)

        assert wrote is True
        assert "- [ ] T001" in tasks_md.read_text(encoding="utf-8")
        assert st.rollback_uncheck_error is None

    def test_attempt_uncheck_write_returns_false_when_nothing_to_uncheck(self, tmp_path: Path) -> None:
        feature_dir, tasks_md = _seed_tasks_md(tmp_path, content="## WP01\n\n- [ ] T001 already unchecked\n")
        st = _make_state(tmp_path)

        wrote = tasks_move_task._mt_attempt_uncheck_write(st, tasks_md, feature_dir)

        assert wrote is False
        assert st.rollback_uncheck_error is None

    def test_attempt_uncheck_write_returns_false_and_records_error_on_failure(
        self, tmp_path: Path
    ) -> None:
        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path)

        with patch(f"{_MODULE}.write_text_within_directory", side_effect=OSError("disk full")):
            wrote = tasks_move_task._mt_attempt_uncheck_write(st, tasks_md, feature_dir)

        assert wrote is False
        assert st.rollback_uncheck_error is not None

    def test_commit_uncheck_tasks_md_swallows_commit_failure(self, tmp_path: Path) -> None:
        from specify_cli.agent_tasks_ports import MissionHandle

        feature_dir, tasks_md = _seed_tasks_md(tmp_path)
        st = _make_state(tmp_path)
        ports = _make_uncheck_ports(feature_dir)
        ports.coord.commit_artifact.side_effect = RuntimeError("commit backend down")
        handle = MissionHandle(repo_root=tmp_path, mission_slug=st.mission_slug)

        with patch("specify_cli.cli.commands.agent.tasks.ProtectionPolicy") as mock_pp:
            mock_pp.resolve.return_value = MagicMock()
            tasks_move_task._mt_commit_uncheck_tasks_md(st, ports, handle, tasks_md)  # no raise

        assert st.rollback_uncheck_error is None


# --------------------------------------------------------------------------- #
# T033 — _do_move_task parameter-object ceiling (the ONE hard local gate)
# --------------------------------------------------------------------------- #


def test_do_move_task_param_count_at_or_under_ceiling() -> None:
    params = inspect.signature(_do_move_task).parameters
    assert len(params) <= 13, (
        f"_do_move_task has {len(params)} parameters — must stay <=13 "
        "(the parameter-object ceiling, T033/#2649)."
    )


def test_do_move_task_accepts_move_task_args_param_object() -> None:
    params = list(inspect.signature(_do_move_task).parameters)
    assert params[0] == "args"
    assert "ports" in params


def test_move_task_args_field_set_matches_pre_extraction_signature() -> None:
    """The param object groups every raw CLI-facing input the pre-extraction
    21-parameter signature carried (minus ``ports``, which stays a separate DI
    seam) — NFR-002 behavior preservation."""
    expected = {
        "task_id",
        "to",
        "mission",
        "agent",
        "assignee",
        "shell_pid",
        "note",
        "review_feedback_file",
        "approval_ref",
        "reviewer",
        "self_review_fallback",
        "intended_reviewer",
        "reviewer_failure_reason",
        "done_override_reason",
        "force",
        "tracker_ref",
        "skip_review_artifact_check",
        "auto_commit",
        "json_output",
        "skip_pre_review_gate",
    }
    assert set(_MoveTaskArgs.__dataclass_fields__) == expected
