"""Scope: mock-boundary tests for deprecated agent check-prerequisites alias — no real git."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.agent import app

pytestmark = pytest.mark.fast

runner = CliRunner()


def test_alias_forwards_to_feature_command() -> None:
    """check-prerequisites alias routes all flags to feature.check_prerequisites."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act
    with patch("specify_cli.cli.commands.agent.mission.check_prerequisites") as mock_cmd:
        result = runner.invoke(
            app,
            [
                "check-prerequisites",
                "--feature",
                "001-test",
                "--json",
                "--paths-only",
                "--include-tasks",
            ],
        )

    # Assert
    assert result.exit_code == 0
    mock_cmd.assert_called_once_with(
        feature="001-test",
        json_output=True,
        paths_only=True,
        include_tasks=True,
        require_tasks=False,
    )


def test_alias_passes_deprecated_require_tasks_flag() -> None:
    """check-prerequisites alias forwards --require-tasks to the underlying command."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act
    with patch("specify_cli.cli.commands.agent.mission.check_prerequisites") as mock_cmd:
        result = runner.invoke(
            app,
            [
                "check-prerequisites",
                "--json",
                "--require-tasks",
            ],
        )

    # Assert
    assert result.exit_code == 0
    mock_cmd.assert_called_once_with(
        feature=None,
        json_output=True,
        paths_only=False,
        include_tasks=False,
        require_tasks=True,
    )
