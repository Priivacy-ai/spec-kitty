"""Diagnostics command implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli.helpers import console, show_banner
from specify_cli.dashboard.diagnostics import run_diagnostics


def diagnostics(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for programmatic use"),
) -> None:
    """Show project health and diagnostics information.

    Run this command to check the overall health of your spec-kitty project,
    including git status, worktrees, features, and file integrity.
    """
    if not json_output:
        show_banner()

    try:
        project_path = Path.cwd()
        diag = run_diagnostics(project_path)

        if json_output:
            # Machine-readable output for scripts and tools
            console.print(json.dumps(diag, indent=2, default=str))
        else:
            # Human-readable output
            _print_human_diagnostics(diag)

    except Exception as exc:
        if json_output:
            error_output = {
                "status": "error",
                "message": str(exc),
            }
            console.print(json.dumps(error_output, indent=2))
        else:
            console.print(f"[red]✗ Diagnostics failed:[/red] {exc}")
        raise typer.Exit(1)


def _print_human_diagnostics(diag: dict[str, Any]) -> None:
    """Print diagnostics in human-readable format using Rich."""
    # Project info panel
    project_info = f"""
[bold]Project Path:[/bold] {diag['project_path']}
[bold]Current Directory:[/bold] {diag['current_working_directory']}
[bold]Git Branch:[/bold] {diag.get('git_branch') or '[yellow]Not detected[/yellow]'}
[bold]Active Mission:[/bold] {diag.get('active_mission') or '[yellow]None[/yellow]'}
"""
    console.print(Panel(project_info.strip(), title="Project Information", border_style="cyan"))

    # File integrity
    file_integrity = diag.get("file_integrity", {})
    total_expected = file_integrity.get("total_expected", 0)
    total_present = file_integrity.get("total_present", 0)
    total_missing = file_integrity.get("total_missing", 0)

    if total_missing == 0:
        integrity_status = "[green]✓ All files present[/green]"
    else:
        integrity_status = f"[yellow]⚠ {total_missing} files missing[/yellow]"

    file_info = f"""
[bold]Files:[/bold] {total_present}/{total_expected} present {integrity_status}
"""

    if file_integrity.get("missing_files"):
        file_info += f"\n[red]Missing:[/red]\n"
        for missing in file_integrity.get("missing_files", [])[:5]:
            file_info += f"  • {missing}\n"
        if len(file_integrity.get("missing_files", [])) > 5:
            file_info += f"  ... and {len(file_integrity.get('missing_files', [])) - 5} more\n"

    console.print(Panel(file_info.strip(), title="File Integrity", border_style="cyan"))

    # Worktree overview
    worktree_overview = diag.get("worktree_overview", {})
    in_worktree = diag.get("in_worktree", False)
    worktrees_exist = diag.get("worktrees_exist", False)

    worktree_info = f"""
[bold]Worktrees Exist:[/bold] {'[green]Yes[/green]' if worktrees_exist else '[red]No[/red]'}
[bold]Currently in Worktree:[/bold] {'[green]Yes[/green]' if in_worktree else '[red]No[/red]'}
[bold]Active Worktrees:[/bold] {worktree_overview.get('active_worktrees', 0)}
[bold]Total Features:[/bold] {worktree_overview.get('total_features', 0)}
"""
    console.print(Panel(worktree_info.strip(), title="Worktrees", border_style="cyan"))

    # Dashboard health
    dashboard_health = diag.get("dashboard_health", {})
    metadata_exists = dashboard_health.get("metadata_exists", False)
    can_start = dashboard_health.get("can_start")
    startup_test = dashboard_health.get("startup_test")

    if metadata_exists:
        responding = dashboard_health.get("responding", False)
        dashboard_info = f"""
[bold]Metadata File:[/bold] {'[green]Exists[/green]' if metadata_exists else '[red]Missing[/red]'}
[bold]Port:[/bold] {dashboard_health.get('port', 'Unknown')}
[bold]Process PID:[/bold] {dashboard_health.get('pid', 'Not tracked')}
[bold]Responding:[/bold] {'[green]Yes[/green]' if responding else '[red]No[/red]'}
"""
        if not responding:
            dashboard_info += f"[red]⚠️  Dashboard is not responding - may need restart[/red]\n"
    else:
        # No dashboard - show startup test results
        if startup_test == 'SUCCESS':
            dashboard_info = f"""
[bold]Status:[/bold] [green]Can start successfully[/green]
[bold]Test Port:[/bold] {dashboard_health.get('test_port', 'N/A')}
"""
        elif startup_test == 'FAILED':
            dashboard_info = f"""
[bold]Status:[/bold] [red]Cannot start[/red]
[bold]Error:[/bold] {dashboard_health.get('startup_error', 'Unknown')}
[red]⚠️  Dashboard startup is broken for this project[/red]
"""
        else:
            dashboard_info = "[yellow]Dashboard not running (startup not tested)[/yellow]"

    console.print(Panel(dashboard_info.strip(), title="Dashboard Health", border_style="cyan"))

    # Current feature
    current_feature = diag.get("current_feature", {})
    if current_feature.get("detected"):
        feature_info = f"""
[bold]Detected Feature:[/bold] {current_feature.get('name')}
[bold]State:[/bold] {current_feature.get('state')}
[bold]Branch Exists:[/bold] {'[green]Yes[/green]' if current_feature.get('branch_exists') else '[red]No[/red]'}
[bold]Worktree Exists:[/bold] {'[green]Yes[/green]' if current_feature.get('worktree_exists') else '[red]No[/red]'}
"""
    else:
        feature_info = "[yellow]No feature detected in current context[/yellow]"

    console.print(Panel(feature_info.strip(), title="Current Feature", border_style="cyan"))

    # All features table
    all_features = diag.get("all_features", [])
    if all_features:
        table = Table(title="All Features", show_lines=False, header_style="bold cyan")
        table.add_column("Feature", style="bright_cyan")
        table.add_column("State", style="bright_white")
        table.add_column("Branch", justify="center")
        table.add_column("Merged", justify="center")
        table.add_column("Worktree", justify="center")

        for feature in all_features:
            branch_emoji = "✓" if feature.get("branch_exists") else "✗"
            merged_emoji = "✓" if feature.get("branch_merged") else "○"
            worktree_emoji = "✓" if feature.get("worktree_exists") else "✗"

            table.add_row(
                feature.get("name", "Unknown"),
                feature.get("state", "Unknown"),
                branch_emoji,
                merged_emoji,
                worktree_emoji,
            )

        console.print(table)
    else:
        console.print("[yellow]No features found[/yellow]")

    # Observations and issues
    observations = diag.get("observations", [])
    issues = diag.get("issues", [])

    if observations or issues:
        console.print()
        if observations:
            console.print("[bold cyan]📝 Observations:[/bold cyan]")
            for obs in observations:
                console.print(f"  • {obs}")

        if issues:
            console.print("[bold red]⚠️  Issues:[/bold red]")
            for issue in issues:
                console.print(f"  • {issue}")
    else:
        console.print("\n[bold green]✓ No issues or observations[/bold green]")
