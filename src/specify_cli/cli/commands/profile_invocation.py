"""CLI command group: spec-kitty profile-invocation.

``spec-kitty dispatch`` opens standalone Ops. This module owns the companion
``profile-invocation complete`` close path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console

from specify_cli.cli.commands.dispatch import _build_executor
from specify_cli.invocation.errors import (
    AlreadyClosedError,
    ContextUnavailableError,  # noqa: F401 — re-exported for callers/tests
    InvalidModeForEvidenceError,
)
from specify_cli.invocation.writer import normalise_ref
from specify_cli.task_utils import find_repo_root

# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

console = Console()


def _get_repo_root() -> Path:
    """Resolve the repository root using the project's canonical utility."""
    result: Path = find_repo_root()
    return result


profile_invocation_app = typer.Typer(
    name="profile-invocation",
    help="Manage invocation records.",
)


def _handle_complete_already_closed(
    invocation_id: str,
    *,
    json_output: bool,
) -> None:
    msg: dict[str, str] = {"error": "already_closed", "invocation_id": invocation_id}
    if json_output:
        typer.echo(json.dumps(msg), err=True)
    else:
        console.print(f"[red]Error:[/red] Invocation {invocation_id} is already closed.")
    raise typer.Exit(1) from None


def _render_complete_response(
    *,
    invocation_id: str,
    outcome: str | None,
    evidence_ref: str | None,
    artifact: list[str] | None,
    commit: str | None,
    repo_root: Path,
    json_output: bool,
) -> None:
    if json_output:
        response = {
            "result": "success",
            "invocation_id": invocation_id,
            "outcome": outcome,
            "evidence_ref": evidence_ref,
            "artifact_links": [normalise_ref(a, repo_root) for a in (artifact or [])],
            "commit_link": commit,
        }
        typer.echo(json.dumps(response, indent=2))
        return

    console.print(f"[green]✓[/green] Invocation [bold]{invocation_id}[/bold] closed.")
    if outcome:
        console.print(f"  Outcome: {outcome}")
    if artifact:
        for item in artifact:
            console.print(f"  Artifact: {normalise_ref(item, repo_root)}")
    if commit:
        console.print(f"  Commit: {commit}")


@profile_invocation_app.command("complete")
def complete_invocation(
    invocation_id: str = typer.Option(..., "--invocation-id", "-i", help="Invocation ULID to close"),
    outcome: str = typer.Option(..., "--outcome", help="done | failed | abandoned"),
    evidence: str | None = typer.Option(None, "--evidence", help="Path to evidence file (Tier 2 promotion)"),
    artifact: list[str] = typer.Option(
        None,
        "--artifact",
        help="Path (repo-relative or absolute) of an artifact produced by this invocation. Repeatable.",
    ),
    commit: str | None = typer.Option(
        None,
        "--commit",
        help="Git commit SHA most directly produced by this invocation. Singular.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON payload"),
) -> None:
    """Close an open invocation record. --invocation-id and --outcome are required.

    Use --artifact (repeatable) to link output artifacts to this invocation.
    Use --commit (singular) to link the primary git commit produced.
    Use --evidence to promote a file to a Tier 2 evidence artifact.
    Note: --evidence is rejected for records that are not execution records.
    """
    # Explicit-outcome guard (schema v2): a missing or invalid outcome is a
    # usage error at the CLI boundary — never silently coerced to "done".
    valid_outcomes: dict[str, Literal["done", "failed", "abandoned"]] = {
        "done": "done",
        "failed": "failed",
        "abandoned": "abandoned",
    }
    checked_outcome = valid_outcomes.get(outcome)
    if checked_outcome is None:
        raise typer.BadParameter(
            f"invalid outcome {outcome!r}: must be one of done, failed, abandoned",
            param_hint="--outcome",
        )

    repo_root = _get_repo_root()
    executor = _build_executor(repo_root)
    try:
        completed = executor.complete_invocation(
            invocation_id=invocation_id,
            outcome=checked_outcome,
            evidence_ref=evidence,
            artifact_refs=artifact or [],
            commit_sha=commit,
            # The CLI surface is the manual/agent close path; the doctor sweep
            # (the only other closer) calls the executor directly (FR-003).
            closed_by="agent",
        )
    except InvalidModeForEvidenceError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2) from e
    except AlreadyClosedError:
        _handle_complete_already_closed(invocation_id, json_output=json_output)
    except Exception as e:
        typer.echo(json.dumps({"error": "complete_failed", "message": str(e)}), err=True)
        raise typer.Exit(1) from e

    _render_complete_response(
        invocation_id=invocation_id,
        outcome=outcome,
        evidence_ref=completed.evidence_ref,
        artifact=artifact,
        commit=commit,
        repo_root=repo_root,
        json_output=json_output,
    )
