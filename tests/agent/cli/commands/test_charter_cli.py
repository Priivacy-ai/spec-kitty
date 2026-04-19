"""Tests for charter CLI commands."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app

pytestmark = pytest.mark.fast

runner = CliRunner()


SAMPLE_CHARTER = """# Testing Standards

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

    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)

    charter_file = charter_dir / "charter.md"
    charter_file.write_text(SAMPLE_CHARTER, encoding="utf-8")

    return repo_root


def test_sync_command_success(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0
        assert "Charter synced successfully" in result.stdout
        assert "governance.yaml" in result.stdout
        assert "directives.yaml" in result.stdout
        assert "metadata.yaml" in result.stdout


def test_sync_command_already_synced(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result1 = runner.invoke(app, ["sync"])
        assert result1.exit_code == 0

        result2 = runner.invoke(app, ["sync"])
        assert result2.exit_code == 0
        assert "already in sync" in result2.stdout


def test_sync_command_json_output(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        result = runner.invoke(app, ["sync", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["files_written"]) == 3


def test_sync_command_missing_charter(tmp_path: Path) -> None:
    repo_root = tmp_path / "no_charter"
    repo_root.mkdir()

    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 1
        assert "Charter not found" in result.stdout


def test_status_command_synced(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        runner.invoke(app, ["sync"])
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "SYNCED" in result.stdout
        assert "governance.yaml" in result.stdout
        assert "directives.yaml" in result.stdout


def test_status_command_json_output(mock_repo: Path) -> None:
    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = mock_repo

        runner.invoke(app, ["sync"])
        result = runner.invoke(app, ["status", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["charter_sync"]["status"] == "synced"
        assert len(data["charter_sync"]["files"]) == 4


def test_interview_defaults_writes_answers(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["interview", "--defaults", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        answers_path = repo_root / payload["interview_path"]
        assert answers_path.exists()


def test_generate_command_success(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "charter").mkdir(parents=True)

    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate"])

        assert result.exit_code == 0
        assert "generated and synced" in result.stdout
        assert (repo_root / ".kittify" / "charter" / "charter.md").exists()
        assert (repo_root / ".kittify" / "charter" / "references.yaml").exists()
        assert (repo_root / ".kittify" / "charter" / "governance.yaml").exists()
        assert (repo_root / ".kittify" / "charter" / "library").exists()


def test_generate_command_requires_force_when_existing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    (charter_dir / "charter.md").write_text("# Existing", encoding="utf-8")

    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate"])

        assert result.exit_code == 1
        assert "--force" in result.stdout


def test_generate_command_force_overwrites(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    charter_file = charter_dir / "charter.md"
    charter_file.write_text("# Existing", encoding="utf-8")

    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        result = runner.invoke(app, ["generate", "--force", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["template_set"]
        assert "selected_directives" in data
        assert data["references_count"] >= 1


def test_context_bootstrap_then_compact(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".kittify" / "charter").mkdir(parents=True)

    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        generate_result = runner.invoke(app, ["generate", "--json"])
        assert generate_result.exit_code == 0

        first = runner.invoke(app, ["context", "--action", "specify", "--json"])
        assert first.exit_code == 0
        first_payload = json.loads(first.stdout)
        assert first_payload["mode"] == "bootstrap"
        assert first_payload["first_load"] is True

        second = runner.invoke(app, ["context", "--action", "specify", "--json"])
        assert second.exit_code == 0
        second_payload = json.loads(second.stdout)
        assert second_payload["mode"] == "compact"
        assert second_payload["first_load"] is False


def test_context_compact_mode_auto_syncs_missing_extracted_artifacts(tmp_path: Path) -> None:
    import subprocess as _subprocess

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    # WP03: chokepoint requires a git-tracked project root (FR-003).
    _subprocess.run(["git", "init", "--quiet", str(repo_root)], check=True)
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)

    with patch("specify_cli.cli.commands.charter.find_repo_root") as mock_find_root:
        mock_find_root.return_value = repo_root

        generate_result = runner.invoke(app, ["generate", "--json"])
        assert generate_result.exit_code == 0

        first = runner.invoke(app, ["context", "--action", "plan", "--json"])
        assert first.exit_code == 0
        first_payload = json.loads(first.stdout)
        assert first_payload["mode"] == "bootstrap"

        for name in ("governance.yaml", "directives.yaml", "metadata.yaml"):
            (charter_dir / name).unlink()

        second = runner.invoke(app, ["context", "--action", "plan", "--json"])
        assert second.exit_code == 0
        second_payload = json.loads(second.stdout)
        assert second_payload["mode"] == "compact"
        assert second_payload["first_load"] is False
        assert (charter_dir / "governance.yaml").exists()
        assert (charter_dir / "directives.yaml").exists()
        assert (charter_dir / "metadata.yaml").exists()
        assert "Run 'spec-kitty charter sync'" not in second.stdout


def test_help_output() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "charter" in result.stdout.lower() or "Charter" in result.stdout
    assert "interview" in result.stdout
    assert "generate" in result.stdout
    assert "context" in result.stdout
    assert "sync" in result.stdout
    assert "status" in result.stdout
