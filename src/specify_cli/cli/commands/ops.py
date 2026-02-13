"""Ops command - operation history and undo functionality.

This command provides access to VCS operation history and undo capabilities.
For jj, this leverages the full operation log with undo support.
For git, this provides read-only access to the reflog.

Key differences:
- jj: Full operation log with complete undo capability
- git: Reflog as read-only operation history (no undo)
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.core.vcs import (
    OperationInfo,
    VCSBackend,
    get_vcs,
)

app = typer.Typer(
    name="ops",
    help="Operation history and undo (jj: full undo, git: reflog only)",
    no_args_is_help=True,
)

console = Console()


def _display_operations(ops: list[OperationInfo], backend: VCSBackend) -> None:
    """Display operation history in a formatted table.

    Args:
        ops: List of operations to display
        backend: VCS backend (affects column display)
    """
    if not ops:
        console.print("[dim]No operations found[/dim]")
        return

    backend_label = "jj" if backend == VCSBackend.JUJUTSU else "git reflog"
    table = Table(title=f"Operation History ({backend_label})")

    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Time", style="dim")
    table.add_column("Description")

    if backend == VCSBackend.JUJUTSU:
        table.add_column("Undoable", style="green", justify="center")

    for op in ops:
        # Truncate operation ID for display
        short_id = op.operation_id[:12] if len(op.operation_id) > 12 else op.operation_id

        # Format timestamp
        time_str = op.timestamp.strftime("%Y-%m-%d %H:%M")

        # Truncate description if too long
        desc = op.description[:60] + "..." if len(op.description) > 60 else op.description

        row = [short_id, time_str, desc]

        if backend == VCSBackend.JUJUTSU:
            row.append("✓" if op.is_undoable else "")

        table.add_row(*row)

    console.print(table)


@app.command()
def log(
    limit: int = typer.Option(
        20,
        "--limit",
        "-n",
        help="Number of operations to show",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show full operation IDs and details",
    ),
) -> None:
    """Show operation history.

    For jj workspaces, shows the operation log with undo information.
    For git workspaces, shows the reflog (read-only history).

    Examples:
        # Show recent operations
        spec-kitty ops log

        # Show last 5 operations
        spec-kitty ops log --limit 5

        # Show with full details
        spec-kitty ops log --verbose
    """
    workspace_path = Path.cwd()

    # Get VCS implementation
    try:
        vcs = get_vcs(workspace_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to detect VCS: {e}")
        raise typer.Exit(1)

    console.print(f"\n[cyan]Backend:[/cyan] git")
    console.print()

    # Get operation history (git reflog only)
    from specify_cli.core.vcs.git import git_get_reflog

    ops = git_get_reflog(workspace_path, limit=limit)

    _display_operations(ops, vcs.backend)

    if verbose and ops:
        console.print("\n[dim]Full operation IDs:[/dim]")
        for op in ops[:5]:  # Show first 5 full IDs
            console.print(f"  {op.operation_id}")

    console.print()


@app.command()
def undo(
    operation_id: str = typer.Argument(
        None,
        help="Operation ID to undo (jj only, defaults to last operation)",
    ),
) -> None:
    """Undo last operation (jj only).

    Reverts the repository to the state before the last operation.
    This is only supported for jj workspaces - git does not have
    reversible operation history.

    Examples:
        # Undo last operation
        spec-kitty ops undo

        # Undo specific operation
        spec-kitty ops undo abc123def456
    """
    workspace_path = Path.cwd()

    # Get VCS implementation
    try:
        vcs = get_vcs(workspace_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to detect VCS: {e}")
        raise typer.Exit(1)

    # Capability check - undo only supported for jj
    if not vcs.capabilities.supports_operation_undo:
        console.print(f"\n[red]✗ Undo not supported for {vcs.backend.value}[/red]")
        console.print()
        console.print("[dim]Git does not have reversible operation history.[/dim]")
        console.print("[dim]Consider using these alternatives manually:[/dim]")
        console.print("  • git reset --soft HEAD~1  (undo last commit, keep changes)")
        console.print("  • git reset --hard HEAD~1  (undo last commit, discard changes)")
        console.print("  • git revert <commit>      (create reverting commit)")
        console.print("  • git reflog               (find previous states)")
        console.print()
        raise typer.Exit(1)

    # jj undo
    console.print("\n[cyan]Undoing operation...[/cyan]")

    from specify_cli.core.vcs.jujutsu import jj_undo_operation

    success = jj_undo_operation(workspace_path, operation_id)

    if success:
        console.print("[green]✓ Operation undone successfully[/green]")
        console.print()
        console.print("[dim]Use 'spec-kitty ops log' to see the updated history.[/dim]")
    else:
        console.print("[red]✗ Undo failed[/red]")
        console.print()
        console.print("[dim]Try these commands to debug:[/dim]")
        console.print("  jj op log          # View operation history")
        console.print("  jj status          # Check current state")
        raise typer.Exit(1)

    console.print()


@app.command()
def restore(
    operation_id: str = typer.Argument(
        ...,
        help="Operation ID to restore to (jj only)",
    ),
) -> None:
    """Restore to a specific operation (jj only).

    Restores the repository to the exact state at a specific operation.
    This is more powerful than undo - it can jump to any point in history.

    Examples:
        # Restore to specific operation
        spec-kitty ops restore abc123def456
    """
    workspace_path = Path.cwd()

    # Get VCS implementation
    try:
        vcs = get_vcs(workspace_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to detect VCS: {e}")
        raise typer.Exit(1)

    # Capability check - restore only supported for jj
    if not vcs.capabilities.supports_operation_undo:
        console.print(f"\n[red]✗ Restore not supported for {vcs.backend.value}[/red]")
        console.print()
        console.print("[dim]Git does not support operation-level restore.[/dim]")
        console.print("[dim]Consider using these alternatives:[/dim]")
        console.print("  • git checkout <commit>    (detached HEAD)")
        console.print("  • git reset --hard <commit>(destructive)")
        console.print()
        raise typer.Exit(1)

    # jj restore
    console.print(f"\n[cyan]Restoring to operation {operation_id[:12]}...[/cyan]")

    import subprocess

    try:
        result = subprocess.run(
            ["jj", "op", "restore", operation_id],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
        )

        if result.returncode == 0:
            console.print("[green]✓ Restored successfully[/green]")
            console.print()
            console.print("[dim]Use 'spec-kitty ops log' to see the updated history.[/dim]")
        else:
            console.print("[red]✗ Restore failed[/red]")
            if result.stderr:
                console.print(f"[dim]{result.stderr.strip()}[/dim]")
            raise typer.Exit(1)

    except subprocess.TimeoutExpired:
        console.print("[red]✗ Restore timed out[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]✗ jj command not found[/red]")
        raise typer.Exit(1)

    console.print()
