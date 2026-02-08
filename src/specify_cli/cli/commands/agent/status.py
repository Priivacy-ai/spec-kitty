"""Status commands for AI agents -- validation and reconciliation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from specify_cli.core.feature_detection import (
    FeatureDetectionError,
    detect_feature_slug,
)
from specify_cli.core.paths import get_main_repo_root, locate_project_root

app = typer.Typer(
    name="status",
    help="Status model commands for AI agents",
    no_args_is_help=True,
)

console = Console()


def _find_feature_slug(explicit_feature: str | None = None) -> str:
    """Find the current feature slug using centralized detection."""
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


@app.command()
def reconcile(
    feature: Annotated[
        Optional[str],
        typer.Option("--feature", "-f", help="Feature slug (auto-detected if omitted)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--apply", help="Preview vs persist reconciliation events"),
    ] = True,
    target_repo: Annotated[
        Optional[list[Path]],
        typer.Option("--target-repo", "-t", help="Target repo path(s) to scan"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Detect planning-vs-implementation drift and suggest reconciliation events.

    Scans target repositories for WP-linked branches and commits, compares
    against the canonical snapshot state, and generates StatusEvent objects
    to align planning with implementation reality.

    Default mode is --dry-run which previews without persisting.
    Use --apply to emit reconciliation events (Phase 1+ required).

    Exit codes:
      0: no drift detected (or dry-run completed successfully)
      1: drift detected and --apply not used, or errors
      2: errors during scanning

    Examples:
        spec-kitty agent status reconcile --dry-run
        spec-kitty agent status reconcile --feature 034-feature-name --json
        spec-kitty agent status reconcile --apply --target-repo /path/to/repo
        spec-kitty agent status reconcile -t /repo1 -t /repo2
    """
    from specify_cli.status.reconcile import (
        format_reconcile_report,
        reconcile as do_reconcile,
        reconcile_result_to_json,
    )

    # Resolve feature slug
    feature_slug = _find_feature_slug(explicit_feature=feature)

    # Resolve repo root
    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)
    if repo_root is None:
        if json_output:
            print(json.dumps({"error": "Could not locate project root"}))
        else:
            console.print("[red]Error:[/red] Could not locate project root")
        raise typer.Exit(1)

    main_repo_root = get_main_repo_root(repo_root)
    feature_dir = main_repo_root / "kitty-specs" / feature_slug

    if not feature_dir.exists():
        msg = f"Feature directory not found: {feature_dir}"
        if json_output:
            print(json.dumps({"error": msg}))
        else:
            console.print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(1)

    # Resolve target repos
    target_repos: list[Path] = []
    if target_repo:
        for repo_path in target_repo:
            target_repos.append(repo_path.resolve())
    else:
        # Default: self-reconcile against the current repo
        target_repos.append(main_repo_root)

    # Phase gating for apply mode
    if not dry_run:
        from specify_cli.status.phase import resolve_phase

        phase, source = resolve_phase(main_repo_root, feature_slug)
        if phase < 1:
            msg = (
                "Cannot apply reconciliation events at Phase 0. "
                "Upgrade to Phase 1+ to enable event persistence. "
                "Use --dry-run to preview without persisting."
            )
            if json_output:
                print(json.dumps({"error": msg}))
            else:
                console.print(f"[red]Error:[/red] {msg}")
            raise typer.Exit(1)

    # Run reconciliation
    try:
        result = do_reconcile(
            feature_dir=feature_dir,
            repo_root=main_repo_root,
            target_repos=target_repos,
            dry_run=dry_run,
        )
    except ValueError as exc:
        # Phase gating or other validation errors
        if json_output:
            print(json.dumps({"error": str(exc)}))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    # Output
    if json_output:
        print(json.dumps(reconcile_result_to_json(result), indent=2))
    else:
        format_reconcile_report(result)

    # Exit codes
    if result.errors:
        raise typer.Exit(2)
    if result.drift_detected and dry_run:
        raise typer.Exit(1)
    raise typer.Exit(0)
