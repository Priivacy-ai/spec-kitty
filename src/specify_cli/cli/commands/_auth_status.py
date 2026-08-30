"""Implementation of ``spec-kitty auth status``. Owned by WP07.

This module is lazy-imported from ``cli.commands.auth`` when the ``status``
command fires. The dispatch shell in ``auth.py`` (owned by WP04) imports
:func:`status_impl` on demand so WP07 can ship independently of WP04's
command surface.

Output layout (spec 080 §2.4, FR-015):

- Authenticated banner
- SaaS endpoint the CLI is pointed at, with its provenance, plus a plain
  warning when the stored session was minted against a *different*
  endpoint (#176 — after a hostname move this is the line that explains
  why every call suddenly 401s); or, when ``SPEC_KITTY_SAAS_URL`` and
  ``config.toml [sync].server_url`` genuinely disagree, a split-brain line
  naming both values instead of silently picking the env one (#193)
- SaaS endpoint the stored session was minted against, when known
- email / name / user_id
- Team list with the default team marked
- Access token remaining time (human-readable)
- Refresh token remaining time (human-readable) — or a defensive
  "server-managed (legacy session)" fallback when the stored session
  pre-dates the C-012 SaaS refresh-TTL amendment (landed 2026-04-09).
  New sessions always carry a concrete ``refresh_token_expires_at``;
  the None branch only trips for replayed/legacy sessions.
- Storage backend (human label for the encrypted local session file)
- Session ID, last_used_at, auth method

The not-authenticated and session-expired early returns also print the
``SaaS:`` endpoint line — the expired case additionally gets the session
issuer + mismatch warning, since that is exactly the post-hostname-move
symptom #176 exists to diagnose (#189). ``whoami``'s separate exit-1/no-output
contract when unauthenticated is untouched.

Exit code is 0 in both authenticated and not-authenticated cases per
FR-015: ``auth status`` is purely informational and must never surface
as a failure to shells / scripts.
"""

from __future__ import annotations

from kernel.clock import UTC, datetime, now_utc
from rich.markup import escape

from specify_cli.cli.console import console

from specify_cli.auth import get_token_manager
from specify_cli.auth.errors import ConfigurationError
from specify_cli.auth.server_target import (
    SAAS_URL_ENV_VAR,
    ResolvedServerTarget,
    ServerTargetSplitBrainError,
    resolve_server_target,
)
from specify_cli.auth.session import StoredSession


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

_SAAS_STATUS_LABEL = "  SaaS:           "


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
        _print_saas_endpoint()
        console.print("  Run [bold]spec-kitty auth login[/bold] to authenticate.")
        return

    if session.is_refresh_token_expired():
        console.print("[red]X Session expired (refresh token expired)[/red]")
        _print_saas_target(session)
        console.print("  Run [bold]spec-kitty auth login[/bold] to re-authenticate.")
        return

    console.print("[green]+ Authenticated[/green]")
    console.print()

    _print_saas_target(session)
    _print_identity(session)
    console.print()

    _print_teams(session)
    console.print()

    _print_token_expiry(session)
    console.print()

    _print_storage_backend(session)
    console.print(f"  Session ID:     {session.session_id}")
    console.print(f"  Last used:      {_format_iso(session.last_used_at)}")
    console.print(f"  Auth method:    {escape(format_auth_method(session.auth_method))}")


# ---------------------------------------------------------------------------
# Section printers
# ---------------------------------------------------------------------------


def _print_saas_endpoint() -> ResolvedServerTarget | None:
    """Print the ``SaaS:`` endpoint line — the resolved URL + provenance, or
    the not-configured notice — and return the resolved target (``None`` on
    the not-configured branch).

    Split out of :func:`_print_saas_target` so callers with no
    :class:`StoredSession` (the not-authenticated branch) can print this line
    alone, without the session-issuer/mismatch parts that need one (#189).

    The URL is the *same* resolved target ``auth login`` prints
    (:func:`specify_cli.auth.server_target.resolve_server_target`), so the two
    commands can never name different endpoints. Since #179 that resolver
    fails closed when neither ``SPEC_KITTY_SAAS_URL`` nor ``config.toml``
    names a server — there is no default endpoint to fall back to — so this
    reports "not configured" (with the remedy) instead of a URL.

    Resolved with ``process_wide_override=False`` (#193): this call is purely
    descriptive (no network, no config mutation), so it should show a
    genuine env/config disagreement instead of the whole-process override
    silently picking the env value — otherwise a split-brain machine looks
    identical to a clean one here, with no hint that ``config.toml`` says
    something else. ``ServerTargetSplitBrainError`` is caught and rendered as
    a friendly line naming both values, never a traceback.
    """
    try:
        target = resolve_server_target(process_wide_override=False)
    except ServerTargetSplitBrainError as exc:
        # escape(): the message embeds the raw config/env URLs, which are
        # attacker- or fat-finger-controlled and can contain
        # `[sync]`/`[/]`-shaped substrings (#182's rationale applies here too).
        console.print(f"{_SAAS_STATUS_LABEL}[red]split-brain[/red] [dim](env and config.toml disagree)[/dim]")
        console.print(f"  [yellow]{escape(str(exc))}[/yellow]")
        return
    except ConfigurationError:
        # escape(): the remedy names `[sync].server_url` — unescaped, Rich
        # markup parses "[sync]" as a style tag and silently drops it (#182).
        remedy = escape(f"— set {SAAS_URL_ENV_VAR} (or [sync].server_url in config.toml)")
        console.print(f"{_SAAS_STATUS_LABEL}not configured [dim]{remedy}[/dim]")
        return None
    # escape(): both the resolved URL and the provenance suffix can contain
    # `[sync]`/`[/]`-shaped substrings (a config.toml server_url is
    # attacker- or fat-finger-controlled) — unescaped, Rich markup either
    # drops the bracketed text or raises MarkupError out of console.print,
    # which would violate this module's own never-fail invariant (#182).
    console.print(f"{_SAAS_STATUS_LABEL}{escape(target.resolved_server_url)} [dim]{escape(format_saas_provenance(target))}[/dim]")
    return target


def _print_saas_target(session: StoredSession) -> None:
    """Print the SaaS endpoint line (first line of the status block) plus,
    when it disagrees with where the session was minted, the mismatch warning.
    """
    target = _print_saas_endpoint()
    _print_session_issuer(session.issuer_url)
    if target is None:
        return
    warning = format_saas_mismatch_warning(
        session.issuer_url,
        source_name=saas_source_name(target),
        resolved_server_url=target.resolved_server_url,
    )
    if warning is not None:
        console.print(f"  [yellow]{escape(warning)}[/yellow]")


def _print_session_issuer(issuer_url: str | None) -> None:
    """Print where the stored session was minted, when the session knows it."""
    if issuer_url is None:
        return
    console.print(f"  Session SaaS:   {escape(_normalize_endpoint(issuer_url))} [dim](authenticated session)[/dim]")


def _print_identity(session: StoredSession) -> None:
    """Print the authenticated user's identity block."""
    if session.name and session.name != session.email:
        console.print(f"  User:           {escape(session.email)} ({escape(session.name)})")
    else:
        console.print(f"  User:           {escape(session.email)}")
    console.print(f"  User ID:        {session.user_id}")


def _print_teams(session: StoredSession) -> None:
    """Print the team list, marking the default team."""
    if not session.teams:
        console.print("  Teams:          (none)")
        return
    console.print("  Teams:")
    for team in session.teams:
        is_default = team.id == session.default_team_id
        marker_parts: list[str] = []
        if team.is_private_teamspace:
            marker_parts.append("private")
        if is_default:
            marker_parts.append("default")
        marker = f" [dim]({', '.join(marker_parts)})[/dim]" if marker_parts else ""
        console.print(f"    - {escape(team.name)} ({team.role}){marker}")


def _print_token_expiry(session: StoredSession) -> None:
    """Print access + refresh token remaining time.

    Per the C-012 SaaS refresh-TTL amendment (landed 2026-04-09) new
    sessions always carry a concrete ``refresh_token_expires_at``. The
    ``None`` branch is retained only as a defensive fallback for
    replayed/legacy sessions written before the amendment — re-login
    populates the field.
    """
    now = now_utc()
    access_remaining = (session.access_token_expires_at - now).total_seconds()
    console.print(f"  Access token:   {format_duration(access_remaining)}")

    if session.refresh_token_expires_at is None:
        console.print("  Refresh token:  [dim]server-managed (legacy session - re-login to populate refresh expiry)[/dim]")
    else:
        refresh_remaining = (session.refresh_token_expires_at - now).total_seconds()
        console.print(f"  Refresh token:  {format_duration(refresh_remaining)}")


def _print_storage_backend(session: StoredSession) -> None:
    """Print the storage backend with a user-friendly label."""
    label = escape(format_storage_backend(session.storage_backend))
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


def saas_source_name(target: ResolvedServerTarget) -> str:
    """Name the configuration source the resolved SaaS URL came from.

    Mirrors the precedence inside
    :func:`specify_cli.auth.server_target.resolve_server_target`: env first,
    then ``config.toml [sync].server_url`` — the only two sources it can
    resolve from, since #179 that resolver fails closed when neither is set.
    Used in the mismatch warning so the sentence names the thing the user
    must change. Note ``.kittify/saas-auth.json`` is deliberately absent — it
    feeds the tracker/zeitgeist transport chain, not the OAuth login target.
    """
    if target.env_server_url is not None:
        return SAAS_URL_ENV_VAR
    return "config.toml [sync].server_url"


def format_saas_provenance(target: ResolvedServerTarget) -> str:
    """Return the dim provenance suffix shown next to the ``SaaS:`` line."""
    if target.env_server_url is not None:
        return f"(from {SAAS_URL_ENV_VAR})"
    return "(from config.toml [sync].server_url)"


def format_saas_mismatch_warning(
    session_issuer_url: str | None,
    *,
    source_name: str,
    resolved_server_url: str,
) -> str | None:
    """Build the stale-session warning, or ``None`` when there is nothing to warn about.

    ``None`` when the session carries no issuer (minted before #176 recorded
    one — nothing to compare against) or when it matches the currently
    configured endpoint modulo a trailing slash.
    """
    if session_issuer_url is None:
        return None
    if _normalize_endpoint(session_issuer_url) == _normalize_endpoint(resolved_server_url):
        return None
    return f"Session is for {_normalize_endpoint(session_issuer_url)}; {source_name} now points at {resolved_server_url} — run spec-kitty auth login --force"


def _normalize_endpoint(url: str) -> str:
    """Normalize a URL for endpoint comparison.

    Same semantics as ``server_target._normalize_url`` (strip surrounding
    whitespace, drop one trailing slash); kept local so the comparison does
    not reach into another module's private helper.
    """
    return url.strip().rstrip("/")


def _format_iso(dt: datetime) -> str:
    """Render a datetime as an ISO-8601 UTC string for display."""
    # Normalize to UTC then strip microseconds for display compactness.
    dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "status_impl",
    "format_duration",
    "format_storage_backend",
    # format_auth_method: demoted — no cross-module src/ callers (WP01).
    # format_saas_provenance: demoted — called within this module (and
    # unit-tested directly), with no other src/ consumer (#176).
    # format_saas_mismatch_warning / saas_source_name: demoted from __all__,
    # but still imported cross-module by _auth_doctor.py — keep exporting
    # them from this module rather than treating them as module-private.
]
