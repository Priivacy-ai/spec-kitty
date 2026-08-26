"""Implementation of ``spec-kitty auth login``. Owned by WP04.

This module is lazy-imported from ``cli.commands.auth`` when the ``login``
command fires. Separating the implementation from the Typer command shell
lets WP06 (logout) and WP07 (status) ship their own per-command modules
without file-level conflicts on ``auth.py``.

The ``--headless`` branch lazy-imports a future ``auth.flows.device_code``
module that WP05 will supply. Until WP05 lands, attempting to use
``--headless`` surfaces a clear "not yet implemented" error.

This module never hardcodes a SaaS URL. It resolves the login target through the
canonical resolver :func:`specify_cli.auth.server_target.resolve_server_target`,
which folds ``SPEC_KITTY_SAAS_URL`` (env) over ``[sync].server_url`` in
``config.toml`` over the documented default — the *same* precedence ``sync`` uses.
This is deliberate (#3406, FR-005): login previously read the env-only accessor
``get_saas_base_url`` and errored when the env var was unset, even when the user
had already set a server via ``spec-kitty sync server``. That inconsistency meant
a token could be obtained one way while sync targeted another; resolving both the
same way removes it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import typer
from specify_cli.cli.console import console

from specify_cli.auth import (
    AuthenticationError,
    BrowserLaunchError,
    CallbackTimeoutError,
    CallbackValidationError,
    get_token_manager,
)
from specify_cli.auth.server_target import resolve_server_target

if TYPE_CHECKING:
    from specify_cli.auth.session import StorageBackend, StoredSession
    from specify_cli.auth.token_manager import TokenManager

log = logging.getLogger(__name__)


async def login_impl(*, headless: bool, force: bool) -> None:
    """Run the login flow. Called by ``cli.commands.auth.login``.

    Args:
        headless: When True, dispatches to the device authorization flow
            (WP05). Defaults to False (browser PKCE flow).
        force: When True, re-authenticates even if a session is already
            present. Defaults to False.

    Note:
        Identity acquisition is intentionally decoupled from TeamSpace
        mission-state readiness (DDD: Identity & Access vs TeamSpace
        contexts). Sync / tracker / connect commands continue to call
        ``enforce_teamspace_mission_state_ready`` themselves — those are
        the commands that actually depend on TeamSpace state.
    """
    # Resolve the login target the same way sync does — env over config.toml
    # over the documented default (#3406, FR-005). Login previously read the
    # env-only accessor and errored when only `sync server` had been set, so a
    # token could be minted against one server while sync targeted another.
    # We still refuse when NEITHER an env override nor an explicit config
    # server_url is set, rather than silently defaulting to the descriptive dev
    # URL — preserving the "choose your server" intent while honouring config.
    target = resolve_server_target()
    if target.env_server_url is None and target.configured_server_url is None:
        console.print(
            "[red]X No hosted server is configured. Set SPEC_KITTY_SAAS_URL (or set "
            "[sync].server_url in your config.toml), then try again.[/red]"
        )
        raise typer.Exit(1)
    saas_url = target.resolved_server_url

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
            suffix = " [Private Teamspace]" if default_team.is_private_teamspace else ""
            console.print(f"  Default team: {default_team.name}{suffix}")


__all__ = ["login_impl"]
