"""Canonical status management commands for AI agents.

Provides CLI access to the status emit/materialize pipeline:
- ``spec-kitty agent status emit`` -- record a lane transition
- ``spec-kitty agent status materialize`` -- rebuild status.json from event log
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table
from typing import Annotated

from specify_cli.cli.commands._flag_utils import resolve_mission_or_feature
from specify_cli.core.mission_detection import (
    detect_mission_slug,
    MissionDetectionError,
)
from specify_cli.core.paths import locate_project_root, get_main_repo_root
from specify_cli.status.locking import mission_status_lock

logger = logging.getLogger(__name__)

app: typer.Typer = typer.Typer(
    name="status",
    help="Canonical status management commands",
    no_args_is_help=True,
)

console = Console()


def _find_mission_slug(explicit_mission: str | None = None) -> str:
    """Find the current mission slug using centralized detection.

    Args:
        explicit_mission: Optional explicit mission slug from --mission flag

    Returns:
        Mission slug (e.g., "034-mission-name")

    Raises:
        typer.Exit: If mission slug cannot be determined
    """
    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)

    if repo_root is None:
        console.print("[red]Error:[/red] Could not locate project root")
        raise typer.Exit(1)

    try:
        return detect_mission_slug(
            repo_root,
            explicit_mission=explicit_mission,
            cwd=cwd,
            mode="strict",
        )
    except MissionDetectionError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("\n[dim]Hint: Use --mission <slug> to specify explicitly[/dim]")
        raise typer.Exit(1)


def _output_result(json_mode: bool, data: dict, success_message: str | None = None):
    """Output result in JSON or human-readable format."""
    if json_mode:
        print(json.dumps(data))
    elif success_message:
        console.print(success_message)


def _output_error(json_mode: bool, error_message: str):
    """Output error in JSON or human-readable format."""
    if json_mode:
        print(json.dumps({"error": error_message}))
    else:
        console.print(f"[red]Error:[/red] {error_message}")


def _resolve_mission_dir(
    explicit_mission: str | None = None,
) -> tuple[Path, str, Path]:
    """Resolve mission directory, mission slug, and repo root.

    Returns:
        (mission_dir, mission_slug, repo_root)

    Raises:
        typer.Exit: If resolution fails
    """
    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)

    if repo_root is None:
        console.print("[red]Error:[/red] Could not locate project root")
        raise typer.Exit(1)

    mission_slug = _find_mission_slug(explicit_mission=explicit_mission)
    main_repo_root = get_main_repo_root(repo_root)
    mission_dir = main_repo_root / "kitty-specs" / mission_slug

    return mission_dir, mission_slug, main_repo_root


@app.command()
def emit(
    wp_id: Annotated[str, typer.Argument(help="Work package ID (e.g., WP01)")],
    to: Annotated[
        str, typer.Option("--to", help="Target lane (e.g., claimed, in_progress, for_review, approved, done)")
    ] = ...,
    actor: Annotated[str, typer.Option("--actor", help="Who is making this transition")] = ...,
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug (auto-detected if omitted)")] = None,
    feature: Annotated[str | None, typer.Option("--feature", hidden=True, help="[Deprecated] Use --mission")] = None,
    force: Annotated[bool, typer.Option("--force", help="Force transition bypassing guards")] = False,
    reason: Annotated[str | None, typer.Option("--reason", help="Reason for forced transition")] = None,
    evidence_json: Annotated[
        str | None, typer.Option("--evidence-json", help="JSON string with done evidence")
    ] = None,
    review_ref: Annotated[str | None, typer.Option("--review-ref", help="Review feedback reference")] = None,
    workspace_context: Annotated[
        str | None, typer.Option("--workspace-context", help="Workspace context identifier for claimed->in_progress")
    ] = None,
    subtasks_complete: Annotated[
        bool | None,
        typer.Option("--subtasks-complete", help="Whether required subtasks are complete for in_progress->for_review"),
    ] = None,
    implementation_evidence_present: Annotated[
        bool | None,
        typer.Option(
            "--implementation-evidence-present",
            help="Whether implementation evidence exists for in_progress->for_review",
        ),
    ] = None,
    execution_mode: Annotated[
        str, typer.Option("--execution-mode", help="Execution mode (worktree or direct_repo)")
    ] = "worktree",
    json_output: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output")] = False,
) -> None:
    """Emit a status transition event for a work package.

    Records a lane transition in the canonical event log, validates the
    transition against the state machine, materializes a snapshot, and
    updates legacy compatibility views.

    Examples:
        spec-kitty agent status emit WP01 --to claimed --actor claude
        spec-kitty agent status emit WP01 --to done --actor claude --evidence-json '{"review": {"reviewer": "alice", "verdict": "approved", "reference": "PR#1"}}'
        spec-kitty agent status emit WP01 --to in_progress --actor claude --force --reason "resuming after crash"
    """
    mission_flag = resolve_mission_or_feature(mission, feature)
    try:
        # Resolve repo root
        cwd = Path.cwd().resolve()
        repo_root = locate_project_root(cwd)
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        main_repo_root = get_main_repo_root(repo_root)

        # Resolve mission slug
        mission_slug = _find_mission_slug(explicit_mission=mission_flag)

        # Construct mission directory
        mission_dir = main_repo_root / "kitty-specs" / mission_slug

        # Parse evidence JSON if provided
        evidence = None
        if evidence_json is not None:
            try:
                evidence = json.loads(evidence_json)
            except json.JSONDecodeError as exc:
                example = '{"review": {"reviewer": "alice", "verdict": "approved", "reference": "PR#1"}}'
                _output_error(
                    json_output,
                    f"Invalid JSON in --evidence-json: {exc}\nExpected valid JSON object, e.g.: '{example}'",
                )
                raise typer.Exit(1)

        # Lazy import to avoid circular imports
        from specify_cli.status.emit import (
            TransitionError,
            emit_status_transition,
        )

        event = emit_status_transition(
            mission_dir=mission_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            to_lane=to,
            actor=actor,
            force=force,
            reason=reason,
            evidence=evidence,
            review_ref=review_ref,
            workspace_context=workspace_context,
            subtasks_complete=subtasks_complete,
            implementation_evidence_present=implementation_evidence_present,
            execution_mode=execution_mode,
            repo_root=main_repo_root,
        )

        # Build result
        result = {
            "event_id": event.event_id,
            "wp_id": event.wp_id,
            "from_lane": str(event.from_lane),
            "to_lane": str(event.to_lane),
            "actor": event.actor.to_dict(),
        }

        _output_result(
            json_output,
            result,
            f"[green]OK[/green] {event.wp_id}: {event.from_lane} -> {event.to_lane} (event: {event.event_id[:12]}...)",
        )

    except typer.Exit:
        raise
    except Exception as exc:
        # Check if it's a TransitionError (imported lazily above)
        try:
            from specify_cli.status.emit import TransitionError

            if isinstance(exc, TransitionError):
                _output_error(json_output, str(exc))
                raise typer.Exit(1)
        except ImportError:
            pass
        _output_error(json_output, str(exc))
        raise typer.Exit(1)


@app.command()
def materialize(
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug (auto-detected if omitted)")] = None,
    feature: Annotated[str | None, typer.Option("--feature", hidden=True, help="[Deprecated] Use --mission")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output")] = False,
) -> None:
    """Rebuild status.json from the canonical event log.

    Reads all events from status.events.jsonl, applies the deterministic
    reducer to produce a snapshot, writes status.json, and updates legacy
    compatibility views.

    Examples:
        spec-kitty agent status materialize
        spec-kitty agent status materialize --mission 034-my-mission
        spec-kitty agent status materialize --json
    """
    mission_flag = resolve_mission_or_feature(mission, feature)
    try:
        # Resolve repo root
        cwd = Path.cwd().resolve()
        repo_root = locate_project_root(cwd)
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        main_repo_root = get_main_repo_root(repo_root)

        # Resolve mission slug
        mission_slug = _find_mission_slug(explicit_mission=mission_flag)

        # Construct mission directory
        mission_dir = main_repo_root / "kitty-specs" / mission_slug

        # Lazy import to avoid circular imports
        from specify_cli.status.reducer import materialize as do_materialize
        from specify_cli.status.store import EVENTS_FILENAME

        # Check that the events file exists
        events_path = mission_dir / EVENTS_FILENAME
        if not events_path.exists():
            _output_error(
                json_output,
                f"No event log found at {events_path}\n"
                "Run 'spec-kitty agent status emit' to create the first event, "
                "or run a migration to initialize the event log.",
            )
            raise typer.Exit(1)

        with mission_status_lock(main_repo_root, mission_slug):
            # Materialize snapshot
            snapshot = do_materialize(mission_dir)

        # Update legacy views (try/except -- don't block on legacy bridge)
        try:
            from specify_cli.status.legacy_bridge import update_all_views

            update_all_views(mission_dir, snapshot)
        except ImportError:
            pass  # Legacy bridge not yet available (WP06 not merged)
        except Exception as exc:
            if not json_output:
                console.print(f"[yellow]Warning:[/yellow] Legacy bridge update failed: {exc}")

        # Build output
        if json_output:
            print(json.dumps(snapshot.to_dict()))
        else:
            # Human-readable summary
            wp_count = len(snapshot.work_packages)
            event_count = snapshot.event_count

            console.print(f"[green]Materialized[/green] {mission_slug}: {event_count} events -> {wp_count} WPs")

            # Lane distribution
            lane_parts = []
            for lane_name, count in sorted(snapshot.summary.items()):
                if count > 0:
                    lane_parts.append(f"{lane_name}: {count}")
            if lane_parts:
                console.print(f"  {', '.join(lane_parts)}")

    except typer.Exit:
        raise
    except Exception as exc:
        _output_error(json_output, str(exc))
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Doctor command (WP12)
# ---------------------------------------------------------------------------


@app.command()
def doctor(
    mission: Annotated[
        str | None,
        typer.Option("--mission", help="Mission slug"),
    ] = None,
    feature: Annotated[
        str | None,
        typer.Option("--feature", hidden=True, help="[Deprecated] Use --mission"),
    ] = None,
    stale_claimed: Annotated[
        int,
        typer.Option("--stale-claimed-days", help="Threshold for stale claims (days)"),
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
    """Run health checks for status hygiene and global runtime.

    Detects global runtime issues (missing ~/.kittify/, version mismatch,
    corrupted missions) and project-level issues (stale claims, orphan
    workspaces, drift).
    Exit code 0 = healthy, 1 = issues found.

    Examples:
        spec-kitty agent status doctor
        spec-kitty agent status doctor --mission 034-my-mission
        spec-kitty agent status doctor --stale-claimed-days 3 --json
    """
    mission_flag = resolve_mission_or_feature(mission, feature)
    from specify_cli.runtime.doctor import run_global_checks
    from specify_cli.status.doctor import run_doctor

    mission_dir, mission_slug, repo_root = _resolve_mission_dir(mission_flag)

    # Run global runtime checks BEFORE project-specific checks
    global_checks = run_global_checks(project_dir=repo_root)
    global_has_issues = any(not c.passed for c in global_checks)

    try:
        result = run_doctor(
            mission_dir=mission_dir,
            mission_slug=mission_slug,
            repo_root=repo_root,
            stale_claimed_days=stale_claimed,
            stale_in_progress_days=stale_in_progress,
        )
    except FileNotFoundError as e:
        if json_output:
            console.print_json(json.dumps({"error": str(e), "healthy": False}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    overall_healthy = result.is_healthy and not global_has_issues

    if json_output:
        report = {
            "mission_slug": result.mission_slug,
            "healthy": overall_healthy,
            "global_runtime": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "severity": c.severity,
                }
                for c in global_checks
            ],
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
        console.print_json(json.dumps(report))
    else:
        # Global Runtime section
        console.print("\n[bold]Global Runtime:[/bold]")
        for check in global_checks:
            if check.passed:
                icon = "✓"
                color = "green"
            elif check.severity == "warning":
                icon = "⚠"
                color = "yellow"
            else:
                icon = "✗"
                color = "red"
            console.print(f"  [{color}]{icon}[/{color}] {check.message}")

        # Project-specific section
        console.print(f"\n[bold]Mission Status: {result.mission_slug}[/bold]")
        if result.is_healthy:
            console.print("  [green]Healthy[/green]")
        else:
            console.print("  [yellow]Issues found[/yellow]")
            table = Table(title="Doctor Findings")
            table.add_column("Severity", style="bold")
            table.add_column("Category")
            table.add_column("WP")
            table.add_column("Message")
            table.add_column("Action")
            for f in result.findings:
                severity_style = "red" if f.severity == "error" else "yellow"
                table.add_row(
                    f"[{severity_style}]{f.severity}[/{severity_style}]",
                    str(f.category),
                    f.wp_id or "-",
                    f.message,
                    f.recommended_action,
                )
            console.print(table)

    raise typer.Exit(0 if overall_healthy else 1)


# ---------------------------------------------------------------------------
# Migration command (WP14)
# ---------------------------------------------------------------------------


def _migration_result_to_dict(result: Any) -> dict[str, Any]:
    """Convert a MigrationResult to a JSON-serializable dict."""
    return {
        "missions": [
            {
                "mission_slug": f.mission_slug,
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
            for f in result.missions
        ],
        "summary": {
            "total_migrated": result.total_migrated,
            "total_skipped": result.total_skipped,
            "total_failed": result.total_failed,
            "aliases_resolved": result.aliases_resolved,
        },
    }


def _status_style(status: str) -> str:
    return {
        "migrated": "[green]migrated[/green]",
        "skipped": "[yellow]skipped[/yellow]",
        "failed": "[red]failed[/red]",
    }.get(status, status)


def _print_rich_migrate_output(result: Any, *, dry_run: bool) -> None:
    title = "Migration Preview (dry-run)" if dry_run else "Migration Results"
    table = Table(title=title)
    table.add_column("Mission", style="cyan")
    table.add_column("Status")
    table.add_column("WPs", justify="right")
    table.add_column("Aliases Resolved", justify="right")
    table.add_column("Notes")

    for f in result.missions:
        aliases = sum(1 for wp in f.wp_details if wp.alias_resolved)
        notes = f.error or ""
        table.add_row(
            f.mission_slug,
            _status_style(f.status),
            str(len(f.wp_details)),
            str(aliases),
            notes,
        )

    console.print()
    console.print(table)
    console.print()

    console.print(
        f"Migrated: [green]{result.total_migrated}[/green]  "
        f"Skipped: [yellow]{result.total_skipped}[/yellow]  "
        f"Failed: [red]{result.total_failed}[/red]  "
        f"Aliases resolved: {result.aliases_resolved}"
    )
    console.print()


@app.command()
def migrate(
    mission: Annotated[
        str | None,
        typer.Option("--mission", "-f", help="Single mission slug to migrate"),
    ] = None,
    feature: Annotated[
        str | None,
        typer.Option("--feature", hidden=True, help="[Deprecated] Use --mission"),
    ] = None,
    all_features: Annotated[
        bool,
        typer.Option("--all", help="Migrate all missions in kitty-specs/"),
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
    Idempotent: missions with existing event logs are skipped.

    Examples:
        spec-kitty agent status migrate --mission 034-mission-name --dry-run
        spec-kitty agent status migrate --all
        spec-kitty agent status migrate --all --json
    """
    mission_flag = resolve_mission_or_feature(mission, feature)
    from specify_cli.status.migrate import (
        MissionMigrationResult,
        MigrationResult,
        migrate_mission,
    )

    if mission_flag and all_features:
        _output_error(json_output, "Cannot use both --mission and --all")
        raise typer.Exit(1)

    if not mission_flag and not all_features:
        _output_error(json_output, "Specify --mission or --all")
        raise typer.Exit(1)

    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)
    if repo_root is None:
        _output_error(json_output, "Could not locate project root")
        raise typer.Exit(1)

    kitty_specs = repo_root / "kitty-specs"
    if not kitty_specs.exists():
        _output_error(json_output, "No kitty-specs/ directory found")
        raise typer.Exit(1)

    if mission_flag:
        mission_dir = kitty_specs / mission_flag
        if not mission_dir.is_dir():
            _output_error(json_output, f"Mission directory not found: {mission_dir}")
            raise typer.Exit(1)
        mission_dirs = [mission_dir]
    else:
        mission_dirs = sorted(d for d in kitty_specs.iterdir() if d.is_dir() and not d.name.startswith("."))
        if not mission_dirs:
            _output_error(json_output, "No missions found to migrate")
            raise typer.Exit(1)

    result = MigrationResult()

    for mdir in mission_dirs:
        try:
            fr = migrate_mission(mdir, actor=actor, dry_run=dry_run)
        except Exception as exc:
            fr = MissionMigrationResult(
                mission_slug=mdir.name,
                status="failed",
                error=str(exc),
            )

        result.missions.append(fr)

        if fr.status == "migrated":
            result.total_migrated += 1
        elif fr.status == "skipped":
            result.total_skipped += 1
        elif fr.status == "failed":
            result.total_failed += 1

    result.aliases_resolved = sum(1 for f in result.missions for wp in f.wp_details if wp.alias_resolved)

    if json_output:
        print(json.dumps(_migration_result_to_dict(result), indent=2))
    else:
        _print_rich_migrate_output(result, dry_run=dry_run)

    if dry_run:
        raise typer.Exit(0)

    if result.total_failed > 0:
        raise typer.Exit(1)

    raise typer.Exit(0)


# ---------------------------------------------------------------------------
# Validate command (WP11)
# ---------------------------------------------------------------------------


@app.command()
def validate(
    mission: Annotated[
        str | None,
        typer.Option("--mission", help="Mission slug (auto-detected if omitted)"),
    ] = None,
    feature: Annotated[
        str | None,
        typer.Option("--feature", hidden=True, help="[Deprecated] Use --mission"),
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

    Examples:
        spec-kitty agent status validate
        spec-kitty agent status validate --mission 034-my-mission
        spec-kitty agent status validate --json
    """
    mission_flag = resolve_mission_or_feature(mission, feature)
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

    mission_slug = _find_mission_slug(explicit_mission=mission_flag)

    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)
    if repo_root is None:
        if json_output:
            print(json.dumps({"error": "Could not locate project root"}))
        else:
            console.print("[red]Error:[/red] Could not locate project root")
        raise typer.Exit(1)

    main_repo_root = get_main_repo_root(repo_root)
    mission_dir = main_repo_root / "kitty-specs" / mission_slug

    if not mission_dir.exists():
        msg = f"Mission directory not found: {mission_dir}"
        if json_output:
            print(json.dumps({"error": msg}))
        else:
            console.print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(1)

    phase, phase_source = resolve_phase(main_repo_root, mission_slug)

    result = ValidationResult()
    result.phase_source = phase_source

    raw_events = read_events_raw(mission_dir)

    if not raw_events:
        if json_output:
            print(
                json.dumps(
                    {
                        "mission_slug": mission_slug,
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
            console.print(f"[green]Status Validation: {mission_slug} (Phase {phase})[/green]")
            console.print("No events to validate.")
            console.print("[green]Result: PASS[/green]")
        raise typer.Exit(0)

    for event in raw_events:
        result.errors.extend(validate_event_schema(event))

    result.errors.extend(validate_transition_legality(raw_events))
    result.errors.extend(validate_done_evidence(raw_events))

    drift_findings = validate_materialization_drift(mission_dir)
    if phase >= 2:
        result.errors.extend(drift_findings)
    else:
        result.warnings.extend(drift_findings)

    try:
        events = read_events(mission_dir)
        snapshot = reduce(events)
        view_findings = validate_derived_views(mission_dir, snapshot.work_packages, phase)
        for finding in view_findings:
            if finding.startswith("ERROR:"):
                result.errors.append(finding)
            elif finding.startswith("WARNING:"):
                result.warnings.append(finding)
            else:
                result.errors.append(finding)
    except Exception as exc:
        result.errors.append(f"Failed to validate derived views: {exc}")

    if json_output:
        print(
            json.dumps(
                {
                    "mission_slug": mission_slug,
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
        console.print(f"\n[bold]Status Validation: {mission_slug} (Phase {phase})[/bold]")
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
                console.print(f"\n[green]Result: PASS[/green] ({len(result.warnings)} warning(s))")
            else:
                console.print("\n[green]Result: PASS[/green]")
        else:
            console.print("\n[red]Result: FAIL[/red]")

    raise typer.Exit(0 if result.passed else 1)


# ---------------------------------------------------------------------------
# Reconcile command (WP13)
# ---------------------------------------------------------------------------


@app.command()
def reconcile(
    mission: Annotated[
        str | None,
        typer.Option("--mission", "-f", help="Mission slug (auto-detected if omitted)"),
    ] = None,
    feature: Annotated[
        str | None,
        typer.Option("--feature", hidden=True, help="[Deprecated] Use --mission"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--apply", help="Preview vs persist reconciliation events"),
    ] = True,
    target_repo: Annotated[
        list[Path] | None,
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

    Examples:
        spec-kitty agent status reconcile --dry-run
        spec-kitty agent status reconcile --mission 034-mission-name --json
        spec-kitty agent status reconcile --apply --target-repo /path/to/repo
    """
    mission_flag = resolve_mission_or_feature(mission, feature)
    from specify_cli.status.reconcile import (
        format_reconcile_report,
        reconcile as do_reconcile,
        reconcile_result_to_json,
    )

    mission_slug = _find_mission_slug(explicit_mission=mission_flag)

    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)
    if repo_root is None:
        if json_output:
            print(json.dumps({"error": "Could not locate project root"}))
        else:
            console.print("[red]Error:[/red] Could not locate project root")
        raise typer.Exit(1)

    main_repo_root = get_main_repo_root(repo_root)
    mission_dir = main_repo_root / "kitty-specs" / mission_slug

    if not mission_dir.exists():
        msg = f"Mission directory not found: {mission_dir}"
        if json_output:
            print(json.dumps({"error": msg}))
        else:
            console.print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(1)

    target_repos: list[Path] = []
    if target_repo:
        for repo_path in target_repo:
            target_repos.append(repo_path.resolve())
    else:
        target_repos.append(main_repo_root)

    if not dry_run:
        from specify_cli.status.phase import resolve_phase

        phase, source = resolve_phase(main_repo_root, mission_slug)
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

    try:
        result = do_reconcile(
            mission_dir=mission_dir,
            repo_root=main_repo_root,
            target_repos=target_repos,
            dry_run=dry_run,
        )
    except ValueError as exc:
        if json_output:
            print(json.dumps({"error": str(exc)}))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(reconcile_result_to_json(result), indent=2))
    else:
        format_reconcile_report(result)

    if result.errors:
        raise typer.Exit(2)
    if result.drift_detected and dry_run:
        raise typer.Exit(1)
    raise typer.Exit(0)
