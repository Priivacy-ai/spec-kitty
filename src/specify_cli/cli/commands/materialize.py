"""Materialize command — regenerate all derived views from the event log.

Derived views (status.json, board-summary.json, progress.json) are
output-only artefacts stored under ``.kittify/derived/<mission_slug>/``.
This command forces full regeneration for one or all features, which is
useful for CI pipelines, debugging, and external SaaS consumers.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Annotated, Any

import typer
from rich.console import Console

from specify_cli.cli.selector_resolution import resolve_selector
from specify_cli.core.paths import locate_project_root

console = Console()


def materialize(
    mission: Annotated[
        str | None,
        typer.Option("--mission", help="Mission slug to materialise (all if omitted)"),
    ] = None,
    feature: Annotated[
        str | None,
        typer.Option("--feature", hidden=True, help="(deprecated) Use --mission"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output a machine-readable JSON summary"),
    ] = False,
) -> None:
    """Regenerate all derived views from the canonical event log.

    For each feature (or a single feature when --mission is given),
    writes the following files to ``.kittify/derived/<slug>/``:

    - ``status.json`` — full StatusSnapshot
    - ``board-summary.json`` — lane counts and WP lists
    - ``progress.json`` — lane-weighted progress percentage

    Examples::

        spec-kitty materialize
        spec-kitty materialize --mission 034-my-feature
        spec-kitty materialize --json
    """
    from specify_cli.status.views import write_derived_views
    from specify_cli.status.progress import generate_progress_json

    repo_root = locate_project_root()
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    specs_dir = repo_root / "kitty-specs"
    derived_dir = repo_root / ".kittify" / "derived"
    derived_dir.mkdir(parents=True, exist_ok=True)

    # Resolve feature directories to process
    mission_slug = None
    if mission is not None or feature is not None:
        mission_slug = resolve_selector(
            canonical_value=mission,
            canonical_flag="--mission",
            alias_value=feature,
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
            command_hint="--mission <slug>",
        ).canonical_value

    if mission_slug:
        feature_dirs = [specs_dir / mission_slug]
        if not feature_dirs[0].exists():
            console.print(f"[red]Error:[/red] Mission not found: {mission_slug}")
            raise typer.Exit(1)
    else:
        if not specs_dir.exists():
            feature_dirs = []
        else:
            feature_dirs = sorted(
                p for p in specs_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
            )

    processed: list[dict[str, Any]] = []
    errors: list[str] = []

    for feature_dir in feature_dirs:
        slug = feature_dir.name
        files_written: list[str] = []
        try:
            write_derived_views(feature_dir, derived_dir)
            files_written += ["status.json", "board-summary.json"]
            generate_progress_json(feature_dir, derived_dir)
            files_written.append("progress.json")
            processed.append({
                "mission_slug": slug,
                "files_written": files_written,
                "timestamp": datetime.now(UTC).isoformat(),
            })
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{slug}: {exc}")

    summary = {
        "processed": len(processed),
        "errors": errors,
        "missions": processed,
        "derived_dir": str(derived_dir),
    }

    if json_output:
        console.print_json(json.dumps(summary, indent=2))
    else:
        if not processed:
            console.print("[dim]No features materialised.[/dim]")
        else:
            for entry in processed:
                slug = entry.get("mission_slug") or entry.get("mission_slug")
                files = ", ".join(entry["files_written"])
                console.print(f"[green]OK[/green] {slug} — {files}")
        if errors:
            console.print()
            for err in errors:
                console.print(f"[red]ERR[/red] {err}")
        else:
            console.print(f"\n[dim]{len(processed)} mission(s) materialised to {derived_dir}[/dim]")

    raise typer.Exit(0 if not errors else 1)
