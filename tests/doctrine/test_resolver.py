"""Focused tests for doctrine-level asset resolution branches."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import doctrine.missions as missions_module
import doctrine.resolver as resolver_module
from doctrine.resolver import (
    ResolutionTier,
    _resolve_asset,
    _warn_legacy_asset,
    resolve_command,
    resolve_mission,
    resolve_template,
)

pytestmark = pytest.mark.fast


def _build_fake_repo(root: Path) -> SimpleNamespace:
    missions_root = root / "missions"
    mission_root = missions_root / "software-dev"
    (mission_root / "templates").mkdir(parents=True)
    (mission_root / "extras").mkdir(parents=True)
    (mission_root / "templates" / "spec-template.md").write_text("package template", encoding="utf-8")
    (mission_root / "command-plan.md").write_text("package command", encoding="utf-8")
    (mission_root / "mission.yaml").write_text("name: software-dev\n", encoding="utf-8")
    (mission_root / "extras" / "custom.txt").write_text("custom asset", encoding="utf-8")

    return SimpleNamespace(
        _missions_root=missions_root,
        _content_template_path=lambda mission, name: mission_root / "templates" / name,
        _command_template_path=lambda mission, name: mission_root / f"command-{name}.md",
        _mission_config_path=lambda mission: mission_root / "mission.yaml",
    )


def test_is_global_runtime_configured_detects_bootstrapped_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    (home / "cache").mkdir(parents=True)
    (home / "cache" / "version.lock").write_text("3.0.0\n", encoding="utf-8")

    monkeypatch.setattr(resolver_module, "get_kittify_home", lambda: home)

    assert resolver_module._is_global_runtime_configured() is True


def test_is_global_runtime_configured_handles_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_runtime_error() -> Path:
        raise RuntimeError("home unavailable")

    monkeypatch.setattr(resolver_module, "get_kittify_home", _raise_runtime_error)

    assert resolver_module._is_global_runtime_configured() is False


def test_warn_legacy_asset_emits_deprecation_warning_before_runtime_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resolver_module, "_is_global_runtime_configured", lambda: False)

    with pytest.deprecated_call():
        _warn_legacy_asset(Path("/tmp/spec-template.md"))


def test_warn_legacy_asset_emits_single_migrate_nudge_after_runtime_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(resolver_module, "_is_global_runtime_configured", lambda: True)
    resolver_module._reset_migrate_nudge()

    _warn_legacy_asset(Path("/tmp/spec-template.md"))
    _warn_legacy_asset(Path("/tmp/plan-template.md"))

    stderr = capsys.readouterr().err
    assert stderr.count("spec-kitty migrate") == 1


def test_resolve_template_and_command_use_package_default_when_global_home_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    fake_repo = _build_fake_repo(tmp_path / "package-root")

    def _raise_runtime_error() -> Path:
        raise RuntimeError("no global runtime")

    monkeypatch.setattr(resolver_module, "get_kittify_home", _raise_runtime_error)
    monkeypatch.setattr(missions_module.MissionTemplateRepository, "default", lambda: fake_repo)

    template = resolve_template("spec-template.md", project, mission="software-dev")
    command = resolve_command("plan.md", project, mission="software-dev")

    assert template.tier is ResolutionTier.PACKAGE_DEFAULT
    assert template.path.read_text(encoding="utf-8") == "package template"
    assert command.tier is ResolutionTier.PACKAGE_DEFAULT
    assert command.path.read_text(encoding="utf-8") == "package command"


def test_resolve_asset_unknown_subdir_uses_package_root_and_raises_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    fake_repo = _build_fake_repo(tmp_path / "package-root")

    def _raise_runtime_error() -> Path:
        raise RuntimeError("no global runtime")

    monkeypatch.setattr(resolver_module, "get_kittify_home", _raise_runtime_error)
    monkeypatch.setattr(missions_module.MissionTemplateRepository, "default", lambda: fake_repo)

    custom = _resolve_asset("custom.txt", "extras", project, mission="software-dev")
    assert custom.tier is ResolutionTier.PACKAGE_DEFAULT
    assert custom.path.read_text(encoding="utf-8") == "custom asset"

    (fake_repo._missions_root / "software-dev" / "extras" / "custom.txt").unlink()

    with pytest.raises(FileNotFoundError):
        _resolve_asset("custom.txt", "extras", project, mission="software-dev")


def test_resolve_mission_covers_all_resolution_tiers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    kittify = project / ".kittify"
    fake_home = tmp_path / "global-home"
    fake_repo = _build_fake_repo(tmp_path / "package-root")

    (kittify / "overrides" / "missions" / "software-dev").mkdir(parents=True)
    override = kittify / "overrides" / "missions" / "software-dev" / "mission.yaml"
    override.write_text("name: override\n", encoding="utf-8")

    monkeypatch.setattr(resolver_module, "get_kittify_home", lambda: fake_home)
    monkeypatch.setattr(missions_module.MissionTemplateRepository, "default", lambda: fake_repo)

    result = resolve_mission("software-dev", project)
    assert result.tier is ResolutionTier.OVERRIDE

    override.unlink()
    (kittify / "missions" / "software-dev").mkdir(parents=True)
    legacy = kittify / "missions" / "software-dev" / "mission.yaml"
    legacy.write_text("name: legacy\n", encoding="utf-8")

    result = resolve_mission("software-dev", project)
    assert result.tier is ResolutionTier.LEGACY

    legacy.unlink()
    (fake_home / "missions" / "software-dev").mkdir(parents=True)
    global_mission = fake_home / "missions" / "software-dev" / "mission.yaml"
    global_mission.write_text("name: global\n", encoding="utf-8")

    result = resolve_mission("software-dev", project)
    assert result.tier is ResolutionTier.GLOBAL_MISSION

    global_mission.unlink()
    result = resolve_mission("software-dev", project)
    assert result.tier is ResolutionTier.PACKAGE_DEFAULT

    monkeypatch.setattr(
        missions_module.MissionTemplateRepository,
        "default",
        lambda: SimpleNamespace(_mission_config_path=lambda mission: None),
    )
    with pytest.raises(FileNotFoundError):
        resolve_mission("software-dev", project)
