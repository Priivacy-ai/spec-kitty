"""Authentication commands for spec-kitty sync."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

import typer

from specify_cli.cli.helpers import console


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
    username: str = typer.Option(None, "--username", "-u", prompt=True, help="Your username or email"),
    password: str = typer.Option(
        None,
        "--password",
        "-p",
        prompt=True,
        hide_input=True,
        help="Your password",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Re-authenticate even if already logged in"),
) -> None:
    """Log in to the sync service."""
    try:
        from specify_cli.sync.auth import AuthClient, AuthenticationError
    except ImportError:
        console.print("[red]Error:[/red] Authentication module unavailable. Please upgrade spec-kitty.")
        raise typer.Exit(1)

    client = AuthClient()

    try:
        if client.is_authenticated() and not force:
            console.print("✅ Already authenticated.")
            console.print("Use --force to re-authenticate or 'auth logout' first.")
            return

        console.print(f"Authenticating with {client.server_url}...")
        client.obtain_tokens(username, password)
        console.print("✅ Login successful!")
        console.print(f"   Logged in as: {username}")
    except AuthenticationError as exc:
        _handle_auth_error(str(exc), client.server_url)
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
