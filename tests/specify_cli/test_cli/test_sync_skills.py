"""Tests for skill root awareness in agent config sync (WP06, T032).

Validates:
- Missing skill roots are repaired when --create-missing is used.
- Shared root (.agents/skills/) is preserved when a configured agent needs it.
- Orphaned skill roots are removed when no configured agent requires them.
- Non-managed (user) content in skill roots is preserved (rmdir safety).
- Manifest is updated after sync changes.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.agent.config import app
from specify_cli.core.agent_config import save_agent_config, AgentConfig
from specify_cli.skills.manifest import (
    SkillsManifest,
    load_manifest,
    write_manifest,
)
from specify_cli.skills.verification import verify_installation

runner = CliRunner()


def _make_project(tmp_path: Path, agents: list[str]) -> Path:
    """Create a minimal spec-kitty project with given configured agents."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    config = AgentConfig(available=list(agents))
    save_agent_config(tmp_path, config)
    return tmp_path


def _make_manifest(
    tmp_path: Path,
    *,
    skills_mode: str = "auto",
    selected_agents: list[str] | None = None,
    installed_skill_roots: list[str] | None = None,
) -> SkillsManifest:
    """Create and persist a minimal skills manifest."""
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0",
        created_at="2026-03-20T16:00:00Z",
        updated_at="2026-03-20T16:00:00Z",
        skills_mode=skills_mode,
        selected_agents=selected_agents or [],
        installed_skill_roots=installed_skill_roots or [],
        managed_files=[],
    )
    write_manifest(tmp_path, manifest)
    return manifest


class TestSyncRepairsMissingSkillRoots:
    """T029: Repair missing skill roots for configured agents."""

    def test_sync_repairs_missing_native_skill_root(self, tmp_path: Path) -> None:
        """Missing .claude/skills/ is recreated with .gitkeep when --create-missing."""
        project = _make_project(tmp_path, ["claude"])
        _make_manifest(
            project,
            selected_agents=["claude"],
            installed_skill_roots=[".claude/skills/"],
        )
        # .claude/skills/ does NOT exist on filesystem
        (project / ".claude" / "commands").mkdir(parents=True, exist_ok=True)

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync", "--create-missing", "--keep-orphaned"])

        assert result.exit_code == 0
        assert "Recreated skill root .claude/skills/" in result.output
        skill_root = project / ".claude" / "skills"
        assert skill_root.exists()
        assert (skill_root / ".gitkeep").exists()

    def test_sync_repairs_missing_shared_skill_root(self, tmp_path: Path) -> None:
        """Missing .agents/skills/ is recreated for shared-root-capable agents."""
        project = _make_project(tmp_path, ["codex"])
        _make_manifest(
            project,
            selected_agents=["codex"],
            installed_skill_roots=[".agents/skills/"],
        )
        # .agents/skills/ does NOT exist on filesystem
        (project / ".codex" / "prompts").mkdir(parents=True, exist_ok=True)

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync", "--create-missing", "--keep-orphaned"])

        assert result.exit_code == 0
        assert "Recreated skill root .agents/skills/" in result.output
        assert (project / ".agents" / "skills").exists()
        assert (project / ".agents" / "skills" / ".gitkeep").exists()

    def test_sync_skips_repair_without_create_missing(self, tmp_path: Path) -> None:
        """Skill root repair requires --create-missing flag."""
        project = _make_project(tmp_path, ["claude"])
        _make_manifest(
            project,
            selected_agents=["claude"],
            installed_skill_roots=[".claude/skills/"],
        )
        (project / ".claude" / "commands").mkdir(parents=True, exist_ok=True)

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync", "--keep-orphaned"])

        assert result.exit_code == 0
        # Should NOT recreate skill root without --create-missing
        assert not (project / ".claude" / "skills").exists()


class TestSyncSharedRootProtection:
    """T030: Shared root protection during orphan removal."""

    def test_sync_preserves_shared_root_for_remaining_agent(
        self, tmp_path: Path
    ) -> None:
        """Shared .agents/skills/ kept when codex still needs it (copilot removed)."""
        # Config now has only codex (copilot was removed)
        project = _make_project(tmp_path, ["codex"])
        _make_manifest(
            project,
            selected_agents=["copilot", "codex"],
            installed_skill_roots=[".agents/skills/"],
        )
        # .agents/skills/ exists with .gitkeep
        agents_skills = project / ".agents" / "skills"
        agents_skills.mkdir(parents=True, exist_ok=True)
        (agents_skills / ".gitkeep").write_text("", encoding="utf-8")

        # codex directory exists
        (project / ".codex" / "prompts").mkdir(parents=True, exist_ok=True)

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0
        # .agents/skills/ must survive — codex is shared-root-capable
        assert agents_skills.exists()
        assert "Removed orphaned skill root .agents/skills/" not in result.output

    def test_sync_removes_orphaned_skill_root_when_no_agent_needs_it(
        self, tmp_path: Path
    ) -> None:
        """Shared root removed when no configured agent needs it (all wrapper-only)."""
        # Only q (wrapper-only) is configured — no skill roots needed
        project = _make_project(tmp_path, ["q"])
        _make_manifest(
            project,
            selected_agents=["codex", "q"],
            installed_skill_roots=[".agents/skills/"],
        )
        # .agents/skills/ exists with only .gitkeep (managed content)
        agents_skills = project / ".agents" / "skills"
        agents_skills.mkdir(parents=True, exist_ok=True)
        (agents_skills / ".gitkeep").write_text("", encoding="utf-8")

        # q directory exists
        (project / ".amazonq" / "prompts").mkdir(parents=True, exist_ok=True)

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0
        assert "Removed orphaned skill root .agents/skills/" in result.output
        # Directory should be gone (only had .gitkeep which was managed)
        assert not agents_skills.exists()

    def test_sync_preserves_user_content_in_skill_root(
        self, tmp_path: Path
    ) -> None:
        """rmdir() safety: directory with user files is NOT deleted."""
        project = _make_project(tmp_path, ["q"])
        _make_manifest(
            project,
            selected_agents=["codex", "q"],
            installed_skill_roots=[".agents/skills/"],
        )
        # .agents/skills/ has user-created files (not just .gitkeep)
        agents_skills = project / ".agents" / "skills"
        agents_skills.mkdir(parents=True, exist_ok=True)
        (agents_skills / ".gitkeep").write_text("", encoding="utf-8")
        (agents_skills / "my-custom-skill.md").write_text("user content")

        (project / ".amazonq" / "prompts").mkdir(parents=True, exist_ok=True)

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0
        assert "has non-managed content, keeping" in result.output
        # Directory should still exist — rmdir() fails on non-empty
        assert agents_skills.exists()
        # User file preserved
        assert (agents_skills / "my-custom-skill.md").exists()
        # .gitkeep was removed (managed content cleanup)
        assert not (agents_skills / ".gitkeep").exists()

    def test_sync_removes_orphaned_native_root_via_agent_cleanup(
        self, tmp_path: Path
    ) -> None:
        """Native root (.claude/skills/) removed as part of agent orphan cleanup.

        When claude is unconfigured, the orphaned agent directory removal
        (shutil.rmtree on .claude/) also removes .claude/skills/.  The manifest
        is then updated to prune the stale entry.
        """
        # Only codex configured — claude was removed
        project = _make_project(tmp_path, ["codex"])
        _make_manifest(
            project,
            selected_agents=["claude", "codex"],
            installed_skill_roots=[".agents/skills/", ".claude/skills/"],
        )
        # .agents/skills/ exists (still needed by codex)
        (project / ".agents" / "skills").mkdir(parents=True, exist_ok=True)
        (project / ".agents" / "skills" / ".gitkeep").write_text("", encoding="utf-8")
        # .claude/ exists as orphaned agent dir (includes skills/)
        (project / ".claude" / "commands").mkdir(parents=True, exist_ok=True)
        (project / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
        (project / ".claude" / "skills" / ".gitkeep").write_text("", encoding="utf-8")
        # codex directory
        (project / ".codex" / "prompts").mkdir(parents=True, exist_ok=True)

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0
        # .claude/ removed by agent orphan cleanup
        assert not (project / ".claude").exists()
        # .agents/skills/ kept — codex needs it
        assert (project / ".agents" / "skills").exists()
        # Manifest should no longer list .claude/skills/
        updated_manifest = load_manifest(project)
        assert updated_manifest is not None
        assert ".claude/skills/" not in updated_manifest.installed_skill_roots
        assert ".agents/skills/" in updated_manifest.installed_skill_roots


class TestSyncManifestUpdate:
    """T031: Manifest updated after sync changes."""

    def test_manifest_updated_after_repair(self, tmp_path: Path) -> None:
        """Manifest updated_at and installed_skill_roots updated after repair."""
        project = _make_project(tmp_path, ["claude"])
        _make_manifest(
            project,
            selected_agents=["claude"],
            installed_skill_roots=[],
        )
        # Directory missing — will be created
        (project / ".claude" / "commands").mkdir(parents=True, exist_ok=True)

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync", "--create-missing", "--keep-orphaned"])

        assert result.exit_code == 0

        updated_manifest = load_manifest(project)
        assert updated_manifest is not None
        assert ".claude/skills/" in updated_manifest.installed_skill_roots
        # updated_at should have changed from the initial value
        assert updated_manifest.updated_at != "2026-03-20T16:00:00Z"

    def test_manifest_updated_after_orphan_removal(self, tmp_path: Path) -> None:
        """Manifest installed_skill_roots pruned when orphan root removed."""
        project = _make_project(tmp_path, ["q"])
        _make_manifest(
            project,
            selected_agents=["codex", "q"],
            installed_skill_roots=[".agents/skills/"],
        )
        agents_skills = project / ".agents" / "skills"
        agents_skills.mkdir(parents=True, exist_ok=True)
        (agents_skills / ".gitkeep").write_text("", encoding="utf-8")
        (project / ".amazonq" / "prompts").mkdir(parents=True, exist_ok=True)

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0

        updated_manifest = load_manifest(project)
        assert updated_manifest is not None
        # The removed root should no longer appear
        assert ".agents/skills/" not in updated_manifest.installed_skill_roots

    def test_manifest_tracks_recreated_wrappers_for_wrapper_only_agent(
        self, tmp_path: Path
    ) -> None:
        """Recreated wrapper-only surfaces must be added back into the manifest."""
        project = _make_project(tmp_path, ["q"])
        _make_manifest(
            project,
            selected_agents=["q"],
            installed_skill_roots=[],
        )
        missions_dir = project / ".kittify" / "missions" / "software-dev" / "command-templates"
        missions_dir.mkdir(parents=True, exist_ok=True)
        (missions_dir / "specify.md").write_text("body", encoding="utf-8")

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync", "--create-missing", "--keep-orphaned"])

        assert result.exit_code == 0

        updated_manifest = load_manifest(project)
        assert updated_manifest is not None
        wrapper_paths = [
            mf.path for mf in updated_manifest.managed_files if mf.file_type == "wrapper"
        ]
        assert wrapper_paths == [".amazonq/prompts/spec-kitty.specify.md"]

        verification = verify_installation(project, ["q"], updated_manifest)
        assert verification.passed is True

    def test_no_manifest_skips_skill_sync(self, tmp_path: Path) -> None:
        """When no manifest exists, skill root sync is skipped entirely."""
        project = _make_project(tmp_path, ["claude"])
        # No manifest written — pre-Phase-0 project
        (project / ".claude" / "commands").mkdir(parents=True, exist_ok=True)

        with patch(
            "specify_cli.cli.commands.agent.config.find_repo_root",
            return_value=project,
        ):
            result = runner.invoke(app, ["sync", "--create-missing", "--keep-orphaned"])

        assert result.exit_code == 0
        assert "No skills manifest found" in result.output
        # No skill roots should have been created
        assert not (project / ".claude" / "skills").exists()
