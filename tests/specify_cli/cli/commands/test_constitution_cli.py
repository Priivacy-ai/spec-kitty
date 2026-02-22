"""Tests for constitution CLI commands."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.constitution import app

runner = CliRunner()


SAMPLE_CONSTITUTION = """# Testing Standards

## Coverage Requirements
- Minimum 80% coverage

## Quality Gates
- Pass all linters

## Project Directives
1. Write tests for new features
"""


@pytest.fixture
def mock_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "mock_repo"
    repo_root.mkdir()

    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)

    constitution_file = constitution_dir / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    return repo_root


def test_sync_command_success(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0
        assert "✅ Constitution synced successfully" in result.stdout
        assert "governance.yaml" in result.stdout
        assert "directives.yaml" in result.stdout
        assert "metadata.yaml" in result.stdout


def test_sync_command_already_synced(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result1 = runner.invoke(app, ["sync"])
        assert result1.exit_code == 0

        result2 = runner.invoke(app, ["sync"])
        assert result2.exit_code == 0
        assert "already in sync" in result2.stdout


def test_sync_command_json_output(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result = runner.invoke(app, ["sync", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["files_written"]) == 3


def test_sync_command_missing_constitution(tmp_path: Path) -> None:
    repo_root = tmp_path / "no_constitution"
    repo_root.mkdir()

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 1
        assert "Constitution not found" in result.stdout


def test_status_command_synced(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        runner.invoke(app, ["sync"])
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "✅ SYNCED" in result.stdout
        assert "governance.yaml" in result.stdout
        assert "directives.yaml" in result.stdout


def test_status_command_json_output(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        runner.invoke(app, ["sync"])
        result = runner.invoke(app, ["status", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["status"] == "synced"
        assert len(data["files"]) == 3


def test_generate_command_success(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "constitution").mkdir(parents=True)

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate"])

        assert result.exit_code == 0
        assert "generated and synced" in result.stdout
        assert (repo_root / ".kittify" / "constitution" / "constitution.md").exists()
        assert (repo_root / ".kittify" / "constitution" / "governance.yaml").exists()
        assert (repo_root / ".kittify" / "constitution" / "directives.yaml").exists()


def test_generate_command_requires_force_when_existing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    (constitution_dir / "constitution.md").write_text("# Existing", encoding="utf-8")

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate"])

        assert result.exit_code == 1
        assert "Use --force" in result.stdout


def test_generate_command_force_overwrites(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    constitution_file = constitution_dir / "constitution.md"
    constitution_file.write_text("# Existing", encoding="utf-8")

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate", "--force", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["template_set"]
        assert "selected_directives" in data


def test_help_output() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "constitution" in result.stdout.lower() or "Constitution" in result.stdout
    assert "generate" in result.stdout
    assert "sync" in result.stdout
    assert "status" in result.stdout
