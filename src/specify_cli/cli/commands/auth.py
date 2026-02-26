"""Authentication commands for spec-kitty sync."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

import typer

from specify_cli.cli.helpers import console
from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR, is_saas_sync_enabled, saas_sync_disabled_message
from specify_cli.sync.queue import (
    pending_events_for_scope,
    read_active_scope,
    read_queue_scope_from_credentials,
    write_active_scope,
)


app = typer.Typer(help="Authentication commands")


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_duration(delta: timedelta) -> str:
    """Format a timedelta as human-readable string."""
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s"
    if total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes}m"
    if total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours}h"
    days = total_seconds // 86400
    return f"{days}d"


def _handle_auth_error(message: str, server_url: str) -> None:
    lowered = message.lower()
    if "invalid username or password" in lowered or "no active account" in lowered:
        console.print("❌ Invalid username or password")
        console.print("   Please check your credentials and try again.")
    elif "cannot reach server" in lowered or "timeout" in lowered or "timed out" in lowered:
        console.print("❌ Cannot reach server. Check your connection.")
        console.print(f"   Server: {server_url}")
    elif "server error" in lowered or "temporarily unavailable" in lowered:
        console.print("❌ Server temporarily unavailable")
        console.print("   Please try again in a few minutes.")
    elif "session expired" in lowered or "refresh token" in lowered:
        console.print("❌ Session expired. Please log in again.")
    else:
        console.print(f"❌ Authentication failed: {message}")


@app.command()
def login(
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Your username or email"),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        hide_input=True,
        help="Your password",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Re-authenticate even if already logged in"),
) -> None:
    """Log in to the sync service."""
    if not is_saas_sync_enabled():
        console.print(f"❌ {saas_sync_disabled_message()}")
        console.print(f"   Set {SAAS_SYNC_ENV_VAR}=1 to enable authentication.")
        raise typer.Exit(1)

    if not username:
        username = typer.prompt("Username")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    try:
        from specify_cli.sync.auth import AuthClient, AuthenticationError
    except ImportError:
        console.print("[red]Error:[/red] Authentication module unavailable. Please upgrade spec-kitty.")
        raise typer.Exit(1)

    client = AuthClient()
    # Get raw URL for display (won't raise on non-HTTPS)
    raw_server_url = client.config.get_server_url()

    try:
        if client.is_authenticated() and not force:
            scope = read_queue_scope_from_credentials()
            if scope:
                write_active_scope(scope)
            console.print("✅ Already authenticated.")
            console.print("Use --force to re-authenticate or 'auth logout' first.")
            return

        console.print(f"Authenticating with {client.server_url}...")
        client.obtain_tokens(username, password)

        new_scope = read_queue_scope_from_credentials()
        previous_scope = read_active_scope()
        if new_scope and previous_scope and previous_scope != new_scope:
            pending = pending_events_for_scope(previous_scope)
            if pending > 0 and not force:
                # Prevent accidental cross-account data transfer.
                client.clear_credentials()
                console.print("❌ Account switch blocked: previous account has queued unsynced events.")
                console.print(f"   Pending events in previous account queue: {pending}")
                console.print("   Run 'spec-kitty sync now' before switching accounts,")
                console.print("   or re-run login with --force to keep queues isolated.")
                raise typer.Exit(1)
            if pending > 0 and force:
                console.print(
                    f"⚠️  Switching accounts with {pending} pending event(s) in the previous account queue."
                )

        if new_scope:
            write_active_scope(new_scope)

        console.print("✅ Login successful!")
        console.print(f"   Logged in as: {username}")
    except AuthenticationError as exc:
        _handle_auth_error(str(exc), raw_server_url)
        raise typer.Exit(1)
    except PermissionError:
        console.print("❌ Cannot access credentials file. Check permissions.")
        console.print("   Please ensure the file is readable and writable.")
        console.print("   Try: chmod 600 ~/.spec-kitty/credentials")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"❌ Unexpected error: {exc}")
        raise typer.Exit(1)


@app.command()
def logout() -> None:
    """Log out from the sync service."""
    try:
        from specify_cli.sync.auth import AuthClient
    except ImportError:
        console.print("[red]Error:[/red] Authentication module unavailable. Please upgrade spec-kitty.")
        raise typer.Exit(1)

    client = AuthClient()

    try:
        if not client.is_authenticated():
            console.print("ℹ️  No active session. Already logged out.")
            return

        username = client.credential_store.get_username() or "unknown"
        client.clear_credentials()
        console.print("✅ Logged out successfully.")
        console.print(f"   Cleared credentials for: {username}")
    except PermissionError:
        console.print("❌ Cannot access credentials file. Check permissions.")
        console.print("   Please ensure the file is readable and writable.")
        console.print("   Try: chmod 600 ~/.spec-kitty/credentials")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"❌ Unexpected error: {exc}")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show current authentication status."""
    if not is_saas_sync_enabled():
        console.print(f"ℹ️  {saas_sync_disabled_message()}")

    try:
        from specify_cli.sync.auth import AuthClient
    except ImportError:
        console.print("[red]Error:[/red] Authentication module unavailable. Please upgrade spec-kitty.")
        raise typer.Exit(1)

    client = AuthClient()

    try:
        if not client.is_authenticated():
            console.print("❌ Not authenticated")
            console.print("   Run 'spec-kitty auth login' to authenticate.")
            return

        username = client.credential_store.get_username() or "unknown"
        server_url = client.credential_store.get_server_url() or client.server_url
        expiry_info = client.credential_store.get_token_expiry_info() or {}

        console.print("✅ Authenticated")
        console.print(f"   Username: {username}")
        console.print(f"   Server:   {server_url}")

        now = datetime.now(timezone.utc)

        access_exp = _parse_datetime(expiry_info.get("access_expires_at"))
        if access_exp:
            if now < access_exp:
                remaining = access_exp - now
                console.print(f"   Access token: valid ({_format_duration(remaining)} remaining)")
            else:
                console.print("   Access token: expired (will refresh automatically)")
        else:
            console.print("   Access token: unknown expiry")

        refresh_exp = _parse_datetime(expiry_info.get("refresh_expires_at"))
        if refresh_exp:
            if now < refresh_exp:
                remaining = refresh_exp - now
                console.print(f"   Refresh token: valid ({_format_duration(remaining)} remaining)")
            else:
                console.print("   Refresh token: expired (re-login required)")
        else:
            console.print("   Refresh token: unknown expiry")
    except PermissionError:
        console.print("❌ Cannot access credentials file. Check permissions.")
        console.print("   Please ensure the file is readable and writable.")
        console.print("   Try: chmod 600 ~/.spec-kitty/credentials")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"❌ Unexpected error: {exc}")
        raise typer.Exit(1)


__all__ = ["app"]
