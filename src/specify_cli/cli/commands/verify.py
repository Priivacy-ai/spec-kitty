"""Verify setup command implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from specify_cli.cli.helpers import console, get_project_root_or_exit, show_banner
from specify_cli.tasks_support import TaskCliError, find_repo_root
from specify_cli.verify_enhanced import run_enhanced_verify


def verify_setup(
    feature: Optional[str] = typer.Option(None, "--feature", help="Feature slug to verify (auto-detected when omitted)"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format for AI agents"),
    check_files: bool = typer.Option(True, "--check-files", help="Check mission file integrity"),
) -> None:
    """Verify that the current environment matches Spec Kitty expectations."""
    output_data: dict[str, object] = {}

    if not json_output:
        show_banner()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        if json_output:
            output_data["error"] = str(exc)
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

    if json_output:
        print(json.dumps(result, indent=2))
        return

    return


__all__ = ["verify_setup"]
