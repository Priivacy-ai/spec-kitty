"""Lint and type-check command implementation.

Wraps ``ruff`` and ``mypy`` for a single file and reports the result. The
command is designed to run as a harness post-edit hook (Claude Code
``PostToolUse``, Cursor ``afterFileEdit``). Those harnesses do **not** append
the edited path as an argv; they deliver it as a JSON payload on **stdin**. So
when no path argument is given, the target is resolved from the stdin payload
(``tool_input.file_path`` for Claude, ``file_path`` for Cursor/generic). A hook
that fires without a resolvable Python file is a benign no-op (exit 0), never a
hard failure that would block the agent's edit.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any

import typer

from specify_cli.cli.helpers import console
from specify_cli.core.project_resolver import locate_project_root

# mypy's summary lines we never want to surface as "errors".
_MYPY_SUMMARY_RE = re.compile(r"^(Success:|Found \d+ error)")


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
        mypy_args = [
            "mypy",
            "--strict",
            "--ignore-missing-imports",
            "--no-error-summary",
            str(path),
        ]

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
                return [
                    line
                    for line in raw_output.splitlines()
                    if not _MYPY_SUMMARY_RE.match(line)
                ]
    except FileNotFoundError:
        return ["mypy not found in PATH. Please install it with 'pip install mypy'."]
    return []


def _path_from_payload(payload: Any) -> Path | None:
    """Extract an edited-file path from a harness hook stdin payload.

    Supports Claude Code (``tool_input.file_path``) and Cursor / generic
    (``file_path``) shapes, plus their ``*_paths`` list variants. Returns the
    first resolvable path, or ``None`` when the payload carries no file path.
    """
    if not isinstance(payload, dict):
        return None
    tool_input = payload.get("tool_input")
    candidates: list[Any] = []
    if isinstance(tool_input, dict):
        candidates.append(tool_input.get("file_path"))
        candidates.extend(tool_input.get("file_paths") or [])
    candidates.append(payload.get("file_path"))
    candidates.extend(payload.get("file_paths") or [])
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return Path(candidate)
    return None


def _resolve_target_from_stdin() -> Path | None:
    """Resolve the target file from a harness hook payload on stdin.

    Returns ``None`` when stdin is a terminal, empty, not JSON, or carries no
    file path — all of which mean "nothing to lint", a benign hook no-op.
    """
    if sys.stdin.isatty():
        return None
    raw = sys.stdin.read().strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return _path_from_payload(payload)


def lint_command(
    file_path: Annotated[
        Path | None,
        typer.Argument(help="File to lint/type-check; omit to read the path from a hook stdin payload"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output in JSON format for AI agents")] = False,
    fix: Annotated[bool, typer.Option("--fix", help="Attempt to automatically fix lint errors")] = False,
) -> None:
    """
    Run ruff and mypy on a file and report errors.

    This command is designed to be used as a post-edit hook for AI agents,
    providing immediate feedback on linting and type-checking violations.
    When invoked without a path (the wired hook form), the target file is read
    from the harness JSON payload on stdin.
    """
    if file_path is None:
        file_path = _resolve_target_from_stdin()
    if file_path is None:
        # Hook fired with no file to lint (e.g. a non-edit tool event): no-op.
        if json_output:
            print(json.dumps({"skipped": True, "reason": "No file path provided"}))
        else:
            console.print("[dim]Skipping:[/dim] no file path provided.")
        return

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
    # Resolve to an absolute path so ruff/mypy (run with cwd=project_root) find
    # the file regardless of the caller's working directory.
    target = file_path.resolve()

    ruff_errors = _run_ruff(target, project_root, fix)
    mypy_errors = _run_mypy(target, project_root)
    all_errors = ruff_errors + mypy_errors

    if json_output:
        print(json.dumps({"file": str(file_path), "success": len(all_errors) == 0, "ruff_errors": ruff_errors, "mypy_errors": mypy_errors}, indent=2))
    elif not all_errors:
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
