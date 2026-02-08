"""Status management commands for the canonical event-log engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from specify_cli.core.paths import locate_project_root
from specify_cli.status.migrate import (
    FeatureMigrationResult,
    MigrationResult,
    migrate_feature,
)

app = typer.Typer(
    name="status",
    help="Status engine commands (event log, migration, validation)",
    no_args_is_help=True,
)

console = Console()


# ---------------------------------------------------------------------------
# JSON serialization helper
# ---------------------------------------------------------------------------

def _migration_result_to_dict(result: MigrationResult) -> dict[str, Any]:
    """Convert a MigrationResult to a JSON-serializable dict."""
    return {
        "features": [
            {
                "feature_slug": f.feature_slug,
                "status": f.status,
                "wp_count": len(f.wp_details),
                "wp_details": [
                    {
                        "wp_id": wp.wp_id,
                        "original_lane": wp.original_lane,
                        "canonical_lane": wp.canonical_lane,
                        "alias_resolved": wp.alias_resolved,
                    }
                    for wp in f.wp_details
                ],
                "error": f.error,
            }
            for f in result.features
        ],
        "summary": {
            "total_migrated": result.total_migrated,
            "total_skipped": result.total_skipped,
            "total_failed": result.total_failed,
            "aliases_resolved": result.aliases_resolved,
        },
    }


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------

@app.command()
def migrate(
    feature: Annotated[
        Optional[str],
        typer.Option("--feature", "-f", help="Single feature slug to migrate"),
    ] = None,
    all_features: Annotated[
        bool,
        typer.Option("--all", help="Migrate all features in kitty-specs/"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview migration without writing events"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON"),
    ] = False,
    actor: Annotated[
        str,
        typer.Option("--actor", help="Actor name for bootstrap events"),
    ] = "migration",
) -> None:
    """Bootstrap canonical event logs from existing frontmatter state.

    Reads WP frontmatter lanes and creates bootstrap StatusEvents in
    status.events.jsonl. Resolves aliases (e.g. ``doing`` -> ``in_progress``).
    Idempotent: features with existing event logs are skipped.

    Examples:
        spec-kitty agent status migrate --feature 034-feature-name --dry-run
        spec-kitty agent status migrate --all
        spec-kitty agent status migrate --all --json
    """
    # ------------------------------------------------------------------
    # Validate flags
    # ------------------------------------------------------------------
    if feature and all_features:
        _output_error(json_output, "Cannot use both --feature and --all")
        raise typer.Exit(1)

    if not feature and not all_features:
        _output_error(json_output, "Specify --feature or --all")
        raise typer.Exit(1)

    # ------------------------------------------------------------------
    # Locate kitty-specs
    # ------------------------------------------------------------------
    repo_root = locate_project_root()
    if repo_root is None:
        _output_error(json_output, "Could not locate project root")
        raise typer.Exit(1)

    kitty_specs = repo_root / "kitty-specs"
    if not kitty_specs.exists():
        _output_error(json_output, "No kitty-specs/ directory found")
        raise typer.Exit(1)

    # ------------------------------------------------------------------
    # Resolve feature directories
    # ------------------------------------------------------------------
    if feature:
        feature_dir = kitty_specs / feature
        if not feature_dir.is_dir():
            _output_error(json_output, f"Feature directory not found: {feature_dir}")
            raise typer.Exit(1)
        feature_dirs = [feature_dir]
    else:
        feature_dirs = sorted(
            d for d in kitty_specs.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        if not feature_dirs:
            _output_error(json_output, "No features found to migrate")
            raise typer.Exit(1)

    # ------------------------------------------------------------------
    # Run migration for each feature
    # ------------------------------------------------------------------
    result = MigrationResult()

    for fdir in feature_dirs:
        try:
            fr = migrate_feature(fdir, actor=actor, dry_run=dry_run)
        except Exception as exc:
            fr = FeatureMigrationResult(
                feature_slug=fdir.name,
                status="failed",
                error=str(exc),
            )

        result.features.append(fr)

        if fr.status == "migrated":
            result.total_migrated += 1
        elif fr.status == "skipped":
            result.total_skipped += 1
        elif fr.status == "failed":
            result.total_failed += 1

    # Compute aggregate alias count
    result.aliases_resolved = sum(
        1
        for f in result.features
        for wp in f.wp_details
        if wp.alias_resolved
    )

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    if json_output:
        print(json.dumps(_migration_result_to_dict(result), indent=2))
    else:
        _print_rich_output(result, dry_run=dry_run)

    # ------------------------------------------------------------------
    # Exit code
    # ------------------------------------------------------------------
    if dry_run:
        raise typer.Exit(0)

    if result.total_failed > 0:
        raise typer.Exit(1)

    raise typer.Exit(0)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _output_error(json_mode: bool, message: str) -> None:
    if json_mode:
        print(json.dumps({"error": message}))
    else:
        console.print(f"[red]Error:[/red] {message}")


def _status_style(status: str) -> str:
    return {
        "migrated": "[green]migrated[/green]",
        "skipped": "[yellow]skipped[/yellow]",
        "failed": "[red]failed[/red]",
    }.get(status, status)


def _print_rich_output(result: MigrationResult, *, dry_run: bool) -> None:
    title = "Migration Preview (dry-run)" if dry_run else "Migration Results"
    table = Table(title=title)
    table.add_column("Feature", style="cyan")
    table.add_column("Status")
    table.add_column("WPs", justify="right")
    table.add_column("Aliases Resolved", justify="right")
    table.add_column("Notes")

    for f in result.features:
        aliases = sum(1 for wp in f.wp_details if wp.alias_resolved)
        notes = f.error or ""
        table.add_row(
            f.feature_slug,
            _status_style(f.status),
            str(len(f.wp_details)),
            str(aliases),
            notes,
        )

    console.print()
    console.print(table)
    console.print()

    # Summary line
    console.print(
        f"Migrated: [green]{result.total_migrated}[/green]  "
        f"Skipped: [yellow]{result.total_skipped}[/yellow]  "
        f"Failed: [red]{result.total_failed}[/red]  "
        f"Aliases resolved: {result.aliases_resolved}"
    )
    console.print()
