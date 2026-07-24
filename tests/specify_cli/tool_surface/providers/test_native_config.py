"""Unit tests for ``tool_surface.providers.native_config``."""

from __future__ import annotations

from pathlib import Path

from specify_cli.tool_surface.enums import ToolSurfaceKind
from specify_cli.tool_surface.providers.command_skills import (
    command_skill_definition,
)
from specify_cli.tool_surface.providers.native_config import (
    NativeConfigProvider,
    native_config_definition,
)
from specify_cli.tool_surface.providers.protocol import ReportingSurfaceProvider
from specify_cli.tool_surface.status import (
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_PRESENT,
)

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_provider_satisfies_reporting_protocol() -> None:
    provider = NativeConfigProvider()
    assert isinstance(provider, ReportingSurfaceProvider)
    assert provider.provider_key == "native_config"


def test_can_handle_native_config_only() -> None:
    provider = NativeConfigProvider()
    assert provider.can_handle(native_config_definition()) is True
    assert provider.can_handle(command_skill_definition()) is False


def test_definition_kind_is_native_config() -> None:
    assert native_config_definition().kind == ToolSurfaceKind.NATIVE_CONFIG


def test_expand_vibe_yields_config_instance(tmp_path: Path) -> None:
    provider = NativeConfigProvider()
    instances = provider.expand(native_config_definition(), "vibe", tmp_path)
    assert len(instances) == 1
    assert instances[0].path == tmp_path / ".vibe" / "config.toml"
    assert instances[0].owner == "vibe"


def test_expand_non_vibe_yields_research_gap(tmp_path: Path) -> None:
    provider = NativeConfigProvider()
    instances = provider.expand(native_config_definition(), "claude", tmp_path)
    assert len(instances) == 1
    status = provider.probe(instances[0])
    assert status.state == STATE_NOT_APPLICABLE
    assert status.findings[0].code == "research-gap-surface"
    assert status.findings[0].severity == "info"


def test_probe_missing_when_config_absent(tmp_path: Path) -> None:
    provider = NativeConfigProvider()
    instance = provider.expand(native_config_definition(), "vibe", tmp_path)[0]
    status = provider.probe(instance)
    assert status.state == STATE_MISSING
    assert status.findings[0].code == "native-config-missing"
    assert status.findings[0].repair_command is not None


def test_probe_missing_when_skill_path_absent(tmp_path: Path) -> None:
    vibe = tmp_path / ".vibe"
    vibe.mkdir()
    (vibe / "config.toml").write_text('other = "value"\n', encoding="utf-8")
    provider = NativeConfigProvider()
    instance = provider.expand(native_config_definition(), "vibe", tmp_path)[0]
    assert provider.probe(instance).state == STATE_MISSING


def test_probe_present_when_skill_path_listed(tmp_path: Path) -> None:
    vibe = tmp_path / ".vibe"
    vibe.mkdir()
    (vibe / "config.toml").write_text(
        'skill_paths = [".agents/skills"]\n', encoding="utf-8"
    )
    provider = NativeConfigProvider()
    instance = provider.expand(native_config_definition(), "vibe", tmp_path)[0]
    assert provider.probe(instance).state == STATE_PRESENT


def test_probe_present_when_skill_path_is_string(tmp_path: Path) -> None:
    vibe = tmp_path / ".vibe"
    vibe.mkdir()
    (vibe / "config.toml").write_text(
        'skill_paths = ".agents/skills"\n', encoding="utf-8"
    )
    provider = NativeConfigProvider()
    instance = provider.expand(native_config_definition(), "vibe", tmp_path)[0]
    assert provider.probe(instance).state == STATE_PRESENT


def test_probe_missing_on_invalid_toml(tmp_path: Path) -> None:
    vibe = tmp_path / ".vibe"
    vibe.mkdir()
    (vibe / "config.toml").write_text("not = valid = toml", encoding="utf-8")
    provider = NativeConfigProvider()
    instance = provider.expand(native_config_definition(), "vibe", tmp_path)[0]
    assert provider.probe(instance).state == STATE_MISSING


def test_repair_writes_skill_path(tmp_path: Path) -> None:
    provider = NativeConfigProvider()
    instance = provider.expand(native_config_definition(), "vibe", tmp_path)[0]
    missing = provider.probe(instance)
    assert missing.state == STATE_MISSING
    result = provider.repair(tmp_path, [missing])
    assert result.repaired
    assert not result.failed
    assert provider.probe(instance).state == STATE_PRESENT
    assert (tmp_path / ".vibe" / "config.toml").exists()


def test_repair_dry_run_writes_nothing(tmp_path: Path) -> None:
    provider = NativeConfigProvider()
    instance = provider.expand(native_config_definition(), "vibe", tmp_path)[0]
    status = provider.probe(instance)
    result = provider.repair(tmp_path, [status], dry_run=True)
    assert result.dry_run is True
    assert result.repaired
    assert not (tmp_path / ".vibe").exists()


def test_repair_skips_research_gap(tmp_path: Path) -> None:
    provider = NativeConfigProvider()
    instance = provider.expand(native_config_definition(), "claude", tmp_path)[0]
    status = provider.probe(instance)
    result = provider.repair(tmp_path, [status])
    assert result.repaired == ()
    assert result.skipped


def test_remove_is_noop(tmp_path: Path) -> None:
    provider = NativeConfigProvider()
    instance = provider.expand(native_config_definition(), "vibe", tmp_path)[0]
    assert provider.remove(instance) is False
