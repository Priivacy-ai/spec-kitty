"""CLI command: spec-kitty do <request> [--json]

Anonymous profile dispatch — always routes through ActionRouter, never
accepts an explicit profile hint. This is the simplest entry point for
operators who want governance context without knowing which profile to target.

Registration: do is a plain function registered via @app.command() in __init__.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from specify_cli.invocation.errors import InvocationWriteError, RouterAmbiguityError
from specify_cli.invocation.executor import InvocationPayload, ProfileInvocationExecutor
from specify_cli.invocation.modes import derive_mode
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.router import ActionRouter
from specify_cli.task_utils import find_repo_root

# ---------------------------------------------------------------------------
# Shared utilities (mirror of advise.py — both modules kept lean)
# ---------------------------------------------------------------------------

console = Console()


def _get_repo_root() -> Path:
    """Resolve the repository root using the project's canonical utility."""
    result: Path = find_repo_root()
    return result


def _build_executor(repo_root: Path) -> ProfileInvocationExecutor:
    registry = ProfileRegistry(repo_root)
    router = ActionRouter(registry)
    return ProfileInvocationExecutor(repo_root, router=router)


def _detect_actor() -> str:
    """Detect caller identity from environment variables."""
    import os

    if os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude"
    if os.environ.get("CODEX_CLI"):
        return "codex"
    return "operator"


def _render_rich_payload(payload: InvocationPayload) -> None:
    """Rich console output for human-readable do response."""
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


# ---------------------------------------------------------------------------
# do command function — registered via @app.command() in __init__.py
# ---------------------------------------------------------------------------


def do(
    request: str = typer.Argument(
        ..., help="Natural language request. The router picks the best profile."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON payload"),
) -> None:
    """Route a request to the best-matching profile (anonymous dispatch).

    Always uses ActionRouter — no explicit profile hint. On ambiguity or no-match,
    exits 1 with a structured error listing candidates.
    Use 'spec-kitty ask <profile> <request>' to be explicit.
    """
    repo_root = _get_repo_root()
    executor = _build_executor(repo_root)
    mode = derive_mode("do")
    try:
        payload = executor.invoke(request, profile_hint=None, actor=_detect_actor(), mode_of_work=mode)
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
