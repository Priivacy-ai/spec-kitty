"""Helper utilities for verifying test isolation.

This module provides functions to check version consistency between
source code and installed packages, ensuring tests run against the
correct version of spec-kitty-cli.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def get_source_version() -> str:
    """Get version from pyproject.toml (single source of truth).

    Returns:
        Version string (e.g., "0.10.13")
    """
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def get_installed_version() -> str | None:
    """Get installed spec-kitty-cli version, if any.

    Returns:
        Version string if package is installed, None otherwise
    """
    try:
        from importlib.metadata import version
        return version("spec-kitty-cli")
    except Exception:
        return None


def assert_test_isolation() -> None:
    """Assert that test environment is properly isolated.

    Call this in test setup to catch isolation issues early.
    Will fail the test if:
    - Installed version exists and doesn't match source version

    Raises:
        pytest.fail: If version mismatch is detected
    """
    source = get_source_version()
    installed = get_installed_version()

    if installed is None:
        # Perfect - no installed version to conflict
        return

    if installed != source:
        pytest.fail(
            f"Test isolation broken! Source: {source}, Installed: {installed}. "
            f"Run: pip uninstall spec-kitty-cli -y"
        )


def run_cli_subprocess(
    project_path: Path,
    *args: str,
    check: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run CLI in subprocess with guaranteed source version.

    This is a lower-level helper for tests that need full control.
    Most tests should use the run_cli fixture instead.

    Args:
        project_path: Path to test project directory
        *args: CLI arguments
        check: If True, raise exception on non-zero exit

    Returns:
        Completed subprocess result
    """
    env = os.environ.copy()

    # Force isolation
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["SPEC_KITTY_CLI_VERSION"] = get_source_version()
    env["SPEC_KITTY_TEMPLATE_ROOT"] = str(REPO_ROOT)
    env["SPEC_KITTY_TEST_MODE"] = "1"

    command = [sys.executable, "-m", "specify_cli.__init__", *args]

    return subprocess.run(
        command,
        cwd=str(project_path),
        capture_output=True,
        text=True,
        env=env,
        check=check,
    )


__all__ = [
    "get_source_version",
    "get_installed_version",
    "assert_test_isolation",
    "run_cli_subprocess",
    "REPO_ROOT",
]
