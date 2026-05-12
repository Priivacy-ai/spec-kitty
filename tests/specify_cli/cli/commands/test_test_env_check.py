"""Regression tests for the _test_env_check preflight helper.

T005 from WP01 of mission review-merge-gate-hardening-3-2-x-01KRC57C.
FR-001, FR-002: prevent PATH fallthrough to system pytest in gate commands.
"""

from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

import pytest

from specify_cli.cli.commands._test_env_check import (
    TestExtraMissing,
    assert_pytest_available,
)


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

    assert venv_python.exists(), (
        f"Expected venv interpreter at {venv_python} but it does not exist."
    )

    # Verify the venv truly lacks pytest to avoid a false pass.
    probe = subprocess.run(
        [str(venv_python), "-c", "import pytest"],
        capture_output=True,
    )
    assert probe.returncode != 0, (
        "The synthetic venv unexpectedly has pytest installed — "
        "the negative test premise is broken."
    )

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
