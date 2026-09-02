"""CLI command: spec-kitty dispatch <request> [--profile <id>] [--json].

This is the single public standalone governance surface. It routes the request,
loads governance context, opens an Op record, and returns synchronously. It
never spawns a separate LLM call.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import typer
from specify_cli.cli.console import console
from rich.panel import Panel

if TYPE_CHECKING:
    from charter.model_routing import RoutingRecommendation

from specify_cli.invocation.errors import (
    InvocationWriteError,
    ProfileNotFoundError,
    RouterAmbiguityError,
)
from specify_cli.invocation.executor import (
    InvocationPayload,
    ProfileInvocationExecutor,
    build_ambiguous_dry_run_payload,
)
from specify_cli.invocation.modes import ModeOfWork, derive_mode
from specify_cli.invocation.propagator import InvocationSaaSPropagator
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.router import ActionRouter
from specify_cli.task_utils import find_repo_root



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


def _render_empty_charter_warning(payload: InvocationPayload) -> None:
    """One-shot warning (WP02/#3064) when dispatch auto-routed under a wholly-empty charter.

    Gated on the dedicated ``empty_charter_fallback`` flag -- NOT on
    ``payload.profile_id == "generic-agent"`` -- so a deliberate
    ``--profile generic-agent`` dispatch on a configured charter never
    false-warns (research.md Decision 5). Read via ``getattr`` with a
    default: ``InvocationPayload.__init__`` only sets keys callers pass, so
    payloads built without the kwarg (e.g. pre-WP02 test fixtures) must not
    raise ``AttributeError`` here.
    """
    if not getattr(payload, "empty_charter_fallback", False):
        return
    console.print(
        Panel(
            "No charter activations found in this project -- routed to the generic agent.\n"
            "To set a governance baseline, run (see all packs with "
            "`spec-kitty charter pack list`):\n"
            "  spec-kitty charter pack apply minimal\n"
            "This activates config entries -- it does not by itself make an "
            "unmatched request route to a specialist; you may still need an "
            "explicit --profile <name>.",
            title="Empty Charter",
            border_style="yellow",
            expand=False,
        )
    )


def _render_rich_payload(payload: InvocationPayload) -> None:
    """Rich console output for profile/action/context."""
    console.print(f"[bold green]Profile:[/bold green] {payload.profile_friendly_name} ({payload.profile_id})")
    console.print(f"[bold]Action:[/bold] {payload.action}")
    if payload.router_confidence:
        console.print(f"[dim]Router confidence:[/dim] {payload.router_confidence}")
    console.print(f"[dim]Invocation ID:[/dim] {payload.invocation_id}")
    _render_empty_charter_warning(payload)
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
    recommendation = payload.recommendation
    if recommendation is not None:
        console.print(Panel(_format_recommendation(recommendation), title="Model Routing Recommendation (advisory)", border_style="cyan", expand=False))
    if payload.governance_context_available and payload.governance_context_text:
        console.print(Panel(payload.governance_context_text, title="Governance Context", expand=False))
    else:
        console.print("[yellow]Governance context unavailable.[/yellow] Run 'spec-kitty charter synthesize'.")


def _format_recommendation(recommendation: RoutingRecommendation) -> str:
    """Render the FR-004 advisory recommendation as rich-panel body text.

    Advisory only (C-001): both the catalog's computed pick and the
    profile's declared preference are surfaced with provenance, neither is
    enforced -- mirrors the ``--json`` payload's ``recommendation`` shape
    (dataclasses.asdict) so both renders carry identical data.
    """
    lines = [f"Task type: {recommendation.task_type} (objective: {recommendation.objective})"]
    catalog_candidate = recommendation.catalog_candidate
    if catalog_candidate is not None:
        score = f"{catalog_candidate.score:.2f}" if catalog_candidate.score is not None else "n/a"
        line = f"Catalog pick: {catalog_candidate.model_id} (score={score})"
        if catalog_candidate.rationale:
            line += f" — {catalog_candidate.rationale}"
        lines.append(line)
    profile_candidate = recommendation.profile_candidate
    if profile_candidate is not None:
        line = f"Profile preference: {profile_candidate.model_id}"
        if profile_candidate.effort:
            line += f" (effort={profile_candidate.effort})"
        lines.append(line)
    return "\n".join(lines)


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


def _emit_routing_error_and_exit(e: RouterAmbiguityError) -> NoReturn:
    """Build and emit the one exit-1 structured routing-error JSON shape.

    Shared by both the invoke()-path handler and the dry-run-path's non-
    ROUTER_AMBIGUOUS branch (extracted so the two never hand-duplicate this
    construction and silently drift apart).
    """
    error_obj = {
        "error": "routing_failed",
        "error_code": e.error_code,
        "message": str(e),
        "candidates": e.candidates,
        "suggestion": e.suggestion,
    }
    typer.echo(json.dumps(error_obj), err=True)
    raise typer.Exit(1) from e


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
    dry_run: bool = False,
) -> None:
    """Open a standalone Op and emit either JSON or rich console output.

    ``dry_run=True`` (FR-001) is a SECOND, separate try/except scoped only to
    ``executor.dry_run(...)`` -- kept distinct from the invoke()-path
    try/except below, never merged with it. Python ``except`` selects by
    exception type, not a boolean: ROUTER_AMBIGUOUS and ROUTER_NO_MATCH are
    the *same* exception type (``RouterAmbiguityError``, distinguished only
    by ``e.error_code``), so the two paths' different policies for
    ROUTER_AMBIGUOUS (exit 0 with a payload here; exit 1 on invoke()) cannot
    share one ``except`` clause across two call sites.
    """
    if dry_run:
        try:
            payload = executor.dry_run(request, profile_hint=profile_hint, actor=_detect_actor())
        except RouterAmbiguityError as e:
            if e.error_code == "ROUTER_AMBIGUOUS":
                # FR-009: exit 0 with the ambiguous dry-run payload, alternatives populated.
                typer.echo(json.dumps(build_ambiguous_dry_run_payload(request, e)))
                return
            # ROUTER_NO_MATCH: "no partial signal worth reporting" — same
            # exit-1 shape real dispatch already produces.
            _emit_routing_error_and_exit(e)
        except ProfileNotFoundError as e:
            # Dead/defensive branch: route()'s Level-1 explicit-hint branch
            # already catches ProfileNotFoundError internally and re-raises
            # it as RouterAmbiguityError(error_code="PROFILE_NOT_FOUND")
            # before it would ever reach this call site — mirrors the
            # existing pragma-no-cover dead branch on the invoke()-path
            # handler below. Kept for defense-in-depth, not because it fires.
            profile_not_found_routing(e)
            return  # pragma: no cover — handler always raises typer.Exit
        typer.echo(json.dumps(payload.to_dry_run_dict([])))
        return

    try:
        payload = executor.invoke(request, profile_hint=profile_hint, actor=_detect_actor(), mode_of_work=mode)
    except RouterAmbiguityError as e:
        _emit_routing_error_and_exit(e)
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
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Route the request and return the routing signal without opening an Op or writing anything.",
    ),
) -> None:
    """Dispatch a request to a governed Op.

    Uses ActionRouter by default. Pass --profile to bypass routing when the
    request verb is ambiguous. Opens an Op record; the caller closes it with the
    real outcome. Pass --dry-run to get the routing signal only -- no Op is
    opened, no kitty-ops/ file is written, no glossary event is persisted, and
    nothing is submitted to the SaaS propagator.
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
        dry_run=dry_run,
    )
