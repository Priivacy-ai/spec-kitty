"""Tests for the 3.0.3 globalize-skill-pack migration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.skills.manifest import ManagedFileEntry, ManagedSkillManifest, save_manifest
from specify_cli.skills.registry import SkillRegistry
from specify_cli.upgrade.migrations.m_3_0_3_globalize_skill_pack import (
    GlobalizeSkillPackMigration,
)

pytestmark = pytest.mark.fast


def _setup_project(tmp_path: Path, agents: list[str]) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    kittify = project / ".kittify"
    kittify.mkdir()

    config_content = "agents:\n  available:\n"
    for agent_key in agents:
        config_content += f"    - {agent_key}\n"
    (kittify / "config.yaml").write_text(config_content, encoding="utf-8")
    return project


def _setup_skills(tmp_path: Path) -> Path:
    skills_root = tmp_path / "doctrine_skills"
    skill_dir = skills_root / "spec-kitty-test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: spec-kitty-test-skill\ndescription: test\n---\n# Test\n",
        encoding="utf-8",
    )
    return skills_root


def test_detects_project_local_snapshot_copy(tmp_path: Path) -> None:
    project = _setup_project(tmp_path, ["claude"])
    skills_root = _setup_skills(tmp_path)

    copied_skill = project / ".claude" / "skills" / "spec-kitty-test-skill" / "SKILL.md"
    copied_skill.parent.mkdir(parents=True, exist_ok=True)
    copied_skill.write_text("# stale copy\n", encoding="utf-8")
    save_manifest(
        ManagedSkillManifest(
            entries=[
                ManagedFileEntry(
                    skill_name="spec-kitty-test-skill",
                    source_file="SKILL.md",
                    installed_path=".claude/skills/spec-kitty-test-skill/SKILL.md",
                    installation_class="native-root-required",
                    agent_key="claude",
                    content_hash="sha256:stale",
                    installed_at="2026-01-01T00:00:00+00:00",
                )
            ]
        ),
        project,
    )

    with patch(
        "specify_cli.upgrade.migrations.m_3_0_3_globalize_skill_pack._discover_registry",
        return_value=SkillRegistry(skills_root),
    ):
        assert GlobalizeSkillPackMigration().detect(project) is True


def test_apply_relinks_project_to_global_skill_home(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

    project = _setup_project(tmp_path, ["claude"])
    skills_root = _setup_skills(tmp_path)

    copied_skill = project / ".claude" / "skills" / "spec-kitty-test-skill" / "SKILL.md"
    copied_skill.parent.mkdir(parents=True, exist_ok=True)
    copied_skill.write_text("# stale copy\n", encoding="utf-8")

    with patch(
        "specify_cli.upgrade.migrations.m_3_0_3_globalize_skill_pack._discover_registry",
        return_value=SkillRegistry(skills_root),
    ):
        result = GlobalizeSkillPackMigration().apply(project)

    assert result.success is True

    installed = project / ".claude" / "skills" / "spec-kitty-test-skill" / "SKILL.md"
    assert installed.is_file()

    manifest_path = project / ".kittify" / "skills-manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["spec_kitty_version"] == "3.0.3"
    assert data["entries"][0]["delivery_mode"] in {"symlink", "copy"}
