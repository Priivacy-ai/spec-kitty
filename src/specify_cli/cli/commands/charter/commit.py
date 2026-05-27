"""``spec-kitty charter commit`` command.

Commits charter-generation inputs through ``safe_commit`` so the slash-command
flow does not need raw ``git add`` / ``git commit`` instructions.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer

from specify_cli.git import ProtectedBranchCommitError, safe_commit
from specify_cli.task_utils import TaskCliError

from specify_cli.cli.commands.charter._app import charter_app, console

import specify_cli.cli.commands.charter as _charter_pkg

__all__ = ["commit"]


_CHARTER_COMMIT_CANDIDATES = (
    Path(".kittify/charter/interview/answers.yaml"),
    Path(".kittify/charter/charter.md"),
    Path(".kittify/charter/references.yaml"),
    Path(".gitignore"),
)


def _has_candidate_changes(repo_root: Path, files_to_commit: list[Path]) -> bool:
    rel_paths = [str(path.relative_to(repo_root)) for path in files_to_commit]
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *rel_paths],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Unable to inspect charter files before commit.")
    return bool(result.stdout.strip())


@charter_app.command(name="commit")
def commit(
    message: str = typer.Option(
        "chore: generate project charter",
        "--message",
        "-m",
        help="Commit message for charter changes.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Commit generated charter files via the shared safe-commit path."""
    try:
        repo_root = _charter_pkg.find_repo_root()
        files_to_commit = [
            (repo_root / candidate).resolve()
            for candidate in _CHARTER_COMMIT_CANDIDATES
            if (repo_root / candidate).exists()
        ]
        if not files_to_commit:
            raise ValueError("No charter files exist to commit.")

        had_changes = _has_candidate_changes(repo_root, files_to_commit)
        committed = safe_commit(
            repo_path=repo_root,
            files_to_commit=files_to_commit,
            commit_message=message,
            allow_empty=False,
        )
        if had_changes and not committed:
            raise RuntimeError("Charter files changed but no commit was created.")
        payload = {
            "result": "success",
            "success": True,
            "committed": committed,
            "files": [
                str(path.relative_to(repo_root))
                for path in files_to_commit
            ],
        }
        if json_output:
            print(json.dumps(payload, indent=2))
            return

        if committed:
            console.print("[green]Charter changes committed[/green]")
        else:
            console.print("[yellow]No charter changes to commit[/yellow]")
    except ProtectedBranchCommitError as e:
        if json_output:
            print(json.dumps({"result": "error", "success": False, "error": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except (TaskCliError, ValueError, RuntimeError) as e:
        if json_output:
            print(json.dumps({"result": "error", "success": False, "error": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
