"""Unit tests for charter.asset_resolver — the doctrine-backed 5-tier gateway."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from charter.asset_resolver import (
    ResolutionResult,
    ResolutionTier,
    resolve_command,
    resolve_mission,
    resolve_template,
)


@pytest.fixture
def providers(tmp_path: Path) -> dict[str, MagicMock]:
    """Fresh mock providers per test. Return a dict for readable test assertions."""
    home = tmp_path / "home-kittify"
    home.mkdir()
    asset_root = tmp_path / "pkg-missions"
    asset_root.mkdir()
    return {
        "home": MagicMock(return_value=home),
        "asset_root": MagicMock(return_value=asset_root),
        "home_path": home,
        "asset_root_path": asset_root,
    }


def _write(path: Path, content: str = "stub") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestTierPrecedence:
    def test_override_tier_wins(self, tmp_path: Path, providers: dict[str, MagicMock]) -> None:
        override = _write(tmp_path / ".kittify" / "overrides" / "templates" / "spec.md")
        # Also put stubs at other tiers to prove OVERRIDE wins.
        _write(tmp_path / ".kittify" / "templates" / "spec.md")
        _write(providers["home_path"] / "missions" / "software-dev" / "templates" / "spec.md")
        _write(providers["asset_root_path"] / "software-dev" / "templates" / "spec.md")

        result = resolve_template(
            "spec.md", tmp_path,
            home_provider=providers["home"],
            asset_root_provider=providers["asset_root"],
        )

        assert result == ResolutionResult(path=override, tier=ResolutionTier.OVERRIDE, mission="software-dev")

    def test_legacy_tier_when_override_missing(
        self, tmp_path: Path, providers: dict[str, MagicMock]
    ) -> None:
        legacy = _write(tmp_path / ".kittify" / "templates" / "spec.md")

        result = resolve_template(
            "spec.md", tmp_path,
            home_provider=providers["home"],
            asset_root_provider=providers["asset_root"],
        )

        assert result.tier is ResolutionTier.LEGACY
        assert result.path == legacy

    def test_legacy_warn_hook_called_on_legacy_hit(
        self, tmp_path: Path, providers: dict[str, MagicMock]
    ) -> None:
        legacy = _write(tmp_path / ".kittify" / "command-templates" / "plan.md")
        hook = MagicMock()

        resolve_command(
            "plan.md", tmp_path,
            home_provider=providers["home"],
            asset_root_provider=providers["asset_root"],
            legacy_warn_hook=hook,
        )

        hook.assert_called_once_with(legacy)

    def test_legacy_warn_hook_not_called_when_override_wins(
        self, tmp_path: Path, providers: dict[str, MagicMock]
    ) -> None:
        _write(tmp_path / ".kittify" / "overrides" / "command-templates" / "plan.md")
        _write(tmp_path / ".kittify" / "command-templates" / "plan.md")
        hook = MagicMock()

        resolve_command(
            "plan.md", tmp_path,
            home_provider=providers["home"],
            asset_root_provider=providers["asset_root"],
            legacy_warn_hook=hook,
        )

        hook.assert_not_called()

    def test_global_mission_tier_uses_home_provider(
        self, tmp_path: Path, providers: dict[str, MagicMock]
    ) -> None:
        target = _write(
            providers["home_path"] / "missions" / "software-dev" / "templates" / "spec.md"
        )

        result = resolve_template(
            "spec.md", tmp_path,
            home_provider=providers["home"],
            asset_root_provider=providers["asset_root"],
        )

        assert result.tier is ResolutionTier.GLOBAL_MISSION
        assert result.path == target
        providers["home"].assert_called()

    def test_global_tier_non_mission_for_templates(
        self, tmp_path: Path, providers: dict[str, MagicMock]
    ) -> None:
        target = _write(providers["home_path"] / "templates" / "spec.md")

        result = resolve_template(
            "spec.md", tmp_path,
            home_provider=providers["home"],
            asset_root_provider=providers["asset_root"],
        )

        assert result.tier is ResolutionTier.GLOBAL
        assert result.path == target

    def test_package_default_uses_asset_root_provider(
        self, tmp_path: Path, providers: dict[str, MagicMock]
    ) -> None:
        target = _write(
            providers["asset_root_path"] / "software-dev" / "templates" / "spec.md"
        )

        result = resolve_template(
            "spec.md", tmp_path,
            home_provider=providers["home"],
            asset_root_provider=providers["asset_root"],
        )

        assert result.tier is ResolutionTier.PACKAGE_DEFAULT
        assert result.path == target
        providers["asset_root"].assert_called()

    def test_file_not_found_raises(self, tmp_path: Path, providers: dict[str, MagicMock]) -> None:
        with pytest.raises(FileNotFoundError) as exc_info:
            resolve_template(
                "nonexistent.md", tmp_path,
                home_provider=providers["home"],
                asset_root_provider=providers["asset_root"],
            )
        assert "nonexistent.md" in str(exc_info.value)
        assert "templates" in str(exc_info.value)


class TestProviderSeamContract:
    """Providers must be invoked per call — never cached at import time."""

    def test_home_provider_invoked_every_call(
        self, tmp_path: Path, providers: dict[str, MagicMock]
    ) -> None:
        _write(providers["home_path"] / "missions" / "software-dev" / "templates" / "a.md")
        _write(providers["home_path"] / "missions" / "software-dev" / "templates" / "b.md")

        resolve_template("a.md", tmp_path, home_provider=providers["home"],
                         asset_root_provider=providers["asset_root"])
        resolve_template("b.md", tmp_path, home_provider=providers["home"],
                         asset_root_provider=providers["asset_root"])

        assert providers["home"].call_count >= 2

    def test_asset_root_provider_invoked_every_call(
        self, tmp_path: Path, providers: dict[str, MagicMock]
    ) -> None:
        _write(providers["asset_root_path"] / "software-dev" / "templates" / "x.md")
        _write(providers["asset_root_path"] / "software-dev" / "templates" / "y.md")

        resolve_template("x.md", tmp_path, home_provider=providers["home"],
                         asset_root_provider=providers["asset_root"])
        resolve_template("y.md", tmp_path, home_provider=providers["home"],
                         asset_root_provider=providers["asset_root"])

        assert providers["asset_root"].call_count >= 2

    def test_home_provider_runtime_error_is_tolerated(
        self, tmp_path: Path, providers: dict[str, MagicMock]
    ) -> None:
        """If home_provider raises RuntimeError, resolution skips GLOBAL tiers gracefully."""
        providers["home"].side_effect = RuntimeError("no home")
        target = _write(
            providers["asset_root_path"] / "software-dev" / "templates" / "spec.md"
        )

        result = resolve_template(
            "spec.md", tmp_path,
            home_provider=providers["home"],
            asset_root_provider=providers["asset_root"],
        )

        assert result.tier is ResolutionTier.PACKAGE_DEFAULT
        assert result.path == target


class TestResolveMission:
    def test_override_wins(self, tmp_path: Path, providers: dict[str, MagicMock]) -> None:
        override = _write(
            tmp_path / ".kittify" / "overrides" / "missions" / "custom" / "mission.yaml"
        )
        result = resolve_mission(
            "custom", tmp_path,
            home_provider=providers["home"],
            asset_root_provider=providers["asset_root"],
        )
        assert result.tier is ResolutionTier.OVERRIDE
        assert result.path == override
        assert result.mission == "custom"

    def test_package_default(self, tmp_path: Path, providers: dict[str, MagicMock]) -> None:
        target = _write(providers["asset_root_path"] / "custom" / "mission.yaml")
        result = resolve_mission(
            "custom", tmp_path,
            home_provider=providers["home"],
            asset_root_provider=providers["asset_root"],
        )
        assert result.tier is ResolutionTier.PACKAGE_DEFAULT
        assert result.path == target

    def test_no_global_non_mission_tier_for_mission(
        self, tmp_path: Path, providers: dict[str, MagicMock]
    ) -> None:
        """resolve_mission has no GLOBAL tier — missions are inherently mission-scoped."""
        _write(providers["home_path"] / "mission.yaml")
        with pytest.raises(FileNotFoundError):
            resolve_mission(
                "custom", tmp_path,
                home_provider=providers["home"],
                asset_root_provider=providers["asset_root"],
            )

    def test_file_not_found_raises(self, tmp_path: Path, providers: dict[str, MagicMock]) -> None:
        with pytest.raises(FileNotFoundError) as exc_info:
            resolve_mission(
                "nope", tmp_path,
                home_provider=providers["home"],
                asset_root_provider=providers["asset_root"],
            )
        assert "nope" in str(exc_info.value)
