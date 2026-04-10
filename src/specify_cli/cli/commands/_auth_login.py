"""Implementation of ``spec-kitty auth login``. Owned by WP04.

This module is lazy-imported from ``cli.commands.auth`` when the ``login``
command fires. Separating the implementation from the Typer command shell
lets WP06 (logout) and WP07 (status) ship their own per-command modules
without file-level conflicts on ``auth.py``.

The ``--headless`` branch lazy-imports a future ``auth.flows.device_code``
module that WP05 will supply. Until WP05 lands, attempting to use
``--headless`` surfaces a clear "not yet implemented" error.

Per constraint C-012 and decision D-5, this module never hardcodes a SaaS
URL — it always reads from :func:`specify_cli.auth.config.get_saas_base_url`
so operators must set ``SPEC_KITTY_SAAS_URL`` in the environment.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import typer
from rich.console import Console

from specify_cli.auth import (
    AuthenticationError,
    BrowserLaunchError,
    CallbackTimeoutError,
    CallbackValidationError,
    ConfigurationError,
    get_token_manager,
)
from specify_cli.auth.config import get_saas_base_url

if TYPE_CHECKING:
    from specify_cli.auth.session import StorageBackend, StoredSession
    from specify_cli.auth.token_manager import TokenManager

log = logging.getLogger(__name__)
console = Console()


async def login_impl(*, headless: bool, force: bool) -> None:
    """Run the login flow. Called by ``cli.commands.auth.login``.

    Args:
        headless: When True, dispatches to the device authorization flow
            (WP05). Defaults to False (browser PKCE flow).
        force: When True, re-authenticates even if a session is already
            present. Defaults to False.
    """
    try:
        saas_url = get_saas_base_url()
    except ConfigurationError as exc:
        console.print(f"[red]X {exc}[/red]")
        raise typer.Exit(1) from exc

    tm = get_token_manager()

    if tm.is_authenticated and not force:
        session = tm.get_current_session()
        assert session is not None  # is_authenticated guarantees this
        console.print(f"[green]+ Already logged in as {session.email}[/green]")
        console.print(
            "Run [bold]spec-kitty auth login --force[/bold] to re-authenticate, "
            "or [bold]spec-kitty auth logout[/bold] first."
        )
        return

    if force and tm.is_authenticated:
        console.print("[dim]Forcing re-authentication...[/dim]")
        tm.clear_session()

    if headless:
        await _run_device_flow(tm, saas_url)
    else:
        await _run_browser_flow(tm, saas_url)


async def _run_browser_flow(tm: TokenManager, saas_url: str) -> None:
    """Run the browser-based OAuth Authorization Code + PKCE flow."""
    from specify_cli.auth.flows.authorization_code import AuthorizationCodeFlow

    console.print("Opening browser for OAuth authentication...")
    console.print(f"[dim]SaaS: {saas_url}[/dim]")

    flow = AuthorizationCodeFlow(
        saas_base_url=saas_url,
        storage_backend=cast("StorageBackend", tm._storage.backend_name),
    )

    try:
        session = await flow.login()
    except CallbackTimeoutError:
        console.print("[red]X Authentication timed out (5 minutes elapsed)[/red]")
        console.print("Run [bold]spec-kitty auth login[/bold] again.")
        raise typer.Exit(1) from None
    except CallbackValidationError as exc:
        console.print(f"[red]X Callback validation failed: {exc}[/red]")
        console.print(
            "This may indicate a CSRF attack or a stale browser tab. "
            "Run [bold]spec-kitty auth login[/bold] again."
        )
        raise typer.Exit(1) from exc
    except BrowserLaunchError as exc:
        console.print(f"[red]X Could not launch browser: {exc}[/red]")
        console.print("Try [bold]spec-kitty auth login --headless[/bold] instead.")
        raise typer.Exit(1) from exc
    except AuthenticationError as exc:
        console.print(f"[red]X Authentication failed: {exc}[/red]")
        raise typer.Exit(1) from exc

    tm.set_session(session)
    _print_success(session)


async def _run_device_flow(tm: TokenManager, saas_url: str) -> None:
    """Run the device authorization flow (RFC 8628).

    The actual ``DeviceCodeFlow`` orchestrator is provided by WP05 in
    ``specify_cli.auth.flows.device_code``. Until that module lands, the
    import below raises ``ImportError`` which we surface as a clear
    "not yet implemented" message.
    """
    try:
        # Lazy import: WP05 ships this module. Until it lands, this import
        # fails at runtime and we surface a "not yet implemented" error.
        # mypy silencing: the module does not exist in lane-a yet, and any
        # stale bytecode in sibling checkouts may confuse import analysis.
        from specify_cli.auth.flows.device_code import (  # type: ignore[import-not-found,import-untyped,unused-ignore]
            DeviceCodeFlow,
        )
    except ImportError as exc:
        console.print(
            "[red]X Headless login is not yet implemented (waiting on WP05).[/red]"
        )
        raise typer.Exit(1) from exc

    flow = DeviceCodeFlow(
        saas_base_url=saas_url,
        storage_backend=cast("StorageBackend", tm._storage.backend_name),
    )

    try:
        session = await flow.login(progress_writer=console.print)
    except AuthenticationError as exc:
        console.print(f"[red]X Device flow failed: {exc}[/red]")
        raise typer.Exit(1) from exc

    tm.set_session(session)
    _print_success(session)


def _print_success(session: StoredSession) -> None:
    """Print the post-login success message."""
    console.print()
    console.print(f"[green]+ Authenticated as {session.email}[/green]")
    if session.teams:
        default_team = next(
            (t for t in session.teams if t.id == session.default_team_id),
            None,
        )
        if default_team:
            console.print(f"  Default team: {default_team.name}")


__all__ = ["login_impl"]
