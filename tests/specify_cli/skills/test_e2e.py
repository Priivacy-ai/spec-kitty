"""End-to-end integration tests for the skill lifecycle.

T036 - Full lifecycle: install -> verify -> delete -> verify -> repair -> verify
T037 - Per-class distribution: native, shared, wrapper-only
T038 - Manifest persistence: save -> load -> verify entries match
T039 - Drift detection and repair: modify file -> verify detects drift -> repair -> verify ok
T040 - Multiple agents mixed classes: native + shared + wrapper simultaneously
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.core.config import (
    SKILL_CLASS_NATIVE,
    SKILL_CLASS_SHARED,
)
from specify_cli.skills.installer import install_all_skills, install_skills_for_agent
from specify_cli.skills.manifest import (
    ManagedFileEntry,
    ManagedSkillManifest,
    compute_content_hash,
    load_manifest,
    save_manifest,
)
from specify_cli.skills.registry import CanonicalSkill, SkillRegistry
from specify_cli.skills.verifier import repair_skills, verify_installed_skills


# ── Helpers ──────────────────────────────────────────────────────────


def _create_skill_on_disk(
    skills_root: Path,
    name: str,
    *,
    skill_md_content: str | None = None,
    references: dict[str, str] | None = None,
) -> None:
    """Create a minimal canonical skill directory with SKILL.md and optional references."""
    skill_dir = skills_root / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    content = skill_md_content or f"---\nname: {name}\n---\n# {name}\nSkill content.\n"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    if references:
        ref_dir = skill_dir / "references"
        ref_dir.mkdir(exist_ok=True)
        for fname, ref_content in references.items():
            (ref_dir / fname).write_text(ref_content, encoding="utf-8")


def _setup_project(tmp_path: Path) -> tuple[Path, Path]:
    """Create project dir with .kittify/ and a skills_root dir. Returns (project, skills_root)."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".kittify").mkdir()

    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    return project, skills_root


# ── T036: Full lifecycle ─────────────────────────────────────────────


def test_full_lifecycle(tmp_path: Path) -> None:
    """Install skills, verify ok, delete a file, verify detects missing, repair, verify ok again."""
    project, skills_root = _setup_project(tmp_path)

    # Create a canonical skill with SKILL.md and a reference
    _create_skill_on_disk(
        skills_root,
        "spec-kitty-setup-doctor",
        skill_md_content="---\nname: spec-kitty-setup-doctor\n---\n# Setup Doctor\nDiagnostic skill.\n",
        references={"troubleshooting.md": "# Troubleshooting\nCommon fixes.\n"},
    )

    registry = SkillRegistry(skills_root)
    skills = registry.discover_skills()
    assert len(skills) == 1

    # Step 1: Install for claude (native-root)
    entries = install_skills_for_agent(project, "claude", skills)
    assert len(entries) == 2  # SKILL.md + references/troubleshooting.md

    manifest = ManagedSkillManifest(entries=entries)
    save_manifest(manifest, project)

    # Step 2: Verify -> should be ok
    result = verify_installed_skills(project)
    assert result.ok is True
    assert result.missing == []
    assert result.drifted == []

    # Step 3: Delete one installed file
    skill_file = project / ".claude" / "skills" / "spec-kitty-setup-doctor" / "SKILL.md"
    assert skill_file.exists()
    skill_file.unlink()

    # Step 4: Verify -> should detect missing
    result = verify_installed_skills(project)
    assert result.ok is False
    assert len(result.missing) == 1
    assert result.missing[0].source_file == "SKILL.md"
    assert result.missing[0].skill_name == "spec-kitty-setup-doctor"

    # Step 5: Repair
    repaired, failed = repair_skills(project, result, registry)
    assert repaired == 1
    assert failed == 0

    # Verify the file was restored
    assert skill_file.exists()

    # Step 6: Verify again -> should be ok
    result = verify_installed_skills(project)
    assert result.ok is True
    assert result.missing == []
    assert result.drifted == []


# ── T037: Per-class distribution ─────────────────────────────────────


def test_per_class_distribution(tmp_path: Path) -> None:
    """Install for claude (native -> .claude/skills/), codex (shared -> .agents/skills/), q (wrapper-only -> nothing)."""
    project, skills_root = _setup_project(tmp_path)

    _create_skill_on_disk(skills_root, "test-skill")
    registry = SkillRegistry(skills_root)
    skills = registry.discover_skills()

    # Claude: native-root-required -> .claude/skills/
    claude_entries = install_skills_for_agent(project, "claude", skills)
    assert len(claude_entries) == 1
    assert claude_entries[0].installation_class == SKILL_CLASS_NATIVE
    assert claude_entries[0].installed_path == ".claude/skills/test-skill/SKILL.md"
    assert (project / ".claude" / "skills" / "test-skill" / "SKILL.md").is_file()

    # Codex: shared-root-capable -> .agents/skills/
    codex_entries = install_skills_for_agent(project, "codex", skills)
    assert len(codex_entries) == 1
    assert codex_entries[0].installation_class == SKILL_CLASS_SHARED
    assert codex_entries[0].installed_path == ".agents/skills/test-skill/SKILL.md"
    assert (project / ".agents" / "skills" / "test-skill" / "SKILL.md").is_file()

    # Q: wrapper-only -> no files, empty entries
    q_entries = install_skills_for_agent(project, "q", skills)
    assert q_entries == []
    assert not (project / ".amazonq" / "skills").exists()


# ── T038: Manifest persistence ───────────────────────────────────────


def test_manifest_persistence(tmp_path: Path) -> None:
    """Install, save manifest, load manifest from fresh call, verify entries match."""
    project, skills_root = _setup_project(tmp_path)

    _create_skill_on_disk(
        skills_root,
        "persist-skill",
        references={"ref.md": "# Reference\nSome reference content.\n"},
    )
    registry = SkillRegistry(skills_root)
    skills = registry.discover_skills()

    # Install and save
    entries = install_skills_for_agent(project, "claude", skills)
    original_manifest = ManagedSkillManifest(
        version=1,
        created_at="2026-01-15T10:00:00+00:00",
        spec_kitty_version="0.14.0",
        entries=entries,
    )
    save_manifest(original_manifest, project)

    # Verify the JSON file exists and is valid
    manifest_path = project / ".kittify" / "skills-manifest.json"
    assert manifest_path.is_file()

    # Load from fresh call (simulating new session)
    loaded = load_manifest(project)
    assert loaded is not None

    # Verify structural fields
    assert loaded.version == original_manifest.version
    assert loaded.created_at == original_manifest.created_at
    assert loaded.spec_kitty_version == original_manifest.spec_kitty_version
    # updated_at is set by save_manifest, so it will differ from the original empty string

    # Verify entries match
    assert len(loaded.entries) == len(original_manifest.entries)
    for orig, reloaded in zip(original_manifest.entries, loaded.entries):
        assert reloaded.skill_name == orig.skill_name
        assert reloaded.source_file == orig.source_file
        assert reloaded.installed_path == orig.installed_path
        assert reloaded.installation_class == orig.installation_class
        assert reloaded.agent_key == orig.agent_key
        assert reloaded.content_hash == orig.content_hash
        assert reloaded.installed_at == orig.installed_at


# ── T039: Drift detection and repair ─────────────────────────────────


def test_drift_detection_and_repair(tmp_path: Path) -> None:
    """Install, modify a file, verify detects drift with wrong hash, repair restores content, verify ok."""
    project, skills_root = _setup_project(tmp_path)

    canonical_content = "---\nname: drift-skill\n---\n# Drift Skill\nCanonical content here.\n"
    _create_skill_on_disk(
        skills_root,
        "drift-skill",
        skill_md_content=canonical_content,
    )

    registry = SkillRegistry(skills_root)
    skills = registry.discover_skills()

    # Install and save manifest
    entries = install_skills_for_agent(project, "claude", skills)
    manifest = ManagedSkillManifest(entries=entries)
    save_manifest(manifest, project)

    # Record the original hash
    installed_file = project / ".claude" / "skills" / "drift-skill" / "SKILL.md"
    original_hash = compute_content_hash(installed_file)
    assert entries[0].content_hash == original_hash

    # Modify the installed file (simulate user edit / drift)
    installed_file.write_text("User modified this content!", encoding="utf-8")
    modified_hash = compute_content_hash(installed_file)
    assert modified_hash != original_hash

    # Verify -> should detect drift
    result = verify_installed_skills(project)
    assert result.ok is False
    assert len(result.drifted) == 1
    assert result.missing == []

    drifted_entry, actual_hash = result.drifted[0]
    assert drifted_entry.skill_name == "drift-skill"
    assert actual_hash == modified_hash
    assert actual_hash != original_hash

    # Repair
    repaired, failed = repair_skills(project, result, registry)
    assert repaired == 1
    assert failed == 0

    # Verify the file content was restored
    assert installed_file.read_text(encoding="utf-8") == canonical_content

    # Verify the manifest hash was updated after repair
    reloaded_manifest = load_manifest(project)
    assert reloaded_manifest is not None
    repaired_entry = reloaded_manifest.find_by_installed_path(
        ".claude/skills/drift-skill/SKILL.md"
    )
    assert repaired_entry is not None
    assert repaired_entry.content_hash == compute_content_hash(installed_file)

    # Verify again -> should be ok
    result = verify_installed_skills(project)
    assert result.ok is True
    assert result.missing == []
    assert result.drifted == []


# ── T040: Multiple agents mixed classes ──────────────────────────────


def test_multiple_agents_mixed_classes(tmp_path: Path) -> None:
    """Install for claude + copilot + codex + q simultaneously and verify correct distribution."""
    project, skills_root = _setup_project(tmp_path)

    _create_skill_on_disk(
        skills_root,
        "multi-skill",
        skill_md_content="---\nname: multi-skill\n---\n# Multi Skill\nContent.\n",
        references={"guide.md": "# Guide\nUsage guide.\n"},
    )

    registry = SkillRegistry(skills_root)

    # Install for all four agents simultaneously using install_all_skills
    manifest = install_all_skills(
        project,
        ["claude", "copilot", "codex", "q"],
        registry,
    )
    save_manifest(manifest, project)

    # 1. .claude/skills/ has files (native)
    claude_skill_dir = project / ".claude" / "skills" / "multi-skill"
    assert (claude_skill_dir / "SKILL.md").is_file()
    assert (claude_skill_dir / "references" / "guide.md").is_file()

    # 2. .agents/skills/ has files (shared, deduplicated)
    shared_skill_dir = project / ".agents" / "skills" / "multi-skill"
    assert (shared_skill_dir / "SKILL.md").is_file()
    assert (shared_skill_dir / "references" / "guide.md").is_file()

    # 3. No .amazonq/skills/ (wrapper-only)
    assert not (project / ".amazonq" / "skills").exists()
    # Also no .amazonq directory at all
    assert not (project / ".amazonq").exists()

    # 4. Manifest entries exist for claude, copilot, codex but not q
    claude_entries = [e for e in manifest.entries if e.agent_key == "claude"]
    copilot_entries = [e for e in manifest.entries if e.agent_key == "copilot"]
    codex_entries = [e for e in manifest.entries if e.agent_key == "codex"]
    q_entries = [e for e in manifest.entries if e.agent_key == "q"]

    assert len(claude_entries) == 2  # SKILL.md + references/guide.md
    assert len(copilot_entries) == 2
    assert len(codex_entries) == 2
    assert len(q_entries) == 0

    # Verify installation classes
    assert all(e.installation_class == SKILL_CLASS_NATIVE for e in claude_entries)
    assert all(e.installation_class == SKILL_CLASS_SHARED for e in copilot_entries)
    assert all(e.installation_class == SKILL_CLASS_SHARED for e in codex_entries)

    # 5. copilot and codex entries point to same .agents/skills/ path
    copilot_paths = {e.installed_path for e in copilot_entries}
    codex_paths = {e.installed_path for e in codex_entries}
    assert copilot_paths == codex_paths
    assert all(p.startswith(".agents/skills/") for p in copilot_paths)

    # Claude entries point to .claude/skills/ (different from shared)
    claude_paths = {e.installed_path for e in claude_entries}
    assert all(p.startswith(".claude/skills/") for p in claude_paths)
    assert claude_paths != copilot_paths  # Different roots

    # Verify shared-root deduplication: only one file copy exists in .agents/skills/
    # (no duplicate directories like .codex/skills/ or .github/skills/)
    assert not (project / ".codex" / "skills").exists()
    assert not (project / ".github" / "skills").exists()

    # Verify the whole system passes verification
    result = verify_installed_skills(project)
    assert result.ok is True
    assert result.missing == []
    assert result.drifted == []
