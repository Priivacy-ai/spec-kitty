"""Unit tests for detect_install_method (T013 — install-method branch coverage).

Each test forces exactly one branch of the detection chain and asserts that
the correct InstallMethod is returned.  All I/O is faked via injectable
*executable* and *distribution_loader* arguments so no OS state is required.
"""

from __future__ import annotations

import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.compat._detect.install_method import InstallMethod, detect_install_method

# Module path prefix for patching helpers inside install_method.py
_MOD = "specify_cli.compat._detect.install_method"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dist(installer: str | None = None, location: str | None = None) -> Any:
    """Return a mock Distribution object."""
    dist = MagicMock()
    dist.read_text.return_value = installer
    if location is not None:
        # Provide a realistic _path so _get_distribution_location can resolve.
        dist._path = Path(location) / "spec_kitty_cli-0.1.dist-info"
    else:
        dist._path = None
        dist.files = []
    return dist


def _loader_returning(installer: str | None, location: str | None = None):
    """Return a distribution_loader callable that yields a mock dist."""

    def _load(package_name: str) -> Any:  # noqa: ARG001
        return _make_dist(installer=installer, location=location)

    return _load


def _raising_loader(exc: Exception):
    """Return a distribution_loader callable that always raises *exc*."""

    def _load(package_name: str) -> Any:  # noqa: ARG001
        raise exc

    return _load


@contextmanager
def _no_source() -> Generator[None, None, None]:
    """Context manager that suppresses the SOURCE branch.

    Since tests run inside the spec-kitty source tree, _is_source_install()
    returns True unless we suppress it.  Wrap non-SOURCE branch tests with
    this to prevent the SOURCE branch from shadowing the branch under test.
    """
    with patch(f"{_MOD}._is_source_install", return_value=False):
        yield


# ---------------------------------------------------------------------------
# Branch 1 — SOURCE
# ---------------------------------------------------------------------------


class TestSourceBranch:
    def test_source_detected_when_package_file_under_cwd_and_pyproject_exists(self, tmp_path: Path) -> None:
        """If specify_cli.__file__ is under cwd and pyproject.toml exists → SOURCE."""
        pkg_dir = tmp_path / "src" / "specify_cli"
        pkg_dir.mkdir(parents=True)
        (tmp_path / "pyproject.toml").write_text("[build-system]\n")

        fake_module = MagicMock()
        fake_module.__file__ = str(pkg_dir / "__init__.py")

        with (
            patch("specify_cli.compat._detect.install_method.Path.cwd", return_value=tmp_path),
            patch.dict("sys.modules", {"specify_cli": fake_module}),
        ):
            result = detect_install_method(
                executable="/usr/local/bin/python3",
                distribution_loader=_loader_returning(None),
            )
        assert result == InstallMethod.SOURCE

    def test_source_not_detected_when_no_pyproject(self, tmp_path: Path) -> None:
        """No pyproject.toml → SOURCE branch does not match."""
        pkg_dir = tmp_path / "src" / "specify_cli"
        pkg_dir.mkdir(parents=True)

        fake_module = MagicMock()
        fake_module.__file__ = str(pkg_dir / "__init__.py")

        with (
            patch("specify_cli.compat._detect.install_method.Path.cwd", return_value=tmp_path),
            patch.dict("sys.modules", {"specify_cli": fake_module}),
        ):
            result = detect_install_method(
                executable="/not/pipx/not/brew",
                distribution_loader=_loader_returning(None),
            )
        assert result != InstallMethod.SOURCE


# ---------------------------------------------------------------------------
# Branch 2 — PIPX
# ---------------------------------------------------------------------------


class TestPipxBranch:
    def test_pipx_detected_via_local_pipx_venvs(self) -> None:
        home = Path.home()
        executable = str(home / ".local" / "pipx" / "venvs" / "spec-kitty" / "bin" / "python")
        with _no_source():
            result = detect_install_method(
                executable=executable,
                distribution_loader=_loader_returning(None),
            )
        assert result == InstallMethod.PIPX

    def test_pipx_detected_via_pattern_match(self) -> None:
        executable = "/some/path/pipx/venvs/spec-kitty-1.2.3/bin/python"
        with _no_source():
            result = detect_install_method(
                executable=executable,
                distribution_loader=_loader_returning(None),
            )
        assert result == InstallMethod.PIPX

    def test_pipx_not_detected_for_regular_path(self) -> None:
        with _no_source():
            result = detect_install_method(
                executable="/usr/bin/python3",
                distribution_loader=_loader_returning(None),
            )
        assert result != InstallMethod.PIPX


# ---------------------------------------------------------------------------
# Branch 3 — BREW
# ---------------------------------------------------------------------------


class TestBrewBranch:
    def test_brew_detected_via_opt_homebrew(self) -> None:
        executable = "/opt/homebrew/Cellar/python/3.12.1/bin/python3"
        with _no_source():
            result = detect_install_method(
                executable=executable,
                distribution_loader=_loader_returning(None),
            )
        assert result == InstallMethod.BREW

    def test_brew_detected_via_usr_local_cellar(self) -> None:
        executable = "/usr/local/Cellar/python@3.12/3.12.1/bin/python3"
        with _no_source():
            result = detect_install_method(
                executable=executable,
                distribution_loader=_loader_returning(None),
            )
        assert result == InstallMethod.BREW

    def test_brew_detected_via_usr_local_opt(self) -> None:
        executable = "/usr/local/opt/python@3.12/bin/python3"
        with _no_source():
            result = detect_install_method(
                executable=executable,
                distribution_loader=_loader_returning(None),
            )
        assert result == InstallMethod.BREW

    def test_brew_detected_via_dynamic_prefix(self) -> None:
        """Brew prefix resolved by subprocess → BREW."""
        executable = "/opt/custom-brew/Cellar/python@3.12/3.12.1/bin/python3"

        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = b"/opt/custom-brew\n"

        with _no_source(), patch("subprocess.run", return_value=fake_result):
            result = detect_install_method(
                executable=executable,
                distribution_loader=_loader_returning(None),
            )
        assert result == InstallMethod.BREW

    def test_brew_subprocess_timeout_falls_through(self) -> None:
        """TimeoutExpired from brew --prefix → fall through, no crash."""
        executable = "/some/other/path/bin/python3"

        with (
            _no_source(),
            patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["brew", "--prefix"], timeout=1.0),
            ),
        ):
            result = detect_install_method(
                executable=executable,
                distribution_loader=_loader_returning(None),
            )
        # Should not crash; may fall through to UNKNOWN or PIP_SYSTEM depending on
        # installer text.
        assert isinstance(result, InstallMethod)
        assert result != InstallMethod.BREW


# ---------------------------------------------------------------------------
# Branch 4 — SYSTEM_PACKAGE
# ---------------------------------------------------------------------------


class TestSystemPackageBranch:
    @pytest.mark.parametrize("installer", ["apt", "dnf", "pacman", "yum", "zypper"])
    def test_system_package_detected_for_system_installers(self, installer: str) -> None:
        with _no_source():
            result = detect_install_method(
                executable="/usr/bin/python3",
                distribution_loader=_loader_returning(installer),
            )
        assert result == InstallMethod.SYSTEM_PACKAGE

    def test_system_package_not_detected_for_non_usr_bin(self) -> None:
        with _no_source():
            result = detect_install_method(
                executable="/opt/homebrew/bin/python3",
                distribution_loader=_loader_returning("apt"),
            )
        # Homebrew branch fires first.
        assert result == InstallMethod.BREW

    def test_system_package_not_detected_for_pip_installer(self) -> None:
        with _no_source():
            result = detect_install_method(
                executable="/usr/bin/python3",
                distribution_loader=_loader_returning("pip"),
            )
        # pip installer — not a system package.
        assert result in {InstallMethod.PIP_USER, InstallMethod.PIP_SYSTEM}


# ---------------------------------------------------------------------------
# Branch 5 & 6 — PIP_USER / PIP_SYSTEM
# ---------------------------------------------------------------------------


class TestPipBranches:
    def test_pip_user_detected_when_dist_under_user_site(self, tmp_path: Path) -> None:
        user_site = str(tmp_path / "user_site")
        dist_location = user_site

        with _no_source(), patch("site.getusersitepackages", return_value=user_site):
            result = detect_install_method(
                executable="/usr/local/bin/python3",
                distribution_loader=_loader_returning("pip", dist_location),
            )
        assert result == InstallMethod.PIP_USER

    def test_pip_system_detected_when_dist_not_under_user_site(self, tmp_path: Path) -> None:
        user_site = str(tmp_path / "user_site")
        dist_location = str(tmp_path / "system_site")

        with _no_source(), patch("site.getusersitepackages", return_value=user_site):
            result = detect_install_method(
                executable="/usr/local/bin/python3",
                distribution_loader=_loader_returning("pip", dist_location),
            )
        assert result == InstallMethod.PIP_SYSTEM


# ---------------------------------------------------------------------------
# Fallback — UNKNOWN
# ---------------------------------------------------------------------------


class TestUnknownFallback:
    def test_unknown_when_no_branch_matches(self) -> None:
        """No match in any branch → UNKNOWN."""
        with _no_source():
            result = detect_install_method(
                executable="/usr/local/bin/python3",
                distribution_loader=_loader_returning(None),
            )
        assert result == InstallMethod.UNKNOWN

    def test_unknown_is_returned_not_raised(self) -> None:
        """Confirm the fallback never raises."""
        with _no_source():
            try:
                result = detect_install_method(
                    executable="/totally/unknown/python",
                    distribution_loader=_loader_returning("totally-unknown-installer"),
                )
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"detect_install_method raised unexpectedly: {exc!r}")
            assert isinstance(result, InstallMethod)


# ---------------------------------------------------------------------------
# Resilience — exceptions must not crash detection
# ---------------------------------------------------------------------------


class TestExceptionResilience:
    def test_distribution_loader_exception_does_not_crash(self) -> None:
        """An exception from distribution_loader → falls through to UNKNOWN, no crash."""
        loader = _raising_loader(RuntimeError("distribution not found"))
        with _no_source():
            try:
                result = detect_install_method(
                    executable="/usr/local/bin/python3",
                    distribution_loader=loader,
                )
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"detect_install_method raised unexpectedly: {exc!r}")
        assert result == InstallMethod.UNKNOWN

    def test_distribution_loader_os_error_does_not_crash(self) -> None:
        """OSError from distribution_loader → falls through, no crash."""
        loader = _raising_loader(OSError("permission denied"))
        with _no_source():
            result = detect_install_method(
                executable="/usr/local/bin/python3",
                distribution_loader=loader,
            )
        assert isinstance(result, InstallMethod)

    def test_brew_subprocess_exception_falls_through(self) -> None:
        """Any exception in brew --prefix subprocess → falls through silently."""
        executable = "/some/random/python"

        with _no_source(), patch("subprocess.run", side_effect=FileNotFoundError("brew not found")):
            result = detect_install_method(
                executable=executable,
                distribution_loader=_loader_returning(None),
            )
        assert isinstance(result, InstallMethod)
        assert result != InstallMethod.BREW

    def test_function_never_raises_with_bizarre_executable(self) -> None:
        """Bizarre executable strings must not cause a raise."""
        for exe in ["", "\x00", "///", "a" * 10_000]:
            with _no_source():
                try:
                    detect_install_method(
                        executable=exe,
                        distribution_loader=_loader_returning(None),
                    )
                except Exception as exc:  # noqa: BLE001
                    pytest.fail(f"detect_install_method raised with exe={exe!r}: {exc!r}")
