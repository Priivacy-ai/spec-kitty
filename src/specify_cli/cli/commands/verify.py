"""Verify setup command implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import console, get_project_root_or_exit, show_banner
from specify_cli.core.tool_checker import check_tool_for_tracker
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
) -> None:
    """Verify that the current environment matches Spec Kitty expectations."""
    output_data: dict[str, object] = {}

    if not json_output:
        show_banner()

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
            console.print("\n[yellow]Solution:[/yellow] Ensure you're in a git repository or spec-kitty project")
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


__all__ = ["verify_setup"]
