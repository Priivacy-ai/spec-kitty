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

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


# Note: tier equality is asserted via ``.name == .name`` rather than ``is``
# or ``==``. Under pytest ``--import-mode=importlib`` combined with
# ``pytestarch`` (which walks ``src/`` and can load ``doctrine/resolver.py``
# under alternate module names), ``ResolutionTier`` can end up defined twice
# in-process with identical members but distinct class identities. Python
# enums' ``==`` delegates to ``is`` after a type check, so cross-class
# comparison returns False even when ``.name`` / ``.value`` match. Comparing
# ``.name`` verifies the semantic invariant these tests care about
# ("resolve_* returned a PACKAGE_DEFAULT tier") without coupling to which
# of the possibly-duplicated class objects the resolver implementation
# happened to reference.


def _build_fake_repo(root: Path) -> SimpleNamespace:
    missions_root = root / "missions"
    mission_root = missions_root / "software-dev"
    (mission_root / "templates").mkdir(parents=True)
    (mission_root / "extras").mkdir(parents=True)
    (mission_root / "templates" / "spec-template.md").write_text("package template", encoding="utf-8")
    (mission_root / "command-plan.md").write_text("package command", encoding="utf-8")
    (mission_root / "mission.yaml").write_text("name: software-dev\n", encoding="utf-8")
    (mission_root / "extras" / "custom.txt").write_text("custom asset", encoding="utf-8")

    def _content_template_path(mission: str | None, name: str) -> Path:
        if mission is None:
            raise FileNotFoundError("mission arg is None")
        return mission_root / "templates" / name

    def _command_template_path(mission: str | None, name: str) -> Path:
        if mission is None:
            raise FileNotFoundError("mission arg is None")
        return mission_root / f"command-{name}.md"

    def _mission_config_path(mission: str | None) -> Path:
        if mission is None:
            raise FileNotFoundError("mission arg is None")
        return mission_root / "mission.yaml"

    return SimpleNamespace(
        _missions_root=missions_root,
        _content_template_path=_content_template_path,
        _command_template_path=_command_template_path,
        _mission_config_path=_mission_config_path,
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

    assert template.tier.name == ResolutionTier.PACKAGE_DEFAULT.name
    assert template.path.read_text(encoding="utf-8") == "package template"
    assert command.tier.name == ResolutionTier.PACKAGE_DEFAULT.name
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
    assert custom.tier.name == ResolutionTier.PACKAGE_DEFAULT.name
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
    assert result.tier.name == ResolutionTier.OVERRIDE.name
    assert result.path == override
    assert result.mission == "software-dev"

    override.unlink()
    (kittify / "missions" / "software-dev").mkdir(parents=True)
    legacy = kittify / "missions" / "software-dev" / "mission.yaml"
    legacy.write_text("name: legacy\n", encoding="utf-8")

    monkeypatch.setattr(resolver_module, "_is_global_runtime_configured", lambda: False)
    with pytest.warns(DeprecationWarning, match="mission.yaml"):
        result = resolve_mission("software-dev", project)
    assert result.tier.name == ResolutionTier.LEGACY.name
    assert result.path == legacy
    assert result.mission == "software-dev"

    legacy.unlink()
    (fake_home / "missions" / "software-dev").mkdir(parents=True)
    global_mission = fake_home / "missions" / "software-dev" / "mission.yaml"
    global_mission.write_text("name: global\n", encoding="utf-8")

    result = resolve_mission("software-dev", project)
    assert result.tier.name == ResolutionTier.GLOBAL_MISSION.name
    assert result.path == global_mission
    assert result.mission == "software-dev"

    global_mission.unlink()
    result = resolve_mission("software-dev", project)
    assert result.tier.name == ResolutionTier.PACKAGE_DEFAULT.name
    assert result.path is not None
    assert result.mission == "software-dev"

    monkeypatch.setattr(
        missions_module.MissionTemplateRepository,
        "default",
        lambda: SimpleNamespace(_mission_config_path=lambda mission: None),
    )
    with pytest.raises(FileNotFoundError):
        resolve_mission("software-dev", project)


# ---------------------------------------------------------------------------
# T017 – _resolve_asset tier precedence with full field assertions
# ---------------------------------------------------------------------------


def test_resolve_asset_tier1_override_asserts_path_tier_mission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tier-1 override result has correct path, tier, and mission."""
    project = tmp_path / "project"
    kittify = project / ".kittify"
    (kittify / "overrides" / "templates").mkdir(parents=True)
    asset = kittify / "overrides" / "templates" / "spec-template.md"
    asset.write_text("override content", encoding="utf-8")

    monkeypatch.setattr(resolver_module, "get_kittify_home", lambda: tmp_path / "no-home")

    result = _resolve_asset("spec-template.md", "templates", project, mission="docs")

    assert result.tier.name == ResolutionTier.OVERRIDE.name
    assert result.path == asset
    assert result.mission == "docs"


def test_resolve_asset_tier2_legacy_asserts_path_tier_mission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tier-2 legacy result has correct path, tier, mission; warning names the path."""
    project = tmp_path / "project"
    kittify = project / ".kittify"
    (kittify / "templates").mkdir(parents=True)
    asset = kittify / "templates" / "spec-template.md"
    asset.write_text("legacy content", encoding="utf-8")

    monkeypatch.setattr(resolver_module, "_is_global_runtime_configured", lambda: False)
    monkeypatch.setattr(resolver_module, "get_kittify_home", lambda: tmp_path / "no-home")

    with pytest.warns(DeprecationWarning, match="spec-template.md"):
        result = _resolve_asset("spec-template.md", "templates", project, mission="docs")

    assert result.tier.name == ResolutionTier.LEGACY.name
    assert result.path == asset
    assert result.mission == "docs"


def test_resolve_asset_tier3_global_mission_asserts_path_tier_mission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tier-3 global-mission result has correct path, tier, and mission."""
    project = tmp_path / "project"
    project.mkdir()
    fake_home = tmp_path / "global-home"
    (fake_home / "missions" / "docs" / "templates").mkdir(parents=True)
    asset = fake_home / "missions" / "docs" / "templates" / "spec-template.md"
    asset.write_text("global-mission content", encoding="utf-8")

    monkeypatch.setattr(resolver_module, "get_kittify_home", lambda: fake_home)

    result = _resolve_asset("spec-template.md", "templates", project, mission="docs")

    assert result.tier.name == ResolutionTier.GLOBAL_MISSION.name
    assert result.path == asset
    assert result.mission == "docs"


def test_resolve_asset_tier4_global_asserts_path_tier_mission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tier-4 global result has correct path, tier, and mission."""
    project = tmp_path / "project"
    project.mkdir()
    fake_home = tmp_path / "global-home"
    (fake_home / "templates").mkdir(parents=True)
    asset = fake_home / "templates" / "spec-template.md"
    asset.write_text("global content", encoding="utf-8")

    monkeypatch.setattr(resolver_module, "get_kittify_home", lambda: fake_home)

    result = _resolve_asset("spec-template.md", "templates", project, mission="docs")

    assert result.tier.name == ResolutionTier.GLOBAL.name
    assert result.path == asset
    assert result.mission == "docs"


def test_resolve_asset_default_mission_is_software_dev(
    tmp_path: Path,
) -> None:
    """Calling _resolve_asset without explicit mission defaults to software-dev."""
    project = tmp_path / "project"
    kittify = project / ".kittify"
    (kittify / "overrides" / "templates").mkdir(parents=True)
    (kittify / "overrides" / "templates" / "x.md").write_text("x", encoding="utf-8")

    result = _resolve_asset("x.md", "templates", project)

    assert result.mission == "software-dev"


# ---------------------------------------------------------------------------
# T018 – _warn_legacy_asset message content and _reset_migrate_nudge exact value
# ---------------------------------------------------------------------------


def test_warn_legacy_asset_message_contains_path_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deprecation warning message contains the actual path text."""
    monkeypatch.setattr(resolver_module, "_is_global_runtime_configured", lambda: False)

    with pytest.warns(DeprecationWarning, match="spec-template.md"):
        _warn_legacy_asset(Path("/tmp/spec-template.md"))


def test_reset_migrate_nudge_allows_nudge_to_fire_again(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """After _reset_migrate_nudge, calling _emit_migrate_nudge emits a second nudge."""
    monkeypatch.setattr(resolver_module, "get_kittify_home", lambda: Path("/tmp/fake-home"))
    resolver_module._emit_migrate_nudge()
    capsys.readouterr()  # consume the first nudge
    resolver_module._reset_migrate_nudge()

    resolver_module._emit_migrate_nudge()

    stderr = capsys.readouterr().err
    assert "spec-kitty migrate" in stderr


def test_emit_migrate_nudge_message_starts_with_note(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Nudge message begins with 'Note:' (case-sensitive)."""
    monkeypatch.setattr(resolver_module, "get_kittify_home", lambda: Path("/tmp/fake-home"))
    resolver_module._reset_migrate_nudge()

    resolver_module._emit_migrate_nudge()

    stderr = capsys.readouterr().err
    assert "Note:" in stderr


# ---------------------------------------------------------------------------
# T019 – resolve_template / resolve_command default mission and passthrough
# ---------------------------------------------------------------------------


def test_resolve_template_default_mission_is_software_dev(
    tmp_path: Path,
) -> None:
    """resolve_template default mission is 'software-dev'."""
    project = tmp_path / "project"
    kittify = project / ".kittify"
    (kittify / "overrides" / "templates").mkdir(parents=True)
    (kittify / "overrides" / "templates" / "t.md").write_text("t", encoding="utf-8")

    result = resolve_template("t.md", project)

    assert result.mission == "software-dev"


def test_resolve_template_passes_mission_to_resolve_asset(
    tmp_path: Path,
) -> None:
    """resolve_template passes the mission argument through to _resolve_asset."""
    project = tmp_path / "project"
    kittify = project / ".kittify"
    (kittify / "overrides" / "templates").mkdir(parents=True)
    (kittify / "overrides" / "templates" / "t.md").write_text("t", encoding="utf-8")

    result = resolve_template("t.md", project, mission="docs")

    assert result.mission == "docs"


def test_resolve_command_default_mission_is_software_dev(
    tmp_path: Path,
) -> None:
    """resolve_command default mission is 'software-dev'."""
    project = tmp_path / "project"
    kittify = project / ".kittify"
    (kittify / "overrides" / "command-templates").mkdir(parents=True)
    (kittify / "overrides" / "command-templates" / "plan.md").write_text("p", encoding="utf-8")

    result = resolve_command("plan.md", project)

    assert result.mission == "software-dev"


def test_resolve_command_passes_mission_to_resolve_asset(
    tmp_path: Path,
) -> None:
    """resolve_command passes the mission argument through to _resolve_asset."""
    project = tmp_path / "project"
    kittify = project / ".kittify"
    (kittify / "overrides" / "command-templates").mkdir(parents=True)
    (kittify / "overrides" / "command-templates" / "plan.md").write_text("p", encoding="utf-8")

    result = resolve_command("plan.md", project, mission="docs")

    assert result.mission == "docs"


def test_resolve_template_and_command_package_tier_assert_path_and_mission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Package-tier results for resolve_template and resolve_command include path and mission."""
    project = tmp_path / "project"
    project.mkdir()
    fake_repo = _build_fake_repo(tmp_path / "package-root")

    monkeypatch.setattr(resolver_module, "get_kittify_home", lambda: tmp_path / "no-home")
    monkeypatch.setattr(missions_module.MissionTemplateRepository, "default", lambda: fake_repo)

    template = resolve_template("spec-template.md", project, mission="software-dev")
    command = resolve_command("plan.md", project, mission="software-dev")

    assert template.tier.name == ResolutionTier.PACKAGE_DEFAULT.name
    assert template.path is not None
    assert template.mission == "software-dev"
    assert command.tier.name == ResolutionTier.PACKAGE_DEFAULT.name
    assert command.path is not None
    assert command.mission == "software-dev"
