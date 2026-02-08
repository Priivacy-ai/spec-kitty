"""Status health check commands for AI agents."""

from __future__ import annotations

import json as json_mod
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from specify_cli.core.feature_detection import (
    FeatureDetectionError,
    detect_feature_slug,
)
from specify_cli.core.paths import get_main_repo_root, locate_project_root

app = typer.Typer(
    name="status",
    help="Status health check commands",
    no_args_is_help=True,
)

console = Console()


def _find_feature_slug(explicit_feature: str | None = None) -> str:
    """Find the current feature slug using centralized detection.

    Args:
        explicit_feature: Optional explicit feature slug from --feature flag

    Returns:
        Feature slug (e.g., "034-feature-status-state-model-remediation")

    Raises:
        typer.Exit: If feature slug cannot be determined
    """
    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)

    if repo_root is None:
        console.print("[red]Error:[/red] Could not locate project root")
        raise typer.Exit(1)

    try:
        return detect_feature_slug(
            repo_root,
            explicit_feature=explicit_feature,
            cwd=cwd,
            mode="strict",
        )
    except FeatureDetectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _resolve_feature_dir(
    explicit_feature: str | None,
) -> tuple[Path, str, Path]:
    """Resolve feature directory, feature slug, and repo root.

    Returns:
        (feature_dir, feature_slug, repo_root)

    Raises:
        typer.Exit: If resolution fails
    """
    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)

    if repo_root is None:
        console.print("[red]Error:[/red] Could not locate project root")
        raise typer.Exit(1)

    feature_slug = _find_feature_slug(explicit_feature=explicit_feature)
    main_repo_root = get_main_repo_root(repo_root)
    feature_dir = main_repo_root / "kitty-specs" / feature_slug

    return feature_dir, feature_slug, main_repo_root


@app.command()
def doctor(
    feature: Annotated[
        Optional[str],
        typer.Option("--feature", help="Feature slug"),
    ] = None,
    stale_claimed: Annotated[
        int,
        typer.Option(
            "--stale-claimed-days", help="Threshold for stale claims (days)"
        ),
    ] = 7,
    stale_in_progress: Annotated[
        int,
        typer.Option(
            "--stale-in-progress-days",
            help="Threshold for stale in-progress (days)",
        ),
    ] = 14,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Run health checks for status hygiene.

    Detects stale claims, orphan workspaces, and drift issues.
    Exit code 0 = healthy, 1 = issues found.

    Examples:
        spec-kitty agent status doctor
        spec-kitty agent status doctor --feature 034-my-feature
        spec-kitty agent status doctor --stale-claimed-days 3 --json
    """
    from specify_cli.status.doctor import run_doctor

    feature_dir, feature_slug, repo_root = _resolve_feature_dir(feature)

    try:
        result = run_doctor(
            feature_dir=feature_dir,
            feature_slug=feature_slug,
            repo_root=repo_root,
            stale_claimed_days=stale_claimed,
            stale_in_progress_days=stale_in_progress,
        )
    except FileNotFoundError as e:
        if json_output:
            console.print_json(
                json_mod.dumps({"error": str(e), "healthy": False})
            )
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        report = {
            "feature_slug": result.feature_slug,
            "healthy": result.is_healthy,
            "findings": [
                {
                    "severity": str(f.severity),
                    "category": str(f.category),
                    "wp_id": f.wp_id,
                    "message": f.message,
                    "recommended_action": f.recommended_action,
                }
                for f in result.findings
            ],
        }
        console.print_json(json_mod.dumps(report))
    else:
        if result.is_healthy:
            console.print(
                f"[green]Healthy[/green]: {result.feature_slug}"
            )
        else:
            console.print(
                f"[yellow]Issues found[/yellow]: {result.feature_slug}"
            )
            table = Table(title="Doctor Findings")
            table.add_column("Severity", style="bold")
            table.add_column("Category")
            table.add_column("WP")
            table.add_column("Message")
            table.add_column("Action")
            for f in result.findings:
                severity_style = (
                    "red" if f.severity == "error" else "yellow"
                )
                table.add_row(
                    f"[{severity_style}]{f.severity}[/{severity_style}]",
                    str(f.category),
                    f.wp_id or "-",
                    f.message,
                    f.recommended_action,
                )
            console.print(table)

    raise typer.Exit(0 if result.is_healthy else 1)
