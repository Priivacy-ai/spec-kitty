"""Tests for specify_cli.runtime.home — cross-platform path resolution.

Covers:
- T004: Cross-platform path resolution tests (G6, 1A-08)
- T005: SPEC_KITTY_HOME env var override tests (1A-09)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.runtime.home import get_kittify_home, get_package_asset_root


# ---------------------------------------------------------------------------
# T004: Cross-platform path resolution tests
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit, pytest.mark.fast]

class TestGetKittifyHomeUnix:
    """Unix (macOS/Linux) default path resolution."""

    def test_unix_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On Unix, default is ~/.kittify/ (1A-08)."""
        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
        monkeypatch.setattr("specify_cli.runtime.home._is_windows", lambda: False)
        result = get_kittify_home()
        assert result == Path.home() / ".kittify"

    def test_returns_path_object(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Return type is Path, not str."""
        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
        monkeypatch.setattr("specify_cli.runtime.home._is_windows", lambda: False)
        result = get_kittify_home()
        assert isinstance(result, Path)

    def test_returns_absolute_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Path is always absolute."""
        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
        monkeypatch.setattr("specify_cli.runtime.home._is_windows", lambda: False)
        result = get_kittify_home()
        assert result.is_absolute()


class TestGetKittifyHomeWindows:
    """Windows default path resolution.

    As of DRIFT-3 in the Windows Compatibility Hardening mission,
    ``get_kittify_home()`` on Windows delegates to
    ``specify_cli.paths.get_runtime_root().base`` rather than hitting
    ``platformdirs.user_data_dir`` directly. The monkeypatch-based simulation
    that worked when the implementation was a thin platformdirs wrapper no
    longer drives the code path reliably on non-Windows runners, so this test
    must run on the real ``windows-latest`` CI job.
    """

    @pytest.mark.windows_ci
    def test_windows_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On Windows, default uses platformdirs user_data_dir (1A-08)."""
        import platformdirs

        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
        monkeypatch.setattr("specify_cli.runtime.home._is_windows", lambda: True)
        monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_args, **_kwargs: (
            r"C:\Users\test\AppData\Local\kittify"
        ))
        result = get_kittify_home()
        assert result == Path(r"C:\Users\test\AppData\Local\kittify")


# ---------------------------------------------------------------------------
# T005: SPEC_KITTY_HOME env var override tests
# ---------------------------------------------------------------------------


class TestSpecKittyHomeEnvOverride:
    """SPEC_KITTY_HOME environment variable overrides default path."""

    def test_env_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """SPEC_KITTY_HOME overrides default on all platforms (1A-09)."""
        custom_path = str(tmp_path / "custom-kittify")
        monkeypatch.setenv("SPEC_KITTY_HOME", custom_path)
        result = get_kittify_home()
        assert result == Path(custom_path)

    def test_env_override_on_windows(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """SPEC_KITTY_HOME takes precedence even on Windows (1A-09)."""
        custom_path = str(tmp_path / "custom-kittify")
        monkeypatch.setenv("SPEC_KITTY_HOME", custom_path)
        monkeypatch.setattr("specify_cli.runtime.home._is_windows", lambda: True)
        result = get_kittify_home()
        assert result == Path(custom_path)  # env var wins over platformdirs

    def test_env_override_returns_path(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Env override returns a Path object."""
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
        result = get_kittify_home()
        assert isinstance(result, Path)

    def test_empty_env_var_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty SPEC_KITTY_HOME falls through to platform default."""
        monkeypatch.setenv("SPEC_KITTY_HOME", "")
        monkeypatch.setattr("specify_cli.runtime.home._is_windows", lambda: False)
        result = get_kittify_home()
        # Empty string is falsy, so should fall through
        assert result == Path.home() / ".kittify"


# ---------------------------------------------------------------------------
# T005: get_package_asset_root() tests
# ---------------------------------------------------------------------------


class TestGetPackageAssetRoot:
    """Package asset discovery via SPEC_KITTY_TEMPLATE_ROOT and importlib."""

    def test_template_root_env_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """SPEC_KITTY_TEMPLATE_ROOT overrides package discovery."""
        missions = tmp_path / "missions"
        templates = missions / "software-dev" / "templates"
        templates.mkdir(parents=True)
        (templates / "plan-template.md").write_text("# Plan\n", encoding="utf-8")
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(missions))
        result = get_package_asset_root()
        assert result == missions

    def test_template_root_checkout_root_normalizes_to_doctrine_missions(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A checkout root env var resolves to src/doctrine/missions."""
        checkout = tmp_path / "spec-kitty"
        missions = checkout / "src" / "doctrine" / "missions"
        templates = missions / "software-dev" / "templates"
        templates.mkdir(parents=True)
        (templates / "plan-template.md").write_text("# Plan\n", encoding="utf-8")

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(checkout))

        assert get_package_asset_root() == missions

    def test_template_root_direct_legacy_missions_remaps_to_sibling_doctrine(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A direct stale specify_cli missions root resolves to doctrine assets."""
        checkout = tmp_path / "spec-kitty"
        stale_missions = checkout / "src" / "specify_cli" / "missions"
        stale_software_dev = stale_missions / "software-dev"
        stale_software_dev.mkdir(parents=True)
        (stale_software_dev / "mission.yaml").write_text("name: software-dev\n", encoding="utf-8")

        doctrine_missions = checkout / "src" / "doctrine" / "missions"
        templates = doctrine_missions / "software-dev" / "templates"
        templates.mkdir(parents=True)
        (templates / "plan-template.md").write_text("# Plan\n", encoding="utf-8")

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(stale_missions))

        assert get_package_asset_root() == doctrine_missions

    def test_template_root_checkout_root_falls_back_to_legacy_specify_cli_missions(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A legacy checkout without doctrine assets still resolves."""
        checkout = tmp_path / "spec-kitty"
        missions = checkout / "src" / "specify_cli" / "missions"
        templates = missions / "software-dev" / "templates"
        templates.mkdir(parents=True)
        (templates / "plan-template.md").write_text("# Plan\n", encoding="utf-8")

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(checkout))

        assert get_package_asset_root() == missions

    def test_template_root_legacy_package_asset_root_with_command_templates(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A direct package asset root with command templates remains valid."""
        package_assets = tmp_path / "pkg"
        command_templates = package_assets / "software-dev" / "command-templates"
        command_templates.mkdir(parents=True)
        (command_templates / "implement.md").write_text("# Implement\n", encoding="utf-8")

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(package_assets))

        assert get_package_asset_root() == package_assets

    def test_template_root_legacy_package_asset_root_with_mission_yaml(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A direct package asset root with only mission YAML is incomplete."""
        package_assets = tmp_path / "pkg"
        mission = package_assets / "software-dev"
        mission.mkdir(parents=True)
        (mission / "mission.yaml").write_text("name: software-dev\n", encoding="utf-8")

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(package_assets))

        with pytest.raises(FileNotFoundError, match="does not contain mission assets"):
            get_package_asset_root()

    def test_template_root_env_nonexistent_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SPEC_KITTY_TEMPLATE_ROOT with invalid path raises FileNotFoundError."""
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", "/nonexistent/path")
        with pytest.raises(FileNotFoundError, match="SPEC_KITTY_TEMPLATE_ROOT"):
            get_package_asset_root()

    def test_template_root_existing_invalid_dir_raises(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """SPEC_KITTY_TEMPLATE_ROOT must contain recognizable mission assets."""
        empty_root = tmp_path / "empty"
        empty_root.mkdir()

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(empty_root))

        with pytest.raises(FileNotFoundError, match="does not contain mission assets"):
            get_package_asset_root()

    def test_importlib_discovery(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls through to importlib.resources when env var not set."""
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        # Should find missions via importlib or dev layout
        result = get_package_asset_root()
        assert result.is_dir()
        assert result.name == "missions"

    def test_returns_path_object(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Return type is Path."""
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        result = get_package_asset_root()
        assert isinstance(result, Path)

    def test_returns_existing_directory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returned path must exist as a directory."""
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        result = get_package_asset_root()
        assert result.is_dir()

    def test_delegates_fail_closed_to_kernel_authority(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fail-closed delegation (retargeted C-007 seam).

        Replaces the retired ``importlib.resources``/dev-layout fallback seam:
        after IC-01 ``specify_cli.runtime.home.get_package_asset_root`` is a
        thin delegate to the single kernel authority
        (``kernel.paths.get_package_asset_root``), which drops the legacy
        ``specify_cli/missions`` importlib and dev-root fallbacks (DR-2). This
        forces the kernel resolution primitive to fail and asserts the delegate
        surfaces the closed ``FileNotFoundError`` rather than falling through.
        """
        from pathlib import PurePosixPath

        from kernel.sibling_paths import SiblingPathNotFound

        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        monkeypatch.delenv("SPEC_KITTY_PACKS_ROOT", raising=False)

        def _raise(**_kwargs: object) -> Path:
            raise SiblingPathNotFound(PurePosixPath("missions"), Path("/nonexistent"))

        monkeypatch.setattr("kernel.paths.resolve_installed_sibling", _raise)
        with pytest.raises(FileNotFoundError, match="Cannot locate package mission assets"):
            get_package_asset_root()


class TestGetPackageAssetRootPacksRoot:
    """SPEC_KITTY_PACKS_ROOT relocates the collapsed home door (DR-1; C-R2/C-R3/C-R4).

    After IC-01 ``specify_cli.runtime.home.get_package_asset_root`` delegates to
    the single kernel authority, so the same PACKS_ROOT relocation, fail-closed,
    and both-vars-precedence contracts hold through this compatibility surface.
    """

    def test_packs_root_relocates_the_door(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A PACKS_ROOT with ``built-in/missions`` present resolves under it."""
        packs_root = tmp_path / "packs-root"
        missions = packs_root / "built-in" / "missions"
        missions.mkdir(parents=True)
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        monkeypatch.setenv("SPEC_KITTY_PACKS_ROOT", str(packs_root))

        assert get_package_asset_root() == missions

    def test_packs_root_without_missions_tree_fails_closed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A PACKS_ROOT whose ``built-in`` has no ``missions`` leaf raises, no fall-through."""
        packs_root = tmp_path / "packs-root"
        (packs_root / "built-in").mkdir(parents=True)
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        monkeypatch.setenv("SPEC_KITTY_PACKS_ROOT", str(packs_root))

        with pytest.raises(FileNotFoundError):
            get_package_asset_root()

    def test_packs_root_wins_over_template_root(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """With BOTH env vars set, PACKS_ROOT governs pack-root location (C-R3)."""
        packs_root = tmp_path / "packs-root"
        packs_missions = packs_root / "built-in" / "missions"
        packs_missions.mkdir(parents=True)

        template_root = tmp_path / "template-root"
        template_templates = template_root / "software-dev" / "templates"
        template_templates.mkdir(parents=True)
        (template_templates / "plan-template.md").write_text("# Plan\n", encoding="utf-8")

        monkeypatch.setenv("SPEC_KITTY_PACKS_ROOT", str(packs_root))
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(template_root))

        assert get_package_asset_root() == packs_missions
