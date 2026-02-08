"""Status validation commands for AI agents."""

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
    help="Status model validation commands for AI agents",
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
def validate(
    feature: Annotated[
        Optional[str],
        typer.Option("--feature", help="Feature slug (auto-detected if omitted)"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Validate canonical status model integrity.

    Runs all validation checks: event schema, transition legality,
    done-evidence completeness, materialization drift, and derived-view drift.

    Exit code 0 for pass (no errors), exit code 1 for fail (any errors).
    Warnings do not cause failure.

    Phase-aware: Phase 1 drift is reported as warnings, Phase 2 drift
    is reported as errors.

    Examples:
        spec-kitty agent status validate
        spec-kitty agent status validate --feature 034-my-feature
        spec-kitty agent status validate --json
    """
    from specify_cli.status.phase import resolve_phase
    from specify_cli.status.reducer import reduce
    from specify_cli.status.store import read_events, read_events_raw
    from specify_cli.status.validate import (
        ValidationResult,
        validate_derived_views,
        validate_done_evidence,
        validate_event_schema,
        validate_materialization_drift,
        validate_transition_legality,
    )

    # Resolve feature slug and paths
    feature_slug = _find_feature_slug(explicit_feature=feature)

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

    # Resolve phase
    phase, phase_source = resolve_phase(main_repo_root, feature_slug)

    # Build validation result
    result = ValidationResult()
    result.phase_source = phase_source

    # 1. Read raw events (dicts, not StatusEvent objects)
    raw_events = read_events_raw(feature_dir)

    if not raw_events:
        # No events to validate -- nothing to report
        if json_output:
            print(
                json.dumps(
                    {
                        "feature_slug": feature_slug,
                        "phase": phase,
                        "phase_source": phase_source,
                        "passed": True,
                        "errors": [],
                        "warnings": [],
                        "error_count": 0,
                        "warning_count": 0,
                    }
                )
            )
        else:
            console.print(
                f"[green]Status Validation: {feature_slug} (Phase {phase})[/green]"
            )
            console.print("No events to validate.")
            console.print("[green]Result: PASS[/green]")
        raise typer.Exit(0)

    # 2. Schema validation
    for event in raw_events:
        result.errors.extend(validate_event_schema(event))

    # 3. Transition legality
    result.errors.extend(validate_transition_legality(raw_events))

    # 4. Done-evidence completeness
    result.errors.extend(validate_done_evidence(raw_events))

    # 5. Materialization drift
    drift_findings = validate_materialization_drift(feature_dir)
    if phase >= 2:
        result.errors.extend(drift_findings)
    else:
        result.warnings.extend(drift_findings)

    # 6. Derived-view drift
    # Build snapshot from events for comparison
    try:
        events = read_events(feature_dir)
        snapshot = reduce(events)
        view_findings = validate_derived_views(
            feature_dir, snapshot.work_packages, phase
        )
        # Phase-aware: findings already have severity prefix from validate_derived_views
        for finding in view_findings:
            if finding.startswith("ERROR:"):
                result.errors.append(finding)
            elif finding.startswith("WARNING:"):
                result.warnings.append(finding)
            else:
                # No severity prefix (e.g., missing WP file) -- treat as error
                result.errors.append(finding)
    except Exception as exc:
        result.errors.append(f"Failed to validate derived views: {exc}")

    # Output
    if json_output:
        print(
            json.dumps(
                {
                    "feature_slug": feature_slug,
                    "phase": phase,
                    "phase_source": phase_source,
                    "passed": result.passed,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "error_count": len(result.errors),
                    "warning_count": len(result.warnings),
                }
            )
        )
    else:
        console.print(
            f"\n[bold]Status Validation: {feature_slug} (Phase {phase})[/bold]"
        )
        console.print("-" * 50)

        if result.errors:
            console.print(f"[red]Errors: {len(result.errors)}[/red]")
            for error in result.errors:
                console.print(f"  - {error}")

        if result.warnings:
            console.print(f"[yellow]Warnings: {len(result.warnings)}[/yellow]")
            for warning in result.warnings:
                console.print(f"  - {warning}")

        if result.passed:
            if result.warnings:
                console.print(
                    f"\n[green]Result: PASS[/green] ({len(result.warnings)} warning(s))"
                )
            else:
                console.print("\n[green]Result: PASS[/green]")
        else:
            console.print(f"\n[red]Result: FAIL[/red]")

    raise typer.Exit(0 if result.passed else 1)
