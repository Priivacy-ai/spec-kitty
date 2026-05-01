"""Tests for the skill installer."""

from __future__ import annotations

from pathlib import Path


from specify_cli.core.config import (
    SKILL_CLASS_NATIVE,
    SKILL_CLASS_SHARED,
)
from specify_cli.skills.installer import install_all_skills, install_skills_for_agent
from specify_cli.skills.manifest import compute_content_hash
from specify_cli.skills.registry import CanonicalSkill, SkillRegistry


def _make_skill(
    root: Path,
    name: str,
    *,
    references: list[str] | None = None,
    scripts: list[str] | None = None,
    assets: list[str] | None = None,
) -> CanonicalSkill:
    """Create a minimal canonical skill on disk and return the dataclass."""
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"---\nname: {name}\n---\n# {name}\nPlaceholder.\n")

    ref_paths: list[Path] = []
    script_paths: list[Path] = []
    asset_paths: list[Path] = []

    for sub, files, out in [
        ("references", references or [], ref_paths),
        ("scripts", scripts or [], script_paths),
        ("assets", assets or [], asset_paths),
    ]:
        if files:
            sub_dir = skill_dir / sub
            sub_dir.mkdir(exist_ok=True)
            for fname in files:
                p = sub_dir / fname
                p.write_text(f"# {fname}\n")
                out.append(p)

    return CanonicalSkill(
        name=name,
        skill_dir=skill_dir,
        skill_md=skill_md,
        references=ref_paths,
        scripts=script_paths,
        assets=asset_paths,
    )


# ── T014 / T017: install_skills_for_agent ────────────────────────────


class TestInstallNativeRootAgent:
    """test_install_native_root_agent -- claude gets .claude/skills/"""

    def test_files_placed_in_native_root(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(skills_root, "my-skill")
        entries = install_skills_for_agent(project, "claude", [skill])

        installed = project / ".claude" / "skills" / "my-skill" / "SKILL.md"
        assert installed.is_file()
        assert len(entries) == 1
        assert entries[0].installed_path == ".claude/skills/my-skill/SKILL.md"
        assert entries[0].installation_class == SKILL_CLASS_NATIVE
        assert entries[0].agent_key == "claude"

    def test_content_matches_source(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(skills_root, "my-skill")
        install_skills_for_agent(project, "claude", [skill])

        installed = project / ".claude" / "skills" / "my-skill" / "SKILL.md"
        assert installed.read_text() == skill.skill_md.read_text()


class TestInstallSharedRootAgent:
    """test_install_shared_root_agent -- codex gets .agents/skills/"""

    def test_files_placed_in_shared_root(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(skills_root, "my-skill")
        entries = install_skills_for_agent(project, "codex", [skill])

        installed = project / ".agents" / "skills" / "my-skill" / "SKILL.md"
        assert installed.is_file()
        assert len(entries) == 1
        assert entries[0].installed_path == ".agents/skills/my-skill/SKILL.md"
        assert entries[0].installation_class == SKILL_CLASS_SHARED
        assert entries[0].agent_key == "codex"


class TestInstallWrapperOnlyAgentSkipped:
    """test_install_wrapper_only_agent_skipped -- q gets nothing"""

    def test_returns_empty_list(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(skills_root, "my-skill")
        entries = install_skills_for_agent(project, "q", [skill])

        assert entries == []

    def test_no_files_created(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(skills_root, "my-skill")
        install_skills_for_agent(project, "q", [skill])

        # No directories created under project
        children = list(project.iterdir())
        assert children == []


# ── T016: shared-root deduplication ──────────────────────────────────


class TestSharedRootDeduplication:
    """test_shared_root_deduplication -- two shared agents share one copy"""

    def test_second_agent_skips_file_copy(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(skills_root, "my-skill")
        shared_set: set[str] = set()

        # First shared-root agent (codex) copies files
        entries_1 = install_skills_for_agent(project, "codex", [skill], shared_root_installed=shared_set)
        assert "my-skill" in shared_set
        assert len(entries_1) == 1

        # Second shared-root agent (copilot) reuses files
        entries_2 = install_skills_for_agent(project, "copilot", [skill], shared_root_installed=shared_set)
        assert len(entries_2) == 1

        # Both point to the same installed path
        assert entries_1[0].installed_path == entries_2[0].installed_path

        # But have different agent keys
        assert entries_1[0].agent_key == "codex"
        assert entries_2[0].agent_key == "copilot"

    def test_only_one_file_on_disk(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(skills_root, "my-skill")
        shared_set: set[str] = set()

        install_skills_for_agent(project, "codex", [skill], shared_root_installed=shared_set)
        install_skills_for_agent(project, "copilot", [skill], shared_root_installed=shared_set)

        # Only one copy on disk (in .agents/skills/)
        installed = project / ".agents" / "skills" / "my-skill" / "SKILL.md"
        assert installed.is_file()

        # No vendor-specific copy
        assert not (project / ".codex").exists()
        assert not (project / ".github").exists()


# ── T017: manifest entries ───────────────────────────────────────────


class TestManifestEntriesCreated:
    """test_manifest_entries_created -- verify entry fields"""

    def test_entry_fields_correct(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(skills_root, "my-skill")
        entries = install_skills_for_agent(project, "claude", [skill])

        entry = entries[0]
        assert entry.skill_name == "my-skill"
        assert entry.source_file == "SKILL.md"
        assert entry.installed_path == ".claude/skills/my-skill/SKILL.md"
        assert entry.installation_class == SKILL_CLASS_NATIVE
        assert entry.agent_key == "claude"
        assert entry.content_hash.startswith("sha256:")
        assert entry.installed_at != ""

    def test_hash_computed_from_installed_file(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(skills_root, "my-skill")
        entries = install_skills_for_agent(project, "claude", [skill])

        installed = project / ".claude" / "skills" / "my-skill" / "SKILL.md"
        expected_hash = compute_content_hash(installed)
        assert entries[0].content_hash == expected_hash


# ── T015: install_all_skills ─────────────────────────────────────────


class TestInstallAllSkillsOrchestration:
    """test_install_all_skills_orchestration -- full flow with mixed agents"""

    def test_mixed_agents(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        _make_skill(skills_root, "alpha")
        _make_skill(skills_root, "beta")

        registry = SkillRegistry(skills_root)
        # claude = native, codex = shared, q = wrapper
        manifest = install_all_skills(project, ["claude", "codex", "q"], registry)

        # claude: native, gets both skills -> 2 entries
        claude_entries = [e for e in manifest.entries if e.agent_key == "claude"]
        assert len(claude_entries) == 2

        # codex: shared, gets both skills -> 2 entries
        codex_entries = [e for e in manifest.entries if e.agent_key == "codex"]
        assert len(codex_entries) == 2

        # q: wrapper, gets nothing -> 0 entries
        q_entries = [e for e in manifest.entries if e.agent_key == "q"]
        assert len(q_entries) == 0

        # Total entries: 4
        assert len(manifest.entries) == 4

    def test_manifest_timestamps_set(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        _make_skill(skills_root, "alpha")
        registry = SkillRegistry(skills_root)

        manifest = install_all_skills(project, ["claude"], registry)
        assert manifest.created_at != ""
        assert manifest.updated_at != ""
        assert manifest.version == 1

    def test_shared_root_deduplication_across_agents(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        _make_skill(skills_root, "alpha")
        registry = SkillRegistry(skills_root)

        # Two shared-root agents: copilot and codex
        manifest = install_all_skills(project, ["copilot", "codex"], registry)

        # Both get entries
        copilot_entries = [e for e in manifest.entries if e.agent_key == "copilot"]
        codex_entries = [e for e in manifest.entries if e.agent_key == "codex"]
        assert len(copilot_entries) == 1
        assert len(codex_entries) == 1

        # Both point to same installed_path
        assert copilot_entries[0].installed_path == codex_entries[0].installed_path

        # Only one copy on disk
        installed = project / ".agents" / "skills" / "alpha" / "SKILL.md"
        assert installed.is_file()

    def test_no_skills_returns_empty_manifest(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        skills_root.mkdir()  # Empty -- no skills
        project = tmp_path / "project"
        project.mkdir()

        registry = SkillRegistry(skills_root)
        manifest = install_all_skills(project, ["claude", "codex"], registry)

        assert len(manifest.entries) == 0
        assert manifest.version == 1


# ── T018: edge cases ────────────────────────────────────────────────


class TestInstallPreservesExistingFiles:
    """test_install_preserves_existing_files -- existing non-managed files not deleted"""

    def test_existing_file_not_removed(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        # Pre-existing file in the skill root
        existing_dir = project / ".claude" / "skills" / "my-skill"
        existing_dir.mkdir(parents=True)
        existing_file = existing_dir / "custom-notes.md"
        existing_file.write_text("user notes")

        skill = _make_skill(skills_root, "my-skill")
        install_skills_for_agent(project, "claude", [skill])

        # The existing file should still be there
        assert existing_file.is_file()
        assert existing_file.read_text() == "user notes"

        # And the new skill file should also exist
        assert (existing_dir / "SKILL.md").is_file()


class TestInstallCopiesReferencesAndScripts:
    """test_install_copies_references_and_scripts -- subdirectories copied"""

    def test_all_subdirs_copied(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(
            skills_root,
            "full-skill",
            references=["arch.md", "rfc.txt"],
            scripts=["setup.sh"],
            assets=["logo.png"],
        )
        entries = install_skills_for_agent(project, "claude", [skill])

        base = project / ".claude" / "skills" / "full-skill"

        # Check each sub-file exists
        assert (base / "SKILL.md").is_file()
        assert (base / "references" / "arch.md").is_file()
        assert (base / "references" / "rfc.txt").is_file()
        assert (base / "scripts" / "setup.sh").is_file()
        assert (base / "assets" / "logo.png").is_file()

        # 1 SKILL.md + 2 references + 1 script + 1 asset = 5 entries
        assert len(entries) == 5

    def test_subdir_content_matches(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(
            skills_root,
            "full-skill",
            references=["arch.md"],
        )
        install_skills_for_agent(project, "claude", [skill])

        installed_ref = project / ".claude" / "skills" / "full-skill" / "references" / "arch.md"
        source_ref = skills_root / "full-skill" / "references" / "arch.md"
        assert installed_ref.read_text() == source_ref.read_text()

    def test_entry_source_file_is_relative_within_skill(self, tmp_path: Path) -> None:
        skills_root = tmp_path / "skills_src"
        project = tmp_path / "project"
        project.mkdir()

        skill = _make_skill(
            skills_root,
            "full-skill",
            references=["arch.md"],
            scripts=["run.sh"],
        )
        entries = install_skills_for_agent(project, "claude", [skill])

        source_files = {e.source_file for e in entries}
        assert "SKILL.md" in source_files
        assert "references/arch.md" in source_files
        assert "scripts/run.sh" in source_files
