"""Regression tests for agent wrapper delegation into top-level commands."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app
from specify_cli.cli.commands.agent import workflow
from specify_cli.merge.config import MergeStrategy

pytestmark = pytest.mark.fast

runner = CliRunner()


def _workspace(exists: bool) -> SimpleNamespace:
    return SimpleNamespace(
        exists=exists,
        worktree_path=Path("/tmp/spec-kitty-test-worktree"),
        resolution_kind="repo_root",
    )


@patch("specify_cli.cli.commands.agent.mission.top_level_accept")
def test_agent_mission_accept_passes_explicit_feature_none(
    mock_top_level_accept: MagicMock,
) -> None:
    """Wrapper must pass explicit values for hidden Typer params.

    Without ``feature=None``, the delegated top-level command receives Typer's
    ``OptionInfo`` sentinel and selector resolution crashes before acceptance.
    """

    result = runner.invoke(
        app,
        ["accept", "--mission", "077-mission-terminology-cleanup", "--json"],
    )

    assert result.exit_code == 0, result.output
    mock_top_level_accept.assert_called_once_with(
        mission="077-mission-terminology-cleanup",
        feature=None,
        mode="auto",
        actor=None,
        test=[],
        json_output=True,
        lenient=False,
        no_commit=False,
        allow_fail=False,
    )


@patch("specify_cli.cli.commands.agent.mission.top_level_merge")
@patch("specify_cli.cli.commands.agent.mission.get_feature_target_branch")
@patch("specify_cli.cli.commands.agent.mission.locate_project_root")
def test_agent_mission_merge_passes_explicit_wrapper_defaults(
    mock_locate_project_root: MagicMock,
    mock_get_feature_target_branch: MagicMock,
    mock_top_level_merge: MagicMock,
    tmp_path: Path,
) -> None:
    """Merge wrapper must not leak OptionInfo sentinels into the delegate."""

    mock_locate_project_root.return_value = tmp_path
    mock_get_feature_target_branch.return_value = "main"

    result = runner.invoke(
        app,
        ["merge", "--mission", "077-mission-terminology-cleanup", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    mock_top_level_merge.assert_called_once_with(
        strategy=MergeStrategy.MERGE,
        delete_branch=True,
        remove_worktree=True,
        push=False,
        target_branch="main",
        dry_run=True,
        json_output=False,
        mission="077-mission-terminology-cleanup",
        feature=None,
        resume=False,
        abort=False,
        context_token=None,
        keep_workspace=False,
    )


@patch("specify_cli.cli.commands.agent.workflow.top_level_implement")
@patch("specify_cli.cli.commands.agent.workflow.resolve_workspace_for_wp")
@patch("specify_cli.cli.commands.agent.workflow.locate_work_package")
@patch("specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out")
@patch("specify_cli.cli.commands.agent.workflow.get_main_repo_root")
@patch("specify_cli.cli.commands.agent.workflow.locate_project_root")
@patch("specify_cli.cli.commands.agent.workflow._find_mission_slug")
def test_agent_action_implement_passes_acknowledge_default_false(
    mock_find_mission_slug: MagicMock,
    mock_locate_project_root: MagicMock,
    mock_get_main_repo_root: MagicMock,
    mock_ensure_target_branch_checked_out: MagicMock,
    mock_locate_work_package: MagicMock,
    mock_resolve_workspace_for_wp: MagicMock,
    mock_top_level_implement: MagicMock,
    tmp_path: Path,
) -> None:
    """Wrapper must forward the default acknowledgement value explicitly."""

    mock_find_mission_slug.return_value = "demo-mission"
    mock_locate_project_root.return_value = tmp_path
    mock_get_main_repo_root.return_value = tmp_path
    mock_ensure_target_branch_checked_out.return_value = (tmp_path, "main")
    mock_locate_work_package.return_value = SimpleNamespace(path=tmp_path / "wp01.md")
    mock_resolve_workspace_for_wp.return_value = _workspace(exists=False)
    mock_top_level_implement.side_effect = RuntimeError("stop after delegation")

    with pytest.raises(typer.Exit) as exc_info:
        workflow.implement(wp_id="WP01", mission="demo-mission", agent="claude")

    assert exc_info.value.exit_code == 1
    mock_top_level_implement.assert_called_once_with(
        wp_id="WP01",
        mission="demo-mission",
        json_output=False,
        recover=False,
        acknowledge_not_bulk_edit=False,
    )


@patch("specify_cli.cli.commands.agent.workflow.top_level_implement")
@patch("specify_cli.cli.commands.agent.workflow.resolve_workspace_for_wp")
@patch("specify_cli.cli.commands.agent.workflow.locate_work_package")
@patch("specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out")
@patch("specify_cli.cli.commands.agent.workflow.get_main_repo_root")
@patch("specify_cli.cli.commands.agent.workflow.locate_project_root")
@patch("specify_cli.cli.commands.agent.workflow._find_mission_slug")
def test_agent_action_implement_passes_acknowledge_true_when_requested(
    mock_find_mission_slug: MagicMock,
    mock_locate_project_root: MagicMock,
    mock_get_main_repo_root: MagicMock,
    mock_ensure_target_branch_checked_out: MagicMock,
    mock_locate_work_package: MagicMock,
    mock_resolve_workspace_for_wp: MagicMock,
    mock_top_level_implement: MagicMock,
    tmp_path: Path,
) -> None:
    """Wrapper must forward the explicit acknowledgement override."""

    mock_find_mission_slug.return_value = "demo-mission"
    mock_locate_project_root.return_value = tmp_path
    mock_get_main_repo_root.return_value = tmp_path
    mock_ensure_target_branch_checked_out.return_value = (tmp_path, "main")
    mock_locate_work_package.return_value = SimpleNamespace(path=tmp_path / "wp01.md")
    mock_resolve_workspace_for_wp.return_value = _workspace(exists=False)
    mock_top_level_implement.side_effect = RuntimeError("stop after delegation")

    with pytest.raises(typer.Exit) as exc_info:
        workflow.implement(
            wp_id="WP01",
            mission="demo-mission",
            agent="claude",
            acknowledge_not_bulk_edit=True,
        )

    assert exc_info.value.exit_code == 1
    mock_top_level_implement.assert_called_once_with(
        wp_id="WP01",
        mission="demo-mission",
        json_output=False,
        recover=False,
        acknowledge_not_bulk_edit=True,
    )
