"""#2037: the worktree kitty-specs/ note must not probe an unsafe mission_slug.

``_mt_warn_worktree_kitty_specs`` builds ``worktree_kitty / st.mission_slug /
"tasks"`` from ``st.mission_slug``, which threads back to the operator-typed
``--mission`` CLI value with no ``assert_safe_path_segment`` upstream. This is
a read-only ``.exists()`` probe feeding a purely informational console note,
so a hostile slug must fail closed by skipping the note — not by raising, and
not by letting a crafted value walk the probe outside the intended
``kitty-specs/`` directory.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from specify_cli.cli.commands.agent import tasks_move_task
from specify_cli.cli.commands.agent.tasks_move_task import _MoveTaskState
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.status import Lane

pytestmark = pytest.mark.fast

_MODULE = "specify_cli.cli.commands.agent.tasks_move_task"
_TASKS = "specify_cli.cli.commands.agent.tasks"


def _make_state(*, mission_slug: str, main_repo_root: Path) -> _MoveTaskState:
    st = _MoveTaskState(
        task_id="WP01",
        to="for_review",
        mission=mission_slug,
        agent="claude",
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
        skip_pre_review_gate=False,
    )
    st.target_lane = Lane.FOR_REVIEW
    st.main_repo_root = main_repo_root
    st.target_branch = "main"
    st.mission_slug = mission_slug
    st.wp = SimpleNamespace(path=Path("WP01-x.md"), frontmatter="")
    return st


def _worktree_cwd(tmp_path: Path, *, kitty_specs_child: str) -> Path:
    """A ``.worktrees/<lane>`` cwd whose kitty-specs/ dir carries one child."""
    worktree = tmp_path / "main-repo" / ".worktrees" / "lane-a"
    kitty = worktree / KITTY_SPECS_DIR
    (kitty / kitty_specs_child / "tasks").mkdir(parents=True)
    return worktree


def test_note_probe_skips_and_warns_for_unsafe_mission_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A traversal-shaped slug must not reach the ``.exists()`` join at all."""
    cwd = _worktree_cwd(tmp_path, kitty_specs_child="evil")
    monkeypatch.chdir(cwd)
    st = _make_state(mission_slug="../evil", main_repo_root=tmp_path / "main-repo-root")

    with (
        patch(f"{_MODULE}.is_worktree_context", return_value=True),
        patch(f"{_TASKS}.console.print") as print_mock,
        caplog.at_level("WARNING"),
    ):
        tasks_move_task._mt_warn_worktree_kitty_specs(st)

    print_mock.assert_not_called()
    assert "unsafe mission_slug" in caplog.text


def test_note_probe_still_prints_for_safe_mission_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sanity check: the guard does not regress the legitimate note."""
    cwd = _worktree_cwd(tmp_path, kitty_specs_child="001-m")
    monkeypatch.chdir(cwd)
    st = _make_state(mission_slug="001-m", main_repo_root=tmp_path / "main-repo-root")

    with (
        patch(f"{_MODULE}.is_worktree_context", return_value=True),
        patch(f"{_TASKS}.console.print") as print_mock,
    ):
        tasks_move_task._mt_warn_worktree_kitty_specs(st)

    print_mock.assert_called_once()
