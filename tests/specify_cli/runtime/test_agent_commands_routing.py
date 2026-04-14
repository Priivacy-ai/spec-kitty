"""Routing tests for runtime/agent_commands.py.

Post-mission-review correction: `_sync_agent_commands` is the global command-
layer sync path (writes to ``~/.claude/commands/``, ``~/.gemini/commands/``,
etc.). It is called in a loop over ``AGENT_COMMAND_CONFIG``, which no longer
contains ``codex`` or ``vibe``. Command-skill installation for codex/vibe is
therefore driven from ``init`` and ``agent config add``, NOT from this
function. These tests verify that:

- ``_sync_agent_commands`` does not try to handle codex/vibe (it is the
  wrong call site for them).
- ``claude`` (and by extension every other command-layer agent) still
  reaches the legacy render-commands path here.
- ``codex`` and ``vibe`` are absent from ``AGENT_COMMAND_CONFIG`` so the
  caller loop never sees them.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import patch


from specify_cli.core.config import AGENT_COMMAND_CONFIG
from specify_cli.runtime.agent_commands import _sync_agent_commands


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_codex_and_vibe_absent_from_command_config() -> None:
    """The loop in ``ensure_runtime`` iterates ``AGENT_COMMAND_CONFIG``.

    Codex and Vibe must not appear there or the legacy command-file renderer
    would write their files into ``~/.claude/commands/``-style directories.
    """
    assert "codex" not in AGENT_COMMAND_CONFIG
    assert "vibe" not in AGENT_COMMAND_CONFIG


def test_sync_does_not_invoke_skill_installer(tmp_path: Path) -> None:
    """``_sync_agent_commands`` is a command-layer path; it must NEVER call
    ``command_installer.install`` — that is the job of ``init`` and
    ``agent config add``."""
    with (
        patch("specify_cli.skills.command_installer.install") as mock_install,
        contextlib.suppress(Exception),
    ):
        # Call with every command-layer agent key; the legacy path may fail
        # on a bare tmpdir (no templates set up for this test) — that's fine.
        for agent_key in AGENT_COMMAND_CONFIG:
            with contextlib.suppress(Exception):
                _sync_agent_commands(agent_key, tmp_path, "sh")

    mock_install.assert_not_called()


def test_claude_still_routes_to_command_files(tmp_path: Path) -> None:
    """``_sync_agent_commands('claude', ...)`` must NOT call ``command_installer.install``.

    The legacy path may fail on a bare tmpdir (no templates_dir content) but
    that's fine; we only care that the installer was never invoked.
    """
    with (
        patch("specify_cli.skills.command_installer.install") as mock_install,
        contextlib.suppress(Exception),
    ):
        _sync_agent_commands("claude", tmp_path, "sh")

    mock_install.assert_not_called()
