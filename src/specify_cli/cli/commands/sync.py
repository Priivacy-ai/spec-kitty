"""Sync commands - workspace synchronization and connection status.

This module provides two groups of sync functionality:
1. Workspace sync: updates workspace with changes from base branch
2. Connection status: shows WebSocket sync connection state
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from specify_cli.core.vcs import (
    ChangeInfo,
    ConflictInfo,
    SyncResult,
    SyncStatus,
    VCSBackend,
    get_vcs,
)

console = Console()

# Create a Typer app for sync subcommands
app = typer.Typer(
    help="Synchronization commands",
    no_args_is_help=True,
)


def _detect_workspace_context() -> tuple[Path, str | None]:
    """Detect current workspace and feature context.

    Returns:
        Tuple of (workspace_path, feature_slug)
        If not in a workspace, returns (cwd, None)
    """
    cwd = Path.cwd()

    # Check if we're in a .worktrees directory
    parts = cwd.parts
    for i, part in enumerate(parts):
        if part == ".worktrees" and i + 1 < len(parts):
            # Found a worktree path like: /repo/.worktrees/010-feature-WP01
            workspace_name = parts[i + 1]
            # Extract feature slug from workspace name (###-feature-WP##)
            match = re.match(r"^(\d{3}-[a-zA-Z0-9-]+)-WP\d+$", workspace_name)
            if match:
                return cwd, match.group(1)

    # Try to detect from git branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        if result.returncode == 0:
            branch_name = result.stdout.strip()
            # Check if branch matches WP pattern (###-feature-WP##)
            match = re.match(r"^(\d{3}-[a-zA-Z0-9-]+)-WP\d+$", branch_name)
            if match:
                return cwd, match.group(1)
    except (FileNotFoundError, OSError):
        pass

    # Not in a recognized workspace
    return cwd, None


def _display_changes_integrated(changes: list[ChangeInfo]) -> None:
    """Display changes that were integrated during sync."""
    if not changes:
        return

    console.print(f"\n[cyan]Changes integrated ({len(changes)}):[/cyan]")
    for change in changes[:5]:  # Show first 5 changes
        short_id = change.commit_id[:7] if change.commit_id else "unknown"
        # Truncate message to 50 chars
        msg = change.message[:50] + "..." if len(change.message) > 50 else change.message
        console.print(f"  • [dim]{short_id}[/dim] {msg}")

    if len(changes) > 5:
        console.print(f"  [dim]... and {len(changes) - 5} more[/dim]")


def _display_conflicts(conflicts: list[ConflictInfo]) -> None:
    """Display conflicts with actionable details.

    Shows:
    - File path
    - Line ranges (if available)
    - Conflict type
    - Resolution hints
    """
    if not conflicts:
        return

    console.print(f"\n[yellow]Conflicts ({len(conflicts)} files):[/yellow]")

    # Create a table for better formatting
    table = Table(show_header=True, header_style="bold yellow", show_lines=False)
    table.add_column("File", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Lines", style="dim")

    for conflict in conflicts:
        # Format line ranges
        if conflict.line_ranges:
            lines = ", ".join(f"{start}-{end}" for start, end in conflict.line_ranges)
        else:
            lines = "entire file"

        table.add_row(
            str(conflict.file_path),
            conflict.conflict_type.value,
            lines,
        )

    console.print(table)

    # Show resolution hints
    console.print("\n[dim]To resolve conflicts:[/dim]")
    console.print("[dim]  1. Edit the conflicted files to resolve markers[/dim]")
    console.print("[dim]  2. Continue your work (jj) or commit resolution (git)[/dim]")


def _git_repair(workspace_path: Path) -> bool:
    """Attempt git workspace recovery.

    This is a best-effort recovery that tries:
    1. Abort any in-progress rebase/merge
    2. Reset to HEAD

    Returns:
        True if recovery succeeded, False otherwise

    Note: This may lose uncommitted work.
    """
    try:
        # First, try to abort any in-progress operations
        for abort_cmd in [
            ["git", "rebase", "--abort"],
            ["git", "merge", "--abort"],
            ["git", "cherry-pick", "--abort"],
        ]:
            subprocess.run(
                abort_cmd,
                cwd=workspace_path,
                capture_output=True,
                check=False,
                timeout=10,
            )

        # Reset to HEAD (keeping changes in working tree)
        result = subprocess.run(
            ["git", "reset", "--mixed", "HEAD"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

        return result.returncode == 0

    except (subprocess.TimeoutExpired, OSError):
        return False


def _jj_repair(workspace_path: Path) -> bool:
    """Attempt jj workspace recovery via operation undo.

    Jujutsu has much better recovery capabilities via the operation log.
    This function tries to undo the last operation.

    Returns:
        True if recovery succeeded, False otherwise
    """
    try:
        # Try to undo the last operation
        result = subprocess.run(
            ["jj", "undo"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

        if result.returncode == 0:
            return True

        # If undo fails, try to update the workspace
        result = subprocess.run(
            ["jj", "workspace", "update-stale"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

        return result.returncode == 0

    except (subprocess.TimeoutExpired, OSError):
        return False


@app.command(name="workspace")
def sync_workspace(
    repair: bool = typer.Option(
        False,
        "--repair",
        "-r",
        help="Attempt workspace recovery (may lose uncommitted work)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed sync output",
    ),
) -> None:
    """Synchronize workspace with upstream changes.

    Updates the current workspace with changes from its base branch or parent.
    This is equivalent to:
    - git: `git rebase <base-branch>`
    - jj: `jj workspace update-stale` + auto-rebase

    Key difference between VCS backends:
    - git: Sync may FAIL on conflicts (must resolve before continuing)
    - jj: Sync always SUCCEEDS (conflicts stored, resolve later)

    Examples:
        # Sync current workspace
        spec-kitty sync workspace

        # Sync with verbose output
        spec-kitty sync workspace --verbose

        # Attempt recovery from broken state
        spec-kitty sync workspace --repair
    """
    console.print()

    # Detect workspace context
    workspace_path, feature_slug = _detect_workspace_context()

    if feature_slug is None:
        console.print("[yellow]⚠ Not in a recognized workspace[/yellow]")
        console.print("Run this command from a worktree directory:")
        console.print("  cd .worktrees/<feature>-WP##/")
        raise typer.Exit(1)

    console.print(f"[cyan]Workspace:[/cyan] {workspace_path.name}")

    # Get VCS implementation
    try:
        vcs = get_vcs(workspace_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to detect VCS: {e}")
        raise typer.Exit(1)

    console.print(f"[cyan]Backend:[/cyan] git")
    console.print()

    # Handle repair mode
    if repair:
        console.print("[yellow]Attempting workspace recovery...[/yellow]")
        console.print("[dim]Note: This may lose uncommitted work[/dim]")
        console.print()

        if vcs.backend == VCSBackend.JUJUTSU:
            success = _jj_repair(workspace_path)
        else:
            success = _git_repair(workspace_path)

        if success:
            console.print("[green]✓ Recovery successful[/green]")
            console.print("Workspace state has been reset.")
        else:
            console.print("[red]✗ Recovery failed[/red]")
            console.print("Manual intervention may be required.")
            console.print()
            if vcs.backend == VCSBackend.GIT:
                console.print("[dim]Try these commands manually:[/dim]")
                console.print("  git status")
                console.print("  git rebase --abort")
                console.print("  git reset --hard HEAD")
            else:
                console.print("[dim]Try these commands manually:[/dim]")
                console.print("  jj status")
                console.print("  jj op log")
                console.print("  jj undo")
            raise typer.Exit(1)

        return

    # Perform sync
    console.print("[cyan]Syncing workspace...[/cyan]")

    result: SyncResult = vcs.sync_workspace(workspace_path)

    # Display result based on status
    if result.status == SyncStatus.UP_TO_DATE:
        console.print("\n[green]✓ Already up to date[/green]")
        if result.message:
            console.print(f"[dim]{result.message}[/dim]")

    elif result.status == SyncStatus.SYNCED:
        stats_parts = []
        if result.files_updated > 0:
            stats_parts.append(f"{result.files_updated} updated")
        if result.files_added > 0:
            stats_parts.append(f"{result.files_added} added")
        if result.files_deleted > 0:
            stats_parts.append(f"{result.files_deleted} deleted")

        stats = ", ".join(stats_parts) if stats_parts else "no file changes"
        console.print(f"\n[green]✓ Synced[/green] - {stats}")

        if verbose:
            _display_changes_integrated(result.changes_integrated)

        if result.message:
            console.print(f"[dim]{result.message}[/dim]")

    elif result.status == SyncStatus.CONFLICTS:
        # jj: This means sync succeeded but there are conflicts to resolve
        console.print("\n[yellow]⚠ Synced with conflicts[/yellow]")

        if vcs.backend == VCSBackend.JUJUTSU:
            console.print("[dim]Conflicts are stored in the commit.[/dim]")
            console.print("[dim]You can continue working and resolve later.[/dim]")
        else:
            console.print("[dim]You must resolve conflicts before continuing.[/dim]")

        _display_conflicts(result.conflicts)

        if verbose:
            _display_changes_integrated(result.changes_integrated)

    elif result.status == SyncStatus.FAILED:
        console.print(f"\n[red]✗ Sync failed[/red]")
        if result.message:
            console.print(f"[dim]{result.message}[/dim]")

        # Show conflicts if any
        if result.conflicts:
            _display_conflicts(result.conflicts)

        console.print()
        console.print("[dim]Try:[/dim]")
        console.print("  spec-kitty sync workspace --repair")
        raise typer.Exit(1)

    console.print()


def _check_server_connection(server_url: str) -> tuple[str, str]:
    """Probe the batch endpoint using the user's real auth token.

    Returns:
        Tuple of (rich-formatted status string, detail message).
    """
    import httpx
    from specify_cli.sync.auth import AuthClient, AuthenticationError, CredentialStore

    # Step 1: Check if credentials exist at all
    store = CredentialStore()
    if not store.exists():
        return (
            "[yellow]Not authenticated[/yellow]",
            "Run `spec-kitty auth login` to connect.",
        )

    # Step 2: Get a valid access token (with auto-refresh if expired)
    auth = AuthClient()
    try:
        access_token = auth.get_access_token()
    except Exception:
        access_token = None

    if not access_token:
        # Access token expired and refresh also failed
        return (
            "[yellow]Session expired[/yellow]",
            "Run `spec-kitty auth login` to re-authenticate.",
        )

    # Step 3: Probe the batch endpoint with an empty events list
    batch_url = f"{server_url.rstrip('/')}/api/v1/events/batch/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = b'{"events": []}'

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(batch_url, content=payload, headers=headers)

        if response.status_code == 200:
            return (
                "[green]Connected[/green]",
                "Server reachable, authentication valid.",
            )
        elif response.status_code == 401:
            return (
                "[yellow]Authentication failed[/yellow]",
                "Run `spec-kitty auth login` to re-authenticate.",
            )
        elif response.status_code == 403:
            return (
                "[yellow]Permission denied[/yellow]",
                "Check team membership for this project.",
            )
        else:
            return (
                "[yellow]Unexpected[/yellow]",
                f"Server returned HTTP {response.status_code}.",
            )
    except httpx.TimeoutException:
        return (
            "[red]Unreachable[/red]",
            "Connection timeout (server may be down). Events will be queued for later sync.",
        )
    except httpx.ConnectError:
        return (
            "[red]Unreachable[/red]",
            "Connection refused. Events will be queued for later sync.",
        )
    except Exception as e:
        return (
            "[red]Error[/red]",
            f"Probe failed: {str(e)[:80]}",
        )


@app.command(name="server")
def sync_server(
    url: str | None = typer.Argument(
        None,
        help="Sync server URL to set (must be https://...)",
    ),
) -> None:
    """Show or set sync server URL.

    Examples:
        spec-kitty sync server
        spec-kitty sync server https://spec-kitty-dev.fly.dev
    """
    from specify_cli.sync.config import SyncConfig

    config = SyncConfig()
    if url is None:
        console.print(f"Server URL: [cyan]{config.get_server_url()}[/cyan]")
        console.print(f"Config File: [dim]{config.config_file}[/dim]")
        return

    normalized_url = url.strip().rstrip("/")
    parsed = urlparse(normalized_url)
    if parsed.scheme != "https" or not parsed.netloc:
        console.print(
            "[red]Error:[/red] Invalid server URL. Use a full HTTPS URL, "
            "for example: https://spec-kitty-dev.fly.dev"
        )
        raise typer.Exit(1)

    config.set_server_url(normalized_url)
    console.print(f"[green]✓[/green] Sync server set to [cyan]{normalized_url}[/cyan]")
    console.print(
        "[dim]If you switched environments, run "
        "'spec-kitty auth login --force' to refresh credentials.[/dim]"
    )


@app.command()
def now() -> None:
    """Trigger immediate sync of all queued events.

    Drains the offline queue completely, uploading events to the server
    in batches of 1000 until the queue is empty or all remaining events
    have exceeded their retry limit.

    Examples:
        spec-kitty sync now
    """
    from specify_cli.sync.background import get_sync_service

    service = get_sync_service()
    queue_size = service.queue.size()

    if queue_size == 0:
        console.print("[dim]Queue is empty, nothing to sync.[/dim]")
        return

    console.print(f"Syncing {queue_size} queued event(s)...")
    result = service.sync_now()

    console.print(
        f"[green]Synced:[/green] {result.synced_count}  "
        f"[dim]Duplicates:[/dim] {result.duplicate_count}  "
        f"[red]Errors:[/red] {result.error_count}"
    )
    if result.error_messages:
        for err in result.error_messages:
            console.print(f"  [red]Error:[/red] {err}")


@app.command()
def status(
    check_connection: bool = typer.Option(
        False,
        "--check",
        "-c",
        help="Test connection to server (may be slow if server is unreachable)",
    ),
) -> None:
    """Show sync queue status, connection state, and auth info.

    Displays:
    - Offline queue size
    - Connection / emitter status
    - Last sync timestamp
    - Auth status
    - Server URL configuration

    Use --check to test actual connectivity (adds 3s timeout if server unreachable).

    Examples:
        # Show status (fast)
        spec-kitty sync status

        # Test connection to server
        spec-kitty sync status --check
    """
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.events import get_emitter
    from specify_cli.sync.background import get_sync_service

    console.print()
    console.print("[cyan]Spec Kitty Sync Status[/cyan]")
    console.print()

    # Load configuration
    config = SyncConfig()
    server_url = config.get_server_url()

    emitter = get_emitter()
    service = get_sync_service()

    # Display status
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")

    # Queue size
    queue_size = service.queue.size()
    queue_color = "green" if queue_size == 0 else "yellow"
    table.add_row("Queue", f"[{queue_color}]{queue_size} event(s)[/{queue_color}]")

    # Connection status
    conn_status = emitter.get_connection_status()
    conn_color = "green" if conn_status == "Connected" else "yellow"
    table.add_row("Connection", f"[{conn_color}]{conn_status}[/{conn_color}]")

    # Last sync
    if service.last_sync:
        table.add_row("Last Sync", service.last_sync.strftime("%Y-%m-%d %H:%M:%S UTC"))
    else:
        table.add_row("Last Sync", "[dim]Never[/dim]")

    # Background service
    bg_status = "[green]Running[/green]" if service.is_running else "[dim]Stopped[/dim]"
    table.add_row("Background", bg_status)

    if service.consecutive_failures > 0:
        table.add_row("Failures", f"[yellow]{service.consecutive_failures} consecutive[/yellow]")

    # Auth status
    auth_ok = emitter.auth.is_authenticated()
    auth_text = "[green]Authenticated[/green]" if auth_ok else "[yellow]Not authenticated[/yellow]"
    table.add_row("Auth", auth_text)

    # Server URL
    table.add_row("Server URL", server_url)
    table.add_row("Config File", str(config.config_file))

    # Optionally test connection if --check flag is provided
    if check_connection:
        connection_status, connection_note = _check_server_connection(server_url)
        table.add_row("Ping", connection_status)
        if connection_note:
            table.add_row("", f"[dim]{connection_note}[/dim]")

    console.print(table)
    console.print()

    if not check_connection:
        console.print("[dim]Use 'spec-kitty sync status --check' to test connectivity.[/dim]")
        console.print()


__all__ = ["app"]
