from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.skills.registry import SkillRegistry
from specify_cli.upgrade.migrations.m_3_2_0_spk_skill_pack import (
    SpkSkillPackMigration,
)

pytestmark = pytest.mark.fast


def _setup_project(tmp_path: Path, agents: list[str]) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    kittify = project / ".kittify"
    kittify.mkdir()
    available = "\n".join(f"    - {agent}" for agent in agents)
    (kittify / "config.yaml").write_text(
        f"agents:\n  available:\n{available}\n",
        encoding="utf-8",
    )
    return project


def _setup_skills(tmp_path: Path) -> Path:
    skills_root = tmp_path / "doctrine_skills"

    legacy = skills_root / "spec-kitty-runtime-next"
    legacy.mkdir(parents=True)
    (legacy / "SKILL.md").write_text(
        "---\nname: spec-kitty-runtime-next\ndescription: legacy\n---\n# Legacy\n",
        encoding="utf-8",
    )

    spk = skills_root / "spk-start-here"
    spk.mkdir()
    (spk / "SKILL.md").write_text(
        "---\nname: spk-start-here\ndescription: start here\n---\n# Start\n",
        encoding="utf-8",
    )
    refs = spk / "references"
    refs.mkdir()
    (refs / "guide.md").write_text("# Guide\n", encoding="utf-8")

    return skills_root


def _patch_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)


def test_detects_missing_spk_skill_for_installable_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _setup_project(tmp_path, agents=["claude"])
    skills_root = _setup_skills(tmp_path)
    _patch_home(tmp_path, monkeypatch)

    with patch(
        "specify_cli.upgrade.migrations.m_3_2_0_spk_skill_pack._discover_registry",
        return_value=SkillRegistry(skills_root),
    ):
        assert SpkSkillPackMigration().detect(project) is True


def test_apply_installs_spk_skill_and_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _setup_project(tmp_path, agents=["claude"])
    skills_root = _setup_skills(tmp_path)
    _patch_home(tmp_path, monkeypatch)

    with patch(
        "specify_cli.upgrade.migrations.m_3_2_0_spk_skill_pack._discover_registry",
        return_value=SkillRegistry(skills_root),
    ):
        result = SpkSkillPackMigration().apply(project)

    assert result.success is True
    assert (project / ".claude" / "skills" / "spk-start-here" / "SKILL.md").exists()
    assert (
        project
        / ".claude"
        / "skills"
        / "spk-start-here"
        / "references"
        / "guide.md"
    ).exists()

    manifest = json.loads((project / ".kittify" / "skills-manifest.json").read_text())
    assert manifest["spec_kitty_version"] == "3.2.0"
    assert any(entry["skill_name"] == "spk-start-here" for entry in manifest["entries"])


def test_detect_false_after_apply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _setup_project(tmp_path, agents=["claude"])
    skills_root = _setup_skills(tmp_path)
    registry = SkillRegistry(skills_root)
    _patch_home(tmp_path, monkeypatch)

    with patch(
        "specify_cli.upgrade.migrations.m_3_2_0_spk_skill_pack._discover_registry",
        return_value=registry,
    ):
        result = SpkSkillPackMigration().apply(project)
        assert result.success is True
        assert SpkSkillPackMigration().detect(project) is False


def test_skips_wrapper_only_agents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _setup_project(tmp_path, agents=["q"])
    skills_root = _setup_skills(tmp_path)
    _patch_home(tmp_path, monkeypatch)

    with patch(
        "specify_cli.upgrade.migrations.m_3_2_0_spk_skill_pack._discover_registry",
        return_value=SkillRegistry(skills_root),
    ):
        assert SpkSkillPackMigration().detect(project) is False
