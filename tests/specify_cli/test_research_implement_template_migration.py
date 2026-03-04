"""Integration tests for research implement template migration (0.13.0).

Tests validate that the migration correctly updates research implement.md
templates across all 12 agent directories with CSV schema documentation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.agent_config import AgentConfig, save_agent_config
from specify_cli.upgrade.migrations.m_0_13_0_update_research_implement_templates import (
    UpdateResearchImplementTemplatesMigration,
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
def mock_research_project_all_agents(tmp_path):
    """Create a mock project with all 12 agents configured."""
    # Create .kittify structure
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Configure all agents
    config = AgentConfig(available=[agent_key for agent_key, _, _ in ALL_AGENTS])
    save_agent_config(tmp_path, config)

    # Create agent directories with OLD research templates (missing schema docs)
    for _, agent_dir, subdir in ALL_AGENTS:
        agent_path = tmp_path / agent_dir / subdir
        agent_path.mkdir(parents=True)

        # Old research template (has Sprint Planning Artifacts but NO CSV schemas)
        (agent_path / "spec-kitty.implement.md").write_text(
            "---\n"
            "description: Implement research WP\n"
            "---\n\n"
            "## Sprint Planning Artifacts (Separate)\n\n"
            "Planning artifacts in kitty-specs/\n\n"
            "---\n\n"
            "## Key Differences from Software-Dev\n",
            encoding="utf-8",
        )

    # Create kitty-specs for detection
    (tmp_path / "kitty-specs").mkdir()

    return tmp_path


@pytest.fixture
def mock_research_project_one_agent(tmp_path):
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

    # Old research template
    (opencode / "spec-kitty.implement.md").write_text(
        "## Sprint Planning Artifacts (Separate)\n\nPlanning artifacts\n",
        encoding="utf-8",
    )

    # Create kitty-specs
    (tmp_path / "kitty-specs").mkdir()

    return tmp_path


@pytest.fixture
def mock_software_dev_project(tmp_path):
    """Create a mock project with software-dev templates (should NOT be updated)."""
    # Create .kittify structure
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Configure all agents
    config = AgentConfig(available=["claude", "opencode"])
    save_agent_config(tmp_path, config)

    # Create agent directories with SOFTWARE-DEV templates (NO Sprint Planning Artifacts)
    for agent_dir, subdir in [(".claude", "commands"), (".opencode", "command")]:
        agent_path = tmp_path / agent_dir / subdir
        agent_path.mkdir(parents=True)

        # Software-dev template (no Sprint Planning Artifacts)
        (agent_path / "spec-kitty.implement.md").write_text(
            "---\ndescription: Implement software WP\n---\n\n## Implementation Workflow\n\nNavigate to worktree\n",
            encoding="utf-8",
        )

    (tmp_path / "kitty-specs").mkdir()

    return tmp_path


class TestDetection:
    """Tests for migration detection logic."""

    def test_detect_missing_schema_docs(self, mock_research_project_all_agents):
        """Test detection returns True when templates missing schema docs."""
        migration = UpdateResearchImplementTemplatesMigration()
        assert migration.detect(mock_research_project_all_agents) is True

    def test_detect_already_migrated(self, mock_research_project_one_agent):
        """Test detection returns False when templates already have schema docs."""
        # Manually update template with schema section
        opencode = mock_research_project_one_agent / ".opencode" / "command"
        (opencode / "spec-kitty.implement.md").write_text(
            "## Sprint Planning Artifacts (Separate)\n\n"
            "## Research CSV Schemas (CRITICAL - DO NOT MODIFY HEADERS)\n\n"
            "Schema docs here\n",
            encoding="utf-8",
        )

        migration = UpdateResearchImplementTemplatesMigration()
        assert migration.detect(mock_research_project_one_agent) is False

    def test_detect_software_dev_templates(self, mock_software_dev_project):
        """Test detection returns False for software-dev templates."""
        migration = UpdateResearchImplementTemplatesMigration()
        assert migration.detect(mock_software_dev_project) is False


class TestCanApply:
    """Tests for can_apply check."""

    def test_can_apply_when_template_exists(self, mock_research_project_one_agent):
        """Test can_apply returns True when packaged template exists."""
        migration = UpdateResearchImplementTemplatesMigration()
        can_apply, reason = migration.can_apply(mock_research_project_one_agent)

        assert can_apply is True
        assert reason == ""


class TestMigrationApply:
    """Tests for migration application."""

    @pytest.mark.parametrize(
        "agent_key,agent_dir,subdir",
        ALL_AGENTS,
        ids=[agent_key for agent_key, _, _ in ALL_AGENTS],
    )
    def test_update_all_agents(self, mock_research_project_all_agents, agent_key, agent_dir, subdir):
        """Test migration updates research templates for all 12 agents."""
        migration = UpdateResearchImplementTemplatesMigration()
        result = migration.apply(mock_research_project_all_agents, dry_run=False)

        assert result.success is True
        assert len(result.errors) == 0

        # Check this agent's template was updated
        template_path = mock_research_project_all_agents / agent_dir / subdir / "spec-kitty.implement.md"
        content = template_path.read_text()

        # Should have Research CSV Schemas section
        assert "Research CSV Schemas" in content
        assert "evidence-log.csv Schema" in content
        assert "source-register.csv Schema" in content

        # Should have schema table with columns
        assert "timestamp,source_type,citation,key_finding,confidence,notes" in content
        assert "source_id,citation,url,accessed_date,relevance,status" in content

        # Should have warning about validation
        assert "CRITICAL - DO NOT MODIFY HEADERS" in content
        assert "validated during review" in content.lower()

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
        (opencode / "spec-kitty.implement.md").write_text("## Sprint Planning Artifacts (Separate)\n")

        # Create claude directory (NOT configured)
        claude = tmp_path / ".claude" / "commands"
        claude.mkdir(parents=True)
        claude_template = claude / "spec-kitty.implement.md"
        claude_template.write_text("## Sprint Planning Artifacts (Separate)\n")
        original_claude_content = claude_template.read_text()

        (tmp_path / "kitty-specs").mkdir()

        # Run migration
        migration = UpdateResearchImplementTemplatesMigration()
        result = migration.apply(tmp_path, dry_run=False)

        assert result.success is True

        # opencode should be updated
        opencode_content = (opencode / "spec-kitty.implement.md").read_text()
        assert "Research CSV Schemas" in opencode_content

        # claude should NOT be updated (not configured)
        claude_content = claude_template.read_text()
        assert claude_content == original_claude_content
        assert "Research CSV Schemas" not in claude_content

    def test_update_skips_software_dev_templates(self, mock_software_dev_project):
        """Test migration skips software-dev templates."""
        migration = UpdateResearchImplementTemplatesMigration()
        result = migration.apply(mock_software_dev_project, dry_run=False)

        assert result.success is True

        # Software-dev templates should NOT have schema section
        claude_content = (mock_software_dev_project / ".claude" / "commands" / "spec-kitty.implement.md").read_text()
        opencode_content = (mock_software_dev_project / ".opencode" / "command" / "spec-kitty.implement.md").read_text()

        assert "Research CSV Schemas" not in claude_content
        assert "Research CSV Schemas" not in opencode_content
        assert "Implementation Workflow" in claude_content  # Still software-dev template

    def test_update_idempotent(self, mock_research_project_one_agent):
        """Test migration is idempotent (safe to run multiple times)."""
        migration = UpdateResearchImplementTemplatesMigration()

        # Run migration first time
        result1 = migration.apply(mock_research_project_one_agent, dry_run=False)
        assert result1.success is True

        # Read updated content
        opencode_template = mock_research_project_one_agent / ".opencode" / "command" / "spec-kitty.implement.md"
        content_after_first = opencode_template.read_text()

        # Run migration second time
        result2 = migration.apply(mock_research_project_one_agent, dry_run=False)
        assert result2.success is True

        # Content should be identical (no duplicate sections)
        content_after_second = opencode_template.read_text()
        assert content_after_first == content_after_second

        # Should only have one Research CSV Schemas section
        assert content_after_second.count("Research CSV Schemas") == 1

    def test_update_dry_run(self, mock_research_project_one_agent):
        """Test dry run does not modify files."""
        migration = UpdateResearchImplementTemplatesMigration()

        # Read original content
        opencode_template = mock_research_project_one_agent / ".opencode" / "command" / "spec-kitty.implement.md"
        original_content = opencode_template.read_text()

        # Run dry run
        result = migration.apply(mock_research_project_one_agent, dry_run=True)

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

        migration = UpdateResearchImplementTemplatesMigration()
        result = migration.apply(tmp_path, dry_run=False)

        assert result.success is True

        # Claude directory should NOT be created
        assert not (tmp_path / ".claude" / "commands").exists()

    def test_update_provides_example_commands(self, mock_research_project_one_agent):
        """Test migration adds example append commands for CSVs."""
        migration = UpdateResearchImplementTemplatesMigration()
        migration.apply(mock_research_project_one_agent, dry_run=False)

        opencode_template = mock_research_project_one_agent / ".opencode" / "command" / "spec-kitty.implement.md"
        content = opencode_template.read_text()

        # Should have append examples
        assert "To add evidence (append only" in content
        assert "echo" in content
        assert ">> kitty-specs/" in content

    def test_update_documents_enum_values(self, mock_research_project_one_agent):
        """Test migration documents valid enum values for fields."""
        migration = UpdateResearchImplementTemplatesMigration()
        migration.apply(mock_research_project_one_agent, dry_run=False)

        opencode_template = mock_research_project_one_agent / ".opencode" / "command" / "spec-kitty.implement.md"
        content = opencode_template.read_text()

        # Should document enum values (escaped pipes in markdown tables)
        assert "journal" in content
        assert "conference" in content
        assert "high" in content and "medium" in content and "low" in content
        assert "reviewed" in content and "pending" in content and "archived" in content


class TestTemplateContent:
    """Tests for template content quality."""

    def test_template_source_exists(self):
        """Test that research implement template source file exists."""
        repo_root = Path(__file__).resolve().parents[2]
        template_path = (
            repo_root / "src" / "specify_cli" / "missions" / "research" / "command-templates" / "implement.md"
        )
        assert template_path.exists()

        content = template_path.read_text()

        # Should have all required sections
        assert "Research CSV Schemas" in content
        assert "evidence-log.csv Schema" in content
        assert "source-register.csv Schema" in content
        assert "CRITICAL - DO NOT MODIFY HEADERS" in content

    def test_template_has_correct_schemas(self):
        """Test template documents correct canonical schemas."""
        repo_root = Path(__file__).resolve().parents[2]
        template_path = (
            repo_root / "src" / "specify_cli" / "missions" / "research" / "command-templates" / "implement.md"
        )
        content = template_path.read_text()

        # Evidence log schema
        assert "timestamp,source_type,citation,key_finding,confidence,notes" in content

        # Source register schema
        assert "source_id,citation,url,accessed_date,relevance,status" in content
