"""Tests for migration 0.14.3: Add vision, next, and pipeline slash commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_14_3_add_vision_next_pipeline_commands import (
    AddVisionNextPipelineCommandsMigration,
    NEW_TEMPLATES,
    _find_central_template,
)


@pytest.fixture
def migration():
    return AddVisionNextPipelineCommandsMigration()


@pytest.fixture
def project_with_agents(tmp_path: Path):
    """Create a fake project with claude and opencode agent directories."""
    # No config.yaml -> legacy fallback to all agents, but we only create
    # directories for a subset to test that missing dirs are skipped.
    (tmp_path / ".claude" / "commands").mkdir(parents=True)
    (tmp_path / ".opencode" / "command").mkdir(parents=True)
    (tmp_path / ".gemini" / "commands").mkdir(parents=True)
    return tmp_path


class TestFindCentralTemplate:
    """Verify source templates are discoverable."""

    @pytest.mark.parametrize("name", NEW_TEMPLATES)
    def test_find_each_template(self, name: str):
        path = _find_central_template(name)
        assert path is not None, f"Could not find central template: {name}.md"
        assert path.exists()
        assert path.name == f"{name}.md"

    def test_nonexistent_template_returns_none(self):
        assert _find_central_template("nonexistent_template_xyz") is None


class TestDetect:
    """Verify detect() identifies projects needing the migration."""

    def test_detect_true_when_templates_missing(self, migration, project_with_agents):
        assert migration.detect(project_with_agents) is True

    def test_detect_false_when_templates_present(self, migration, project_with_agents):
        # Place all three templates in all agent dirs
        for name in NEW_TEMPLATES:
            (project_with_agents / ".claude" / "commands" / f"spec-kitty.{name}.md").write_text("x")
            (project_with_agents / ".opencode" / "command" / f"spec-kitty.{name}.md").write_text("x")
            (project_with_agents / ".gemini" / "commands" / f"spec-kitty.{name}.toml").write_text("x")

        assert migration.detect(project_with_agents) is False

    def test_detect_true_when_partial(self, migration, project_with_agents):
        # Only place one of three
        (project_with_agents / ".claude" / "commands" / "spec-kitty.next.md").write_text("x")
        assert migration.detect(project_with_agents) is True

    def test_detect_false_when_no_agent_dirs_exist(self, migration, tmp_path: Path):
        # Empty project, no agent dirs at all -> nothing to detect
        assert migration.detect(tmp_path) is False


class TestCanApply:
    """Verify can_apply() checks for source template availability."""

    def test_can_apply_succeeds(self, migration, project_with_agents):
        can, msg = migration.can_apply(project_with_agents)
        assert can is True
        assert msg == ""


class TestApply:
    """Verify apply() deploys templates correctly."""

    def test_apply_creates_templates_for_all_agents(self, migration, project_with_agents):
        result = migration.apply(project_with_agents)

        assert result.success is True
        assert len(result.errors) == 0
        assert len(result.changes_made) > 0

        # Claude uses .md extension
        for name in NEW_TEMPLATES:
            dest = project_with_agents / ".claude" / "commands" / f"spec-kitty.{name}.md"
            assert dest.exists(), f"Missing: {dest}"
            content = dest.read_text(encoding="utf-8")
            assert len(content) > 100, f"Template {name} seems too short"

        # OpenCode uses .md extension
        for name in NEW_TEMPLATES:
            dest = project_with_agents / ".opencode" / "command" / f"spec-kitty.{name}.md"
            assert dest.exists(), f"Missing: {dest}"

        # Gemini uses .toml extension
        for name in NEW_TEMPLATES:
            dest = project_with_agents / ".gemini" / "commands" / f"spec-kitty.{name}.toml"
            assert dest.exists(), f"Missing: {dest}"
            content = dest.read_text(encoding="utf-8")
            assert "description" in content, "TOML template should have description field"

    def test_apply_skips_nonexistent_agent_dirs(self, migration, tmp_path: Path):
        # No agent dirs exist at all
        result = migration.apply(tmp_path)
        assert result.success is True
        # No changes since no agent dirs exist
        assert all("No agents" in c or "skip" in c.lower() for c in result.changes_made) or len(result.changes_made) == 0

    def test_apply_dry_run(self, migration, project_with_agents):
        result = migration.apply(project_with_agents, dry_run=True)

        assert result.success is True
        assert all("Would create" in c for c in result.changes_made)

        # Nothing actually created
        for name in NEW_TEMPLATES:
            assert not (project_with_agents / ".claude" / "commands" / f"spec-kitty.{name}.md").exists()

    def test_apply_is_idempotent(self, migration, project_with_agents):
        result1 = migration.apply(project_with_agents)
        assert result1.success is True

        result2 = migration.apply(project_with_agents)
        assert result2.success is True

        # Same files, overwritten but still valid
        for name in NEW_TEMPLATES:
            dest = project_with_agents / ".claude" / "commands" / f"spec-kitty.{name}.md"
            assert dest.exists()

    def test_detect_false_after_apply(self, migration, project_with_agents):
        """After applying, detect should return False."""
        assert migration.detect(project_with_agents) is True
        migration.apply(project_with_agents)
        assert migration.detect(project_with_agents) is False

    def test_rendered_content_has_no_double_prefix(self, migration, project_with_agents):
        """Ensure templates don't end up as spec-kitty.spec-kitty.*.md."""
        migration.apply(project_with_agents)

        claude_dir = project_with_agents / ".claude" / "commands"
        double_prefix = list(claude_dir.glob("spec-kitty.spec-kitty.*"))
        assert double_prefix == [], f"Double-prefixed files found: {double_prefix}"
