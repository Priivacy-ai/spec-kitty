"""Integration tests for spec-kitty profiles CLI command."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app

# Marked for mutmut sandbox skip — subprocess CLI invocation.
pytestmark = pytest.mark.non_sandbox

runner = CliRunner()

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "profiles"


def _setup_project(tmp_path: Path) -> Path:
    """Set up a minimal project structure with fixture profiles."""
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(parents=True)
    profiles_dir = kittify_dir / "profiles"
    profiles_dir.mkdir()
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProfilesListJsonOutput:
    def test_exits_zero_and_returns_valid_json(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        with patch("specify_cli.cli.commands.profiles_cmd.find_repo_root", return_value=project):
            result = runner.invoke(cli_app, ["profiles", "list", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_json_output_has_required_fields(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        with patch("specify_cli.cli.commands.profiles_cmd.find_repo_root", return_value=project):
            result = runner.invoke(cli_app, ["profiles", "list", "--json"])
        assert result.exit_code == 0
        profiles = json.loads(result.output)
        assert len(profiles) >= 1
        for p in profiles:
            assert "profile_id" in p
            assert "name" in p
            assert "role" in p
            assert "action_domains" in p
            assert "source" in p

    def test_json_output_includes_fixture_profiles(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        with patch("specify_cli.cli.commands.profiles_cmd.find_repo_root", return_value=project):
            result = runner.invoke(cli_app, ["profiles", "list", "--json"])
        profiles = json.loads(result.output)
        profile_ids = [p["profile_id"] for p in profiles]
        assert "implementer-fixture" in profile_ids


class TestProfilesListTableOutput:
    def test_exits_zero_with_table_output(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        with patch("specify_cli.cli.commands.profiles_cmd.find_repo_root", return_value=project):
            result = runner.invoke(cli_app, ["profiles", "list"])
        assert result.exit_code == 0, result.output
        # Table title should appear in output
        assert "Profile" in result.output or "profile" in result.output.lower()

    def test_table_output_contains_profile_ids(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        with patch("specify_cli.cli.commands.profiles_cmd.find_repo_root", return_value=project):
            result = runner.invoke(cli_app, ["profiles", "list"])
        assert result.exit_code == 0
        assert "implementer-fixture" in result.output


class TestProfilesListNoProfiles:
    def test_no_profiles_json_returns_empty_array(self, tmp_path: Path) -> None:
        """When no profiles are returned, --json outputs empty array."""
        from specify_cli.invocation.registry import ProfileRegistry

        project = tmp_path
        (project / ".kittify").mkdir(parents=True)

        with (
            patch("specify_cli.cli.commands.profiles_cmd.find_repo_root", return_value=project),
            patch.object(ProfileRegistry, "list_all", return_value=[]),
        ):
            result = runner.invoke(cli_app, ["profiles", "list", "--json"])
        assert result.exit_code == 0
        assert result.output.strip() == "[]"

    def test_no_profiles_table_shows_helpful_message(self, tmp_path: Path) -> None:
        """When no profiles found, a helpful message is shown."""
        from specify_cli.invocation.registry import ProfileRegistry

        project = tmp_path
        (project / ".kittify").mkdir(parents=True)

        with (
            patch("specify_cli.cli.commands.profiles_cmd.find_repo_root", return_value=project),
            patch.object(ProfileRegistry, "list_all", return_value=[]),
        ):
            result = runner.invoke(cli_app, ["profiles", "list"])
        assert result.exit_code == 0
        assert "No profiles" in result.output or "charter" in result.output.lower()


class TestProfilesHelp:
    def test_profiles_help_exits_zero(self) -> None:
        result = runner.invoke(cli_app, ["profiles", "--help"])
        assert result.exit_code == 0
        assert "profiles" in result.output.lower()
