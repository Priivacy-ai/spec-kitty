"""Tests for constitution CLI commands."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.constitution import app

runner = CliRunner()


# Sample constitution for testing
SAMPLE_CONSTITUTION = """# Testing Standards

## Coverage Requirements
- Minimum 80% coverage

## Quality Gates
- Pass all linters

## Agent Configuration
| agent | role |
|-------|------|
| claude | implementer |

## Project Directives
1. Write tests for new features
"""


@pytest.fixture
def mock_repo(tmp_path: Path):
    """Create a mock repository with constitution."""
    repo_root = tmp_path / "mock_repo"
    repo_root.mkdir()

    # Create .kittify/constitution/ structure
    constitution_dir = repo_root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)

    constitution_file = constitution_dir / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    return repo_root


def test_sync_command_success(mock_repo: Path):
    """Test sync command with valid constitution."""
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0
        assert "✅ Constitution synced successfully" in result.stdout
        assert "governance.yaml" in result.stdout
        assert "agents.yaml" in result.stdout
        assert "directives.yaml" in result.stdout
        assert "metadata.yaml" in result.stdout


def test_sync_command_already_synced(mock_repo: Path):
    """Test sync command when constitution is already synced."""
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        # First sync
        result1 = runner.invoke(app, ["sync"])
        assert result1.exit_code == 0

        # Second sync (should skip)
        result2 = runner.invoke(app, ["sync"])
        assert result2.exit_code == 0
        assert "already in sync" in result2.stdout


def test_sync_command_force_flag(mock_repo: Path):
    """Test sync command with --force flag."""
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        # First sync
        result1 = runner.invoke(app, ["sync"])
        assert result1.exit_code == 0

        # Second sync with --force
        result2 = runner.invoke(app, ["sync", "--force"])
        assert result2.exit_code == 0
        assert "✅ Constitution synced successfully" in result2.stdout


def test_sync_command_json_output(mock_repo: Path):
    """Test sync command with --json flag."""
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result = runner.invoke(app, ["sync", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "files_written" in data
        assert len(data["files_written"]) == 4


def test_sync_command_missing_constitution(tmp_path: Path):
    """Test sync command when constitution doesn't exist."""
    repo_root = tmp_path / "no_constitution"
    repo_root.mkdir()

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 1
        assert "Constitution not found" in result.stdout


def test_sync_command_legacy_path(tmp_path: Path):
    """Test sync command with legacy constitution path."""
    repo_root = tmp_path / "legacy_repo"
    repo_root.mkdir()

    # Create constitution in legacy location
    legacy_dir = repo_root / ".kittify" / "memory"
    legacy_dir.mkdir(parents=True)

    constitution_file = legacy_dir / "constitution.md"
    constitution_file.write_text(SAMPLE_CONSTITUTION, encoding="utf-8")

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0
        assert "✅ Constitution synced successfully" in result.stdout


def test_status_command_synced(mock_repo: Path):
    """Test status command when constitution is synced."""
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        # Sync first
        runner.invoke(app, ["sync"])

        # Check status
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "✅ SYNCED" in result.stdout
        assert "governance.yaml" in result.stdout
        assert "agents.yaml" in result.stdout


def test_status_command_stale(mock_repo: Path):
    """Test status command when constitution is stale."""
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        # Sync first
        runner.invoke(app, ["sync"])

        # Modify constitution
        constitution_file = mock_repo / ".kittify" / "constitution" / "constitution.md"
        modified_content = SAMPLE_CONSTITUTION + "\n2. Another directive\n"
        constitution_file.write_text(modified_content, encoding="utf-8")

        # Check status
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "⚠️  STALE" in result.stdout
        assert "spec-kitty constitution sync" in result.stdout


def test_status_command_no_prior_sync(mock_repo: Path):
    """Test status command when no prior sync exists."""
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "⚠️  STALE" in result.stdout


def test_status_command_json_output(mock_repo: Path):
    """Test status command with --json flag."""
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        # Sync first
        runner.invoke(app, ["sync"])

        # Check status with JSON
        result = runner.invoke(app, ["status", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        data = json.loads(result.stdout)
        assert data["status"] == "synced"
        assert "current_hash" in data
        assert "files" in data
        assert len(data["files"]) == 4


def test_status_command_file_sizes(mock_repo: Path):
    """Test status command displays file sizes."""
    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        # Sync first
        runner.invoke(app, ["sync"])

        # Check status
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        # Should show file sizes (KB)
        assert "KB" in result.stdout or "✓" in result.stdout


def test_status_command_missing_constitution(tmp_path: Path):
    """Test status command when constitution doesn't exist."""
    repo_root = tmp_path / "no_constitution"
    repo_root.mkdir()

    with patch("specify_cli.cli.commands.constitution.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "Constitution not found" in result.stdout


def test_help_output():
    """Test help output for constitution commands."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "constitution" in result.stdout.lower() or "Constitution" in result.stdout
    assert "sync" in result.stdout
    assert "status" in result.stdout
