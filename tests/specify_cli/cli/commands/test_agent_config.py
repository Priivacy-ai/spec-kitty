"""Tests for agent config management commands."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.config import app
from specify_cli.core.agent_config import AgentConfig, save_agent_config

runner = CliRunner()


@pytest.fixture
def mock_project(tmp_path):
    """Create a mock spec-kitty project."""
    # Create .kittify structure
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    config_file = kittify / "config.yaml"
    config_file.write_text("agents:\n  available:\n    - opencode\n")

    # Create mission templates
    missions = kittify / "missions" / "software-dev" / "command-templates"
    missions.mkdir(parents=True)

    (missions / "implement.md").write_text("# Implement Template")
    (missions / "review.md").write_text("# Review Template")

    # Create agent directories
    opencode = tmp_path / ".opencode" / "command"
    opencode.mkdir(parents=True)
    (opencode / "spec-kitty.implement.md").write_text("# Old Implement")

    return tmp_path


class TestListCommand:
    """Tests for 'spec-kitty agent config list' command."""

    def test_list_configured_agents(self, mock_project):
        """Test listing configured agents."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "opencode" in result.stdout
            assert ".opencode/command/" in result.stdout
            assert "✓" in result.stdout  # opencode exists

    def test_list_no_agents_configured(self, tmp_path):
        """Test listing when no agents are configured."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        (kittify / "config.yaml").write_text("agents:\n  available: []\n")

        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "No agents configured" in result.stdout

    def test_list_shows_available_agents(self, mock_project):
        """Test that list shows available but not configured agents."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "Available but not configured:" in result.stdout
            assert "claude" in result.stdout


class TestAddCommand:
    """Tests for 'spec-kitty agent config add' command."""

    def test_add_single_agent(self, mock_project):
        """Test adding a single agent."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["add", "claude"])

            assert result.exit_code == 0
            assert "Added .claude/commands/" in result.stdout
            assert "Updated config.yaml" in result.stdout

            # Verify directory was created
            assert (mock_project / ".claude" / "commands").exists()

            # Verify config was updated
            config_file = mock_project / ".kittify" / "config.yaml"
            config_content = config_file.read_text()
            assert "claude" in config_content

    def test_add_multiple_agents(self, mock_project):
        """Test adding multiple agents at once."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["add", "claude", "codex"])

            assert result.exit_code == 0
            assert "Added .claude/commands/" in result.stdout
            assert "Added .codex/prompts/" in result.stdout

            # Verify both directories were created
            assert (mock_project / ".claude" / "commands").exists()
            assert (mock_project / ".codex" / "prompts").exists()

    def test_add_already_configured_agent(self, mock_project):
        """Test adding an agent that's already configured."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["add", "opencode"])

            assert result.exit_code == 0
            assert "Already configured: opencode" in result.stdout

    def test_add_invalid_agent(self, mock_project):
        """Test adding an invalid agent key."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["add", "invalid-agent"])

            assert result.exit_code == 1
            assert "Invalid agent keys: invalid-agent" in result.stdout
            assert "Valid agents:" in result.stdout

    def test_add_creates_templates(self, mock_project):
        """Test that adding an agent copies templates."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["add", "claude"])

            assert result.exit_code == 0

            # Verify templates were copied
            claude_dir = mock_project / ".claude" / "commands"
            assert (claude_dir / "spec-kitty.implement.md").exists()
            assert (claude_dir / "spec-kitty.review.md").exists()


class TestRemoveCommand:
    """Tests for 'spec-kitty agent config remove' command."""

    def test_remove_agent(self, mock_project):
        """Test removing an agent."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["remove", "opencode"])

            assert result.exit_code == 0
            assert "Removed .opencode/" in result.stdout
            assert "Updated config.yaml" in result.stdout

            # Verify directory was deleted
            assert not (mock_project / ".opencode").exists()

    def test_remove_multiple_agents(self, mock_project):
        """Test removing multiple agents."""
        # Add another agent first (if not exists)
        claude = mock_project / ".claude" / "commands"
        if not claude.exists():
            claude.mkdir(parents=True)

        # Update config to include claude
        from specify_cli.core.agent_config import load_agent_config
        config = load_agent_config(mock_project)
        config.available.append("claude")
        save_agent_config(mock_project, config)

        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["remove", "opencode", "claude"])

            assert result.exit_code == 0
            assert "Removed .opencode/" in result.stdout
            assert "Removed .claude/" in result.stdout

    def test_remove_nonexistent_directory(self, mock_project):
        """Test removing an agent whose directory doesn't exist."""
        # Add gemini to config but not filesystem
        from specify_cli.core.agent_config import load_agent_config
        config = load_agent_config(mock_project)
        config.available.append("gemini")
        save_agent_config(mock_project, config)

        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["remove", "gemini"])

            assert result.exit_code == 0
            assert "already removed" in result.stdout.lower()

    def test_remove_with_keep_config(self, mock_project):
        """Test removing agent with --keep-config flag."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["remove", "opencode", "--keep-config"])

            assert result.exit_code == 0
            assert "Removed .opencode/" in result.stdout

            # Verify directory was deleted but config still has it
            assert not (mock_project / ".opencode").exists()

            from specify_cli.core.agent_config import load_agent_config
            config = load_agent_config(mock_project)
            assert "opencode" in config.available


class TestStatusCommand:
    """Tests for 'spec-kitty agent config status' command."""

    def test_status_shows_all_agents(self, mock_project):
        """Test status command shows all agents."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["status"])

            assert result.exit_code == 0
            assert "Agent Status" in result.stdout
            assert "opencode" in result.stdout
            assert "claude" in result.stdout

    def test_status_shows_ok_for_configured_and_present(self, mock_project):
        """Test status shows OK for agents that are configured and present."""
        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["status"])

            assert result.exit_code == 0
            # opencode is configured and present
            assert "OK" in result.stdout

    def test_status_shows_orphaned(self, mock_project):
        """Test status shows orphaned agents (present but not configured)."""
        # Create claude directory but don't add to config (if not exists)
        claude = mock_project / ".claude" / "commands"
        if not claude.exists():
            claude.mkdir(parents=True)

        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["status"])

            assert result.exit_code == 0
            assert "Orphaned" in result.stdout
            assert "orphaned directories found" in result.stdout


class TestSyncCommand:
    """Tests for 'spec-kitty agent config sync' command."""

    def test_sync_removes_orphaned(self, mock_project):
        """Test sync removes orphaned directories by default."""
        # Create orphaned claude directory (if not exists)
        claude = mock_project / ".claude" / "commands"
        if not claude.exists():
            claude.mkdir(parents=True)

        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["sync"])

            assert result.exit_code == 0
            assert "Removed orphaned .claude/" in result.stdout
            assert not (mock_project / ".claude").exists()

    def test_sync_keep_orphaned(self, mock_project):
        """Test sync with --keep-orphaned flag."""
        # Create orphaned claude directory (if not exists)
        claude = mock_project / ".claude" / "commands"
        if not claude.exists():
            claude.mkdir(parents=True)

        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["sync", "--keep-orphaned"])

            assert result.exit_code == 0
            # Should not remove claude
            assert (mock_project / ".claude" / "commands").exists()

    def test_sync_create_missing(self, mock_project):
        """Test sync creates missing directories with --create-missing."""
        # Add gemini to config but don't create directory
        from specify_cli.core.agent_config import load_agent_config
        config = load_agent_config(mock_project)
        config.available.append("gemini")
        save_agent_config(mock_project, config)

        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            result = runner.invoke(app, ["sync", "--create-missing"])

            assert result.exit_code == 0
            assert "Created .gemini/commands/" in result.stdout
            assert (mock_project / ".gemini" / "commands").exists()

    def test_sync_no_changes_needed(self, tmp_path):
        """Test sync when filesystem already matches config."""
        # Create fresh project with matching config and filesystem
        kittify = tmp_path / ".kittify"
        kittify.mkdir()

        # Config with only opencode
        config_file = kittify / "config.yaml"
        config_file.write_text("agents:\n  available:\n    - opencode\n")

        # Create only opencode directory
        opencode = tmp_path / ".opencode" / "command"
        opencode.mkdir(parents=True)

        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["sync"])

            assert result.exit_code == 0
            assert "No changes needed" in result.stdout


class TestAgentKeyMapping:
    """Tests for agent key to directory mapping."""

    def test_special_agent_keys(self, mock_project):
        """Test that special agent keys map correctly."""
        # copilot -> .github
        # auggie -> .augment
        # q -> .amazonq

        with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=mock_project):
            # Test copilot (maps to .github)
            result = runner.invoke(app, ["add", "copilot"])
            assert result.exit_code == 0
            assert (mock_project / ".github" / "prompts").exists()

            # Test auggie (maps to .augment)
            result = runner.invoke(app, ["add", "auggie"])
            assert result.exit_code == 0
            assert (mock_project / ".augment" / "commands").exists()

            # Test q (maps to .amazonq)
            result = runner.invoke(app, ["add", "q"])
            assert result.exit_code == 0
            assert (mock_project / ".amazonq" / "prompts").exists()
