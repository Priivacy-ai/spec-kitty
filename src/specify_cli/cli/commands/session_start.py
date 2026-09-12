"""session-start — emit spec-kitty orientation for the Claude Code SessionStart hook.

This command is invoked automatically by Claude Code's ``SessionStart`` lifecycle
hook on every new session.  It prints the orientation block to stdout when the
cwd is inside a spec-kitty project, and silently exits 0 in all other cases.

Exit 0 guarantee: the outermost ``except Exception: pass`` is intentional.
This command MUST never cause a Claude Code session to fail to start, regardless
of any error in the spec-kitty stack.  All exceptions are swallowed.

Performance (NFR-001): the command must complete in <200ms on a warm filesystem.
Unless ``SPEC_KITTY_NO_UPGRADE_CHECK`` is set, the upgrade check fires a
background subprocess (``check_in_background()``) that returns immediately;
``get_available_version()`` reads only the local cache file — no network calls
on the hot path.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

_logger = logging.getLogger(__name__)


def _find_project_root(
    start: Path | None = None,
    *,
    stop: Path | None = None,
) -> Path | None:
    """Walk up from *start* looking for a ``.kittify/`` directory.

    Returns the first directory at or above *start* that contains a
    ``.kittify/`` subdirectory, or ``None`` when no such directory is found
    (i.e. *start* is not inside a spec-kitty project). *start* defaults to the
    cwd; the walk always terminates at the filesystem root.

    *stop* bounds the walk: it names the last directory examined, so nothing
    above it is ever read (when *stop* is not an ancestor of *start* the walk
    simply runs to the filesystem root). Production callers keep the unbounded
    default; tests pass an explicit *stop* because nothing above ``tmp_path``
    is under test control — on a shared machine any ancestor can gain a stray
    ``.kittify/`` from a sibling test, which would flip outside-project
    verdicts non-deterministically (#130).
    """
    current = (start if start is not None else Path.cwd()).resolve()
    boundary = stop.resolve() if stop is not None else None
    while True:
        if (current / ".kittify").is_dir():
            return current
        if boundary is not None and current == boundary:
            return None
        parent = current.parent
        if parent == current:
            return None
        current = parent


def session_start() -> None:
    """Emit spec-kitty orientation for the Claude Code SessionStart hook."""
    try:
        project_root = _find_project_root()
        if project_root is None:
            return
        from specify_cli.core.agent_config import load_agent_config
        from specify_cli.session_presence.manager import SessionPresenceManager

        agent_config = load_agent_config(project_root)
        content = SessionPresenceManager(project_root, agent_config)._build_content()
        typer.echo(content.render())
        from specify_cli.session_presence.open_ops import render_open_ops_section

        open_ops_section = render_open_ops_section(project_root)
        if open_ops_section:
            typer.echo(open_ops_section)
    except Exception:
        pass  # Always exit 0 — never fail the Claude Code session
