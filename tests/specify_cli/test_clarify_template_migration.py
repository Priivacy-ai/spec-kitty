"""Integration tests for clarify template migration (0.13.5).

Tests validate that the migration correctly updates clarify.md templates
across all 12 agent directories, replacing broken placeholder with
check-prerequisites command.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.orchestrator.agent_config import AgentConfig, save_agent_config
from specify_cli.upgrade.migrations.m_0_13_5_fix_clarify_template import (
    FixClarifyTemplateMigration,
)


# All 12 agents and their directory structures
ALL_AGENTS = [
    ("claude", ".claude", "commands"),
    ("copilot", ".github", "prompts"),
    ("gemini", ".gemini", "commands"),
    ("cursor", ".cursor", "commands"),
    ("qwen", ".qwen", "commands"),
    ("opencode", ".opencode", "command"),
    ("windsurf", ".windsurf", "workflows"),
    ("codex", ".codex", "prompts"),
    ("kilocode", ".kilocode", "workflows"),
    ("auggie", ".augment", "commands"),
    ("roo", ".roo", "commands"),
    ("q", ".amazonq", "prompts"),
]


@pytest.fixture
def mock_project_all_agents_broken_placeholder(tmp_path):
    """Create a mock project with all 12 agents configured with broken placeholder."""
    # Create .kittify structure
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Configure all agents
    config = AgentConfig(available=[agent_key for agent_key, _, _ in ALL_AGENTS])
    save_agent_config(tmp_path, config)

    # Create agent directories with BROKEN clarify templates
    for _, agent_dir, subdir in ALL_AGENTS:
        agent_path = tmp_path / agent_dir / subdir
        agent_path.mkdir(parents=True)

        # Old clarify template with broken placeholder
        (agent_path / "spec-kitty.clarify.md").write_text(
            "---\n"
            "description: Identify underspecified areas\n"
            "---\n\n"
            "## Outline\n\n"
            "1. Run `(Missing script command for sh)` from repo root **once**\n"
            "2. Load the current spec file\n",
            encoding="utf-8",
        )

    # Create kitty-specs for detection
    (tmp_path / "kitty-specs").mkdir()

    return tmp_path


@pytest.fixture
def mock_project_all_agents_old_manual_detection(tmp_path):
    """Create a mock project with all 12 agents configured with old manual detection logic."""
    # Create .kittify structure
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Configure all agents
    config = AgentConfig(available=[agent_key for agent_key, _, _ in ALL_AGENTS])
    save_agent_config(tmp_path, config)

    # Create agent directories with OLD manual detection logic
    for _, agent_dir, subdir in ALL_AGENTS:
        agent_path = tmp_path / agent_dir / subdir
        agent_path.mkdir(parents=True)

        # Old clarify template with manual detection
        (agent_path / "spec-kitty.clarify.md").write_text(
            "---\n"
            "description: Identify underspecified areas\n"
            "---\n\n"
            "## Outline\n\n"
            "1. Detect the active feature and construct feature paths:\n"
            "   - Check git branch name for pattern `###-feature-name-WP##`\n"
            "   - If not found, check for most recent directory in `kitty-specs/`\n"
            "2. Load the current spec file\n",
            encoding="utf-8",
        )

    # Create kitty-specs for detection
    (tmp_path / "kitty-specs").mkdir()

    return tmp_path


@pytest.fixture
def mock_project_one_agent(tmp_path):
    """Create a mock project with only opencode configured."""
    # Create .kittify structure
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Configure only opencode
    config = AgentConfig(available=["opencode"])
    save_agent_config(tmp_path, config)

    # Create opencode directory
    opencode = tmp_path / ".opencode" / "command"
    opencode.mkdir(parents=True)

    # Old clarify template with broken placeholder
    (opencode / "spec-kitty.clarify.md").write_text(
        "1. Run `(Missing script command for sh)` from repo root\n",
        encoding="utf-8",
    )

    # Create kitty-specs
    (tmp_path / "kitty-specs").mkdir()

    return tmp_path


class TestDetection:
    """Tests for migration detection logic."""

    def test_detect_broken_placeholder(self, mock_project_all_agents_broken_placeholder):
        """Test detection returns True when templates have broken placeholder."""
        migration = FixClarifyTemplateMigration()
        assert migration.detect(mock_project_all_agents_broken_placeholder) is True

    def test_detect_old_manual_detection(self, mock_project_all_agents_old_manual_detection):
        """Test detection returns True when templates have old manual detection logic."""
        migration = FixClarifyTemplateMigration()
        assert migration.detect(mock_project_all_agents_old_manual_detection) is True

    def test_detect_already_migrated(self, mock_project_one_agent):
        """Test detection returns False when templates already have correct command."""
        # Manually update template with correct command
        opencode = mock_project_one_agent / ".opencode" / "command"
        (opencode / "spec-kitty.clarify.md").write_text(
            "1. Run `spec-kitty agent feature check-prerequisites --json --paths-only`\n",
            encoding="utf-8",
        )

        migration = FixClarifyTemplateMigration()
        assert migration.detect(mock_project_one_agent) is False


class TestCanApply:
    """Tests for can_apply check."""

    def test_can_apply_when_template_exists(self, mock_project_one_agent):
        """Test can_apply returns True when packaged template exists."""
        migration = FixClarifyTemplateMigration()
        can_apply, reason = migration.can_apply(mock_project_one_agent)

        assert can_apply is True
        assert reason == ""


class TestMigrationApply:
    """Tests for migration application."""

    @pytest.mark.parametrize(
        "agent_key,agent_dir,subdir",
        ALL_AGENTS,
        ids=[agent_key for agent_key, _, _ in ALL_AGENTS],
    )
    def test_update_all_agents_broken_placeholder(
        self, mock_project_all_agents_broken_placeholder, agent_key, agent_dir, subdir
    ):
        """Test migration updates clarify templates for all 12 agents (broken placeholder)."""
        migration = FixClarifyTemplateMigration()
        result = migration.apply(mock_project_all_agents_broken_placeholder, dry_run=False)

        assert result.success is True
        assert len(result.errors) == 0

        # Check this agent's template was updated
        template_path = (
            mock_project_all_agents_broken_placeholder
            / agent_dir
            / subdir
            / "spec-kitty.clarify.md"
        )
        content = template_path.read_text()

        # Should have correct command
        assert "spec-kitty agent feature check-prerequisites --json --paths-only" in content

        # Should NOT have broken placeholder
        assert "(Missing script command for sh)" not in content

        # Should NOT have manual detection logic
        assert "Check git branch name for pattern" not in content

    @pytest.mark.parametrize(
        "agent_key,agent_dir,subdir",
        ALL_AGENTS,
        ids=[agent_key for agent_key, _, _ in ALL_AGENTS],
    )
    def test_update_all_agents_old_manual_detection(
        self, mock_project_all_agents_old_manual_detection, agent_key, agent_dir, subdir
    ):
        """Test migration updates clarify templates for all 12 agents (old manual detection)."""
        migration = FixClarifyTemplateMigration()
        result = migration.apply(mock_project_all_agents_old_manual_detection, dry_run=False)

        assert result.success is True
        assert len(result.errors) == 0

        # Check this agent's template was updated
        template_path = (
            mock_project_all_agents_old_manual_detection
            / agent_dir
            / subdir
            / "spec-kitty.clarify.md"
        )
        content = template_path.read_text()

        # Should have correct command
        assert "spec-kitty agent feature check-prerequisites --json --paths-only" in content

        # Should NOT have manual detection logic
        assert "Check git branch name for pattern" not in content

    def test_update_respects_agent_config(self, tmp_path):
        """Test migration only updates configured agents."""
        # Create project with only opencode configured
        kittify = tmp_path / ".kittify"
        kittify.mkdir()

        config = AgentConfig(available=["opencode"])
        save_agent_config(tmp_path, config)

        # Create opencode directory (configured)
        opencode = tmp_path / ".opencode" / "command"
        opencode.mkdir(parents=True)
        (opencode / "spec-kitty.clarify.md").write_text(
            "1. Run `(Missing script command for sh)` from repo root\n"
        )

        # Create claude directory (NOT configured)
        claude = tmp_path / ".claude" / "commands"
        claude.mkdir(parents=True)
        claude_template = claude / "spec-kitty.clarify.md"
        claude_template.write_text("1. Run `(Missing script command for sh)` from repo root\n")
        original_claude_content = claude_template.read_text()

        (tmp_path / "kitty-specs").mkdir()

        # Run migration
        migration = FixClarifyTemplateMigration()
        result = migration.apply(tmp_path, dry_run=False)

        assert result.success is True

        # opencode should be updated
        opencode_content = (opencode / "spec-kitty.clarify.md").read_text()
        assert "check-prerequisites --json --paths-only" in opencode_content
        assert "(Missing script command for sh)" not in opencode_content

        # claude should NOT be updated (not configured)
        claude_content = claude_template.read_text()
        assert claude_content == original_claude_content
        assert "(Missing script command for sh)" in claude_content

    def test_update_idempotent(self, mock_project_one_agent):
        """Test migration is idempotent (safe to run multiple times)."""
        migration = FixClarifyTemplateMigration()

        # Run migration first time
        result1 = migration.apply(mock_project_one_agent, dry_run=False)
        assert result1.success is True

        # Read updated content
        opencode_template = (
            mock_project_one_agent / ".opencode" / "command" / "spec-kitty.clarify.md"
        )
        content_after_first = opencode_template.read_text()

        # Run migration second time
        result2 = migration.apply(mock_project_one_agent, dry_run=False)
        assert result2.success is True

        # Content should be identical
        content_after_second = opencode_template.read_text()
        assert content_after_first == content_after_second

    def test_update_dry_run(self, mock_project_one_agent):
        """Test dry run does not modify files."""
        migration = FixClarifyTemplateMigration()

        # Read original content
        opencode_template = (
            mock_project_one_agent / ".opencode" / "command" / "spec-kitty.clarify.md"
        )
        original_content = opencode_template.read_text()

        # Run dry run
        result = migration.apply(mock_project_one_agent, dry_run=True)

        assert result.success is True
        assert any("Would update" in change for change in result.changes_made)

        # Content should be unchanged
        assert opencode_template.read_text() == original_content

    def test_update_skips_missing_directories(self, tmp_path):
        """Test migration skips missing agent directories instead of creating them."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()

        # Configure claude but don't create directory
        config = AgentConfig(available=["claude"])
        save_agent_config(tmp_path, config)

        (tmp_path / "kitty-specs").mkdir()

        migration = FixClarifyTemplateMigration()
        result = migration.apply(tmp_path, dry_run=False)

        assert result.success is True

        # Claude directory should NOT be created
        assert not (tmp_path / ".claude" / "commands").exists()


class TestTemplateContent:
    """Tests for template content quality."""

    def test_template_source_exists(self):
        """Test that clarify template source file exists."""
        template_path = Path(
            "src/specify_cli/missions/software-dev/command-templates/clarify.md"
        )
        assert template_path.exists()

        content = template_path.read_text()

        # Should have correct command
        assert "spec-kitty agent feature check-prerequisites --json --paths-only" in content

        # Should NOT have broken placeholder
        assert "(Missing script command for sh)" not in content

        # Should NOT have manual detection logic
        assert "Check git branch name for pattern" not in content

    def test_template_matches_tasks_pattern(self):
        """Test clarify template uses same pattern as tasks.md for consistency."""
        clarify_path = Path(
            "src/specify_cli/missions/software-dev/command-templates/clarify.md"
        )
        tasks_path = Path("src/specify_cli/missions/software-dev/command-templates/tasks.md")

        clarify_content = clarify_path.read_text()
        tasks_content = tasks_path.read_text()

        # Both should use check-prerequisites command
        assert "check-prerequisites --json --paths-only" in clarify_content
        assert "check-prerequisites --json --paths-only" in tasks_content

        # Clarify should NOT have --include-tasks flag (that's only for tasks.md)
        clarify_lines = [
            line for line in clarify_content.split("\n") if "check-prerequisites" in line
        ]
        for line in clarify_lines:
            assert "--include-tasks" not in line
