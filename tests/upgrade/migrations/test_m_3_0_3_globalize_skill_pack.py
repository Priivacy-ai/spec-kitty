"""Tests for the 3.0.3 globalize-skill-pack migration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.skills.manifest import (
    ManagedFileEntry,
    ManagedSkillManifest,
    compute_content_hash,
    load_manifest,
    save_manifest,
)
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
    # A configured agent and a canonical name are not ownership proof.
    save_manifest(
        ManagedSkillManifest(
            spec_kitty_version="3.0.2",
            entries=[
                ManagedFileEntry(
                    skill_name="spec-kitty-test-skill",
                    source_file="SKILL.md",
                    installed_path=".claude/skills/spec-kitty-test-skill/SKILL.md",
                    installation_class="native-root-required",
                    agent_key="claude",
                    content_hash=compute_content_hash(copied_skill),
                    installed_at="2026-01-01T00:00:00+00:00",
                    delivery_mode="copy",
                )
            ],
        ),
        project,
    )

    with patch(
        "specify_cli.upgrade.migrations.m_3_0_3_globalize_skill_pack._discover_registry",
        return_value=SkillRegistry(skills_root),
    ):
        result = GlobalizeSkillPackMigration().apply(project)

    assert result.success is True
    assert result.manual_review_required is True
    assert len(result.preserved_paths) == 1
    assert result.preserved_paths[0].startswith(".kittify/.migration-backup/agent-skills/")
    assert result.preserved_paths[0].endswith(".claude/skills/spec-kitty-test-skill/SKILL.md")
    assert (project / result.preserved_paths[0]).is_file()
    assert (project / result.preserved_paths[0]).read_bytes() == b"# stale copy\n"

    installed = project / ".claude" / "skills" / "spec-kitty-test-skill" / "SKILL.md"
    assert installed.is_file()
    source_skill = skills_root / "spec-kitty-test-skill" / "SKILL.md"
    assert installed.read_bytes() == source_skill.read_bytes()

    manifest_path = project / ".kittify" / "skills-manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["spec_kitty_version"] == "3.0.3"
    assert data["entries"][0]["delivery_mode"] in {"symlink", "copy"}
    assert data["entries"][0]["content_hash"] == compute_content_hash(installed)
    if data["entries"][0]["delivery_mode"] == "symlink":
        assert installed.is_symlink()
        assert installed.resolve().is_relative_to(home / ".kittify")


def test_apply_preserves_untracked_differing_skill(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))
    project = _setup_project(tmp_path, ["claude"])
    skills_root = _setup_skills(tmp_path)
    custom_skill = project / ".claude/skills/spec-kitty-test-skill/SKILL.md"
    custom_skill.parent.mkdir(parents=True)
    custom_skill.write_bytes(b"# stale copy\n")
    before = custom_skill.stat()
    assert load_manifest(project) is None

    with patch(
        "specify_cli.upgrade.migrations.m_3_0_3_globalize_skill_pack._discover_registry",
        return_value=SkillRegistry(skills_root),
    ):
        GlobalizeSkillPackMigration().apply(project)

    # The all-preserved caller's success/change reporting is a separate policy gap.
    assert not custom_skill.is_symlink()
    assert custom_skill.read_bytes() == b"# stale copy\n"
    after = custom_skill.stat()
    assert (after.st_ino, after.st_mode, after.st_mtime_ns) == (
        before.st_ino,
        before.st_mode,
        before.st_mtime_ns,
    )
    assert not (project / ".kittify/.migration-backup").exists()
    manifest = load_manifest(project, strict=True)
    assert manifest is None or manifest.entries == []


def test_identical_skill_copy_does_not_require_manual_review(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))

    project = _setup_project(tmp_path, ["claude"])
    skills_root = _setup_skills(tmp_path)

    source_skill = skills_root / "spec-kitty-test-skill" / "SKILL.md"
    copied_skill = project / ".claude" / "skills" / "spec-kitty-test-skill" / "SKILL.md"
    copied_skill.parent.mkdir(parents=True, exist_ok=True)
    copied_skill.write_text(source_skill.read_text(encoding="utf-8"), encoding="utf-8")

    with patch(
        "specify_cli.upgrade.migrations.m_3_0_3_globalize_skill_pack._discover_registry",
        return_value=SkillRegistry(skills_root),
    ):
        result = GlobalizeSkillPackMigration().apply(project)

    assert result.success is True
    assert result.manual_review_required is False
    assert result.preserved_paths == []
