"""Generic ``spec-kitty safe-commit`` command.

Post-#1348 (mission ``mission-coordination-branch-atomic-event-log``) the
underlying :func:`specify_cli.git.commit_helpers.safe_commit` helper requires
a keyword-only ``destination_ref`` (the short branch name) and
``worktree_root`` argument so the destination is structurally enforced.

This CLI surfaces that contract via a required ``--to-branch`` flag. A
short-lived deprecation escape hatch is provided via the environment variable
``SPEC_KITTY_INFER_DESTINATION_REF=1``: when set, the CLI resolves the
current branch from ``HEAD``, prints a one-line stderr deprecation warning,
and proceeds. This unblocks existing downstream scripts during the v3.2 ->
v3.3 transition. The env var will be removed in v3.3.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import typer
from rich.console import Console

from specify_cli.core.git_ops import get_current_branch
from specify_cli.git import ProtectedBranchCommitError, assert_not_protected_branch, safe_commit
from specify_cli.git.commit_helpers import (
    SafeCommitBackstopError,
    SafeCommitError,
)
from specify_cli.task_utils import find_repo_root

console = Console()


SPEC_KITTY_INFER_ENV = "SPEC_KITTY_INFER_DESTINATION_REF"


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
    return cast(Path, find_repo_root())


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


def _resolve_destination_ref(
    *,
    explicit_to_branch: str | None,
    repo_root: Path,
    json_output: bool,
) -> str:
    """Resolve the destination ref for the CLI command.

    Precedence:

    1. ``--to-branch X`` provided → return ``X``.
    2. ``--to-branch`` missing → resolve current branch via
       :func:`get_current_branch`. Print a one-line stderr deprecation unless
       the legacy env escape hatch is set. Return resolved value.
    """
    _ = json_output
    if explicit_to_branch is not None and explicit_to_branch != "":
        # Normalize fully-qualified refs/heads/<name> → <name>. The helper
        # rejects fully-qualified destination refs with
        # SafeCommitDestinationRefShape; the CLI normalizes for ergonomics.
        if explicit_to_branch.startswith("refs/heads/"):
            return explicit_to_branch[len("refs/heads/"):]
        return explicit_to_branch

    inferred = get_current_branch(repo_root)
    if inferred is None or inferred == "":
        raise ValueError(
            "Cannot infer destination ref: HEAD is detached or not on a branch. "
            "Pass --to-branch <ref> explicitly."
        )
    # Print deprecation to stderr (not stdout) so scripted callers parsing
    # --json on stdout are not affected. Keep the env var as a warning
    # suppressor for transition scripts that cannot tolerate stderr noise.
    if os.environ.get(SPEC_KITTY_INFER_ENV) != "1":
        print(
            f"warning: --to-branch will be required in v3.3; set explicitly or "
            f"set {SPEC_KITTY_INFER_ENV}=1 to suppress this warning",
            file=sys.stderr,
        )
    return cast(str, inferred)


def safe_commit_command(
    files: list[Path] = typer.Argument(..., help="Files to commit, relative to the current worktree root or absolute."),
    message: str = typer.Option(..., "--message", "-m", help="Commit message."),
    to_branch: str | None = typer.Option(
        None,
        "--to-branch",
        help=(
            "Short branch name the commit must land on (required). "
            "The helper asserts HEAD matches this branch before staging. "
            f"For legacy scripts, set {SPEC_KITTY_INFER_ENV}=1 to fall back to "
            "current-HEAD inference (deprecated; removed in v3.3)."
        ),
    ),
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

        destination_ref = _resolve_destination_ref(
            explicit_to_branch=to_branch,
            repo_root=repo_root,
            json_output=json_output,
        )

        had_changes = _has_candidate_changes(repo_root, normalized_files)
        assert_not_protected_branch(repo_root, operation=f"create commit '{message}'")
        committed = False
        if had_changes:
            # The new safe_commit helper raises on commit failure; a successful
            # call always returns a CommitResult. We only invoke it when there
            # is something to commit so the "no requested changes" path stays
            # quiet (matches the pre-#1348 CLI behavior).
            safe_commit(
                repo_root=repo_root,
                worktree_root=repo_root,
                destination_ref=destination_ref,
                message=message,
                paths=tuple(normalized_files),
            )
            committed = True

        payload = _payload(success=True, committed=committed, files=rel_files)
        if json_output:
            print(json.dumps(payload, indent=2))
            return
        if committed:
            console.print("[green]Requested files committed[/green]")
        else:
            console.print("[yellow]No requested changes to commit[/yellow]")
    except (
        SafeCommitError,
        ProtectedBranchCommitError,
        SafeCommitBackstopError,
        ValueError,
        RuntimeError,
    ) as exc:
        if json_output:
            print(json.dumps(_payload(success=False, error=str(exc)), indent=2))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
