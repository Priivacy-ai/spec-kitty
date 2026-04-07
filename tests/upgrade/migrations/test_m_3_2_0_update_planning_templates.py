"""Unit tests for m_3_2_0_update_planning_templates migration.

Covers:
- T025: detect() returns True for stale files, False for fresh files, False for absent dirs
- T026: apply() overwrites stale files with new content, is idempotent on fresh files,
        respects agent config (unconfigured agent NOT processed)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STALE_CONTENT = "# spec-kitty.tasks-outline\nCreate `tasks.md`\n"
_FRESH_CONTENT = "# spec-kitty.tasks-outline\nCreate `wps.yaml`\n"
_NEW_RENDERED = "# New wps.yaml instructions\nCreate `wps.yaml`\n"


def _setup_project(tmp_path: Path, agents: list[str] | None = None) -> Path:
    """Create a minimal project with .kittify/config.yaml."""
    project = tmp_path / "project"
    project.mkdir()
    kittify = project / ".kittify"
    kittify.mkdir()

    selected = agents if agents is not None else ["claude"]
    config_lines = "agents:\n  available:\n"
    for agent in selected:
        config_lines += f"  - {agent}\n"
    (kittify / "config.yaml").write_text(config_lines, encoding="utf-8")

    return project


def _create_agent_file(project: Path, agent_dir: str, subdir: str, filename: str, content: str) -> Path:
    """Write a single agent command file, creating directories as needed."""
    d = project / agent_dir / subdir
    d.mkdir(parents=True, exist_ok=True)
    f = d / filename
    f.write_text(content, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# T025: Tests for detect()
# ---------------------------------------------------------------------------


class TestDetect:
    def test_detect_stale_tasks_outline(self, tmp_path: Path) -> None:
        """Returns True when stale marker is present in tasks-outline file."""
        project = _setup_project(tmp_path, agents=["claude"])
        _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-outline.md",
            _STALE_CONTENT,
        )

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        assert migration.detect(project) is True

    def test_detect_stale_tasks_packages(self, tmp_path: Path) -> None:
        """Returns True when stale marker is present in tasks-packages file."""
        project = _setup_project(tmp_path, agents=["claude"])
        # tasks-outline is fresh, but tasks-packages is stale
        _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-outline.md",
            _FRESH_CONTENT,
        )
        _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-packages.md",
            _STALE_CONTENT,
        )

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        assert migration.detect(project) is True

    def test_detect_fresh_tasks_outline(self, tmp_path: Path) -> None:
        """Returns False when wps.yaml instructions present (no stale marker)."""
        project = _setup_project(tmp_path, agents=["claude"])
        _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-outline.md",
            _FRESH_CONTENT,
        )

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        assert migration.detect(project) is False

    def test_detect_absent_agent_dir(self, tmp_path: Path) -> None:
        """Returns False when no agent directories exist."""
        project = _setup_project(tmp_path, agents=["claude"])
        # No agent directories created at all

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        assert migration.detect(project) is False

    def test_detect_skips_unconfigured_agents(self, tmp_path: Path) -> None:
        """detect() does not scan agent dirs that are not in config.yaml."""
        # Only opencode configured; claude is NOT configured
        project = _setup_project(tmp_path, agents=["opencode"])

        # Create stale file in claude (not configured)
        _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-outline.md",
            _STALE_CONTENT,
        )

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        # claude is not in config, so the stale file is invisible to detect()
        assert migration.detect(project) is False

    def test_detect_skips_unreadable_files(self, tmp_path: Path) -> None:
        """detect() returns False when file exists but cannot be read (OSError)."""
        project = _setup_project(tmp_path, agents=["claude"])
        stale = _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-outline.md",
            _STALE_CONTENT,
        )

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            assert migration.detect(project) is False


# ---------------------------------------------------------------------------
# T026: Tests for apply()
# ---------------------------------------------------------------------------


class TestApply:
    def _patch_helpers(self, rendered_content: str = _NEW_RENDERED):
        """Return context-manager patches for _get_runtime_command_templates_dir and _render_full_prompt."""
        mock_tmpl_dir = MagicMock(spec=Path)
        mock_tmpl_dir.is_dir.return_value = True

        # Make templates_dir / "tasks-outline.md" etc. behave as real files
        mock_template_file = MagicMock(spec=Path)
        mock_template_file.is_file.return_value = True
        mock_tmpl_dir.__truediv__ = lambda self, name: mock_template_file

        patch_dir = patch(
            "specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates._get_runtime_command_templates_dir",
            return_value=mock_tmpl_dir,
        )
        patch_render = patch(
            "specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates._render_full_prompt",
            return_value=rendered_content,
        )
        return patch_dir, patch_render

    def test_apply_overwrites_stale_file(self, tmp_path: Path) -> None:
        """apply() replaces stale tasks-outline with new template content."""
        project = _setup_project(tmp_path, agents=["claude"])
        stale = _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-outline.md",
            _STALE_CONTENT,
        )

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        patch_dir, patch_render = self._patch_helpers(_NEW_RENDERED)
        with patch_dir, patch_render:
            result = migration.apply(project)

        assert result.success is True
        assert stale.read_text(encoding="utf-8") == _NEW_RENDERED
        assert len(result.changes_made) >= 1
        assert any("Updated" in c for c in result.changes_made)

    def test_apply_is_idempotent_on_fresh_file(self, tmp_path: Path) -> None:
        """apply() on a fresh file (no stale marker) makes no changes."""
        project = _setup_project(tmp_path, agents=["claude"])
        fresh = _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-outline.md",
            _FRESH_CONTENT,
        )

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        patch_dir, patch_render = self._patch_helpers()
        with patch_dir, patch_render:
            result = migration.apply(project)

        assert result.success is True
        assert len(result.changes_made) == 0
        # File content unchanged
        assert fresh.read_text(encoding="utf-8") == _FRESH_CONTENT

    def test_apply_respects_agent_config(self, tmp_path: Path) -> None:
        """apply() only processes configured agents; ignores unconfigured agents."""
        # Only opencode configured; claude NOT configured
        project = _setup_project(tmp_path, agents=["opencode"])

        # Create stale file in claude (not configured)
        stale_claude = _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-outline.md",
            _STALE_CONTENT,
        )
        original_content = stale_claude.read_text(encoding="utf-8")

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        # detect() should not see the claude file as stale (not configured)
        assert migration.detect(project) is False

        patch_dir, patch_render = self._patch_helpers()
        with patch_dir, patch_render:
            result = migration.apply(project)

        assert result.success is True
        # claude file must not have been modified
        assert stale_claude.read_text(encoding="utf-8") == original_content

    def test_apply_dry_run_reports_without_modifying(self, tmp_path: Path) -> None:
        """apply(dry_run=True) reports planned changes but does not write files."""
        project = _setup_project(tmp_path, agents=["claude"])
        stale = _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-outline.md",
            _STALE_CONTENT,
        )
        original = stale.read_text(encoding="utf-8")

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        patch_dir, patch_render = self._patch_helpers()
        with patch_dir, patch_render:
            result = migration.apply(project, dry_run=True)

        assert result.success is True
        assert any("Would update" in c for c in result.changes_made)
        # File not modified
        assert stale.read_text(encoding="utf-8") == original

    def test_apply_returns_error_when_no_templates_dir(self, tmp_path: Path) -> None:
        """apply() returns success=False when runtime templates are unavailable."""
        project = _setup_project(tmp_path, agents=["claude"])
        _create_agent_file(
            project,
            ".claude",
            "commands",
            "spec-kitty.tasks-outline.md",
            _STALE_CONTENT,
        )

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        with patch(
            "specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates._get_runtime_command_templates_dir",
            return_value=None,
        ):
            result = migration.apply(project)

        assert result.success is False
        assert len(result.errors) > 0

    def test_apply_skips_nonexistent_agent_dirs(self, tmp_path: Path) -> None:
        """apply() does not create agent directories that do not exist."""
        project = _setup_project(tmp_path, agents=["claude", "codex"])
        # No agent directories created

        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        migration = UpdatePlanningTemplatesMigration()
        patch_dir, patch_render = self._patch_helpers()
        with patch_dir, patch_render:
            result = migration.apply(project)

        assert result.success is True
        assert len(result.changes_made) == 0
        # Directories must not have been created
        assert not (project / ".claude" / "commands").exists()
        assert not (project / ".codex" / "prompts").exists()


# ---------------------------------------------------------------------------
# Tests: registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_migration_is_registered(self) -> None:
        """UpdatePlanningTemplatesMigration is discoverable via MigrationRegistry."""
        from specify_cli.upgrade.registry import MigrationRegistry

        import specify_cli.upgrade.migrations  # noqa: F401

        all_ids = list(MigrationRegistry._migrations.keys())
        assert "3.2.0_update_planning_templates" in all_ids

    def test_migration_has_correct_target_version(self) -> None:
        """target_version is '3.2.0'."""
        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        assert UpdatePlanningTemplatesMigration.target_version == "3.2.0"

    def test_migration_has_description(self) -> None:
        """description is a non-empty string."""
        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        assert UpdatePlanningTemplatesMigration.description != ""

    def test_migration_id_is_correct(self) -> None:
        """migration_id matches expected value."""
        from specify_cli.upgrade.migrations.m_3_2_0_update_planning_templates import (
            UpdatePlanningTemplatesMigration,
        )

        assert UpdatePlanningTemplatesMigration.migration_id == "3.2.0_update_planning_templates"
