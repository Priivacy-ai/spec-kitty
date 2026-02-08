"""Canonical status management commands for AI agents.

Provides CLI access to the status emit/materialize pipeline:
- ``spec-kitty agent status emit`` -- record a lane transition
- ``spec-kitty agent status materialize`` -- rebuild status.json from event log
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from specify_cli.core.feature_detection import (
    detect_feature_slug,
    FeatureDetectionError,
)
from specify_cli.core.paths import locate_project_root, get_main_repo_root

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="status",
    help="Canonical status management commands",
    no_args_is_help=True,
)

console = Console()


def _find_feature_slug(explicit_feature: str | None = None) -> str:
    """Find the current feature slug using centralized detection.

    Args:
        explicit_feature: Optional explicit feature slug from --feature flag

    Returns:
        Feature slug (e.g., "034-feature-name")

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
        console.print(
            "\n[dim]Hint: Use --feature <slug> to specify explicitly[/dim]"
        )
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


@app.command()
def emit(
    wp_id: Annotated[str, typer.Argument(help="Work package ID (e.g., WP01)")],
    to: Annotated[str, typer.Option("--to", help="Target lane (e.g., claimed, in_progress, for_review, done)")] = ...,
    actor: Annotated[str, typer.Option("--actor", help="Who is making this transition")] = ...,
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    force: Annotated[bool, typer.Option("--force", help="Force transition bypassing guards")] = False,
    reason: Annotated[Optional[str], typer.Option("--reason", help="Reason for forced transition")] = None,
    evidence_json: Annotated[Optional[str], typer.Option("--evidence-json", help="JSON string with done evidence")] = None,
    review_ref: Annotated[Optional[str], typer.Option("--review-ref", help="Review feedback reference")] = None,
    execution_mode: Annotated[str, typer.Option("--execution-mode", help="Execution mode (worktree or direct_repo)")] = "worktree",
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
    try:
        # Resolve repo root
        cwd = Path.cwd().resolve()
        repo_root = locate_project_root(cwd)
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        main_repo_root = get_main_repo_root(repo_root)

        # Resolve feature slug
        feature_slug = _find_feature_slug(explicit_feature=feature)

        # Construct feature directory
        feature_dir = main_repo_root / "kitty-specs" / feature_slug

        # Parse evidence JSON if provided
        evidence = None
        if evidence_json is not None:
            try:
                evidence = json.loads(evidence_json)
            except json.JSONDecodeError as exc:
                example = '{"review": {"reviewer": "alice", "verdict": "approved", "reference": "PR#1"}}'
                _output_error(
                    json_output,
                    f"Invalid JSON in --evidence-json: {exc}\n"
                    f"Expected valid JSON object, e.g.: '{example}'",
                )
                raise typer.Exit(1)

        # Lazy import to avoid circular imports
        from specify_cli.status.emit import (
            TransitionError,
            emit_status_transition,
        )

        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=feature_slug,
            wp_id=wp_id,
            to_lane=to,
            actor=actor,
            force=force,
            reason=reason,
            evidence=evidence,
            review_ref=review_ref,
            execution_mode=execution_mode,
            repo_root=main_repo_root,
        )

        # Build result
        result = {
            "event_id": event.event_id,
            "wp_id": event.wp_id,
            "from_lane": str(event.from_lane),
            "to_lane": str(event.to_lane),
            "actor": event.actor,
        }

        _output_result(
            json_output,
            result,
            f"[green]OK[/green] {event.wp_id}: "
            f"{event.from_lane} -> {event.to_lane} "
            f"(event: {event.event_id[:12]}...)",
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
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output")] = False,
) -> None:
    """Rebuild status.json from the canonical event log.

    Reads all events from status.events.jsonl, applies the deterministic
    reducer to produce a snapshot, writes status.json, and updates legacy
    compatibility views.

    Examples:
        spec-kitty agent status materialize
        spec-kitty agent status materialize --feature 034-my-feature
        spec-kitty agent status materialize --json
    """
    try:
        # Resolve repo root
        cwd = Path.cwd().resolve()
        repo_root = locate_project_root(cwd)
        if repo_root is None:
            _output_error(json_output, "Could not locate project root")
            raise typer.Exit(1)

        main_repo_root = get_main_repo_root(repo_root)

        # Resolve feature slug
        feature_slug = _find_feature_slug(explicit_feature=feature)

        # Construct feature directory
        feature_dir = main_repo_root / "kitty-specs" / feature_slug

        # Lazy import to avoid circular imports
        from specify_cli.status.reducer import materialize as do_materialize
        from specify_cli.status.store import EVENTS_FILENAME

        # Check that the events file exists
        events_path = feature_dir / EVENTS_FILENAME
        if not events_path.exists():
            _output_error(
                json_output,
                f"No event log found at {events_path}\n"
                "Run 'spec-kitty agent status emit' to create the first event, "
                "or run a migration to initialize the event log.",
            )
            raise typer.Exit(1)

        # Materialize snapshot
        snapshot = do_materialize(feature_dir)

        # Update legacy views (try/except -- don't block on legacy bridge)
        try:
            from specify_cli.status.legacy_bridge import update_all_views
            update_all_views(feature_dir, snapshot)
        except ImportError:
            pass  # Legacy bridge not yet available (WP06 not merged)
        except Exception as exc:
            if not json_output:
                console.print(
                    f"[yellow]Warning:[/yellow] Legacy bridge update failed: {exc}"
                )

        # Build output
        if json_output:
            print(json.dumps(snapshot.to_dict()))
        else:
            # Human-readable summary
            wp_count = len(snapshot.work_packages)
            event_count = snapshot.event_count

            console.print(
                f"[green]Materialized[/green] {feature_slug}: "
                f"{event_count} events -> {wp_count} WPs"
            )

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
