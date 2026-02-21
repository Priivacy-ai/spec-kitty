"""Context command - query workspace context information.

Provides visibility into current workspace context for LLM agents and users.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.tasks_support import find_repo_root, TaskCliError
from specify_cli.workspace_context import (
    cleanup_orphaned_contexts,
    find_orphaned_contexts,
    list_contexts,
    load_context,
)

console = Console()
app = typer.Typer(help="Query workspace context information")


def detect_current_workspace(cwd: Path, repo_root: Path) -> str | None:
    """Detect if current directory is inside a worktree.

    Args:
        cwd: Current working directory
        repo_root: Repository root path

    Returns:
        Workspace name if inside worktree, None otherwise
    """
    # Check if .worktrees is in path
    if ".worktrees" not in cwd.parts:
        return None

    # Extract workspace name from path
    for i, part in enumerate(cwd.parts):
        if part == ".worktrees" and i + 1 < len(cwd.parts):
            return cwd.parts[i + 1]

    return None


@app.command(name="info")
def info_command(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace name (auto-detected if inside worktree)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
) -> None:
    """Show context information for current or specified workspace.

    Examples:
        # Auto-detect from current directory (if inside worktree)
        spec-kitty context info

        # Explicit workspace
        spec-kitty context info --workspace 010-feature-WP02

        # JSON output
        spec-kitty context info --json
    """
    try:
        repo_root = find_repo_root()
    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Auto-detect workspace if not provided
    if workspace is None:
        workspace = detect_current_workspace(Path.cwd(), repo_root)
        if workspace is None:
            console.print("[red]Error:[/red] Not inside a worktree and no --workspace specified")
            console.print("\nRun from inside a worktree or use --workspace flag:")
            console.print("  spec-kitty context info --workspace 010-feature-WP02")
            raise typer.Exit(1)

    # Load context
    context = load_context(repo_root, workspace)
    if context is None:
        console.print(f"[red]Error:[/red] No context found for workspace: {workspace}")
        console.print("\nContext file not found:")
        console.print(f"  {repo_root / '.kittify' / 'workspaces' / f'{workspace}.json'}")
        raise typer.Exit(1)

    # Output
    if json_output:
        print(json.dumps(context.to_dict(), indent=2))
    else:
        console.print("\n[bold cyan]📍 Workspace Context[/bold cyan]")
        console.print("─" * 50)

        # Build info table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="dim")
        table.add_column("Value")

        table.add_row("Work Package", f"[bold]{context.wp_id}[/bold]")
        table.add_row("Feature", context.feature_slug)
        table.add_row("Base Branch", f"[cyan]{context.base_branch}[/cyan]")
        table.add_row("Base Commit", f"[dim]{context.base_commit[:12]}[/dim]")
        table.add_row("Dependencies", ", ".join(context.dependencies) if context.dependencies else "[dim]none[/dim]")
        table.add_row("Created", context.created_at)
        table.add_row("Worktree", context.worktree_path)
        table.add_row("Branch", context.branch_name)
        table.add_row("VCS Backend", context.vcs_backend)

        console.print(table)
        console.print()


@app.command(name="list")
def list_command(
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    show_orphaned: bool = typer.Option(False, "--orphaned", help="Show only orphaned contexts"),
) -> None:
    """List all workspace contexts.

    Examples:
        # List all contexts
        spec-kitty context list

        # List only orphaned contexts (worktree deleted)
        spec-kitty context list --orphaned

        # JSON output
        spec-kitty context list --json
    """
    try:
        repo_root = find_repo_root()
    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if show_orphaned:
        orphaned = find_orphaned_contexts(repo_root)
        if json_output:
            print(json.dumps([{"workspace": name, "context": ctx.to_dict()} for name, ctx in orphaned], indent=2))
        else:
            if not orphaned:
                console.print("[green]✓[/green] No orphaned contexts found")
                return

            console.print(f"\n[yellow]⚠️  Found {len(orphaned)} orphaned context(s)[/yellow]\n")
            for name, ctx in orphaned:
                console.print(f"  [bold]{name}[/bold]")
                console.print(f"    Worktree: [dim]{ctx.worktree_path} (deleted)[/dim]")
                console.print(f"    Created: {ctx.created_at}")
                console.print()

            console.print("[dim]Clean up with: spec-kitty context cleanup[/dim]\n")
    else:
        contexts = list_contexts(repo_root)
        if json_output:
            print(json.dumps([ctx.to_dict() for ctx in contexts], indent=2))
        else:
            if not contexts:
                console.print("[dim]No workspace contexts found[/dim]")
                return

            console.print(f"\n[bold]Workspace Contexts[/bold] ({len(contexts)} total)\n")

            table = Table(show_header=True)
            table.add_column("WP", style="bold")
            table.add_column("Feature", style="dim")
            table.add_column("Base", style="cyan")
            table.add_column("Dependencies")
            table.add_column("Status")

            for ctx in sorted(contexts, key=lambda c: (c.feature_slug, c.wp_id)):
                # Check if worktree exists
                worktree_path = repo_root / ctx.worktree_path
                status = "[green]Active[/green]" if worktree_path.exists() else "[yellow]Orphaned[/yellow]"

                deps = ", ".join(ctx.dependencies) if ctx.dependencies else "[dim]none[/dim]"

                table.add_row(
                    ctx.wp_id,
                    ctx.feature_slug,
                    ctx.base_branch,
                    deps,
                    status,
                )

            console.print(table)
            console.print()


@app.command(name="cleanup")
def cleanup_command(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be cleaned up without deleting"),
) -> None:
    """Clean up orphaned workspace contexts.

    Removes context files for workspaces that no longer exist.

    Examples:
        # Preview cleanup
        spec-kitty context cleanup --dry-run

        # Clean up orphaned contexts
        spec-kitty context cleanup
    """
    try:
        repo_root = find_repo_root()
    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    orphaned = find_orphaned_contexts(repo_root)

    if not orphaned:
        console.print("[green]✓[/green] No orphaned contexts to clean up")
        return

    console.print(f"\n[yellow]Found {len(orphaned)} orphaned context(s):[/yellow]\n")
    for name, ctx in orphaned:
        console.print(f"  [bold]{name}[/bold]")
        console.print(f"    {ctx.worktree_path}")

    console.print()

    if dry_run:
        console.print("[dim]Dry run - no files deleted[/dim]")
        console.print(f"[dim]Would delete {len(orphaned)} context file(s)[/dim]")
    else:
        cleaned = cleanup_orphaned_contexts(repo_root)
        console.print(f"[green]✓[/green] Cleaned up {cleaned} orphaned context(s)")


# Default command when no subcommand specified
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Query workspace context information."""
    if ctx.invoked_subcommand is None:
        # No subcommand - default to "info"
        info_command()


__all__ = ["app"]
