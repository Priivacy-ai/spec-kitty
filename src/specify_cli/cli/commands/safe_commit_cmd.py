"""Generic ``spec-kitty safe-commit`` command."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from specify_cli.git import ProtectedBranchCommitError, assert_not_protected_branch, safe_commit
from specify_cli.git.commit_helpers import SafeCommitBackstopError
from specify_cli.task_utils import TaskCliError, find_repo_root

console = Console()


def _current_worktree_root() -> Path:
    """Return the git top-level for the current worktree.

    ``find_repo_root()`` intentionally resolves Spec Kitty worktrees back to the
    main repository for status/event callers. This command commits operator
    files, so it must preserve the current worktree as the commit target.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    return find_repo_root()


def _has_candidate_changes(repo_root: Path, files_to_commit: list[Path]) -> bool:
    rel_paths = [str(path.relative_to(repo_root)) if path.is_absolute() else str(path) for path in files_to_commit]
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
        raise RuntimeError("Unable to inspect requested files before commit.")
    return bool(result.stdout.strip())


def _payload(*, success: bool, committed: bool = False, files: list[str] | None = None, error: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "result": "success" if success else "error",
        "success": success,
        "committed": committed,
    }
    if files is not None:
        payload["files"] = files
    if error is not None:
        payload["error"] = error
    return payload


def safe_commit_command(
    files: list[Path] = typer.Argument(..., help="Files to commit, relative to the current worktree root or absolute."),
    message: str = typer.Option(..., "--message", "-m", help="Commit message."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Commit only the requested files via Spec Kitty's safe-commit path."""
    try:
        repo_root = _current_worktree_root()
        normalized_files = [
            (repo_root / file_path).resolve() if not file_path.is_absolute() else file_path.resolve()
            for file_path in files
        ]
        rel_files = [str(path.relative_to(repo_root)) for path in normalized_files]

        had_changes = _has_candidate_changes(repo_root, normalized_files)
        assert_not_protected_branch(repo_root, operation=f"create commit '{message}'")
        committed = safe_commit(
            repo_path=repo_root,
            files_to_commit=normalized_files,
            commit_message=message,
            allow_empty=False,
        )
        if had_changes and not committed:
            raise RuntimeError("Requested files changed but no commit was created.")

        payload = _payload(success=True, committed=committed, files=rel_files)
        if json_output:
            print(json.dumps(payload, indent=2))
            return
        if committed:
            console.print("[green]Requested files committed[/green]")
        else:
            console.print("[yellow]No requested changes to commit[/yellow]")
    except (ProtectedBranchCommitError, SafeCommitBackstopError, TaskCliError, ValueError, RuntimeError) as exc:
        if json_output:
            print(json.dumps(_payload(success=False, error=str(exc)), indent=2))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
