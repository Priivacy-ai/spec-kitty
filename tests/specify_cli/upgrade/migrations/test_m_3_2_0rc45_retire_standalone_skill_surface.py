"""Tests for retiring stale standalone governance skill surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.skills import manifest_store
from specify_cli.skills.manifest import ManagedFileEntry, ManagedSkillManifest, load_manifest, save_manifest
from specify_cli.skills.manifest_store import ManifestEntry, SkillsManifest
from specify_cli.skills.retired import RETIRED_STANDALONE_SKILL_NAMES
from specify_cli.upgrade.migrations.m_3_2_0rc45_retire_standalone_skill_surface import (
    RetireStandaloneSkillSurfaceMigration,
)

pytestmark = [pytest.mark.fast]

_HASH = "a" * 64
_INSTALLED_AT = "2026-01-01T00:00:00+00:00"
_VERSION = "3.2.0rc45"


def _retired_name() -> str:
    return next(iter(RETIRED_STANDALONE_SKILL_NAMES))


def _write_skill(root: Path, name: str, content: str = "# skill\n") -> Path:
    skill = root / name / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text(content, encoding="utf-8")
    return skill


def test_detects_retired_skill_surface_in_known_project_roots(tmp_path: Path) -> None:
    retired_name = _retired_name()
    _write_skill(tmp_path / ".agents" / "skills", retired_name)

    assert RetireStandaloneSkillSurfaceMigration().detect(tmp_path) is True


def test_apply_removes_retired_skill_surface_from_all_known_project_roots(tmp_path: Path) -> None:
    retired_name = _retired_name()
    active = _write_skill(tmp_path / ".agents" / "skills", "spec-kitty")
    for root in [
        tmp_path / ".agents" / "skills",
        tmp_path / ".claude" / "skills",
        tmp_path / ".github" / "skills",
    ]:
        _write_skill(root, retired_name)
        _write_skill(root, "custom-skill")

    result = RetireStandaloneSkillSurfaceMigration().apply(tmp_path)

    assert result.success is True
    assert len(result.changes_made) == 3
    for root in [
        tmp_path / ".agents" / "skills",
        tmp_path / ".claude" / "skills",
        tmp_path / ".github" / "skills",
    ]:
        assert not (root / retired_name).exists()
        assert (root / "custom-skill" / "SKILL.md").is_file()
    assert active.is_file()


def test_apply_dry_run_reports_without_deleting(tmp_path: Path) -> None:
    retired_name = _retired_name()
    stale = _write_skill(tmp_path / ".agents" / "skills", retired_name)

    result = RetireStandaloneSkillSurfaceMigration().apply(tmp_path, dry_run=True)

    assert result.success is True
    assert any("Would remove retired skill surface" in change for change in result.changes_made)
    assert stale.is_file()


def test_apply_prunes_managed_and_command_manifests(tmp_path: Path) -> None:
    retired_name = _retired_name()
    stale_rel = f".agents/skills/{retired_name}/SKILL.md"
    current_rel = ".agents/skills/spec-kitty.specify/SKILL.md"

    managed = ManagedSkillManifest(
        created_at=_INSTALLED_AT,
        updated_at=_INSTALLED_AT,
        spec_kitty_version=_VERSION,
        entries=[
            ManagedFileEntry(
                skill_name=retired_name,
                source_file="SKILL.md",
                installed_path=stale_rel,
                installation_class="shared-root-capable",
                agent_key="codex",
                content_hash=f"sha256:{_HASH}",
                installed_at=_INSTALLED_AT,
                delivery_mode="copy",
            ),
            ManagedFileEntry(
                skill_name="spec-kitty",
                source_file="SKILL.md",
                installed_path=".agents/skills/spec-kitty/SKILL.md",
                installation_class="shared-root-capable",
                agent_key="codex",
                content_hash=f"sha256:{_HASH}",
                installed_at=_INSTALLED_AT,
                delivery_mode="copy",
            ),
        ],
    )
    save_manifest(managed, tmp_path)

    command_manifest = SkillsManifest(entries=[
        ManifestEntry(
            path=stale_rel,
            content_hash=_HASH,
            agents=("codex",),
            installed_at=_INSTALLED_AT,
            spec_kitty_version=_VERSION,
        ),
        ManifestEntry(
            path=current_rel,
            content_hash=_HASH,
            agents=("codex",),
            installed_at=_INSTALLED_AT,
            spec_kitty_version=_VERSION,
        ),
    ])
    manifest_store.save(tmp_path, command_manifest)

    result = RetireStandaloneSkillSurfaceMigration().apply(tmp_path)

    assert result.success is True
    assert [entry.skill_name for entry in load_manifest(tmp_path).entries] == ["spec-kitty"]  # type: ignore[union-attr]
    assert [entry.path for entry in manifest_store.load(tmp_path).entries] == [current_rel]
    assert any("Pruned retired skill manifest entry" in change for change in result.changes_made)
    assert any("Pruned retired command skills manifest entry" in change for change in result.changes_made)


def test_apply_is_idempotent_when_surface_absent(tmp_path: Path) -> None:
    result = RetireStandaloneSkillSurfaceMigration().apply(tmp_path)

    assert result.success is True
    assert result.changes_made == ["Retired standalone governance skill surfaces absent"]


def test_migration_is_registered_by_auto_discovery() -> None:
    from specify_cli.upgrade.migrations import auto_discover_migrations
    from specify_cli.upgrade.registry import MigrationRegistry

    MigrationRegistry.clear()
    auto_discover_migrations()

    assert (
        "3.2.0rc45_retire_standalone_skill_surface"
        in MigrationRegistry._migrations
    )
