"""session-stop — open-Ops reminder for the Claude Code Stop hook.

This command is invoked automatically by Claude Code's ``Stop`` lifecycle hook
when a session ends.  When the cwd is inside a spec-kitty project and open Ops
exist, it prints a reminder listing them with close commands; otherwise it
prints nothing.

Exit 0 guarantee: the outermost ``except Exception: pass`` is intentional and
the command NEVER exits non-zero.  A failure here must never block the host
agent's stop flow.  Scan-only: a single Ops directory scan, no git calls.
"""

from __future__ import annotations

import logging

import typer

from .session_start import _find_project_root

_logger = logging.getLogger(__name__)


def session_stop() -> None:
    """Emit the open-Ops reminder for the Claude Code Stop hook."""
    try:
        project_root = _find_project_root()
        if project_root is None:
            return
        from specify_cli.session_presence.open_ops import render_open_ops_reminder

        reminder = render_open_ops_reminder(project_root)
        if reminder:
            typer.echo(reminder)
    except Exception:
        pass  # Always exit 0 — never block the host agent's stop flow
