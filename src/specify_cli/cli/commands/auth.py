"""spec-kitty auth — OAuth login, logout, and status.

This module is a thin Typer command shell. The actual implementation of
each command lives in a sibling ``_auth_<name>.py`` module that is imported
lazily when the command is invoked. This separation allows different work
packages to own different commands without file-level conflicts.

Owned by WP04 (login dispatch + shell). WP06 owns ``_auth_logout.py`` and
WP07 owns ``_auth_status.py``; those modules are lazy-imported inside the
respective command bodies and do not need to exist at WP04 land time.

Wiring: the ``login`` command dispatches to ``_auth_login.login_impl``,
which in turn uses ``get_token_manager`` from :mod:`specify_cli.auth`
and runs the ``AuthorizationCodeFlow`` from
:mod:`specify_cli.auth.flows.authorization_code` (which consumes the
loopback callback primitives from :mod:`specify_cli.auth.loopback`).
"""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

app = typer.Typer(name="auth", help="Authenticate with spec-kitty SaaS.")
console = Console()


@app.command()
def login(
    headless: bool = typer.Option(
        False,
        "--headless",
        help="Use device authorization flow (for SSH or no-browser environments).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Re-authenticate even if already logged in.",
    ),
) -> None:
    """Log in to spec-kitty SaaS via browser OAuth (or device flow with --headless)."""
    from specify_cli.cli.commands._auth_login import login_impl

    try:
        asyncio.run(login_impl(headless=headless, force=force))
    except KeyboardInterrupt:
        console.print("\n[yellow]Login cancelled by user.[/yellow]")
        raise typer.Exit(130) from None


@app.command()
def logout(
    force: bool = typer.Option(
        False,
        "--force",
        help="Skip server revocation; only delete local credentials.",
    ),
) -> None:
    """Log out and revoke the current session."""
    try:
        from specify_cli.cli.commands._auth_logout import logout_impl
    except ImportError as exc:
        console.print(
            "[red]Error:[/red] Logout is not yet implemented (waiting on WP06)."
        )
        raise typer.Exit(1) from exc

    try:
        asyncio.run(logout_impl(force=force))
    except KeyboardInterrupt:
        console.print("\n[yellow]Logout cancelled.[/yellow]")
        raise typer.Exit(130) from None


@app.command()
def status() -> None:
    """Show current authentication status."""
    try:
        from specify_cli.cli.commands._auth_status import status_impl
    except ImportError as exc:
        console.print(
            "[red]Error:[/red] Status is not yet implemented (waiting on WP07)."
        )
        raise typer.Exit(1) from exc

    status_impl()


@app.command()
def whoami() -> None:
    """Print the authenticated user's email and exit 0, or exit 1 if not authenticated."""
    from specify_cli.cli.commands._auth_whoami import whoami_impl

    whoami_impl()


__all__ = ["app"]
