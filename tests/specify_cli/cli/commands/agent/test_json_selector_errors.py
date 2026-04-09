"""Regression tests for JSON selector error contracts on agent commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.cli.commands.agent.status import app as status_app

pytestmark = pytest.mark.fast

runner = CliRunner()


@patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
def test_agent_tasks_status_missing_mission_returns_json_error(
    mock_locate_project_root: MagicMock,
    tmp_path: Path,
) -> None:
    """Missing selector errors must stay machine-readable under ``--json``."""

    mock_locate_project_root.return_value = tmp_path

    result = runner.invoke(tasks_app, ["status", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "error" in payload
    assert "--mission <slug>" in payload["error"]


def test_agent_status_validate_conflicting_selectors_return_json_error() -> None:
    """Conflict errors must stay machine-readable under ``--json``."""

    result = runner.invoke(
        status_app,
        [
            "validate",
            "--mission",
            "077-alpha",
            "--feature",
            "077-beta",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "error" in payload
    assert "Conflicting selectors" in payload["error"]
