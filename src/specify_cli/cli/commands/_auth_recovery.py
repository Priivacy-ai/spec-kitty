"""Logged-out-on-connected-teamspace recovery helpers (Mission 7, issue #829).

This module provides the small surface that the various `spec-kitty sync ...`
commands call when authentication is missing but the local repo state shows a
prior teamspace connection. The goal is to give interactive operators a
one-keystroke path back to a successful login while keeping CI scripts
deterministic.

Public surface:

- ``EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE``: stable exit code (4) for the
  non-interactive case.
- ``RecoveryOutcome``: enum returned by the facade and the prompt.
- ``detect_logged_out_with_connected_teamspace``: read-only detector.
- ``is_interactive``: TTY + env probe.
- ``offer_login_recovery``: interactive ``[L]ogin / [S]kip / [Q]uit`` prompt.
- ``emit_structured_stderr``: writes the canonical CI-readable line.
- ``handle_unauthenticated_with_teamspace``: facade used by callers.

All third-party / heavy imports (``readchar``, ``TokenManager``, sync routing,
``_auth_login``) are deferred to call-site to keep import cost low and to keep
test isolation tractable.
"""

from __future__ import annotations

import asyncio
import os
import sys
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from rich.console import Console


EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE: int = 4
"""Stable exit code for the non-interactive structured-error case.

Scripts and CI runners can match this code specifically. Do not reuse for
any other condition.
"""


class RecoveryOutcome(StrEnum):
    """Result of attempting interactive auth recovery."""

    LOGGED_IN = "logged_in"
    """User chose ``L`` and the inner login flow succeeded."""

    SKIPPED = "skipped"
    """User chose ``S`` (or unknown input, or login flow raised AuthenticationError)."""

    QUIT = "quit"
    """User chose ``Q``."""

    NO_TEAMSPACE = "no_teamspace"
    """No prior teamspace was detected; caller should keep legacy behavior."""

    EXIT_4 = "exit_4"
    """Non-interactive case; caller should ``raise typer.Exit(4)``."""


def detect_logged_out_with_connected_teamspace(
    repo_root: Path | None = None,  # noqa: ARG001 - reserved for future use
) -> str | None:
    """Return a teamspace handle if logged-out on a connected repo, else None.

    Read-only. No network I/O. All heavy imports are lazy.

    Resolution order:
      1. If TokenManager reports an authenticated session, return ``None``
         (caller has no recovery work to do).
      2. ``resolve_checkout_sync_routing().repo_slug`` if non-empty.
      3. ``resolve_checkout_sync_routing().project_slug`` if non-empty.
      4. Stored session's first private-teamspace ``team.name`` if non-empty.
      5. ``None``.
    """
    # 1) Skip if a valid session exists.
    try:
        from specify_cli.auth import get_token_manager  # lazy
    except Exception:  # pragma: no cover - defensive
        return None

    try:
        tm = get_token_manager()
    except Exception:  # pragma: no cover - defensive
        return None

    try:
        if tm.is_authenticated:
            return None
    except Exception:  # pragma: no cover - defensive
        # If we cannot tell, fall through and try the detectors.
        pass

    # 2/3) Routing-derived handle.
    try:
        from specify_cli.sync.routing import resolve_checkout_sync_routing  # lazy

        routing = resolve_checkout_sync_routing()
    except Exception:  # pragma: no cover - defensive
        routing = None

    if routing is not None:
        repo_slug = getattr(routing, "repo_slug", None)
        if isinstance(repo_slug, str) and repo_slug.strip():
            return repo_slug.strip()
        project_slug = getattr(routing, "project_slug", None)
        if isinstance(project_slug, str) and project_slug.strip():
            return project_slug.strip()

    # 4) Stored-session private team name.
    try:
        session = tm.get_current_session()
    except Exception:  # pragma: no cover - defensive
        session = None

    if session is not None:
        teams = getattr(session, "teams", None) or ()
        for team in teams:
            if bool(getattr(team, "is_private_teamspace", False)):
                name = getattr(team, "name", None)
                if isinstance(name, str) and name.strip():
                    return name.strip()

    return None


def is_interactive() -> bool:
    """Return True iff the caller should run the interactive recovery prompt.

    Decision matrix:
      - ``SPEC_KITTY_FORCE_INTERACTIVE=1`` -> True (highest priority).
      - ``SPEC_KITTY_NON_INTERACTIVE=1`` -> False.
      - Otherwise: ``sys.stdin.isatty()``.

    Tests must monkeypatch ``sys.stdin`` or ``os.environ`` rather than relying
    on the real shell.
    """
    if os.environ.get("SPEC_KITTY_FORCE_INTERACTIVE") == "1":
        return True
    if os.environ.get("SPEC_KITTY_NON_INTERACTIVE") == "1":
        return False
    try:
        return bool(sys.stdin.isatty())
    except (AttributeError, ValueError):  # pragma: no cover - defensive
        return False


def _read_one_keystroke() -> str:
    """Read a single keystroke from the user, lowercased.

    Tries ``readchar.readkey()`` first; falls back to ``input()`` if
    ``readchar`` is not available or the terminal cannot be put into raw mode.
    Returns at most one character.
    """
    try:
        import readchar
    except Exception:  # pragma: no cover - tested via fallback path
        readchar = None  # type: ignore[assignment]

    if readchar is not None:
        try:
            key = readchar.readkey()
        except Exception:  # pragma: no cover - falls through to stdin
            key = ""
        if key:
            return key.strip().lower()[:1]

    try:
        line = sys.stdin.readline()
    except Exception:  # pragma: no cover - defensive
        return ""
    if not line:
        return ""
    stripped = line.strip().lower()
    return stripped[:1]


def offer_login_recovery(
    *,
    teamspace: str,
    command_name: str,
    console: Console,
) -> RecoveryOutcome:
    """Render the interactive recovery panel and act on the user's choice.

    On ``L``: invokes ``_auth_login.login_impl(headless=False, force=False)``
    via ``asyncio.run``. Returns ``LOGGED_IN`` on success, ``SKIPPED`` if the
    login flow raises ``AuthenticationError``.

    On ``S`` or unknown input: returns ``SKIPPED``.

    On ``Q``: returns ``QUIT``.
    """
    from rich.panel import Panel  # lazy

    panel = Panel(
        (
            f"This repo is connected to teamspace [cyan]{teamspace}[/cyan], "
            f"but you are not logged in.\n"
            f"Command: [dim]spec-kitty {command_name}[/dim]\n\n"
            "Choose: [bold]L[/bold]ogin to re-authenticate, "
            "[bold]S[/bold]kip and continue with the legacy message, "
            "[bold]Q[/bold]uit."
        ),
        title="Logged out on a connected teamspace",
        border_style="yellow",
        expand=False,
    )
    console.print(panel)
    console.print("[bold][L]ogin / [S]kip / [Q]uit:[/bold] ", end="")

    choice = _read_one_keystroke()
    console.print(choice or "")

    if choice == "l":
        try:
            from specify_cli.cli.commands._auth_login import login_impl  # lazy
        except Exception as exc:  # pragma: no cover - defensive
            console.print(f"[red]Login flow is unavailable:[/red] {exc}")
            return RecoveryOutcome.SKIPPED

        try:
            from specify_cli.auth.errors import AuthenticationError  # lazy
        except Exception:  # pragma: no cover - defensive
            AuthenticationError = Exception  # type: ignore[assignment, misc]  # fallback when auth module is unavailable

        try:
            asyncio.run(login_impl(headless=False, force=False))
        except AuthenticationError as exc:
            console.print(f"[red]Login failed:[/red] {exc}")
            return RecoveryOutcome.SKIPPED
        return RecoveryOutcome.LOGGED_IN

    if choice == "q":
        return RecoveryOutcome.QUIT

    return RecoveryOutcome.SKIPPED


def emit_structured_stderr(*, teamspace: str, command_name: str) -> None:
    """Write the canonical machine-readable line to ``sys.stderr``.

    Single ASCII line, stable for scripts:

        spec-kitty: logged_out_on_connected_teamspace teamspace=<slug>
        command=<name> action=run-spec-kitty-auth-login

    """
    line = (
        "spec-kitty: logged_out_on_connected_teamspace "
        f"teamspace={teamspace} "
        f"command={command_name} "
        "action=run-spec-kitty-auth-login\n"
    )
    try:
        sys.stderr.write(line)
        sys.stderr.flush()
    except Exception:  # pragma: no cover - defensive
        pass


def handle_unauthenticated_with_teamspace(
    *,
    command_name: str,
    console: Console,
) -> RecoveryOutcome:
    """Facade used by sync commands' auth-missing branches.

    - No prior teamspace detected: returns ``NO_TEAMSPACE`` (no output).
    - Interactive: delegates to ``offer_login_recovery``.
    - Otherwise: emits the structured stderr line and returns ``EXIT_4``.
    """
    teamspace = detect_logged_out_with_connected_teamspace()
    if teamspace is None:
        return RecoveryOutcome.NO_TEAMSPACE

    if is_interactive():
        return offer_login_recovery(
            teamspace=teamspace,
            command_name=command_name,
            console=console,
        )

    emit_structured_stderr(teamspace=teamspace, command_name=command_name)
    return RecoveryOutcome.EXIT_4


__all__ = [
    "EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE",
    "RecoveryOutcome",
    "detect_logged_out_with_connected_teamspace",
    "emit_structured_stderr",
    "handle_unauthenticated_with_teamspace",
    "is_interactive",
    "offer_login_recovery",
]
