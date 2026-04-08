"""Regression tests for agent wrapper delegation into top-level commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app
from specify_cli.merge.config import MergeStrategy

pytestmark = pytest.mark.fast

runner = CliRunner()


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
