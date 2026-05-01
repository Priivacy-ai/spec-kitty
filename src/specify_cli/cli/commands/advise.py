"""CLI command groups: spec-kitty advise, spec-kitty ask, spec-kitty profile-invocation.

All three surfaces are profile-governed invocation commands. They call
ProfileInvocationExecutor.invoke() — no LLM call is ever made here.

advise:             spec-kitty advise <request> [--profile <name>] [--json]
ask:                spec-kitty ask <profile> <request> [--json]
profile-invocation: spec-kitty profile-invocation complete --invocation-id <id>

Registration: advise and ask are plain @app.command() functions registered
directly on the main CLI. profile_invocation_app is a sub-typer registered
as "profile-invocation".
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from specify_cli.invocation.errors import (
    AlreadyClosedError,
    ContextUnavailableError,  # noqa: F401 — re-exported for callers/tests
    InvalidModeForEvidenceError,
    InvocationWriteError,
    ProfileNotFoundError,
    RouterAmbiguityError,
)
from specify_cli.invocation.executor import InvocationPayload, ProfileInvocationExecutor
from specify_cli.invocation.modes import derive_mode
from specify_cli.invocation.propagator import InvocationSaaSPropagator
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.router import ActionRouter
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


def _build_executor(repo_root: Path) -> ProfileInvocationExecutor:
    registry = ProfileRegistry(repo_root)
    router = ActionRouter(registry)
    propagator = InvocationSaaSPropagator(repo_root)
    return ProfileInvocationExecutor(repo_root, router=router, propagator=propagator)


def _detect_actor() -> str:
    """Detect caller identity from environment variables."""
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude"
    if os.environ.get("CODEX_CLI"):
        return "codex"
    return "operator"


def _render_rich_payload(payload: InvocationPayload) -> None:
    """Rich console output for human-readable advise/ask response."""
    console.print(
        f"[bold green]Profile:[/bold green] {payload.profile_friendly_name} ({payload.profile_id})"
    )
    console.print(f"[bold]Action:[/bold] {payload.action}")
    if payload.router_confidence:
        console.print(f"[dim]Router confidence:[/dim] {payload.router_confidence}")
    console.print(f"[dim]Invocation ID:[/dim] {payload.invocation_id}")
    if payload.glossary_observations.high_severity:
        warning_lines = [
            "High-severity terminology conflicts detected before this invocation.",
        ]
        for conflict in payload.glossary_observations.high_severity:
            scopes = ", ".join(sorted({sense.scope for sense in conflict.candidate_senses}))
            detail = f"{conflict.term.surface_text} ({conflict.conflict_type.value})"
            if scopes:
                detail += f" — candidate scopes: {scopes}"
            warning_lines.append(f"- {detail}")
        console.print(
            Panel(
                "\n".join(warning_lines),
                title="Glossary Warning",
                border_style="yellow",
                expand=False,
            )
        )
    if payload.governance_context_available and payload.governance_context_text:
        console.print(
            Panel(payload.governance_context_text, title="Governance Context", expand=False)
        )
    else:
        console.print(
            "[yellow]Governance context unavailable.[/yellow] "
            "Run 'spec-kitty charter synthesize'."
        )
    console.print(
        f"\n[dim]Close this record:[/dim] "
        f"spec-kitty profile-invocation complete --invocation-id {payload.invocation_id}"
    )


def _run_invoke(
    request: str,
    profile: str | None,
    json_output: bool,
    entry_command: str = "advise",
) -> None:
    """Shared implementation for advise and ask commands."""
    repo_root = _get_repo_root()
    executor = _build_executor(repo_root)
    mode = derive_mode(entry_command)
    try:
        payload = executor.invoke(request, profile_hint=profile, actor=_detect_actor(), mode_of_work=mode)
    except RouterAmbiguityError as e:
        error_obj = {
            "error": "routing_failed",
            "error_code": e.error_code,
            "message": str(e),
            "candidates": e.candidates,
            "suggestion": e.suggestion,
        }
        typer.echo(json.dumps(error_obj), err=True)
        raise typer.Exit(1) from e
    except ProfileNotFoundError as e:
        typer.echo(
            json.dumps({"error": "profile_not_found", "message": str(e)}), err=True
        )
        raise typer.Exit(1) from e
    except InvocationWriteError as e:
        typer.echo(
            json.dumps({"error": "write_failed", "message": str(e)}), err=True
        )
        raise typer.Exit(1) from e

    if json_output:
        typer.echo(json.dumps(payload.to_dict(), indent=2))
    else:
        _render_rich_payload(payload)

    # Inline drift observation — reads glossary events written by the chokepoint
    # (WP5.2). Returns [] silently on any error; never blocks or crashes the CLI.
    from specify_cli.glossary.observation import ObservationSurface  # lazy import

    _surface = ObservationSurface()
    _notices = _surface.collect_notices(repo_root, invocation_id=payload.invocation_id)
    _surface.render_notices(_notices, console)


# ---------------------------------------------------------------------------
# advise command function — registered via @app.command() in __init__.py
# ---------------------------------------------------------------------------


def advise(
    request: str = typer.Argument(..., help="Natural language request to route"),
    profile: str | None = typer.Option(
        None, "--profile", "-p", help="Explicit profile ID or name"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON payload"),
) -> None:
    """Get governance context for a request. Opens an invocation record. Does NOT spawn an LLM."""
    _run_invoke(request, profile, json_output, entry_command="advise")


# ---------------------------------------------------------------------------
# ask command function — registered via @app.command() in __init__.py
# ---------------------------------------------------------------------------


def ask(
    profile: str = typer.Argument(..., help="Profile ID or name"),
    request: str = typer.Argument(..., help="Natural language request"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON payload"),
) -> None:
    """Invoke a named profile. Equivalent to 'advise --profile <profile> <request>'."""
    _run_invoke(request, profile, json_output, entry_command="ask")


# ---------------------------------------------------------------------------
# profile-invocation app — registered as a sub-typer
# ---------------------------------------------------------------------------

profile_invocation_app = typer.Typer(
    name="profile-invocation",
    help="Manage invocation records.",
)


def _handle_complete_already_closed(
    invocation_id: str,
    *,
    json_output: bool,
) -> None:
    msg: dict[str, str] = {"warning": "already_closed", "invocation_id": invocation_id}
    if json_output:
        typer.echo(json.dumps(msg))
    else:
        console.print(
            f"[yellow]Warning:[/yellow] Invocation {invocation_id} is already closed."
        )
    raise typer.Exit(0) from None


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
    invocation_id: str = typer.Option(
        ..., "--invocation-id", "-i", help="Invocation ULID to close"
    ),
    outcome: str | None = typer.Option(
        None, "--outcome", help="done | failed | abandoned"
    ),
    evidence: str | None = typer.Option(
        None, "--evidence", help="Path to evidence file (Tier 2 promotion)"
    ),
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
    """Close an open invocation record. Only --invocation-id is required.

    Use --artifact (repeatable) to link output artifacts to this invocation.
    Use --commit (singular) to link the primary git commit produced.
    Use --evidence to promote a file to a Tier 2 evidence artifact.
    Note: --evidence is not allowed on advisory or query invocations (FR-009).
    """
    repo_root = _get_repo_root()
    executor = _build_executor(repo_root)
    try:
        completed = executor.complete_invocation(
            invocation_id=invocation_id,
            outcome=outcome,
            evidence_ref=evidence,
            artifact_refs=artifact or [],
            commit_sha=commit,
        )
    except InvalidModeForEvidenceError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2) from e
    except AlreadyClosedError:
        _handle_complete_already_closed(invocation_id, json_output=json_output)
    except Exception as e:
        typer.echo(
            json.dumps({"error": "complete_failed", "message": str(e)}), err=True
        )
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
