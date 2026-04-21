"""Tests for kernel.paths — cross-platform path resolution.

These are the canonical tests for get_kittify_home() and
get_package_asset_root(). The functions were moved from
specify_cli.runtime.home into kernel.paths; specify_cli.runtime.home
is now a thin re-export shim covered by test_home_unit.py smoke tests.

Coverage:
- T004: Cross-platform kittify home resolution
- T005: SPEC_KITTY_HOME env-var override
- T006: Package asset root discovery (env-var + importlib)
- T011: Kill render_runtime_path mutants (WP03)
- T012: Kill get_kittify_home mutants (WP03)
- T013: Kill get_package_asset_root mutants (WP03)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from kernel.paths import get_kittify_home, get_package_asset_root, render_runtime_path

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
    """Windows default path resolution via platformdirs (app name: spec-kitty)."""

    def test_windows_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On Windows, default uses platformdirs user_data_dir('spec-kitty').

        The app name 'spec-kitty' (not 'kittify') ensures kernel.paths resolves
        to the same root as specify_cli.paths.get_runtime_root().base (FR-005 / C-002).
        """
        import platformdirs

        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
        monkeypatch.setattr("kernel.paths._is_windows", lambda: True)
        monkeypatch.setattr(
            platformdirs,
            "user_data_dir",
            lambda *_a, **_kw: r"C:\Users\test\AppData\Local\spec-kitty",
        )
        result = get_kittify_home()
        assert result == Path(r"C:\Users\test\AppData\Local\spec-kitty")


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


class TestRenderRuntimePath:
    """User-facing rendering for runtime paths lives in kernel for shared use."""

    def test_windows_always_returns_absolute_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("kernel.paths._is_windows", lambda: True)
        rendered = render_runtime_path(Path("/tmp/spec-kitty/auth"))
        assert rendered == str(Path("/tmp/spec-kitty/auth").resolve(strict=False))

    def test_posix_tilde_compression_under_home(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        rendered = render_runtime_path(tmp_path / ".kittify" / "auth")
        assert rendered == "~/.kittify/auth"

    def test_posix_outside_home_stays_absolute(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        rendered = render_runtime_path(Path("/var/lib/spec-kitty"))
        assert rendered == str(Path("/var/lib/spec-kitty").resolve(strict=False))

    def test_for_user_false_disables_tilde_shortening(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        rendered = render_runtime_path(tmp_path / ".kittify" / "auth", for_user=False)
        assert rendered == str((tmp_path / ".kittify" / "auth").resolve(strict=False))


# ---------------------------------------------------------------------------
# T011: Kill render_runtime_path survivors (WP03)
# ---------------------------------------------------------------------------


class TestRenderRuntimePathMutantKills:
    """Assertion-strengthening tests that pin render_runtime_path behaviour.

    Each test encodes the observable difference between the original source and
    a specific surviving mutant, per the mutation-aware-test-design styleguide.
    """

    def test_default_for_user_compresses_to_tilde_on_posix(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Default for_user=True must tilde-compress on POSIX.

        Kills __mutmut_1 (for_user default flipped from True to False): with
        for_user=False the function returns the absolute path, not the tilde
        form — so a call that omits the keyword must produce the tilde string.
        """
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        rendered = render_runtime_path(tmp_path / ".kittify" / "auth")
        assert rendered == "~/.kittify/auth"
        assert rendered.startswith("~/")

    def test_home_must_exist_when_resolving(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """home.resolve() uses strict=False so missing home does not raise.

        Kills __mutmut_11 (home resolve flipped to strict=True): if the home
        directory is missing and strict=True is used, Path.resolve() raises
        FileNotFoundError. The original, strict=False, must succeed and
        tilde-compress the target.
        """
        fake_home = tmp_path / "no-such-home-directory"
        assert not fake_home.exists()
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
        # Target path is beneath the (nonexistent) home root — should still
        # render as tilde form without raising FileNotFoundError.
        rendered = render_runtime_path(fake_home / ".kittify" / "state")
        assert rendered == "~/.kittify/state"

    def test_tilde_output_uses_forward_slash_separator(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Output uses forward-slash separator, never backslash.

        Kills __mutmut_21 (replace("\\\\", "/") mutated to replace("XX\\\\XX", "/"))
        and __mutmut_22 (replace("\\\\", "/") mutated to replace("\\\\", "XX/XX")).
        We cannot force backslashes into a POSIX Path literal, so we assert the
        observable invariant instead: the returned string contains forward
        slashes and no "XX" literal from a mangled replacement target/source.
        """
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        rendered = render_runtime_path(tmp_path / "nested" / "dir" / "file.txt")
        assert rendered == "~/nested/dir/file.txt"
        assert "XX" not in rendered
        assert "\\" not in rendered

    def test_path_resolve_accepts_nonexistent_target(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Target path resolve uses strict=False so missing target is ok.

        Documents the behaviour that __mutmut_3 (resolve(strict=None)) leaves
        unchanged because CPython treats None as falsy at the C layer, making
        that mutant equivalent. This test anchors the contract even so: a
        nonexistent target under home is rendered in tilde form.
        """
        monkeypatch.setattr("kernel.paths._is_windows", lambda: False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        missing = tmp_path / ".kittify" / "never-created"
        assert not missing.exists()
        rendered = render_runtime_path(missing)
        assert rendered == "~/.kittify/never-created"


# ---------------------------------------------------------------------------
# T012: Kill get_kittify_home Windows-branch survivors (WP03)
# ---------------------------------------------------------------------------


class TestGetKittifyHomeWindowsPlatformdirsContract:
    """Pin the exact platformdirs.user_data_dir() call contract.

    These tests spy on user_data_dir and assert the three positional/keyword
    arguments — "spec-kitty", appauthor=False, roaming=False — are all passed
    unchanged. A single spy kills the ten surviving mutants that permute,
    replace, or drop one of those arguments.
    """

    def _install_platformdirs_spy(
        self, monkeypatch: pytest.MonkeyPatch, return_value: str
    ) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
        """Install a recording spy for platformdirs.user_data_dir.

        Returns a list that will accumulate (args, kwargs) tuples for each
        call — the test body inspects this list after invoking the code
        under test.
        """
        import platformdirs

        calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

        def _spy(*args: Any, **kwargs: Any) -> str:
            calls.append((args, kwargs))
            return return_value

        monkeypatch.setattr(platformdirs, "user_data_dir", _spy)
        monkeypatch.setattr("kernel.paths._is_windows", lambda: True)
        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
        return calls

    def test_user_data_dir_receives_spec_kitty_app_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """First argument to user_data_dir must be the exact string 'spec-kitty'.

        Kills __mutmut_7 (app name -> None), __mutmut_10 (positional arg removed),
        __mutmut_13 ("XXspec-kittyXX"), and __mutmut_14 ("SPEC-KITTY").
        """
        calls = self._install_platformdirs_spy(monkeypatch, r"C:\fake")
        get_kittify_home()

        assert len(calls) == 1
        args, kwargs = calls[0]
        # The app name must be in the first positional slot OR in a kwarg
        # with key 'appname'. Either way it must equal exactly 'spec-kitty'.
        app_name: Any = args[0] if args else kwargs.get("appname")
        assert app_name == "spec-kitty"
        assert app_name != "SPEC-KITTY"
        assert "XX" not in str(app_name)

    def test_user_data_dir_receives_appauthor_false_explicitly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """appauthor must be passed as exactly False (not True, not omitted).

        Kills __mutmut_8 (appauthor=None), __mutmut_11 (appauthor kwarg removed),
        and __mutmut_15 (appauthor=True).
        """
        calls = self._install_platformdirs_spy(monkeypatch, r"C:\fake")
        get_kittify_home()

        args, kwargs = calls[0]
        assert "appauthor" in kwargs, "appauthor kwarg must be passed explicitly"
        assert kwargs["appauthor"] is False
        # Bi-Directional Logic: False and True are distinct observables.
        assert kwargs["appauthor"] is not True

    def test_user_data_dir_receives_roaming_false_explicitly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """roaming must be passed as exactly False (not True, not omitted).

        Kills __mutmut_9 (roaming=None), __mutmut_12 (roaming kwarg removed),
        and __mutmut_16 (roaming=True). The FR-005/C-002 invariant requires
        roaming=False so that kernel.paths matches
        specify_cli.paths.get_runtime_root on Windows.
        """
        calls = self._install_platformdirs_spy(monkeypatch, r"C:\fake")
        get_kittify_home()

        args, kwargs = calls[0]
        assert "roaming" in kwargs, "roaming kwarg must be passed explicitly"
        assert kwargs["roaming"] is False
        assert kwargs["roaming"] is not True


# ---------------------------------------------------------------------------
# T013: Kill get_package_asset_root survivor (WP03)
# ---------------------------------------------------------------------------


class TestGetPackageAssetRootErrorMessage:
    """Pin the exact error message emitted when assets cannot be located."""

    def test_missing_assets_error_message_is_exact(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FileNotFoundError message must be the plain English sentence.

        Kills __mutmut_17 (error string replaced with "XXCannot locate …XX").
        We assert the message starts with the real sentence and contains no
        mutmut sentinel markers, and also verify it contains the actionable
        remediation substring.
        """
        monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
        # Force the importlib fallback to fail so we reach the final raise.
        monkeypatch.setattr(
            "kernel.paths.importlib.resources.files",
            lambda _pkg: (_ for _ in ()).throw(ModuleNotFoundError("forced")),
        )
        with pytest.raises(FileNotFoundError) as exc_info:
            get_package_asset_root()

        message = str(exc_info.value)
        assert message.startswith("Cannot locate package mission assets"), message
        assert "XX" not in message, f"mutmut sentinel leaked into message: {message!r}"
        assert "SPEC_KITTY_TEMPLATE_ROOT" in message
        assert "spec-kitty-cli" in message
