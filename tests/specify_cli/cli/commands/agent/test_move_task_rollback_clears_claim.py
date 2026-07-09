"""#2512: move-task --to planned clears stale agent/shell_pid claim markers.

Field repro: an agent process was killed by macOS idle-sleep, leaving
``agent: "claude-code"`` and ``shell_pid: "41417"`` in the WP frontmatter.
``move-task WPxx --to planned`` reset the event-log lane back to ``planned``
but did NOT clear those fields, so the next orchestrator resume call failed
with ``LANE_ALLOCATION_FAILED`` (the allocator's liveness check was absent).

Fix: when ``target_lane == Lane.PLANNED``, delete ``agent`` and ``shell_pid``
from the frontmatter BEFORE any caller-supplied value is re-planted, so a plain
rollback always leaves the WP with a clean claim state.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.task_utils import extract_scalar

pytestmark = [pytest.mark.fast]

_WP_FRONTMATTER_WITH_STALE_CLAIM = """\
---
work_package_id: WP03
title: "Engine Telemetry"
agent: "claude-code"
shell_pid: "41417"
dependencies: []
---

Body text.
"""


def _make_wp_file(tmp_path: Path) -> Path:
    wp_path = tmp_path / "WP03.md"
    wp_path.write_text(_WP_FRONTMATTER_WITH_STALE_CLAIM, encoding="utf-8")
    return wp_path


def _run_persist_wp_file(
    tmp_path: Path,
    *,
    target_lane_value: str,
    agent: str | None = None,
    shell_pid: str | None = None,
) -> str:
    """Exercise _mt_persist_wp_file in isolation via _MoveTaskState."""
    from specify_cli.status.models import Lane
    from specify_cli.cli.commands.agent.tasks_move_task import (
        _MoveTaskState,
        _mt_persist_wp_file,
    )
    from specify_cli.task_utils import WorkPackage, split_frontmatter

    wp_path = _make_wp_file(tmp_path)
    front, body, padding = split_frontmatter(
        wp_path.read_text(encoding="utf-8-sig")
    )
    wp = WorkPackage(
        feature="review-context-depth-01KX2EQ9",
        path=wp_path,
        current_lane="in_review",
        relative_subpath=Path("tasks/WP03.md"),
        frontmatter=front,
        body=body,
        padding=padding,
    )

    decision_mock = MagicMock()
    decision_mock.skip_primary = True  # skip the actual git commit

    st = _MoveTaskState(
        task_id="WP03",
        to=target_lane_value,
        mission=None,
        agent=agent,
        assignee=None,
        shell_pid=shell_pid,
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
        auto_commit=False,
        json_output=True,
    )
    st.target_lane = Lane(target_lane_value)
    st.old_lane = Lane.IN_REVIEW
    st.wp = wp
    st.decision = decision_mock
    st.final_hop_actor = agent or "user"
    st.main_repo_root = tmp_path
    st.target_branch = "main"
    st.mission_slug = "review-context-depth-01KX2EQ9"
    st.resolved_auto_commit = False
    st.note_text = None

    ports = MagicMock()
    ports.coord.commit_artifact.return_value = MagicMock(status="committed")

    with (
        patch(
            "specify_cli.cli.commands.agent.tasks_move_task.write_text_within_directory",
            side_effect=lambda path, content, **_: path.write_text(content, encoding="utf-8"),
        ),
        patch(
            "specify_cli.cli.commands.agent.tasks._tasks",
            create=True,
        ),
    ):
        _mt_persist_wp_file(st, ports)

    return wp_path.read_text(encoding="utf-8")


def test_rollback_to_planned_clears_agent(tmp_path: Path) -> None:
    """Rolling a WP back to planned must erase the agent claim field."""
    result = _run_persist_wp_file(tmp_path, target_lane_value="planned")
    front = result.split("---")[1]
    assert extract_scalar(front, "agent") is None


def test_rollback_to_planned_clears_shell_pid(tmp_path: Path) -> None:
    """Rolling a WP back to planned must erase the shell_pid claim field."""
    result = _run_persist_wp_file(tmp_path, target_lane_value="planned")
    front = result.split("---")[1]
    assert extract_scalar(front, "shell_pid") is None


def test_rollback_to_planned_replants_agent_if_provided(tmp_path: Path) -> None:
    """An explicit --agent on rollback re-plants a fresh claim (override case)."""
    result = _run_persist_wp_file(
        tmp_path, target_lane_value="planned", agent="claude-code"
    )
    front = result.split("---")[1]
    assert extract_scalar(front, "agent") == "claude-code"


def test_forward_transition_preserves_agent(tmp_path: Path) -> None:
    """Forward transitions (e.g. in_progress) must NOT strip existing claim."""
    result = _run_persist_wp_file(tmp_path, target_lane_value="in_progress")
    front = result.split("---")[1]
    # No explicit agent provided, so the stale value should SURVIVE on forward
    # transitions (claim is the implementer's, not the reviewer's to clear).
    assert extract_scalar(front, "agent") == "claude-code"
