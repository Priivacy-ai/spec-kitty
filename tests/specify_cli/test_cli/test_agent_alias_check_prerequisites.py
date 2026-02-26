"""Tests for deprecated top-level agent check-prerequisites alias."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.agent import app


runner = CliRunner()


def test_alias_forwards_to_feature_command() -> None:
    with patch("specify_cli.cli.commands.agent.feature.check_prerequisites") as mock_cmd:
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

    assert result.exit_code == 0
    mock_cmd.assert_called_once_with(
        feature="001-test",
        json_output=True,
        paths_only=True,
        include_tasks=True,
        require_tasks=False,
    )


def test_alias_passes_deprecated_require_tasks_flag() -> None:
    with patch("specify_cli.cli.commands.agent.feature.check_prerequisites") as mock_cmd:
        result = runner.invoke(
            app,
            [
                "check-prerequisites",
                "--json",
                "--require-tasks",
            ],
        )

    assert result.exit_code == 0
    mock_cmd.assert_called_once_with(
        feature=None,
        json_output=True,
        paths_only=False,
        include_tasks=False,
        require_tasks=True,
    )
