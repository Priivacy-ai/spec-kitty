"""Tests for the 2.1.0 agent surface manifest migration.

Validates that the migration correctly:
- Detects projects missing a skills manifest
- Creates manifest and skill roots on apply
- Respects config-aware agent processing
- Is idempotent (run twice, same result)
- Tracks existing wrapper files in the manifest
- Respects dry_run parameter
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.agent_config import AgentConfig, save_agent_config
from specify_cli.skills.manifest import load_manifest
from specify_cli.upgrade.migrations.m_2_1_0_agent_surface_manifest import (
    AgentSurfaceManifestMigration,
)


@pytest.fixture
def migration():
    """Return an instance of the migration under test."""
    return AgentSurfaceManifestMigration()


def _setup_config(tmp_path: Path, agents: list[str]) -> None:
    """Helper: create .kittify/config.yaml with the given agents."""
    config = AgentConfig(available=agents)
    save_agent_config(tmp_path, config)


# ---------------------------------------------------------------------------
# detect() tests
# ---------------------------------------------------------------------------


class TestDetect:
    """Tests for detect() — determines if migration should run."""

    def test_detect_no_manifest(self, tmp_path: Path, migration):
        """Project with config.yaml but no manifest => True."""
        _setup_config(tmp_path, ["claude"])
        assert migration.detect(tmp_path) is True

    def test_detect_with_manifest(self, tmp_path: Path, migration):
        """Project with config.yaml AND manifest => False."""
        _setup_config(tmp_path, ["claude"])
        manifest_dir = tmp_path / ".kittify" / "agent-surfaces"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "skills-manifest.yaml").write_text(
            "spec_kitty_version: '2.1.0'\n"
        )
        assert migration.detect(tmp_path) is False

    def test_detect_no_config(self, tmp_path: Path, migration):
        """Project without config.yaml => False (not a spec-kitty project)."""
        assert migration.detect(tmp_path) is False

    def test_detect_empty_kittify(self, tmp_path: Path, migration):
        """Project with .kittify/ but no config.yaml => False."""
        (tmp_path / ".kittify").mkdir()
        assert migration.detect(tmp_path) is False


# ---------------------------------------------------------------------------
# can_apply() tests
# ---------------------------------------------------------------------------


class TestCanApply:
    """Tests for can_apply() — always safe."""

    def test_can_apply_always_true(self, tmp_path: Path, migration):
        """can_apply() always returns (True, '')."""
        can, reason = migration.can_apply(tmp_path)
        assert can is True
        assert reason == ""


# ---------------------------------------------------------------------------
# apply() tests
# ---------------------------------------------------------------------------


class TestApply:
    """Tests for apply() — creates manifest and skill roots."""

    def test_apply_creates_manifest_and_roots(self, tmp_path: Path, migration):
        """apply() creates manifest file and skill root directories."""
        _setup_config(tmp_path, ["claude", "codex"])

        # Create wrapper dirs with existing wrappers
        claude_cmds = tmp_path / ".claude" / "commands"
        claude_cmds.mkdir(parents=True)
        (claude_cmds / "spec-kitty.specify.md").write_text("test content")

        codex_prompts = tmp_path / ".codex" / "prompts"
        codex_prompts.mkdir(parents=True)
        (codex_prompts / "spec-kitty.specify.md").write_text("test content")

        result = migration.apply(tmp_path)
        assert result.success is True

        # Verify manifest exists
        manifest_path = (
            tmp_path / ".kittify" / "agent-surfaces" / "skills-manifest.yaml"
        )
        assert manifest_path.exists()

        # Verify skill roots created:
        # claude is NATIVE_ROOT_REQUIRED => .claude/skills/
        # codex is SHARED_ROOT_CAPABLE => .agents/skills/
        assert (tmp_path / ".claude" / "skills" / ".gitkeep").exists()
        assert (tmp_path / ".agents" / "skills" / ".gitkeep").exists()

        # Verify existing wrappers were NOT modified
        assert (claude_cmds / "spec-kitty.specify.md").read_text() == "test content"
        assert (codex_prompts / "spec-kitty.specify.md").read_text() == "test content"

    def test_apply_existing_wrappers_tracked(self, tmp_path: Path, migration):
        """apply() tracks existing wrapper files in the manifest."""
        _setup_config(tmp_path, ["claude"])

        claude_cmds = tmp_path / ".claude" / "commands"
        claude_cmds.mkdir(parents=True)
        (claude_cmds / "spec-kitty.specify.md").write_text("specify content")
        (claude_cmds / "spec-kitty.implement.md").write_text("implement content")
        # Non-spec-kitty file should NOT be tracked
        (claude_cmds / "custom-command.md").write_text("custom")

        result = migration.apply(tmp_path)
        assert result.success is True

        manifest = load_manifest(tmp_path)
        assert manifest is not None

        wrapper_paths = [
            mf.path for mf in manifest.managed_files if mf.file_type == "wrapper"
        ]
        assert ".claude/commands/spec-kitty.implement.md" in wrapper_paths
        assert ".claude/commands/spec-kitty.specify.md" in wrapper_paths
        # custom-command.md should NOT be tracked
        assert ".claude/commands/custom-command.md" not in wrapper_paths

    def test_apply_config_aware_only_configured_agents(
        self, tmp_path: Path, migration
    ):
        """apply() only processes configured agents."""
        _setup_config(tmp_path, ["opencode"])

        result = migration.apply(tmp_path)
        assert result.success is True

        # opencode is SHARED_ROOT_CAPABLE => .agents/skills/
        assert (tmp_path / ".agents" / "skills" / ".gitkeep").exists()

        # claude is NOT configured => .claude/skills/ should NOT exist
        assert not (tmp_path / ".claude" / "skills").exists()

    def test_apply_idempotent(self, tmp_path: Path, migration):
        """Running apply() twice produces the same result."""
        _setup_config(tmp_path, ["claude"])

        claude_cmds = tmp_path / ".claude" / "commands"
        claude_cmds.mkdir(parents=True)
        (claude_cmds / "spec-kitty.specify.md").write_text("test")

        # First apply
        result1 = migration.apply(tmp_path)
        assert result1.success is True

        # Read manifest after first apply
        manifest1 = load_manifest(tmp_path)
        assert manifest1 is not None
        files1 = len(manifest1.managed_files)
        roots1 = manifest1.installed_skill_roots

        # Second apply (detect would return False, but apply still succeeds)
        result2 = migration.apply(tmp_path)
        assert result2.success is True

        # Read manifest after second apply
        manifest2 = load_manifest(tmp_path)
        assert manifest2 is not None

        # Same number of managed files and same roots
        assert len(manifest2.managed_files) == files1
        assert manifest2.installed_skill_roots == roots1

    def test_apply_dry_run_no_changes(self, tmp_path: Path, migration):
        """apply() with dry_run=True does not create files."""
        _setup_config(tmp_path, ["claude"])

        result = migration.apply(tmp_path, dry_run=True)
        assert result.success is True

        # No manifest should be created
        assert not (
            tmp_path / ".kittify" / "agent-surfaces" / "skills-manifest.yaml"
        ).exists()

        # No skill roots should be created
        assert not (tmp_path / ".claude" / "skills").exists()

    def test_apply_no_agents_configured(self, tmp_path: Path, migration):
        """apply() with empty agent list skips gracefully."""
        (tmp_path / ".kittify").mkdir(parents=True)
        # Write config with empty agents list
        config_file = tmp_path / ".kittify" / "config.yaml"
        config_file.write_text("agents:\n  available: []\n")

        result = migration.apply(tmp_path)
        assert result.success is True
        assert any("No agents configured" in c for c in result.changes_made)

    def test_apply_manifest_content_correct(self, tmp_path: Path, migration):
        """Verify manifest content has correct structure and values."""
        _setup_config(tmp_path, ["claude", "opencode"])

        claude_cmds = tmp_path / ".claude" / "commands"
        claude_cmds.mkdir(parents=True)
        (claude_cmds / "spec-kitty.plan.md").write_text("plan content")

        result = migration.apply(tmp_path)
        assert result.success is True

        manifest = load_manifest(tmp_path)
        assert manifest is not None
        assert manifest.spec_kitty_version == "2.1.0"
        assert manifest.skills_mode == "auto"
        assert "claude" in manifest.selected_agents
        assert "opencode" in manifest.selected_agents

        # claude => .claude/skills/
        # opencode => .agents/skills/ (shared root)
        assert ".claude/skills/" in manifest.installed_skill_roots
        assert ".agents/skills/" in manifest.installed_skill_roots

        # Verify file types
        for mf in manifest.managed_files:
            assert mf.file_type in ("wrapper", "skill_root_marker")
            assert mf.sha256  # non-empty hash

    def test_apply_wrapper_only_agent(self, tmp_path: Path, migration):
        """Wrapper-only agents (like q/Amazon Q) get no skill roots."""
        _setup_config(tmp_path, ["q"])

        q_prompts = tmp_path / ".amazonq" / "prompts"
        q_prompts.mkdir(parents=True)
        (q_prompts / "spec-kitty.specify.md").write_text("amazon q wrapper")

        result = migration.apply(tmp_path)
        assert result.success is True

        manifest = load_manifest(tmp_path)
        assert manifest is not None

        # q is WRAPPER_ONLY => no skill roots
        assert manifest.installed_skill_roots == []

        # But wrapper should be tracked
        wrapper_paths = [
            mf.path for mf in manifest.managed_files if mf.file_type == "wrapper"
        ]
        assert ".amazonq/prompts/spec-kitty.specify.md" in wrapper_paths


# ---------------------------------------------------------------------------
# Integration: detect + apply workflow
# ---------------------------------------------------------------------------


class TestIntegration:
    """End-to-end tests for detect -> apply workflow."""

    def test_full_workflow(self, tmp_path: Path, migration):
        """detect=True -> apply -> detect=False."""
        _setup_config(tmp_path, ["claude"])

        # Initially needs migration
        assert migration.detect(tmp_path) is True

        # Apply migration
        result = migration.apply(tmp_path)
        assert result.success is True

        # Now detect should return False
        assert migration.detect(tmp_path) is False

    def test_migration_metadata(self, migration):
        """Verify migration class attributes are set correctly."""
        assert migration.migration_id == "2_1_0_agent_surface_manifest"
        assert migration.target_version == "2.1.0"
        assert migration.description != ""
        assert migration.min_version is None
