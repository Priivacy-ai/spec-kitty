"""Implementation of ``spec-kitty auth logout``. Owned by WP06.

This module is lazy-imported from ``cli.commands.auth`` when the ``logout``
command fires. The dispatch shell in ``auth.py`` (owned by WP04) imports
:func:`logout_impl` on demand so WP06 can ship independently.

Behavior (spec 080 FR-013, FR-014):

- **FR-013**: On normal logout, POST ``/api/v1/logout`` with the current
  bearer token so the SaaS can invalidate the server-side session. The
  endpoint is bearer-only — there is NO request body; the session being
  revoked is identified server-side by the bound ``session_id`` claim of
  the access token.
- **FR-014**: Server-side logout failure must NEVER block local credential
  deletion. Whether the server returns 200, 4xx, 5xx, or the call fails
  with a network error, the local session is cleared unconditionally.

The command uses :mod:`httpx` directly rather than the future
``OAuthHttpClient`` transport (WP08) because logout is a single fire-and-
forget call that must NOT trigger automatic refresh on 401: if the access
token is already invalid, the server-side session was already gone, and
we still want to delete the local copy.
"""

from __future__ import annotations

import logging

import httpx
from rich.console import Console

from specify_cli.auth import ConfigurationError, get_token_manager
from specify_cli.auth.config import get_saas_base_url

log = logging.getLogger(__name__)
console = Console()


async def logout_impl(*, force: bool) -> None:
    """Run the logout flow.

    Server-side logout failure does not block local credential deletion
    (FR-014). The ``force`` flag skips the server call entirely and only
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
        # Try to revoke the session server-side. Any failure is downgraded
        # to a warning so local cleanup still runs below.
        try:
            saas_url = get_saas_base_url()
        except ConfigurationError as exc:
            console.print(
                f"[yellow]! Cannot reach SaaS (config error): {exc}. "
                f"Proceeding with local logout only.[/yellow]"
            )
        else:
            await _call_server_logout(saas_url, session.access_token)

    # FR-014: local cleanup is unconditional. This line runs regardless of
    # the server-call outcome — 200, 4xx/5xx, network error, config error,
    # or --force. Deliberately OUTSIDE any try/except for the server call.
    tm.clear_session()
    console.print("[green]+ Logged out.[/green]")


async def _call_server_logout(saas_url: str, access_token: str) -> None:
    """Call POST ``/api/v1/logout`` with the bearer token.

    This function NEVER raises — every failure mode prints a warning and
    returns. The caller (``logout_impl``) always runs local cleanup after
    this returns, so any server-side issue just degrades gracefully.

    Per the SaaS contract (protected-endpoints.md), the logout endpoint
    is bearer-only with NO request body. The session being revoked is
    identified server-side by the bound ``session_id`` of the token, not
    by a client-provided field.
    """
    url = f"{saas_url}/api/v1/logout"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # NO body — bearer-only endpoint.
            response = await client.post(url, headers=headers)
    except httpx.RequestError as exc:
        # Network-level failure (DNS, connection refused, timeout, TLS).
        console.print(
            f"[yellow]! Server logout failed (network error: {exc}). "
            f"Local credentials will still be deleted.[/yellow]"
        )
        return
    except Exception as exc:  # noqa: BLE001 — logout must never crash the CLI
        log.warning("Unexpected exception during server logout: %s", exc)
        console.print(
            f"[yellow]! Server logout failed: {exc}. "
            f"Local credentials will still be deleted.[/yellow]"
        )
        return

    status_code = response.status_code
    if status_code == 200:
        # Success path — no message needed; the caller prints the final
        # "Logged out" banner after local cleanup.
        return
    if status_code in (401, 403):
        # Already invalid server-side; common when the access token
        # expired between the last refresh and the logout call. This is
        # not a real failure — the server-side session is already gone.
        console.print(
            f"[yellow]! Server reports session already invalid "
            f"(HTTP {status_code}). Local credentials will be deleted.[/yellow]"
        )
        return
    # Any other 4xx or 5xx: log a warning but do not fail. Users care
    # that their local credentials are gone; they can call SaaS support
    # if they need the server-side session force-cleared.
    console.print(
        f"[yellow]! Server logout returned HTTP {status_code}. "
        f"Local credentials will still be deleted.[/yellow]"
    )


__all__ = ["logout_impl"]
