"""Tests for agent profile CLI commands."""

from __future__ import annotations

from typer.testing import CliRunner

from specify_cli.cli.commands.agent.profile import app
import pytest
pytestmark = pytest.mark.fast


runner = CliRunner()


class TestListProfiles:
    """Tests for 'spec-kitty agent profile list' command."""

    def test_list_profiles_success(self):
        """List command returns 0 and shows table headers."""
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "Agent Profiles" in result.output
        assert "ID" in result.output
        assert "Name" in result.output
        assert "Role" in result.output


class TestShowProfile:
    """Tests for 'spec-kitty agent profile show' command."""

    def test_show_profile_success(self):
        """Show a known shipped profile returns 0 with details."""
        result = runner.invoke(app, ["show", "architect"])

        assert result.exit_code == 0
        assert "architect" in result.output
        assert "Architect" in result.output

    def test_show_profile_not_found(self):
        """Show a nonexistent profile returns exit code 1."""
        result = runner.invoke(app, ["show", "nonexistent-xyz"])

        assert result.exit_code == 1
        assert "not found" in result.output


class TestHierarchy:
    """Tests for 'spec-kitty agent profile hierarchy' command."""

    def test_hierarchy_success(self):
        """Hierarchy command returns 0 and renders tree output."""
        result = runner.invoke(app, ["hierarchy"])

        assert result.exit_code == 0
        # Should show summary counts
        assert "total profiles" in result.output


class TestCreateProfile:
    """Tests for 'spec-kitty agent profile create' command."""

    def test_create_profile_success(self, tmp_path):
        """Create copies a template profile into project dir."""
        result = runner.invoke(
            app,
            [
                "create",
                "--from-template", "implementer",
                "--profile-id", "my-impl",
                "--project-dir", str(tmp_path),
            ],
        )

        assert result.exit_code == 0
        assert "Created" in result.output
        dest = tmp_path / "my-impl.agent.yaml"
        assert dest.exists()
        content = dest.read_text()
        assert "profile-id: my-impl" in content

    def test_create_profile_duplicate(self, tmp_path):
        """Creating a profile that already exists fails with exit code 1."""
        # Pre-create the file so the duplicate check triggers
        dest = tmp_path / "my-impl.agent.yaml"
        dest.write_text("profile-id: my-impl\n")

        result = runner.invoke(
            app,
            [
                "create",
                "--from-template", "implementer",
                "--profile-id", "my-impl",
                "--project-dir", str(tmp_path),
            ],
        )

        assert result.exit_code == 1
        assert "already exists" in result.output
