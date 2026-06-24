"""Mission-aware ``spec-commit`` entrypoint (FR-001/002/003).

Closes the #1619 P0 specify-phase deadlock: unlike the generic ``safe-commit``
command (which is mission-blind), this command derives the mission slug from a
``kitty-specs/<slug>/`` path argument or ``--mission``, resolves the
:class:`~specify_cli.git.protection_policy.ProtectionPolicy` at the command
boundary, and routes the commit through
:func:`~specify_cli.coordination.commit_router.commit_for_mission`.

On a protected primary the coordination worktree is materialised on demand
(the same canonical ``CoordinationWorkspace.resolve()`` path used by the
planning loop), so the spec commit lands on the coordination branch instead of
tripping the guard (materialize-then-retry).

Design basis: WP02 / IC-02 / ADR ``2026-06-21-1``.

C-001: reuses the canonical materialiser, no new materialiser.
#1718: materialisation happens at this commit boundary, not at read time.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from mission_runtime import MissionArtifactKind
from specify_cli.coordination.commit_router import CommitRouterResult, commit_for_mission
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.task_utils import find_repo_root

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_repo_root() -> Path:
    """Return the primary repo root (follows worktree links to main checkout)."""
    root: Path = find_repo_root()
    return root


def _derive_mission_slug(path_arg: str | None, mission_opt: str | None) -> str | None:
    """Derive the mission slug from a ``kitty-specs/<slug>/`` path or ``--mission``."""
    if mission_opt:
        return mission_opt.strip()
    if path_arg:
        # Accept either the slug directly or a ``kitty-specs/<slug>`` path.
        p = Path(path_arg)
        # If the path contains a ``kitty-specs`` component, take the part after it.
        parts = p.parts
        try:
            idx = next(i for i, part in enumerate(parts) if part == KITTY_SPECS_DIR)
            # slug is the component immediately after ``kitty-specs``
            if idx + 1 < len(parts):
                return parts[idx + 1]
        except StopIteration:
            pass
        # Otherwise treat the final component as the slug.
        return p.name or None
    return None


def _payload(
    *,
    success: bool,
    committed: bool = False,
    placement_ref: str | None = None,
    commit_hash: str | None = None,
    error: str | None = None,
    diagnostic: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "result": "success" if success else "error",
        "success": success,
        "committed": committed,
    }
    if placement_ref is not None:
        result["placement_ref"] = placement_ref
    if commit_hash is not None:
        result["commit_hash"] = commit_hash
    if error is not None:
        result["error"] = error
    if diagnostic is not None:
        result["diagnostic"] = diagnostic
    return result


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def spec_commit_command(
    files: list[Path] = typer.Argument(
        ...,
        help=(
            "Spec artifacts to commit (absolute or relative paths). "
            "Must belong to the mission resolved via --mission or the "
            "kitty-specs/<slug>/ path."
        ),
    ),
    message: str = typer.Option(..., "--message", "-m", help="Commit message."),
    mission: str | None = typer.Option(
        None,
        "--mission",
        help=(
            "Mission slug (e.g. '001-my-mission'). When omitted, the slug is "
            "derived from the first file argument's kitty-specs/<slug>/ path."
        ),
    ),
    target_branch: str | None = typer.Option(
        None,
        "--target-branch",
        help=(
            "Short primary branch name used for the post-commit ff-advance "
            "(WP09 / FR-010). Optional."
        ),
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Commit spec artifacts to the mission's resolved placement.

    On a protected primary the coordination worktree is materialised on demand
    so the commit lands on the coordination branch (materialize-then-retry).
    On an unprotected or flattened primary the commit is direct.
    """
    try:
        repo_root = _current_repo_root()

        # Normalise file paths.
        abs_files: list[Path] = []
        for f in files:
            abs_files.append((repo_root / f).resolve() if not f.is_absolute() else f.resolve())

        # Derive mission slug.
        first_path_arg = str(files[0]) if files else None
        mission_slug = _derive_mission_slug(first_path_arg, mission)
        if not mission_slug:
            _err(
                json_output,
                "Cannot resolve mission slug. Pass --mission <slug> or provide a "
                "kitty-specs/<slug>/ path as the first argument.",
            )
            raise typer.Exit(1)

        # Boundary-resolve the protection policy (FR-007, NFR-003).
        policy = ProtectionPolicy.resolve(repo_root)

        result: CommitRouterResult = commit_for_mission(
            repo_root=repo_root,
            mission_slug=mission_slug,
            files=tuple(abs_files),
            message=message,
            policy=policy,
            # The operator-facing ``spec-commit`` entry point commits the SPEC
            # planning artifact (write-surface-coherence WP02 / T007). SPEC is a
            # primary kind, so it lands on the primary target branch for every
            # topology — no planning→coord transit.
            kind=MissionArtifactKind.SPEC,
            target_branch=target_branch,
        )

        if result.status == "committed":
            payload = _payload(
                success=True,
                committed=True,
                placement_ref=result.placement_ref,
                commit_hash=result.commit_hash,
            )
            if json_output:
                print(json.dumps(payload, indent=2))
            else:
                console.print(
                    f"[green]✓[/green] Spec artifact(s) committed to {result.placement_ref}"
                )
                if result.commit_hash:
                    console.print(f"[dim]Commit: {result.commit_hash[:7]}[/dim]")

        elif result.status == "unchanged":
            payload = _payload(success=True, committed=False, placement_ref=result.placement_ref)
            if json_output:
                print(json.dumps(payload, indent=2))
            else:
                console.print("[dim]Spec artifact(s) unchanged, no commit needed[/dim]")

        elif result.status == "no_op_wrong_surface":
            # T008: actionable refusal — tell the operator what happened and how to recover.
            recovery_cmd = (
                f"spec-kitty spec-commit --mission {mission_slug} "
                f"-m '{message}' <files>"
            )
            diag = result.diagnostic or "Artifact absent at resolved placement."
            actionable = (
                f"{diag}\n"
                f"To retry after materialising the coordination worktree, run:\n"
                f"  {recovery_cmd}"
            )
            payload = _payload(
                success=False,
                error=actionable,
                placement_ref=result.placement_ref,
                diagnostic=result.diagnostic,
            )
            if json_output:
                print(json.dumps(payload, indent=2))
            else:
                console.print(f"[red]Error:[/red] {actionable}")
            raise typer.Exit(1)

        else:  # "error"
            payload = _payload(
                success=False,
                error=result.diagnostic or "Commit failed.",
                placement_ref=result.placement_ref,
            )
            if json_output:
                print(json.dumps(payload, indent=2))
            else:
                console.print(f"[red]Error:[/red] {result.diagnostic or 'Commit failed.'}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        payload = _payload(success=False, error=str(exc))
        if json_output:
            print(json.dumps(payload, indent=2))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


def _err(json_output: bool, message: str) -> None:
    if json_output:
        print(json.dumps(_payload(success=False, error=message), indent=2))
    else:
        console.print(f"[red]Error:[/red] {message}")
