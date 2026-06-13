"""CLI command: spec-kitty dispatch <request> [--profile <id>] [--json]

Canonical profile-governed dispatch surface. `dispatch`, `do`, `ask`, and
`advise` are all first-class verbs that route through the SAME single mechanism
(`ProfileInvocationExecutor.invoke()`) via the shared `_dispatch_impl` below.
No LLM call is ever made here.

| verb     | argument shape                         | mode           |
|----------|----------------------------------------|----------------|
| dispatch | optional `--profile`                   | task_execution |
| do       | optional `--profile` (router fallback) | task_execution |
| ask      | mandatory positional profile           | task_execution |
| advise   | optional `--profile`/`-p`              | advisory       |

Op-record parity (NFR-001): the JSONL written at
`invocation/writer.py::invocation_path(<invocation_id>)` is byte/contract-
identical across the four verbs, except the unique invocation_id, timestamps,
and the deliberate `mode_of_work` difference (advise -> advisory).

Registration: `dispatch` is a plain function registered via @app.command() in
__init__.py. The aliases stay registered alongside it (C-002 — they land in the
same change and are never broken).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
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


# ---------------------------------------------------------------------------
# Shared helpers (unified from the former do_cmd.py + advise.py duplicates)
# ---------------------------------------------------------------------------


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
    """Rich console output shared across all four verbs (profile/action/context)."""
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
    """Open-Op close hint for the dispatch/do/ask verbs (task_execution)."""
    console.print("\n[bold]This Op is OPEN.[/bold] After completing the work, close it with the real outcome:")
    console.print(
        f"  [dim]spec-kitty profile-invocation complete "
        f"--invocation-id {payload.invocation_id} "
        f"--outcome <done|failed|abandoned> "
        f"\\[--evidence <file>] \\[--artifact <path>] \\[--commit <sha>][/dim]"
    )
    console.print("[dim]Unclosed Ops are reported by `spec-kitty doctor ops` and swept to 'abandoned' when stale.[/dim]")


def render_open_hint_advisory(payload: InvocationPayload) -> None:
    """Open-Op close hint for the advise verb (advisory)."""
    console.print(
        f"\n[dim]Close this record:[/dim] spec-kitty profile-invocation complete --invocation-id {payload.invocation_id} --outcome <done|failed|abandoned>"
    )
    console.print(f"[dim]Commit the op record:[/dim] git add kitty-ops/{payload.invocation_id}.jsonl")


def profile_not_found_advisory(error: ProfileNotFoundError) -> None:
    """Emit the advise/ask-style ProfileNotFound error JSON, then exit 1."""
    typer.echo(json.dumps({"error": "profile_not_found", "message": str(error)}), err=True)
    raise typer.Exit(1) from error


def profile_not_found_routing(error: ProfileNotFoundError) -> None:
    """Emit the do/dispatch-style structured routing error JSON, then exit 1.

    `do`/`dispatch` surface the richer `routing_failed`/`PROFILE_NOT_FOUND`
    envelope (with candidates + suggestion) so the router escape hatch is
    discoverable. This shape is pinned by the existing `do` integration tests.
    """
    typer.echo(
        json.dumps(
            {
                "error": "routing_failed",
                "error_code": "PROFILE_NOT_FOUND",
                "message": str(error),
                "candidates": [],
                "suggestion": "Run 'spec-kitty agent profile list' to see available profiles.",
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
    render_open_hint: Callable[[InvocationPayload], None],
    on_profile_not_found: Callable[[ProfileNotFoundError], None] = profile_not_found_advisory,
) -> None:
    """Single shared body for dispatch/do/ask/advise.

    All four verbs route through this function so the Op record, the ``--json``
    envelope, exit codes, and glossary observations stay byte/contract-identical
    (NFR-001). The verb-specific arg shape, the open-Op rich hint, and the
    ProfileNotFound error envelope are the only things that vary, supplied by
    the caller (the two pre-existing ProfileNotFound shapes are preserved
    verbatim — `do`/`dispatch` use the richer routing envelope, advise/ask the
    short one).

    ``repo_root`` and ``executor`` are injected by each verb wrapper so the
    wrapper's own module-level ``find_repo_root`` / ``ProfileRegistry`` seams
    remain patchable by existing tests.
    """
    try:
        payload = executor.invoke(
            request, profile_hint=profile_hint, actor=_detect_actor(), mode_of_work=mode
        )
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
        on_profile_not_found(e)
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
    render_open_hint(payload)

    # Inline drift observation — reads glossary events written by the chokepoint.
    # Returns [] silently on any error; never blocks or crashes the CLI.
    from glossary.observation import ObservationSurface  # lazy import

    _surface = ObservationSurface()
    _notices = _surface.collect_notices(repo_root, invocation_id=payload.invocation_id)
    _surface.render_notices(_notices, console)


# ---------------------------------------------------------------------------
# Canonical dispatch command — registered via @app.command() in __init__.py
# ---------------------------------------------------------------------------


def dispatch(
    request: str = typer.Argument(..., help="Natural language request. The router picks the best profile."),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Optional profile ID. Bypasses the router — use when the request is ambiguous.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON payload"),
) -> None:
    """Dispatch a request to a profile-governed Op (canonical surface).

    Uses ActionRouter by default. Pass --profile to bypass routing when the
    request verb is ambiguous. Opens an Op record; the caller closes it with the
    real outcome. do/ask/advise are first-class aliases of this mechanism.
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
        render_open_hint=render_open_hint_task_execution,
        on_profile_not_found=profile_not_found_routing,
    )
