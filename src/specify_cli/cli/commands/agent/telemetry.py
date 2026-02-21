"""Telemetry and cost tracking CLI commands."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import click
import typer
from rich.console import Console
from rich.table import Table

from specify_cli.tasks_support import TaskCliError, find_repo_root
from specify_cli.telemetry.cost import CostSummary, cost_summary
from specify_cli.telemetry.query import (
    EventFilter,
    query_execution_events,
    query_project_events,
)

app = typer.Typer(
    name="telemetry",
    help="Telemetry and cost tracking commands.",
    no_args_is_help=False,
    invoke_without_command=True,
)

console = Console()


def _resolve_feature_dirs(repo_root: Path, feature: str) -> list[Path]:
    """Resolve feature slug or glob to matching kitty-specs directories."""
    kitty_specs = repo_root / "kitty-specs"
    if not kitty_specs.is_dir():
        return []
    matches = sorted(kitty_specs.glob(f"{feature}*/"))
    return [m for m in matches if m.is_dir()]


@app.callback()
def telemetry_callback(
    ctx: typer.Context,
    feature: str | None = typer.Option(None, "--feature", "-f", help="Filter by feature slug or glob pattern"),
    since: str | None = typer.Option(None, "--since", help="Start date (ISO 8601)"),
    until: str | None = typer.Option(None, "--until", help="End date (ISO 8601)"),
    group_by: str = typer.Option(
        "agent",
        "--group-by",
        "-g",
        help="Group by: agent, model, feature, role",
        click_type=click.Choice(["agent", "model", "feature", "role"]),
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Backward-compatible default behavior: `telemetry` maps to `telemetry cost`."""
    if ctx.invoked_subcommand is None:
        cost_cmd(
            feature=feature,
            since=since,
            until=until,
            group_by=group_by,
            json_output=json_output,
        )


@app.command("cost")
def cost_cmd(
    feature: str | None = typer.Option(None, "--feature", "-f", help="Filter by feature slug or glob pattern"),
    since: str | None = typer.Option(None, "--since", help="Start date (ISO 8601)"),
    until: str | None = typer.Option(None, "--until", help="End date (ISO 8601)"),
    group_by: str = typer.Option(
        "agent",
        "--group-by",
        "-g",
        help="Group by: agent, model, feature, role",
        click_type=click.Choice(["agent", "model", "feature", "role"]),
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show cost report for AI agent invocations."""
    try:
        repo_root = find_repo_root()
    except TaskCliError:
        console.print("[red]Error:[/red] Not inside a spec-kitty project.")
        raise typer.Exit(code=1) from None

    try:
        since_dt = datetime.fromisoformat(since) if since else None
        until_dt = datetime.fromisoformat(until) if until else None
    except ValueError as exc:
        console.print(f"[red]Error:[/red] Invalid date format: {exc}")
        console.print("Expected ISO 8601 (e.g. 2026-01-01 or 2026-01-01T00:00:00+00:00)")
        raise typer.Exit(code=1) from None

    filters = EventFilter(
        event_type="ExecutionEvent",
        since=since_dt,
        until=until_dt,
    )

    if feature:
        feature_dirs = _resolve_feature_dirs(repo_root, feature)
        if not feature_dirs:
            console.print(f"[yellow]No features matching '{feature}' found.[/yellow]")
            raise typer.Exit(code=0)
        events = []
        for fd in feature_dirs:
            events.extend(query_execution_events(fd, filters))
    else:
        events = query_project_events(repo_root, filters)

    if not events:
        console.print("No execution events found.")
        raise typer.Exit(code=0)

    summaries = cost_summary(events, group_by=group_by)

    if json_output:
        output = [s.to_dict() for s in summaries]
        console.print_json(json.dumps(output, indent=2))
        return

    _print_table(summaries, group_by)


def _print_table(summaries: list[CostSummary], group_by: str) -> None:
    """Render a Rich table with cost summaries and totals."""
    table = Table(title=f"Cost Report (grouped by {group_by})")
    table.add_column("Group", style="cyan")
    table.add_column("Input Tokens", justify="right")
    table.add_column("Output Tokens", justify="right")
    table.add_column("Cost (USD)", justify="right", style="green")
    table.add_column("Events", justify="right")
    table.add_column("Estimated", justify="center")

    for summary in summaries:
        estimated_flag = "~" if summary.estimated_cost_usd > 0 else ""
        table.add_row(
            summary.group_key,
            f"{summary.total_input_tokens:,}",
            f"{summary.total_output_tokens:,}",
            f"${summary.total_cost_usd:.4f}",
            str(summary.event_count),
            estimated_flag,
        )

    total_cost = sum(s.total_cost_usd for s in summaries)
    total_events = sum(s.event_count for s in summaries)
    total_input = sum(s.total_input_tokens for s in summaries)
    total_output = sum(s.total_output_tokens for s in summaries)
    table.add_section()
    table.add_row(
        "TOTAL",
        f"{total_input:,}",
        f"{total_output:,}",
        f"${total_cost:.4f}",
        str(total_events),
        "",
        style="bold",
    )

    console.print(table)


@app.command("emit")
def emit_cmd(
    feature: str = typer.Option(
        ..., "--feature", "-f", help="Feature slug (e.g., 048-full-lifecycle-telemetry-events)"
    ),
    role: str = typer.Option(
        ...,
        "--role",
        "-r",
        help="Phase role",
        click_type=click.Choice(["specifier", "planner", "implementer", "reviewer", "merger"]),
    ),
    agent: str | None = typer.Option(None, "--agent", help="Agent identifier (claude, copilot, codex, cursor, etc.)"),
    model: str | None = typer.Option(None, "--model", help="LLM model identifier"),
    input_tokens: int | None = typer.Option(None, "--input-tokens", help="Input tokens consumed"),
    output_tokens: int | None = typer.Option(None, "--output-tokens", help="Output tokens generated"),
    cost_usd: float | None = typer.Option(None, "--cost-usd", help="Cost in USD"),
    duration_ms: int = typer.Option(0, "--duration-ms", help="Duration in milliseconds"),
    success: bool = typer.Option(True, "--success/--failure", help="Phase outcome"),
    wp_id: str = typer.Option("N/A", "--wp-id", help="Work package ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Emit a telemetry event for a workflow phase completion."""
    try:
        repo_root = find_repo_root()
    except TaskCliError:
        console.print("[red]Error:[/red] Not inside a spec-kitty project.")
        raise typer.Exit(code=1) from None

    feature_dir = repo_root / "kitty-specs" / feature
    if not feature_dir.exists():
        feature_dir.mkdir(parents=True, exist_ok=True)

    effective_agent = agent or "unknown"

    try:
        from specify_cli.telemetry.emit import emit_execution_event

        emit_execution_event(
            feature_dir=feature_dir,
            feature_slug=feature,
            wp_id=wp_id,
            agent=effective_agent,
            role=role,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            success=success,
            node_id="cli",
        )
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Telemetry emission failed: %s", exc)
        if json_output:
            print(json.dumps({"result": "error", "error": str(exc)}))
        else:
            console.print(f"[yellow]Warning:[/yellow] Telemetry emission failed: {exc}")
        # Fire-and-forget: always exit 0
        return

    if json_output:
        print(
            json.dumps(
                {
                    "result": "success",
                    "feature": feature,
                    "role": role,
                    "agent": effective_agent,
                    "model": model,
                }
            )
        )
    else:
        console.print(f"[green]✓[/green] Telemetry event emitted: {role} for {feature}")
