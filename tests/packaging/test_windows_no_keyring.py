"""T018 — Packaging assertion: keyring must NOT be installed on Windows.

This test is marked @pytest.mark.windows_ci and runs only on the native
windows-latest CI job (WP07). It verifies that the conditional dependency
marker ``keyring>=24.0; sys_platform != "win32"`` in pyproject.toml is
honored by the installer so that keyring and its transitive Windows deps
(pywin32-ctypes, etc.) are never pulled on Windows.
"""

from __future__ import annotations

import importlib.util

import pytest


@pytest.mark.windows_ci
def test_keyring_not_installed_on_windows():
    """keyring MUST NOT be installed in a Windows spec-kitty-cli environment."""
    spec = importlib.util.find_spec("keyring")
    assert spec is None, (
        "keyring MUST NOT be installed on Windows. The conditional "
        "marker in pyproject.toml (keyring>=24.0; sys_platform != 'win32') is "
        "either missing or not being honored by the installer. "
        "Check: pip show keyring to trace the transitive pull."
    )
