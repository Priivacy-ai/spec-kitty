"""Verify setup command implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import console, get_project_root_or_exit
from specify_cli.core.tool_checker import check_tool_for_tracker
from specify_cli.dashboard.diagnostics import run_diagnostics
from specify_cli.tasks_support import TaskCliError, find_repo_root
from specify_cli.verify_enhanced import run_enhanced_verify

TOOL_LABELS = [
    ("git", "Git version control"),
    ("claude", "Claude Code CLI"),
    ("gemini", "Gemini CLI"),
    ("qwen", "Qwen Code CLI"),
    ("code", "Visual Studio Code"),
    ("code-insiders", "Visual Studio Code Insiders"),
    ("cursor-agent", "Cursor IDE agent"),
    ("windsurf", "Windsurf IDE"),
    ("kilocode", "Kilo Code IDE"),
    ("opencode", "opencode"),
    ("codex", "Codex CLI"),
    ("auggie", "Auggie CLI"),
    ("q", "Amazon Q Developer CLI"),
]


def verify_setup(
    feature: Optional[str] = typer.Option(None, "--feature", help="Feature slug to verify (auto-detected when omitted)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format for AI agents"),
    check_files: bool = typer.Option(True, "--check-files", help="Check mission file integrity"),
    check_tools: bool = typer.Option(True, "--check-tools", help="Check for installed development tools"),
    diagnostics: bool = typer.Option(False, "--diagnostics", help="Show detailed diagnostics with dashboard health"),
) -> None:
    """Verify that the current environment matches Spec Kitty expectations."""
    output_data: dict[str, object] = {}

    # If diagnostics mode requested, use diagnostics output
    if diagnostics:
        _run_diagnostics_mode(json_output, check_tools)
        return

    # Check tools if requested
    tool_statuses = {}
    if check_tools:
        if not json_output:
            console.print("[bold]Checking for installed tools...[/bold]\n")

        tracker = StepTracker("Check Available Tools")
        for key, label in TOOL_LABELS:
            tracker.add(key, label)

        tool_statuses = {key: check_tool_for_tracker(key, tracker) for key, _ in TOOL_LABELS}

        if not json_output:
            console.print(tracker.render())
            console.print()

            if not tool_statuses.get("git", False):
                console.print("[dim]Tip: Install git for repository management[/dim]")
            if not any(tool_statuses[key] for key in tool_statuses if key != "git"):
                console.print("[dim]Tip: Install an AI assistant for the best experience[/dim]")
            console.print()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        if json_output:
            output_data["error"] = str(exc)
            if check_tools:
                output_data["tools"] = {key: {"available": available} for key, available in tool_statuses.items()}
            print(json.dumps(output_data))
        else:
            console.print(f"[red]✗[/red] Repository detection failed: {exc}")
            console.print(
                "\n[yellow]Solution:[/yellow] Run this command from a Spec Kitty project root or from a feature worktree inside .worktrees/<feature>/ (use 'spec-kitty init <name>' to create a project)."
            )
        raise typer.Exit(1)

    project_root = get_project_root_or_exit(repo_root)
    cwd = Path.cwd()

    result = run_enhanced_verify(
        repo_root=repo_root,
        project_root=project_root,
        cwd=cwd,
        feature=feature,
        json_output=json_output,
        check_files=check_files,
        console=console,
    )

    # Add tool checking results to JSON output
    if json_output and check_tools:
        result["tools"] = {key: {"available": available} for key, available in tool_statuses.items()}

    if json_output:
        print(json.dumps(result, indent=2))
        return

    return


def _run_diagnostics_mode(json_output: bool, check_tools: bool) -> None:
    """Run diagnostics mode with detailed health information."""
    try:
        project_path = Path.cwd()
        diag = run_diagnostics(project_path)

        # Add tool checking if requested
        if check_tools:
            tracker = StepTracker("Check Available Tools")
            for key, label in TOOL_LABELS:
                tracker.add(key, label)
            tool_statuses = {key: check_tool_for_tracker(key, tracker) for key, _ in TOOL_LABELS}
            diag["tools"] = {key: {"available": available} for key, available in tool_statuses.items()}

        if json_output:
            # Machine-readable output for scripts and tools
            console.print(json.dumps(diag, indent=2, default=str))
        else:
            # Human-readable output with Rich panels
            _print_diagnostics(diag, check_tools)

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


def _print_diagnostics(diag: dict[str, Any], check_tools: bool) -> None:
    """Print diagnostics in human-readable format using Rich panels."""
    # Tool checking first if enabled
    if check_tools and "tools" in diag:
        tool_statuses = {k: v["available"] for k, v in diag["tools"].items()}

        console.print("[bold]Checking for installed tools...[/bold]\n")
        tracker = StepTracker("Check Available Tools")
        for key, label in TOOL_LABELS:
            tracker.add(key, label)
            if tool_statuses.get(key):
                tracker.complete(key, "available")
            else:
                tracker.skip(key, "not found")

        console.print(tracker.render())
        console.print()

        if not tool_statuses.get("git", False):
            console.print("[dim]Tip: Install git for repository management[/dim]")
        if not any(tool_statuses[key] for key in tool_statuses if key != "git"):
            console.print("[dim]Tip: Install an AI assistant for the best experience[/dim]")
        console.print()

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


__all__ = ["verify_setup"]
