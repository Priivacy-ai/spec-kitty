"""Tests for the 2.0.11 install-skills migration."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_2_0_11_install_skills import (
    InstallSkillsMigration,
)

pytestmark = pytest.mark.fast


def _setup_project(tmp_path: Path, agents: list[str] | None = None) -> Path:
    """Create a minimal initialized project with .kittify/ and config."""
    project = tmp_path / "project"
    project.mkdir()
    kittify = project / ".kittify"
    kittify.mkdir()

    if agents is not None:
        config_content = "agents:\n  available:\n"
        for a in agents:
            config_content += f"    - {a}\n"
        (kittify / "config.yaml").write_text(config_content)

    return project


def _setup_skills(tmp_path: Path) -> Path:
    """Create test skill fixtures. Returns the skills root directory."""
    skills_root = tmp_path / "doctrine_skills"
    skill_dir = skills_root / "spec-kitty-test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: spec-kitty-test-skill\ndescription: test\n---\n# Test\n"
    )
    ref_dir = skill_dir / "references"
    ref_dir.mkdir()
    (ref_dir / "guide.md").write_text("# Guide\nTest reference.\n")
    return skills_root


class TestDetect:
    def test_true_when_no_manifest(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        migration = InstallSkillsMigration()
        assert migration.detect(project) is True

    def test_false_when_manifest_exists(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        manifest = project / ".kittify" / "skills-manifest.json"
        manifest.write_text('{"version": 1, "entries": []}')
        migration = InstallSkillsMigration()
        assert migration.detect(project) is False


class TestCanApply:
    def test_false_when_no_kittify(self, tmp_path: Path) -> None:
        project = tmp_path / "empty"
        project.mkdir()
        migration = InstallSkillsMigration()
        can, reason = migration.can_apply(project)
        assert can is False
        assert ".kittify/" in reason


class TestApply:
    def test_installs_for_native_agent(self, tmp_path: Path) -> None:
        """Skills are installed to native root for claude agent."""
        project = _setup_project(tmp_path, agents=["claude"])
        skills_root = _setup_skills(tmp_path)

        # Directly call the installer instead of going through full apply
        # which has complex import chains. This tests the same behavior.
        from specify_cli.skills.installer import install_skills_for_agent
        from specify_cli.skills.manifest import ManagedSkillManifest, save_manifest
        from specify_cli.skills.registry import SkillRegistry

        registry = SkillRegistry(skills_root)
        skills = registry.discover_skills()
        assert len(skills) == 1

        manifest = ManagedSkillManifest()
        entries = install_skills_for_agent(project, "claude", skills)
        for entry in entries:
            manifest.add_entry(entry)
        save_manifest(manifest, project)

        # Skill should be in native root
        skill_file = project / ".claude" / "skills" / "spec-kitty-test-skill" / "SKILL.md"
        assert skill_file.is_file()
        ref_file = project / ".claude" / "skills" / "spec-kitty-test-skill" / "references" / "guide.md"
        assert ref_file.is_file()

        # Manifest should exist
        manifest_file = project / ".kittify" / "skills-manifest.json"
        assert manifest_file.is_file()

        # detect() should now return False
        migration = InstallSkillsMigration()
        assert migration.detect(project) is False

    def test_installs_for_shared_root_agent(self, tmp_path: Path) -> None:
        """Skills are installed to .agents/skills/ for shared-root agents."""
        project = _setup_project(tmp_path, agents=["codex"])
        skills_root = _setup_skills(tmp_path)

        from specify_cli.skills.installer import install_skills_for_agent
        from specify_cli.skills.manifest import ManagedSkillManifest, save_manifest
        from specify_cli.skills.registry import SkillRegistry

        registry = SkillRegistry(skills_root)
        skills = registry.discover_skills()

        manifest = ManagedSkillManifest()
        entries = install_skills_for_agent(project, "codex", skills)
        for entry in entries:
            manifest.add_entry(entry)
        save_manifest(manifest, project)

        # Skill in shared root
        assert (project / ".agents" / "skills" / "spec-kitty-test-skill" / "SKILL.md").is_file()

    def test_skips_wrapper_only_agent(self, tmp_path: Path) -> None:
        """Wrapper-only agents (q) get no skill files."""
        project = _setup_project(tmp_path, agents=["q"])
        skills_root = _setup_skills(tmp_path)

        from specify_cli.skills.installer import install_skills_for_agent
        from specify_cli.skills.registry import SkillRegistry

        registry = SkillRegistry(skills_root)
        skills = registry.discover_skills()

        entries = install_skills_for_agent(project, "q", skills)
        assert len(entries) == 0
        assert not (project / ".amazonq" / "skills").exists()

    def test_dry_run_no_files_created(self, tmp_path: Path) -> None:
        """Dry run reports what would happen without creating files."""
        project = _setup_project(tmp_path, agents=["claude"])

        migration = InstallSkillsMigration()
        # dry_run with no discoverable skills just returns cleanly
        result = migration.apply(project, dry_run=True)
        assert result.success is True
        # No manifest created
        assert not (project / ".kittify" / "skills-manifest.json").exists()

    def test_mixed_agents_with_verify(self, tmp_path: Path) -> None:
        """Full cycle: install for mixed agents, then verify passes."""
        project = _setup_project(tmp_path, agents=["claude", "codex", "q"])
        skills_root = _setup_skills(tmp_path)

        from specify_cli.skills.installer import install_all_skills
        from specify_cli.skills.manifest import save_manifest
        from specify_cli.skills.registry import SkillRegistry
        from specify_cli.skills.verifier import verify_installed_skills

        registry = SkillRegistry(skills_root)
        manifest = install_all_skills(project, ["claude", "codex", "q"], registry)
        save_manifest(manifest, project)

        # Verify passes
        result = verify_installed_skills(project)
        assert result.ok is True

        # Claude has native root
        assert (project / ".claude" / "skills" / "spec-kitty-test-skill" / "SKILL.md").is_file()
        # Codex has shared root
        assert (project / ".agents" / "skills" / "spec-kitty-test-skill" / "SKILL.md").is_file()
        # q has nothing
        assert not (project / ".amazonq" / "skills").exists()

        # Manifest tracks claude and codex, not q
        claude_entries = [e for e in manifest.entries if e.agent_key == "claude"]
        codex_entries = [e for e in manifest.entries if e.agent_key == "codex"]
        q_entries = [e for e in manifest.entries if e.agent_key == "q"]
        assert len(claude_entries) >= 1
        assert len(codex_entries) >= 1
        assert len(q_entries) == 0
