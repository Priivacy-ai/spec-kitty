"""Regression tests for the _test_env_check preflight helper.

T005 from WP01 of mission review-merge-gate-hardening-3-2-x-01KRC57C.
FR-001, FR-002: prevent PATH fallthrough to system pytest in gate commands.

Also covers WP01 of mission ci-local-preflight-parity-01KWXWY0 (#2283
Phase 3): the typer/click uv.lock-parity check (FR-001).
"""

from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

import pytest

from specify_cli.cli.commands._test_env_check import (
    ENV_SKEW_FAIL_CLOSED_ENV_VAR,
    EnvSkew,
    PackageSkew,
    TestExtraMissing,
    assert_pytest_available,
    assert_typer_click_lock_parity,
    check_typer_click_lock_parity,
    format_env_skew_message,
)


pytestmark = [pytest.mark.unit, pytest.mark.integration]


def test_assert_pytest_available_succeeds_when_pytest_importable(
    tmp_path: Path,
) -> None:
    """Sanity check: pytest is importable in our own dev venv.

    Uses the project root (parent of tests/) as the project_root argument.
    The current venv has the test extra installed, so this must pass.
    """
    # Use the repo root derived from this file's location as project_root.
    # __file__ is tests/specify_cli/cli/commands/test_test_env_check.py, so
    # go up 5 levels to reach the repo root.
    project_root = Path(__file__).resolve().parents[4]
    # Should not raise.
    assert_pytest_available(project_root)


@pytest.mark.slow
def test_assert_pytest_available_raises_when_pytest_missing(
    tmp_path: Path,
) -> None:
    """Negative test: a synthetic venv without the test extra raises TestExtraMissing.

    Creates a minimal venv in tmp_path (no packages beyond pip/setuptools),
    then calls assert_pytest_available using that venv's interpreter.
    Asserts TestExtraMissing is raised with the expected diagnostic code.
    """
    venv_dir = tmp_path / "no_extras_venv"
    # Create a bare venv — no pip, no system-site-packages, no extras.
    venv.create(str(venv_dir), with_pip=False, system_site_packages=False)

    # Locate the venv's Python interpreter.
    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    assert venv_python.exists(), f"Expected venv interpreter at {venv_python} but it does not exist."

    # Verify the venv truly lacks pytest to avoid a false pass.
    probe = subprocess.run(
        [str(venv_python), "-c", "import pytest"],
        capture_output=True,
    )
    assert probe.returncode != 0, "The synthetic venv unexpectedly has pytest installed — the negative test premise is broken."

    # Monkeypatch sys.executable so assert_pytest_available uses the bare venv.
    import specify_cli.cli.commands._test_env_check as _mod

    original_executable = _mod.sys.executable
    try:
        _mod.sys.executable = str(venv_python)
        with pytest.raises(TestExtraMissing) as exc_info:
            assert_pytest_available(tmp_path)
    finally:
        _mod.sys.executable = original_executable

    assert exc_info.value.args[0] == "MISSION_REVIEW_TEST_EXTRA_MISSING"


# ---------------------------------------------------------------------------
# T001 -- typer/click lock-parity check (FR-001)
# ---------------------------------------------------------------------------


def _write_uv_lock(tmp_path: Path, versions: dict[str, str]) -> Path:
    """Write a minimal uv.lock fixture pinning the given package versions."""
    lock_path = tmp_path / "uv.lock"
    body_parts = [
        f'[[package]]\nname = "{name}"\nversion = "{version}"\nsource = {{ registry = "https://pypi.org/simple" }}\n' for name, version in versions.items()
    ]
    lock_path.write_text("\n".join(body_parts), encoding="utf-8")
    return lock_path


class TestTyperClickLockParity:
    """FR-001: local typer/click lock-parity preflight (MISSION_REVIEW_ENV_SKEW)."""

    def test_matching_versions_produce_no_mismatches(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Installed versions matching uv.lock -> no mismatches, no raise."""
        _write_uv_lock(tmp_path, {"typer": "0.24.2", "click": "8.3.3"})

        import specify_cli.cli.commands._test_env_check as _mod

        monkeypatch.setattr(
            _mod,
            "_installed_version",
            lambda pkg: {"typer": "0.24.2", "click": "8.3.3"}[pkg],
        )

        assert check_typer_click_lock_parity(tmp_path) == []

        # Must not raise, even in fail-closed mode, when there is genuinely
        # no divergence.
        assert assert_typer_click_lock_parity(tmp_path, fail_closed=True) == []

    def test_diverging_installed_version_is_detected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A diverging installed typer version is reported as a mismatch."""
        _write_uv_lock(tmp_path, {"typer": "0.24.2", "click": "8.3.3"})

        import specify_cli.cli.commands._test_env_check as _mod

        monkeypatch.setattr(
            _mod,
            "_installed_version",
            lambda pkg: {"typer": "0.26.0", "click": "8.3.3"}[pkg],
        )

        mismatches = check_typer_click_lock_parity(tmp_path)
        assert mismatches == [PackageSkew("typer", "0.24.2", "0.26.0")]

    def test_default_mode_is_warn_loud_not_fail_closed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Red-first: divergence must NOT raise by default (warn-loud, SC-001)."""
        _write_uv_lock(tmp_path, {"typer": "0.24.2", "click": "8.3.3"})

        import specify_cli.cli.commands._test_env_check as _mod

        monkeypatch.setattr(
            _mod,
            "_installed_version",
            lambda pkg: {"typer": "0.26.0", "click": "8.3.3"}[pkg],
        )
        monkeypatch.delenv(ENV_SKEW_FAIL_CLOSED_ENV_VAR, raising=False)

        # Must not raise -- default is warn-loud (SC-001).
        mismatches = assert_typer_click_lock_parity(tmp_path)
        assert mismatches == [PackageSkew("typer", "0.24.2", "0.26.0")]

    def test_explicit_fail_closed_true_raises_env_skew(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Red-first: fail_closed=True raises EnvSkew on divergence."""
        _write_uv_lock(tmp_path, {"typer": "0.24.2", "click": "8.3.3"})

        import specify_cli.cli.commands._test_env_check as _mod

        monkeypatch.setattr(
            _mod,
            "_installed_version",
            lambda pkg: {"typer": "0.26.0", "click": "8.3.3"}[pkg],
        )

        with pytest.raises(EnvSkew) as exc_info:
            assert_typer_click_lock_parity(tmp_path, fail_closed=True)

        assert exc_info.value.args[0] == "MISSION_REVIEW_ENV_SKEW"

    def test_fail_closed_env_var_opts_in_without_explicit_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """SPEC_KITTY_ENV_SKEW_FAIL_CLOSED=1 opts into fail-closed mode."""
        _write_uv_lock(tmp_path, {"typer": "0.24.2", "click": "8.3.3"})

        import specify_cli.cli.commands._test_env_check as _mod

        monkeypatch.setattr(
            _mod,
            "_installed_version",
            lambda pkg: {"typer": "0.26.0", "click": "8.3.3"}[pkg],
        )
        monkeypatch.setenv(ENV_SKEW_FAIL_CLOSED_ENV_VAR, "1")

        with pytest.raises(EnvSkew):
            assert_typer_click_lock_parity(tmp_path)

    def test_remediation_is_named_in_the_message(self) -> None:
        """The diagnostic message names the documented remediation command."""
        message = format_env_skew_message([PackageSkew("typer", "0.24.2", "0.26.0")])
        assert "uv sync --frozen --all-extras" in message
        assert "MISSION_REVIEW_ENV_SKEW" in message

    def test_missing_uv_lock_is_a_harmless_no_op(self, tmp_path: Path) -> None:
        """No uv.lock present (e.g. a uv-tool install) -> no mismatches."""
        assert check_typer_click_lock_parity(tmp_path) == []

    def test_uv_lock_is_read_live_not_hardcoded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Changing the fixture uv.lock's pinned version changes the result.

        Proves the locked version is read from uv.lock at call time, never a
        hardcoded copy embedded in the check itself (NFR-002).
        """
        import specify_cli.cli.commands._test_env_check as _mod

        monkeypatch.setattr(
            _mod,
            "_installed_version",
            lambda pkg: {"typer": "0.24.2", "click": "8.3.3"}[pkg],
        )

        _write_uv_lock(tmp_path, {"typer": "0.24.2", "click": "8.3.3"})
        assert check_typer_click_lock_parity(tmp_path) == []

        # Mutate the lock's pinned typer version -- the same installed
        # version now diverges from the (changed) lock.
        _write_uv_lock(tmp_path, {"typer": "0.25.0", "click": "8.3.3"})
        assert check_typer_click_lock_parity(tmp_path) == [PackageSkew("typer", "0.25.0", "0.24.2")]
