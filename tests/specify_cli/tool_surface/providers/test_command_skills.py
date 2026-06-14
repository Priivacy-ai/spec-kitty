"""Unit tests for ``tool_surface.providers.command_skills``."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.skills import command_installer
from specify_cli.tool_surface.providers.base import AbstractSurfaceProvider
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


def _empty_manifest(project: Path) -> None:
    kittify = project / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "command-skills-manifest.json").write_text(
        json.dumps({"schema_version": 1, "entries": []}), encoding="utf-8"
    )


def test_provider_satisfies_both_protocols() -> None:
    provider = CommandSkillsProvider()
    assert isinstance(provider, AbstractSurfaceProvider)
    assert isinstance(provider, ReportingSurfaceProvider)
    assert provider.provider_key == "command_skills"


def test_can_handle_only_command_skill() -> None:
    from specify_cli.tool_surface.enums import SurfaceKind
    from specify_cli.tool_surface.providers.slash_commands import (
        slash_command_definition,
    )

    provider = CommandSkillsProvider()
    assert provider.can_handle(command_skill_definition()) is True
    other = slash_command_definition()
    assert other.kind == SurfaceKind.COMMAND_FILE
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
    instance.path.parent.mkdir(parents=True, exist_ok=True)
    instance.path.write_text("content", encoding="utf-8")
    # file_hash is None (no manifest entry) -> present once it exists.
    status = provider.probe(instance)
    assert status.state == STATE_PRESENT
    assert status.findings == ()


def test_probe_drift(tmp_path: Path) -> None:
    from dataclasses import replace

    _empty_manifest(tmp_path)
    provider = CommandSkillsProvider()
    instance = provider.expand(command_skill_definition(), "codex", tmp_path)[0]
    instance.path.parent.mkdir(parents=True, exist_ok=True)
    instance.path.write_text("real content", encoding="utf-8")
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
    instance.path.parent.mkdir(parents=True, exist_ok=True)
    instance.path.write_text("content", encoding="utf-8")
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
