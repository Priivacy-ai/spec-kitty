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
    """Windows default path resolution via platformdirs."""

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
        missions.mkdir()
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(missions))
        result = get_package_asset_root()
        assert result == missions

    def test_template_root_env_nonexistent_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SPEC_KITTY_TEMPLATE_ROOT with invalid path raises FileNotFoundError."""
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", "/nonexistent/path")
        with pytest.raises(FileNotFoundError, match="SPEC_KITTY_TEMPLATE_ROOT"):
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
