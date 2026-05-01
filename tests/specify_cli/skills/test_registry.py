"""Tests for the canonical skill registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.skills.registry import SkillRegistry

# Marked for mutmut sandbox skip — see ADR 2026-04-20-1.
# Reason: subprocess CLI invocation
pytestmark = pytest.mark.non_sandbox


def _make_skill(
    root: Path,
    name: str,
    *,
    references: list[str] | None = None,
    scripts: list[str] | None = None,
    assets: list[str] | None = None,
) -> Path:
    """Helper: create a minimal skill directory under *root*."""
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\n# {name}\nPlaceholder.\n")
    for sub, files in [
        ("references", references or []),
        ("scripts", scripts or []),
        ("assets", assets or []),
    ]:
        sub_dir = skill_dir / sub
        sub_dir.mkdir(exist_ok=True)
        # Always add a .gitkeep (should be ignored by _collect_files)
        (sub_dir / ".gitkeep").touch()
        for fname in files:
            (sub_dir / fname).write_text(f"# {fname}\n")
    return skill_dir


# ── discover_skills ──────────────────────────────────────────────────


def test_discover_skills_finds_valid_skill(tmp_path: Path) -> None:
    _make_skill(tmp_path, "my-skill")
    registry = SkillRegistry(tmp_path)
    skills = registry.discover_skills()
    assert len(skills) == 1
    assert skills[0].name == "my-skill"
    assert skills[0].skill_md == tmp_path / "my-skill" / "SKILL.md"


def test_discover_skills_ignores_dir_without_skill_md(tmp_path: Path) -> None:
    # Directory present but no SKILL.md
    (tmp_path / "not-a-skill").mkdir()
    (tmp_path / "not-a-skill" / "README.md").write_text("nope")
    registry = SkillRegistry(tmp_path)
    assert registry.discover_skills() == []


def test_discover_skills_empty_root(tmp_path: Path) -> None:
    registry = SkillRegistry(tmp_path)
    assert registry.discover_skills() == []


def test_discover_skills_missing_root(tmp_path: Path) -> None:
    registry = SkillRegistry(tmp_path / "nonexistent")
    assert registry.discover_skills() == []


def test_discover_skills_collects_references_scripts_assets(tmp_path: Path) -> None:
    _make_skill(
        tmp_path,
        "full-skill",
        references=["arch.md", "rfc.txt"],
        scripts=["setup.sh"],
        assets=["logo.png", "diagram.svg"],
    )
    registry = SkillRegistry(tmp_path)
    skills = registry.discover_skills()
    assert len(skills) == 1
    skill = skills[0]

    ref_names = sorted(p.name for p in skill.references)
    assert ref_names == ["arch.md", "rfc.txt"]

    script_names = [p.name for p in skill.scripts]
    assert script_names == ["setup.sh"]

    asset_names = sorted(p.name for p in skill.assets)
    assert asset_names == ["diagram.svg", "logo.png"]

    # all_files includes SKILL.md + all sub-files
    assert skill.skill_md in skill.all_files
    assert len(skill.all_files) == 1 + 2 + 1 + 2  # SKILL.md + refs + scripts + assets


# ── get_skill ────────────────────────────────────────────────────────


def test_get_skill_by_name(tmp_path: Path) -> None:
    _make_skill(tmp_path, "alpha")
    _make_skill(tmp_path, "beta")
    registry = SkillRegistry(tmp_path)
    skill = registry.get_skill("beta")
    assert skill is not None
    assert skill.name == "beta"


def test_get_skill_not_found(tmp_path: Path) -> None:
    _make_skill(tmp_path, "alpha")
    registry = SkillRegistry(tmp_path)
    assert registry.get_skill("nonexistent") is None


# ── from_local_repo ──────────────────────────────────────────────────


def test_from_local_repo(tmp_path: Path) -> None:
    skills_root = tmp_path / "src" / "doctrine" / "skills"
    skills_root.mkdir(parents=True)
    _make_skill(skills_root, "local-skill")

    registry = SkillRegistry.from_local_repo(tmp_path)
    skills = registry.discover_skills()
    assert len(skills) == 1
    assert skills[0].name == "local-skill"


# ── Multi-skill discovery ──────────────────────────────────────────


def test_discover_multiple_skills_sorted(tmp_path: Path) -> None:
    """Registry discovers multiple skills and returns them sorted by name."""
    _make_skill(tmp_path, "spec-kitty-runtime-next")
    _make_skill(tmp_path, "spec-kitty-setup-doctor")
    _make_skill(tmp_path, "spec-kitty-glossary-context")

    registry = SkillRegistry(tmp_path)
    skills = registry.discover_skills()
    assert len(skills) == 3
    names = [s.name for s in skills]
    assert names == ["spec-kitty-glossary-context", "spec-kitty-runtime-next", "spec-kitty-setup-doctor"]


# ── Packaging verification ─────────────────────────────────────────


def test_skills_module_importable() -> None:
    """Verify the skills module is importable (packaging sanity check)."""
    import specify_cli.skills

    assert hasattr(specify_cli.skills, "CanonicalSkill")
    assert hasattr(specify_cli.skills, "SkillRegistry")
    assert hasattr(specify_cli.skills, "ManagedSkillManifest")
    assert hasattr(specify_cli.skills, "install_skills_for_agent")
    assert hasattr(specify_cli.skills, "verify_installed_skills")


def test_doctrine_skills_exist_in_repo() -> None:
    """Verify canonical skills exist in the doctrine layer of this repo."""
    from specify_cli.skills.registry import SkillRegistry
    import subprocess

    # Find repo root via git
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    repo_root = Path(result.stdout.strip())

    registry = SkillRegistry.from_local_repo(repo_root)
    skills = registry.discover_skills()
    skill_names = {s.name for s in skills}
    assert "spec-kitty-setup-doctor" in skill_names
    assert "spec-kitty-runtime-next" in skill_names
    assert len(skills) >= 2
