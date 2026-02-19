"""Tests for the `spec-kitty agent telemetry emit` CLI command."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.telemetry import app


runner = CliRunner()


@pytest.fixture()
def project_with_feature(tmp_path: Path) -> Path:
    """Create a minimal project structure with a feature directory."""
    kitty_specs = tmp_path / "kitty-specs" / "048-test-feature"
    kitty_specs.mkdir(parents=True)
    # Create .kittify marker so find_repo_root works
    (tmp_path / ".kittify").mkdir()
    return tmp_path


def _read_events(project_root: Path, feature: str) -> list[dict]:
    """Read events from the feature's JSONL file."""
    jsonl_path = project_root / "kitty-specs" / feature / "execution.events.jsonl"
    if not jsonl_path.exists():
        return []
    events = []
    for line in jsonl_path.read_text().strip().splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def test_emit_specifier_event_with_all_flags(project_with_feature: Path) -> None:
    """Emit a specifier event with all optional flags provided."""
    with patch("specify_cli.cli.commands.agent.telemetry.find_repo_root", return_value=project_with_feature):
        result = runner.invoke(app, [
            "emit",
            "--feature", "048-test-feature",
            "--role", "specifier",
            "--agent", "claude",
            "--model", "claude-opus-4-6",
            "--input-tokens", "50000",
            "--output-tokens", "5000",
            "--cost-usd", "1.50",
            "--duration-ms", "90000",
            "--wp-id", "N/A",
        ])

    assert result.exit_code == 0
    events = _read_events(project_with_feature, "048-test-feature")
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["role"] == "specifier"
    assert payload["agent"] == "claude"
    assert payload["model"] == "claude-opus-4-6"
    assert payload["input_tokens"] == 50000
    assert payload["output_tokens"] == 5000
    assert payload["cost_usd"] == 1.50
    assert payload["duration_ms"] == 90000
    assert payload["success"] is True


def test_emit_minimal_flags(project_with_feature: Path) -> None:
    """Emit with only required flags — agent/model default to unknown/None."""
    with patch("specify_cli.cli.commands.agent.telemetry.find_repo_root", return_value=project_with_feature):
        result = runner.invoke(app, [
            "emit",
            "--feature", "048-test-feature",
            "--role", "planner",
        ])

    assert result.exit_code == 0
    events = _read_events(project_with_feature, "048-test-feature")
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["role"] == "planner"
    assert payload["agent"] == "unknown"
    assert payload["model"] is None
    assert payload["input_tokens"] is None
    assert payload["output_tokens"] is None
    assert payload["cost_usd"] is None


def test_emit_failure_flag(project_with_feature: Path) -> None:
    """Emit with --failure sets success to false."""
    with patch("specify_cli.cli.commands.agent.telemetry.find_repo_root", return_value=project_with_feature):
        result = runner.invoke(app, [
            "emit",
            "--feature", "048-test-feature",
            "--role", "merger",
            "--failure",
        ])

    assert result.exit_code == 0
    events = _read_events(project_with_feature, "048-test-feature")
    assert len(events) == 1
    assert events[0]["payload"]["success"] is False


def test_emit_json_output(project_with_feature: Path) -> None:
    """Emit with --json returns structured JSON output."""
    with patch("specify_cli.cli.commands.agent.telemetry.find_repo_root", return_value=project_with_feature):
        result = runner.invoke(app, [
            "emit",
            "--feature", "048-test-feature",
            "--role", "reviewer",
            "--agent", "copilot",
            "--model", "gpt-4.1",
            "--json",
        ])

    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["result"] == "success"
    assert output["feature"] == "048-test-feature"
    assert output["role"] == "reviewer"
    assert output["agent"] == "copilot"
    assert output["model"] == "gpt-4.1"


def test_emit_invalid_role(project_with_feature: Path) -> None:
    """Invalid role is rejected by click.Choice."""
    with patch("specify_cli.cli.commands.agent.telemetry.find_repo_root", return_value=project_with_feature):
        result = runner.invoke(app, [
            "emit",
            "--feature", "048-test-feature",
            "--role", "invalid_role",
        ])

    assert result.exit_code != 0


def test_emit_creates_feature_dir_if_missing(tmp_path: Path) -> None:
    """Feature directory is created if it doesn't exist."""
    (tmp_path / ".kittify").mkdir()
    # Don't create the feature dir — emit should create it

    with patch("specify_cli.cli.commands.agent.telemetry.find_repo_root", return_value=tmp_path):
        result = runner.invoke(app, [
            "emit",
            "--feature", "099-new-feature",
            "--role", "specifier",
        ])

    assert result.exit_code == 0
    assert (tmp_path / "kitty-specs" / "099-new-feature").is_dir()
    events = _read_events(tmp_path, "099-new-feature")
    assert len(events) == 1


def test_emit_all_roles(project_with_feature: Path) -> None:
    """All 5 role values are accepted."""
    roles = ["specifier", "planner", "implementer", "reviewer", "merger"]
    for role in roles:
        with patch("specify_cli.cli.commands.agent.telemetry.find_repo_root", return_value=project_with_feature):
            result = runner.invoke(app, [
                "emit",
                "--feature", "048-test-feature",
                "--role", role,
            ])
        assert result.exit_code == 0, f"Role {role} failed with exit code {result.exit_code}"

    events = _read_events(project_with_feature, "048-test-feature")
    assert len(events) == 5
    emitted_roles = [e["payload"]["role"] for e in events]
    assert set(emitted_roles) == set(roles)
