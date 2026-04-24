"""Tests for the global managed agent-skill bootstrap."""

from __future__ import annotations

from pathlib import Path

from runtime.agents.skills import ensure_global_agent_skills
from specify_cli.skills.registry import SkillRegistry


def _create_skill(root: Path, name: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test\n---\n# {name}\n",
        encoding="utf-8",
    )


def test_global_bootstrap_preserves_non_spec_kitty_user_skills(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

    skills_root = tmp_path / "doctrine_skills"
    _create_skill(skills_root, "spec-kitty-test-skill")
    registry = SkillRegistry(skills_root)

    custom_skill = home / ".claude" / "skills" / "custom-skill" / "SKILL.md"
    custom_skill.parent.mkdir(parents=True, exist_ok=True)
    custom_skill.write_text("# custom\n", encoding="utf-8")

    monkeypatch.setattr(
        "runtime.agents.skills._discover_registry",
        lambda: registry,
    )

    ensure_global_agent_skills()

    managed_skill = home / ".claude" / "skills" / "spec-kitty-test-skill" / "SKILL.md"
    assert managed_skill.is_file()
    assert custom_skill.is_file()
    assert custom_skill.read_text(encoding="utf-8") == "# custom\n"

    mode = managed_skill.stat().st_mode
    assert mode & 0o200 == 0

