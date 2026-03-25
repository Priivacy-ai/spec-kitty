"""Tests for kernel.paths — cross-platform path resolution.

These are the canonical tests for get_kittify_home() and
get_package_asset_root(). The functions were moved from
specify_cli.runtime.home into kernel.paths; specify_cli.runtime.home
is now a thin re-export shim covered by test_home_unit.py smoke tests.

Coverage:
- T004: Cross-platform kittify home resolution
- T005: SPEC_KITTY_HOME env-var override
- T006: Package asset root discovery (env-var + importlib)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kernel.paths import get_kittify_home, get_package_asset_root

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# T004: get_kittify_home — cross-platform default resolution
# ---------------------------------------------------------------------------


class TestGetKittifyHomeUnix:
    """Unix (macOS/Linux) default path resolution."""

    def test_unix_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On Unix, default is ~/.kittify/."""
        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        result = get_kittify_home()
        assert result == Path.home() / ".kittify"

    def test_returns_path_object(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Return type is Path, not str."""
        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        assert isinstance(get_kittify_home(), Path)

    def test_returns_absolute_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Path is always absolute."""
        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        assert get_kittify_home().is_absolute()


class TestGetKittifyHomeWindows:
    """Windows default path resolution via platformdirs."""

    def test_windows_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On Windows, default uses platformdirs user_data_dir."""
        import platformdirs

        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
        monkeypatch.setattr("kernel.paths._is_windows", lambda: True)
        monkeypatch.setattr(
            platformdirs,
            "user_data_dir",
            lambda *_a, **_kw: r"C:\Users\test\AppData\Local\kittify",
        )
        result = get_kittify_home()
        assert result == Path(r"C:\Users\test\AppData\Local\kittify")


# ---------------------------------------------------------------------------
# T005: SPEC_KITTY_HOME env-var override
# ---------------------------------------------------------------------------


class TestSpecKittyHomeEnvOverride:
    """SPEC_KITTY_HOME environment variable overrides default path."""

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SPEC_KITTY_HOME overrides default on all platforms."""
        custom = str(tmp_path / "custom-kittify")
        monkeypatch.setenv("SPEC_KITTY_HOME", custom)
        assert get_kittify_home() == Path(custom)

    def test_env_override_on_windows(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SPEC_KITTY_HOME takes precedence even on Windows."""
        custom = str(tmp_path / "custom-kittify")
        monkeypatch.setenv("SPEC_KITTY_HOME", custom)
        monkeypatch.setattr("kernel.paths._is_windows", lambda: True)
        assert get_kittify_home() == Path(custom)

    def test_env_override_returns_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Env override returns a Path object."""
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
        assert isinstance(get_kittify_home(), Path)

    def test_empty_env_var_uses_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty SPEC_KITTY_HOME falls through to platform default."""
        monkeypatch.setenv("SPEC_KITTY_HOME", "")
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        # Empty string is falsy -> falls through
        assert get_kittify_home() == Path.home() / ".kittify"


# ---------------------------------------------------------------------------
# T006: get_package_asset_root — package asset discovery
# ---------------------------------------------------------------------------


class TestGetPackageAssetRoot:
    """Package asset discovery via SPEC_KITTY_TEMPLATE_ROOT and importlib."""

    def test_template_root_env_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SPEC_KITTY_TEMPLATE_ROOT overrides package discovery."""
        missions = tmp_path / "missions"
        missions.mkdir()
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(missions))
        assert get_package_asset_root() == missions

    def test_template_root_env_nonexistent_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SPEC_KITTY_TEMPLATE_ROOT with invalid path raises FileNotFoundError."""
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", "/nonexistent/path")
        with pytest.raises(FileNotFoundError, match="SPEC_KITTY_TEMPLATE_ROOT"):
            get_package_asset_root()

    def test_importlib_discovery(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls through to importlib.resources when env var not set."""
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        result = get_package_asset_root()
        assert result.is_dir()
        assert result.name == "missions"

    def test_returns_path_object(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Return type is Path."""
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        assert isinstance(get_package_asset_root(), Path)

    def test_returns_existing_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returned path must exist as a directory."""
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        assert get_package_asset_root().is_dir()

    def test_importlib_failure_raises_file_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raises FileNotFoundError when importlib discovery fails."""
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        monkeypatch.setattr(
            "kernel.paths.importlib.resources.files",
            lambda _pkg: type("Fake", (), {"__truediv__": lambda s, n: Path("/nonexistent")})(),
        )
        with pytest.raises(FileNotFoundError, match="Cannot locate package mission assets"):
            get_package_asset_root()

    def test_env_var_takes_precedence_over_importlib(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Env var is checked before importlib."""
        missions = tmp_path / "missions"
        missions.mkdir()
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(missions))
        # Even if importlib would fail, env var wins
        monkeypatch.setattr(
            "kernel.paths.importlib.resources.files",
            lambda _pkg: (_ for _ in ()).throw(ModuleNotFoundError("should not be called")),
        )
        assert get_package_asset_root() == missions
