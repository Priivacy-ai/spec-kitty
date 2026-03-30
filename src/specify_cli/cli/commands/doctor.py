"""Top-level doctor command group for project health diagnostics."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table
from typing import Annotated

from specify_cli.core.paths import locate_project_root

app = typer.Typer(name="doctor", help="Project health diagnostics")
console = Console()


@app.command(name="command-files")
def command_files(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Check all agent command files for correctness.

    Verifies that every configured agent has the correct command files:
    - Full rendered prompts for prompt-driven commands (specify, plan, tasks, ...)
    - Thin shims for CLI-driven commands (implement, review, merge, ...)
    - Current version markers on all files

    Examples:
        spec-kitty doctor command-files
        spec-kitty doctor command-files --json
    """
    from specify_cli.runtime.doctor import check_command_file_health

    try:
        project_path = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc

    if project_path is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    issues = check_command_file_health(project_path)

    if json_output:
        console.print_json(json.dumps(issues, indent=2))
        raise typer.Exit(1 if issues else 0)

    if not issues:
        console.print("[green]Command Files[/green]: all files healthy")
        raise typer.Exit(0)

    console.print(f"\n[bold]Command Files[/bold] — {len(issues)} issue(s) found\n")

    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("Agent", style="cyan", min_width=12)
    table.add_column("Command", min_width=16)
    table.add_column("File", min_width=40)
    table.add_column("Severity", min_width=8)
    table.add_column("Issue")

    for issue in issues:
        severity = issue["severity"]
        severity_display = (
            f"[red]{severity}[/red]" if severity == "error" else f"[yellow]{severity}[/yellow]"
        )
        table.add_row(
            issue["agent"],
            issue["command"],
            issue["file"],
            severity_display,
            issue["issue"],
        )

    console.print(table)
    console.print()
    raise typer.Exit(1)


@app.command(name="state-roots")
def state_roots(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Show state roots, surface classification, and safety warnings.

    Displays the three state roots with resolved paths, all registered
    state surfaces grouped by root with authority and Git classification,
    and warnings for any runtime surfaces not covered by .gitignore.

    Examples:
        spec-kitty doctor state-roots
        spec-kitty doctor state-roots --json
    """
    from specify_cli.state.doctor import check_state_roots
    from specify_cli.state_contract import StateRoot

    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc

    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    report = check_state_roots(repo_root)

    if json_output:
        console.print_json(json.dumps(report.to_dict(), indent=2))
        raise typer.Exit(0 if report.healthy else 1)

    # Human-readable output
    # 1. State roots table
    console.print("\n[bold]State Roots[/bold]")
    for root_info in report.roots:
        status = (
            "[green]exists[/green]"
            if root_info.exists
            else "[dim]absent[/dim]"
        )
        console.print(
            f"  {root_info.name:<20} {root_info.resolved_path}  {status}"
        )

    # 2. Surfaces by root
    console.print()
    root_order = [
        StateRoot.PROJECT,
        StateRoot.FEATURE,
        StateRoot.GLOBAL_RUNTIME,
        StateRoot.GLOBAL_SYNC,
        StateRoot.GIT_INTERNAL,
    ]
    root_labels = {
        StateRoot.PROJECT: "Project Surfaces (.kittify/)",
        StateRoot.FEATURE: "Feature Surfaces (kitty-specs/)",
        StateRoot.GLOBAL_RUNTIME: "Global Runtime (~/.kittify/)",
        StateRoot.GLOBAL_SYNC: "Global Sync (~/.spec-kitty/)",
        StateRoot.GIT_INTERNAL: "Git-Internal (.git/spec-kitty/)",
    }

    for root in root_order:
        root_surfaces = [s for s in report.surfaces if s.surface.root == root]
        if not root_surfaces:
            continue

        console.print(f"[bold]{root_labels.get(root, root.value)}[/bold]")
        table = Table(box=None, padding=(0, 2), show_edge=False)
        table.add_column("Name", style="cyan", min_width=28)
        table.add_column("Authority", min_width=16)
        table.add_column("Git Policy", min_width=22)
        table.add_column("Present", justify="center", min_width=8)

        for check in root_surfaces:
            present_icon = "[green]Y[/green]" if check.present else "[dim]N[/dim]"
            authority = check.surface.authority.value
            git_class = check.surface.git_class.value
            if check.warning:
                authority = f"[yellow]{authority}[/yellow]"
                git_class = f"[yellow]{git_class}[/yellow]"
            table.add_row(check.surface.name, authority, git_class, present_icon)

        console.print(table)
        console.print()

    # 3. Warnings
    if report.warnings:
        console.print("[bold yellow]Warnings[/bold yellow]")
        for w in report.warnings:
            console.print(f"  [yellow]![/yellow] {w}")
    else:
        console.print(
            "[green]No warnings -- all runtime surfaces are properly covered.[/green]"
        )

    console.print()
    raise typer.Exit(0 if report.healthy else 1)
