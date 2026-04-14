"""Routing tests for runtime/agent_commands.py (WP04 T022).

Verifies that:
- ``codex`` and ``vibe`` are routed through
  ``specify_cli.skills.command_installer.install``.
- ``claude`` (a legacy command-file agent) does NOT call the installer.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import patch


from specify_cli.runtime.agent_commands import _sync_agent_commands
from specify_cli.skills.command_installer import InstallReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_install_report() -> InstallReport:
    return InstallReport(added=[], already_installed=[], reused_shared=[], errors=[])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_codex_routes_to_installer(tmp_path: Path) -> None:
    """_sync_agent_commands('codex', ...) must delegate to command_installer.install."""
    mock_report = _make_install_report()
    with patch(
        "specify_cli.skills.command_installer.install", return_value=mock_report
    ) as mock_install:
        _sync_agent_commands("codex", tmp_path, "sh")

    mock_install.assert_called_once()
    _args, _kwargs = mock_install.call_args
    # Second positional arg is agent_key
    assert _args[1] == "codex"


def test_vibe_routes_to_installer(tmp_path: Path) -> None:
    """_sync_agent_commands('vibe', ...) must delegate to command_installer.install."""
    mock_report = _make_install_report()
    with patch(
        "specify_cli.skills.command_installer.install", return_value=mock_report
    ) as mock_install:
        _sync_agent_commands("vibe", tmp_path, "sh")

    mock_install.assert_called_once()
    _args, _kwargs = mock_install.call_args
    assert _args[1] == "vibe"


def test_claude_still_routes_to_command_files(tmp_path: Path) -> None:
    """_sync_agent_commands('claude', ...) must NOT call command_installer.install."""
    with patch(
        "specify_cli.skills.command_installer.install"
    ) as mock_install, contextlib.suppress(Exception):
        # The legacy path will fail (no templates_dir content) but that's fine;
        # we only care that the installer was never invoked.
        _sync_agent_commands("claude", tmp_path, "sh")

    mock_install.assert_not_called()
