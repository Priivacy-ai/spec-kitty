"""Tests for agent profile interview creation flow."""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.profile import app
import pytest
pytestmark = pytest.mark.fast



runner = CliRunner()


def test_create_interview_defaults_generates_profile(tmp_path: Path) -> None:
    project_dir = tmp_path / "agents"
    user_input = "\n".join([
        "python-pedro",
        "Python Pedro",
        "Implement Python tasks",
        "implementer",
        "Python implementation",
    ]) + "\n"

    result = runner.invoke(
        app,
        ["create", "--interview", "--defaults", "--project-dir", str(project_dir)],
        input=user_input,
    )

    assert result.exit_code == 0, result.output

    profile_file = project_dir / "python-pedro.agent.yaml"
    assert profile_file.exists()

    data = yaml.safe_load(profile_file.read_text(encoding="utf-8"))
    assert data["profile-id"] == "python-pedro"
    assert data["role"] == "implementer"
    assert "capabilities" in data
    assert "read" in data["capabilities"]


def test_create_interview_invalid_profile_id_fails_validation(tmp_path: Path) -> None:
    project_dir = tmp_path / "agents"
    user_input = "\n".join([
        "Not-Kebab",
        "Name",
        "Purpose",
        "implementer",
        "Focus",
    ]) + "\n"

    result = runner.invoke(
        app,
        ["create", "--interview", "--defaults", "--project-dir", str(project_dir)],
        input=user_input,
    )

    assert result.exit_code == 1
    assert "failed schema validation" in result.output


def test_create_interview_duplicate_profile_fails(tmp_path: Path) -> None:
    project_dir = tmp_path / "agents"
    project_dir.mkdir(parents=True)
    existing = project_dir / "existing.agent.yaml"
    existing.write_text(
        """profile-id: existing
name: Existing
purpose: Existing profile
specialization:
  primary-focus: existing
""",
        encoding="utf-8",
    )

    user_input = "\n".join([
        "existing",
        "Existing",
        "Purpose",
        "implementer",
        "Focus",
    ]) + "\n"

    result = runner.invoke(
        app,
        ["create", "--interview", "--defaults", "--project-dir", str(project_dir)],
        input=user_input,
    )

    assert result.exit_code == 1
    assert "already exists" in result.output
