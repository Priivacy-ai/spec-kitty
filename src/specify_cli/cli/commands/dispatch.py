"""CLI command: spec-kitty dispatch <request> [--profile <id>] [--json].

This is the single public standalone governance surface. It routes the request,
loads governance context, opens an Op record, and returns synchronously. It
never spawns a separate LLM call.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from specify_cli.invocation.errors import (
    InvocationWriteError,
    ProfileNotFoundError,
    RouterAmbiguityError,
)
from specify_cli.invocation.executor import InvocationPayload, ProfileInvocationExecutor
from specify_cli.invocation.modes import ModeOfWork, derive_mode
from specify_cli.invocation.propagator import InvocationSaaSPropagator
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.router import ActionRouter
from specify_cli.task_utils import find_repo_root

console = Console()


def _get_repo_root() -> Path:
    """Resolve the repository root using the project's canonical utility."""
    result: Path = find_repo_root()
    return result


def _build_executor(repo_root: Path) -> ProfileInvocationExecutor:
    """Construct the executor with router + SaaS propagator (FR-008 parity)."""
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
    """Rich console output for profile/action/context."""
    console.print(f"[bold green]Profile:[/bold green] {payload.profile_friendly_name} ({payload.profile_id})")
    console.print(f"[bold]Action:[/bold] {payload.action}")
    if payload.router_confidence:
        console.print(f"[dim]Router confidence:[/dim] {payload.router_confidence}")
    console.print(f"[dim]Invocation ID:[/dim] {payload.invocation_id}")
    observations = payload.glossary_observations
    if observations is not None and observations.high_severity:
        warning_lines = [
            "High-severity terminology conflicts detected before this invocation.",
        ]
        for conflict in observations.high_severity:
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
        console.print(Panel(payload.governance_context_text, title="Governance Context", expand=False))
    else:
        console.print("[yellow]Governance context unavailable.[/yellow] Run 'spec-kitty charter synthesize'.")


def render_open_hint_task_execution(payload: InvocationPayload) -> None:
    """Open-Op close hint for standalone dispatch."""
    console.print("\n[bold]This Op is OPEN.[/bold] After completing the work, close it with the real outcome:")
    console.print(
        f"  [dim]spec-kitty profile-invocation complete "
        f"--invocation-id {payload.invocation_id} "
        f"--outcome <done|failed|abandoned> "
        f"\\[--evidence <file>] \\[--artifact <path>] \\[--commit <sha>][/dim]"
    )
    console.print("[dim]Unclosed Ops are reported by `spec-kitty doctor ops` and swept to 'abandoned' when stale.[/dim]")


def profile_not_found_routing(error: ProfileNotFoundError) -> None:
    """Emit structured routing error JSON, then exit 1."""
    typer.echo(
        json.dumps(
            {
                "error": "routing_failed",
                "error_code": "PROFILE_NOT_FOUND",
                "message": str(error),
                "candidates": [],
                "suggestion": "Run 'spec-kitty profiles list' to see available profiles.",
            }
        ),
        err=True,
    )
    raise typer.Exit(1) from error


def _dispatch_impl(
    request: str,
    profile_hint: str | None,
    mode: ModeOfWork,
    json_output: bool,
    *,
    repo_root: Path,
    executor: ProfileInvocationExecutor,
) -> None:
    """Open a standalone Op and emit either JSON or rich console output."""
    try:
        payload = executor.invoke(request, profile_hint=profile_hint, actor=_detect_actor(), mode_of_work=mode)
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
        profile_not_found_routing(e)
        return  # pragma: no cover — handler always raises typer.Exit
    except InvocationWriteError as e:
        typer.echo(json.dumps({"error": "write_failed", "message": str(e)}), err=True)
        raise typer.Exit(1) from e

    # FR-001/FR-002: the Op stays OPEN. The caller closes it via
    # `spec-kitty profile-invocation complete` with the real outcome.
    if json_output:
        typer.echo(json.dumps(payload.to_dict(), indent=2))
        return

    _render_rich_payload(payload)
    render_open_hint_task_execution(payload)

    # Inline drift observation — reads glossary events written by the chokepoint.
    # Returns [] silently on any error; never blocks or crashes the CLI.
    from glossary.observation import ObservationSurface  # lazy import

    _surface = ObservationSurface()
    _notices = _surface.collect_notices(repo_root, invocation_id=payload.invocation_id)
    _surface.render_notices(_notices, console)


def dispatch(
    request: str = typer.Argument(..., help="Natural language request. The router picks the best profile."),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Optional profile ID. Bypasses the router — use when the request is ambiguous.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON payload"),
) -> None:
    """Dispatch a request to a governed Op.

    Uses ActionRouter by default. Pass --profile to bypass routing when the
    request verb is ambiguous. Opens an Op record; the caller closes it with the
    real outcome.
    """
    repo_root = _get_repo_root()
    executor = _build_executor(repo_root)
    _dispatch_impl(
        request,
        profile,
        derive_mode("dispatch"),
        json_output,
        repo_root=repo_root,
        executor=executor,
    )
