"""Lint and type-check command implementation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from specify_cli.cli.helpers import console
from specify_cli.core.project_resolver import locate_project_root


def _run_ruff(path: Path, project_root: Path, fix: bool) -> list[str]:
    """Run ruff and return a list of error lines."""
    try:
        ruff_args = ["ruff", "check"]
        if fix:
            ruff_args.append("--fix")
        ruff_args.append(str(path))

        ruff_proc = subprocess.run(
            ruff_args,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if ruff_proc.returncode != 0:
            raw_output = ruff_proc.stdout.strip() or ruff_proc.stderr.strip()
            if raw_output:
                return raw_output.splitlines()
    except FileNotFoundError:
        return ["ruff not found in PATH. Please install it with 'pip install ruff'."]
    return []


def _run_mypy(path: Path, project_root: Path) -> list[str]:
    """Run mypy and return a list of error lines."""
    try:
        mypy_args = ["mypy", "--strict", "--ignore-missing-imports", "--no-error-summary", str(path)]

        mypy_proc = subprocess.run(
            mypy_args,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if mypy_proc.returncode != 0:
            raw_output = mypy_proc.stdout.strip() or mypy_proc.stderr.strip()
            if raw_output:
                return [line for line in raw_output.splitlines() if not line.startswith("Success:") and not line.startswith("Found ")]
    except FileNotFoundError:
        return ["mypy not found in PATH. Please install it with 'pip install mypy'."]
    return []


def lint_command(
    file_path: Annotated[Path, typer.Argument(help="File path to lint and type-check")],
    json_output: Annotated[bool, typer.Option("--json", help="Output in JSON format for AI agents")] = False,
    fix: Annotated[bool, typer.Option("--fix", help="Attempt to automatically fix lint errors")] = False,
) -> None:
    """
    Run ruff and mypy on a file and report errors.

    This command is designed to be used as a post-edit hook for AI agents,
    providing immediate feedback on linting and type-checking violations.
    """
    if not file_path.exists():
        if not json_output:
            console.print(f"[red]Error:[/red] File [cyan]{file_path}[/cyan] does not exist.")
        else:
            print(json.dumps({"error": f"File {file_path} does not exist"}))
        raise typer.Exit(1)

    if file_path.suffix != ".py":
        if not json_output:
            console.print(f"[dim]Skipping:[/dim] [cyan]{file_path}[/cyan] is not a Python file.")
        else:
            print(json.dumps({"skipped": True, "reason": "Not a Python file", "file": str(file_path)}))
        return

    project_root = locate_project_root() or Path.cwd()

    ruff_errors = _run_ruff(file_path, project_root, fix)
    mypy_errors = _run_mypy(file_path, project_root)
    all_errors = ruff_errors + mypy_errors

    if json_output:
        print(json.dumps({"file": str(file_path), "success": len(all_errors) == 0, "ruff_errors": ruff_errors, "mypy_errors": mypy_errors}, indent=2))
    else:
        if not all_errors:
            console.print(f"[green]✓[/green] [cyan]{file_path}[/cyan] passed all checks.")
        else:
            _print_errors(file_path, ruff_errors, mypy_errors)

    if all_errors:
        raise typer.Exit(1)


def _print_errors(file_path: Path, ruff_errors: list[str], mypy_errors: list[str]) -> None:
    """Print error summary to console."""
    console.print(f"[red]✗[/red] [cyan]{file_path}[/cyan] failed code quality checks:")
    if ruff_errors:
        console.print("\n[bold]Ruff Violations:[/bold]")
        for err in ruff_errors:
            console.print(f"  {err}")
    if mypy_errors:
        console.print("\n[bold]Mypy Type Errors:[/bold]")
        for err in mypy_errors:
            console.print(f"  {err}")

    console.print("\n[yellow]Tip:[/yellow] Fix these errors before proceeding to ensure high code quality.")
