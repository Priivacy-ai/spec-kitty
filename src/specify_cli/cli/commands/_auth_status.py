"""Implementation of ``spec-kitty auth status``. Owned by WP07.

This module is lazy-imported from ``cli.commands.auth`` when the ``status``
command fires. The dispatch shell in ``auth.py`` (owned by WP04) imports
:func:`status_impl` on demand so WP07 can ship independently of WP04's
command surface.

Output layout (spec 080 §2.4, FR-015):

- Authenticated banner + email / name / user_id
- Team list with the default team marked
- Access token remaining time (human-readable)
- Refresh token remaining time (human-readable) — or a defensive
  "server-managed (legacy session)" fallback when the stored session
  pre-dates the C-012 SaaS refresh-TTL amendment (landed 2026-04-09).
  New sessions always carry a concrete ``refresh_token_expires_at``;
  the None branch only trips for replayed/legacy sessions.
- Storage backend (human label for the encrypted local session file)
- Session ID, last_used_at, auth method

Exit code is 0 in both authenticated and not-authenticated cases per
FR-015: ``auth status`` is purely informational and must never surface
as a failure to shells / scripts.
"""

from __future__ import annotations

from datetime import datetime, UTC

from rich.console import Console

from specify_cli.auth import get_token_manager
from specify_cli.auth.session import StoredSession

console = Console()

# Mapping from the StorageBackend literal (see session.py) to a
# user-friendly label. Keep this in sync with the supported encrypted-file
# storage implementation in ``specify_cli.auth.secure_storage``.
_STORAGE_LABELS: dict[str, str] = {
    "file": "Encrypted session file",
}

# Mapping from the AuthMethod literal (see session.py) to a user-facing
# label. Keep this in sync with ``AuthMethod`` values.
_AUTH_METHOD_LABELS: dict[str, str] = {
    "authorization_code": "Browser (Authorization Code + PKCE)",
    "device_code": "Headless (Device Authorization Grant)",
}


def status_impl() -> None:
    """Print the current authentication status.

    Called by the Typer shell in ``cli.commands.auth``. Never raises —
    unauthenticated and expired sessions surface as friendly messages on
    stdout with a zero exit code.
    """
    tm = get_token_manager()
    session = tm.get_current_session()

    if session is None:
        console.print("[red]X Not authenticated[/red]")
        console.print(
            "  Run [bold]spec-kitty auth login[/bold] to authenticate."
        )
        return

    if session.is_refresh_token_expired():
        console.print("[red]X Session expired (refresh token expired)[/red]")
        console.print(
            "  Run [bold]spec-kitty auth login[/bold] to re-authenticate."
        )
        return

    console.print("[green]+ Authenticated[/green]")
    console.print()

    _print_identity(session)
    console.print()

    _print_teams(session)
    console.print()

    _print_token_expiry(session)
    console.print()

    _print_storage_backend(session)
    console.print(f"  Session ID:     {session.session_id}")
    console.print(f"  Last used:      {_format_iso(session.last_used_at)}")
    console.print(f"  Auth method:    {format_auth_method(session.auth_method)}")


# ---------------------------------------------------------------------------
# Section printers
# ---------------------------------------------------------------------------


def _print_identity(session: StoredSession) -> None:
    """Print the authenticated user's identity block."""
    if session.name and session.name != session.email:
        console.print(f"  User:           {session.email} ({session.name})")
    else:
        console.print(f"  User:           {session.email}")
    console.print(f"  User ID:        {session.user_id}")


def _print_teams(session: StoredSession) -> None:
    """Print the team list, marking the default team."""
    if not session.teams:
        console.print("  Teams:          (none)")
        return
    console.print("  Teams:")
    for team in session.teams:
        is_default = team.id == session.default_team_id
        # Parens (not square brackets) because Rich treats bracketed
        # tokens as style markup — ``[default]`` would be consumed as a
        # color name and silently stripped. ``(default)`` is also more
        # readable in a plain terminal.
        marker = " [dim](default)[/dim]" if is_default else ""
        console.print(f"    - {team.name} ({team.role}){marker}")


def _print_token_expiry(session: StoredSession) -> None:
    """Print access + refresh token remaining time.

    Per the C-012 SaaS refresh-TTL amendment (landed 2026-04-09) new
    sessions always carry a concrete ``refresh_token_expires_at``. The
    ``None`` branch is retained only as a defensive fallback for
    replayed/legacy sessions written before the amendment — re-login
    populates the field.
    """
    now = datetime.now(UTC)
    access_remaining = (session.access_token_expires_at - now).total_seconds()
    console.print(f"  Access token:   {format_duration(access_remaining)}")

    if session.refresh_token_expires_at is None:
        console.print(
            "  Refresh token:  [dim]server-managed "
            "(legacy session - re-login to populate refresh expiry)[/dim]"
        )
    else:
        refresh_remaining = (
            session.refresh_token_expires_at - now
        ).total_seconds()
        console.print(f"  Refresh token:  {format_duration(refresh_remaining)}")


def _print_storage_backend(session: StoredSession) -> None:
    """Print the storage backend with a user-friendly label."""
    label = format_storage_backend(session.storage_backend)
    console.print(f"  Storage:        {label}")


# ---------------------------------------------------------------------------
# Pure formatters (unit-tested in isolation)
# ---------------------------------------------------------------------------


def format_duration(seconds: float) -> str:
    """Convert seconds-until-expiry into a human-readable string.

    Branch map (all five branches have direct unit tests):

    - ``seconds <= 0`` -> ``"[red]expired[/red]"``
    - ``0 < seconds < 60`` -> ``"< 1 minute"``
    - ``60 <= seconds < 3600`` -> ``"N minutes"`` (singular/plural aware)
    - ``3600 <= seconds < 86400`` -> ``"N hours"``
    - ``seconds >= 86400`` -> ``"N days"``

    The strings deliberately omit an "expires in " prefix so callers can
    compose sentences like ``f"Access token:   {format_duration(s)}"``.
    """
    if seconds <= 0:
        return "[red]expired[/red]"
    if seconds < 60:
        return "< 1 minute"
    if seconds < 3600:
        minutes = int(seconds // 60)
        suffix = "minute" if minutes == 1 else "minutes"
        return f"{minutes} {suffix}"
    if seconds < 86400:
        hours = int(seconds // 3600)
        suffix = "hour" if hours == 1 else "hours"
        return f"{hours} {suffix}"
    days = int(seconds // 86400)
    suffix = "day" if days == 1 else "days"
    return f"{days} {suffix}"


def format_storage_backend(backend: str) -> str:
    """Convert a ``StorageBackend`` literal to a user-facing label.

    Unknown values fall through to ``"Unknown (X)"`` so a mis-wired
    backend surfaces loudly instead of silently swallowing the identifier.
    """
    return _STORAGE_LABELS.get(backend, f"Unknown ({backend})")


def format_auth_method(method: str) -> str:
    """Convert an ``AuthMethod`` literal to a user-facing label."""
    return _AUTH_METHOD_LABELS.get(method, f"Unknown ({method})")


def _format_iso(dt: datetime) -> str:
    """Render a datetime as an ISO-8601 UTC string for display."""
    # Normalize to UTC then strip microseconds for display compactness.
    dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "status_impl",
    "format_duration",
    "format_storage_backend",
    "format_auth_method",
]
