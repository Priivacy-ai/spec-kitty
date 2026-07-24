"""Unit tests for ``tool_surface.providers.command_skills``."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.skills import command_installer
from specify_cli.skills import manifest_store
from specify_cli.tool_surface.providers.command_skills import (
    CommandSkillsProvider,
    command_skill_definition,
)
from specify_cli.tool_surface.providers.protocol import ReportingSurfaceProvider
from specify_cli.tool_surface.status import (
    STATE_DRIFTED,
    STATE_MISSING,
    STATE_PRESENT,
)

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _empty_manifest(project: Path) -> None:
    kittify = project / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "command-skills-manifest.json").write_text(
        json.dumps({"schema_version": 1, "entries": []}), encoding="utf-8"
    )


def _write_manifest_entry(project: Path, rel: str, body: str) -> None:
    target = project / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    manifest_store.save(
        project,
        manifest_store.SkillsManifest(
            entries=[
                manifest_store.ManifestEntry(
                    path=rel,
                    content_hash=manifest_store.fingerprint_file(target),
                    agents=("codex",),
                    installed_at="2026-06-14T00:00:00+00:00",
                    spec_kitty_version="test",
                )
            ]
        ),
    )


def test_provider_satisfies_reporting_protocol() -> None:
    provider = CommandSkillsProvider()
    assert isinstance(provider, ReportingSurfaceProvider)
    assert provider.provider_key == "command_skills"


def test_can_handle_only_command_skill() -> None:
    from specify_cli.tool_surface.enums import ToolSurfaceKind
    from specify_cli.tool_surface.providers.slash_commands import (
        slash_command_definition,
    )

    provider = CommandSkillsProvider()
    assert provider.can_handle(command_skill_definition()) is True
    other = slash_command_definition()
    assert other.kind == ToolSurfaceKind.COMMAND_FILE
    assert provider.can_handle(other) is False


def test_expand_unsupported_agent_returns_empty(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instances = provider.expand(command_skill_definition(), "claude", tmp_path)
    assert instances == []


def test_expand_supported_agent_one_per_command(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instances = provider.expand(command_skill_definition(), "codex", tmp_path)
    assert len(instances) == len(command_installer.CANONICAL_COMMANDS)
    assert all(i.owner == "codex" for i in instances)
    assert all(i.path.name == "SKILL.md" for i in instances)


def test_probe_missing(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    status = provider.probe(instance)
    assert status.state == STATE_MISSING
    assert status.findings[0].code == "generated-surface-missing"
    assert status.findings[0].repair_command is not None


def test_probe_present(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    _write_manifest_entry(
        tmp_path, instance.path.relative_to(tmp_path).as_posix(), "content"
    )
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    status = provider.probe(instance)
    assert status.state == STATE_PRESENT
    assert status.findings == ()


def test_probe_drift(tmp_path: Path) -> None:
    from dataclasses import replace

    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    _write_manifest_entry(
        tmp_path, instance.path.relative_to(tmp_path).as_posix(), "real content"
    )
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    # Force a mismatched expected hash to simulate manifest drift.
    drifted = replace(instance, exists=True, file_hash="deadbeef" * 8)
    status = provider.probe(drifted)
    assert status.state == STATE_DRIFTED
    assert status.findings[0].code == "managed-file-drift"


def test_repair_no_actionable_returns_clean(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    # Materialize the file so probe reports PRESENT (nothing to repair).
    _write_manifest_entry(
        tmp_path, instance.path.relative_to(tmp_path).as_posix(), "content"
    )
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    present = provider.probe(instance)
    assert present.state == STATE_PRESENT
    result = provider.repair(tmp_path, [present])
    assert result.repaired == ()
    assert result.failed == ()


def test_repair_dry_run_reports_without_install(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    status = provider.probe(instance)  # missing
    result = provider.repair(tmp_path, [status], dry_run=True)
    assert result.dry_run is True
    # No file was created during a dry run.
    assert not instance.path.exists()


def test_expand_reports_unmanaged_spec_kitty_orphan(tmp_path: Path) -> None:
    _empty_manifest(tmp_path)
    orphan = tmp_path / ".agents" / "skills" / "spec-kitty.fake" / "SKILL.md"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("orphan", encoding="utf-8")
    provider = CommandSkillsProvider()

    statuses = [
        provider.probe(i)
        for i in provider.expand(command_skill_definition(), "codex", tmp_path)
    ]

    assert any(
        f.code == "unmanaged-spec-kitty-surface"
        for status in statuses
        for f in status.findings
    )


def test_expand_reports_stale_manifest_command(tmp_path: Path) -> None:
    stale_rel = ".agents/skills/spec-kitty.checklist/SKILL.md"
    stale = tmp_path / stale_rel
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("stale", encoding="utf-8")
    manifest = manifest_store.SkillsManifest(
        entries=(
            manifest_store.ManifestEntry(
                path=stale_rel,
                content_hash=manifest_store.fingerprint_file(stale),
                agents=("codex",),
                installed_at="2026-06-14T00:00:00+00:00",
                spec_kitty_version="test",
            ),
        )
    )
    manifest_store.save(tmp_path, manifest)
    provider = CommandSkillsProvider()

    statuses = [
        provider.probe(i)
        for i in provider.expand(command_skill_definition(), "codex", tmp_path)
    ]

    assert any(
        f.code == "stale-generated-surface"
        for status in statuses
        for f in status.findings
    )
