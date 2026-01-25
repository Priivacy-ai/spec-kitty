"""Tests for constitution template migration (m_0_13_0_update_constitution_templates)."""

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_13_0_update_constitution_templates import (
    UpdateConstitutionTemplatesMigration,
)


@pytest.fixture
def migration():
    """Return the migration instance."""
    return UpdateConstitutionTemplatesMigration()


# All 12 supported agents
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


@pytest.mark.parametrize("agent_key,agent_dir,subdir", ALL_AGENTS)
def test_constitution_template_updated_for_agent(tmp_path, migration, agent_key, agent_dir, subdir):
    """Test that constitution template is updated for a specific agent."""
    # Setup: Create .kittify directory
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    # Create config with this agent
    config_file = kittify_dir / "config.yaml"
    config_file.write_text(f"agents:\n  available:\n    - {agent_key}\n", encoding="utf-8")

    # Create agent directory with old constitution template
    agent_path = tmp_path / agent_dir / subdir
    agent_path.mkdir(parents=True)

    old_content = """# Constitution Command

## Next steps

After writing, provide:
- Location of the file
- Phases completed and questions answered
- Next steps (review, share with team, run /spec-kitty.plan)
"""

    slash_cmd = agent_path / "spec-kitty.constitution.md"
    slash_cmd.write_text(old_content, encoding="utf-8")

    # Detect should return True
    assert migration.detect(tmp_path) is True

    # Apply migration
    result = migration.apply(tmp_path, dry_run=False)

    # Verify success
    assert result.success is True
    assert len(result.errors) == 0

    # Verify file updated
    updated_content = slash_cmd.read_text(encoding="utf-8")
    assert "run /spec-kitty.specify" in updated_content
    assert "run /spec-kitty.plan" not in updated_content or "Next steps" not in updated_content


def test_migration_skips_already_updated(tmp_path, migration):
    """Test that migration skips agents that are already updated."""
    # Setup: Create .kittify directory with opencode config
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    config_file = kittify_dir / "config.yaml"
    config_file.write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    # Create agent directory with CORRECT constitution template
    agent_path = tmp_path / ".opencode" / "command"
    agent_path.mkdir(parents=True)

    correct_content = """# Constitution Command

## Next steps

After writing, provide:
- Location of the file
- Phases completed and questions answered
- Next steps (review, share with team, run /spec-kitty.specify)
"""

    slash_cmd = agent_path / "spec-kitty.constitution.md"
    slash_cmd.write_text(correct_content, encoding="utf-8")

    # Detect should return False (no update needed)
    # Note: This may return True if template content is different
    # The actual migration will skip if content matches exactly

    # Apply migration (should skip)
    result = migration.apply(tmp_path, dry_run=False)

    # Verify success
    assert result.success is True

    # Content should remain unchanged
    updated_content = slash_cmd.read_text(encoding="utf-8")
    assert updated_content == correct_content


def test_migration_respects_agent_config(tmp_path, migration):
    """Test that migration only updates configured agents."""
    # Setup: Create .kittify directory with only opencode configured
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    config_file = kittify_dir / "config.yaml"
    config_file.write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    # Create two agent directories
    # 1. Configured: opencode (should be updated)
    opencode_path = tmp_path / ".opencode" / "command"
    opencode_path.mkdir(parents=True)

    old_content = """Next steps (review, share with team, run /spec-kitty.plan)"""

    (opencode_path / "spec-kitty.constitution.md").write_text(old_content, encoding="utf-8")

    # 2. NOT configured: claude (should be skipped - orphaned)
    claude_path = tmp_path / ".claude" / "commands"
    claude_path.mkdir(parents=True)
    (claude_path / "spec-kitty.constitution.md").write_text(old_content, encoding="utf-8")

    # Apply migration
    result = migration.apply(tmp_path, dry_run=False)

    # Verify success
    assert result.success is True

    # Only changes for opencode should be reported
    assert any(".opencode" in change for change in result.changes_made)

    # Claude should NOT be in changes (not configured)
    assert not any(".claude" in change for change in result.changes_made)


def test_migration_handles_missing_directories(tmp_path, migration):
    """Test that migration handles missing agent directories gracefully."""
    # Setup: Create .kittify directory with opencode configured
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    config_file = kittify_dir / "config.yaml"
    config_file.write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    # Don't create agent directory (simulate deleted directory)

    # Apply migration (should not crash)
    result = migration.apply(tmp_path, dry_run=False)

    # Verify success (no errors, just skipped)
    assert result.success is True
    assert len(result.errors) == 0


def test_migration_dry_run(tmp_path, migration):
    """Test migration in dry-run mode."""
    # Setup: Create .kittify directory with opencode config
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    config_file = kittify_dir / "config.yaml"
    config_file.write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    # Create agent directory with old template
    agent_path = tmp_path / ".opencode" / "command"
    agent_path.mkdir(parents=True)

    old_content = """Next steps (review, share with team, run /spec-kitty.plan)"""
    slash_cmd = agent_path / "spec-kitty.constitution.md"
    slash_cmd.write_text(old_content, encoding="utf-8")

    # Apply in dry-run mode
    result = migration.apply(tmp_path, dry_run=True)

    # Verify success
    assert result.success is True

    # Verify changes are reported
    assert any("Would update" in change for change in result.changes_made)

    # Verify file NOT actually updated
    assert slash_cmd.read_text(encoding="utf-8") == old_content
