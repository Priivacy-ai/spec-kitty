"""Implementation of ``spec-kitty auth logout``. Owned by WP02.

This module is lazy-imported from ``cli.commands.auth`` when the ``logout``
command fires. The dispatch shell in ``auth.py`` (owned by WP04) imports
:func:`logout_impl` on demand so WP02 can ship independently.

Behavior (spec 080 FR-001–FR-005, FR-011, FR-016):

- **FR-001/FR-002**: On normal logout, POST ``/oauth/revoke`` with the
  refresh token as a form-encoded body (RFC 7009). No ``Authorization``
  header — token possession is authorization.
- **FR-003**: ``RevokeOutcome`` models four states: REVOKED, SERVER_FAILURE,
  NETWORK_ERROR, NO_REFRESH_TOKEN. Each maps to a distinct console message.
- **FR-004**: Server revocation failure must NEVER block local credential
  deletion. Whether the server returns 200, 4xx, 5xx, or the call fails
  with a network error, the local session is cleared unconditionally.
- **FR-005**: If local cleanup fails (``tm.clear_session()`` raises), print
  an error message and exit with code 1.
- **FR-016**: The final ``Logged out`` banner runs only when local cleanup
  succeeds.

Security invariant: the refresh token value must never appear in any log
line, error message, console output, or exception string.
"""

from __future__ import annotations

import logging

import typer
from rich.console import Console

from specify_cli.auth import ConfigurationError, get_token_manager
from specify_cli.auth.config import get_saas_base_url
from specify_cli.auth.flows.revoke import RevokeFlow, RevokeOutcome

log = logging.getLogger(__name__)
console = Console()


async def logout_impl(*, force: bool) -> None:
    """Run the logout flow.

    Server-side revocation failure does not block local credential deletion
    (FR-004). The ``force`` flag skips the server call entirely and only
    deletes the local session.

    Args:
        force: When True, skip the server-side revocation and delete only
            the local session. Use this when the SaaS is unreachable or
            the user wants a purely local cleanup.
    """
    tm = get_token_manager()
    session = tm.get_current_session()

    if session is None:
        # Already logged out — exit 0 with a friendly notice. This is not
        # an error condition; re-running logout is idempotent.
        console.print("[dim]i[/dim] Not logged in.")
        return

    if force:
        console.print("[dim]Skipping server revocation (--force).[/dim]")
    else:
        # Try to revoke the refresh token server-side. Any failure is
        # reported to the user but does NOT block local cleanup below.
        try:
            saas_url = get_saas_base_url()  # noqa: F841 — validates config
        except ConfigurationError as exc:
            console.print(
                f"[yellow]! Cannot reach SaaS (config error): {exc}. "
                f"Proceeding with local logout only.[/yellow]"
            )
        else:
            outcome = await RevokeFlow().revoke(session)
            _print_revoke_outcome(outcome)

    # FR-004: local cleanup is unconditional. This runs regardless of the
    # server-call outcome — 200, 4xx/5xx, network error, config error, or
    # --force. If clear_session() raises, we report the error and exit 1.
    try:
        tm.clear_session()
    except Exception as exc:
        console.print(
            f"[red]✗ Local credentials could not be deleted: {type(exc).__name__}. "
            f"You may need to delete them manually.[/red]"
        )
        raise typer.Exit(code=1)

    console.print("[green]+ Logged out.[/green]")


def _print_revoke_outcome(outcome: RevokeOutcome) -> None:
    """Print the appropriate console message for the given revoke outcome."""
    if outcome is RevokeOutcome.REVOKED:
        console.print("[green]✓ Server revocation confirmed.[/green]")
    elif outcome is RevokeOutcome.NO_REFRESH_TOKEN:
        console.print(
            "[yellow]! Server revocation could not be attempted "
            "(no refresh token). Local credentials will still be deleted.[/yellow]"
        )
    elif outcome is RevokeOutcome.NETWORK_ERROR:
        console.print(
            "[yellow]! Server revocation not confirmed (network error). "
            "Local credentials will still be deleted.[/yellow]"
        )
    else:  # SERVER_FAILURE
        console.print(
            "[yellow]! Server revocation not confirmed (server error). "
            "Local credentials will still be deleted.[/yellow]"
        )


__all__ = ["logout_impl"]
