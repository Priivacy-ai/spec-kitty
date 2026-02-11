"""Change command - capture mid-implementation review requests as work packages."""

from __future__ import annotations

import json as json_mod
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import (
    check_version_compatibility,
    get_project_root_or_exit,
    show_banner,
)
from specify_cli.core.change_classifier import classify_change_request
from specify_cli.core.change_stack import (
    ChangeStackError,
    ValidationState,
    generate_change_work_packages,
    reconcile_change_stack,
    synthesize_change_plan,
    validate_change_request,
    write_change_work_packages,
)
from specify_cli.tasks_support import TaskCliError, find_repo_root

console = Console()


def change(
    request: Optional[str] = typer.Argument(
        None, help="Change request description (interactive if omitted)"
    ),
    feature: Optional[str] = typer.Option(
        None, "--feature", help="Feature slug to target (auto-detected when omitted)"
    ),
    json_output: Optional[str] = typer.Option(
        None, "--json", help="Write JSON output to this path"
    ),
    preview: bool = typer.Option(
        False, "--preview", help="Preview change plan without applying"
    ),
) -> None:
    """Capture a mid-implementation change request and create work packages.

    Analyzes the change request, assesses complexity, and generates one or
    more work packages with correct dependencies and documentation links.

    Examples:
        # Interactive mode (prompted for request)
        spec-kitty change

        # Direct request
        spec-kitty change "use SQLAlchemy instead of raw SQL"

        # Preview without creating WPs
        spec-kitty change "refactor auth module" --preview

        # JSON output for automation
        spec-kitty change "add caching layer" --json output.json
    """
    show_banner()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    project_root = get_project_root_or_exit(repo_root)
    check_version_compatibility(project_root, "change")

    tracker = StepTracker("Change Request")
    tracker.add("project", "Locate project root")
    tracker.add("validate", "Validate change request")
    tracker.add("assess", "Assess complexity")
    tracker.add("plan", "Plan work packages")
    console.print()

    # Step 1: Locate project
    tracker.start("project")
    tracker.complete("project", str(project_root))

    # Step 2: Validate change request (stash routing + ambiguity)
    tracker.start("validate")
    if not request:
        tracker.error("validate", "No change request provided")
        console.print(tracker.render())
        console.print()
        console.print("[yellow]Usage:[/yellow]")
        console.print('  spec-kitty change "your change request here"')
        console.print()
        console.print("[dim]Interactive mode not yet implemented.[/dim]")
        raise typer.Exit(1)

    try:
        change_req = validate_change_request(
            request_text=request,
            repo_root=repo_root,
            feature=feature,
        )
    except ChangeStackError as exc:
        tracker.error("validate", str(exc))
        console.print(tracker.render())
        console.print(f"\n[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    if change_req.validation_state == ValidationState.AMBIGUOUS:
        tracker.error("validate", "Ambiguous request")
        console.print(tracker.render())
        console.print(
            f"\n[yellow]Clarification needed:[/yellow] {change_req.ambiguity.clarification_prompt}"
        )
        if json_output:
            Path(json_output).write_text(
                json_mod.dumps(
                    {
                        "mode": "preview",
                        "status": "ambiguous",
                        "requestId": change_req.request_id,
                        "clarificationPrompt": change_req.ambiguity.clarification_prompt,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        raise typer.Exit(1)

    tracker.complete("validate", f"Routed to {change_req.stash.scope.value} stash")

    # Step 3: Assess complexity (default scores for human CLI; agents use agent change apply)
    tracker.start("assess")
    score = change_req.complexity_score or classify_change_request(request)
    classification = score.classification.value
    tracker.complete("assess", f"{classification} (score {score.total_score}/10)")

    if preview:
        console.print(tracker.render())
        console.print()
        console.print(f"[bold]Preview:[/bold]")
        console.print(f"  Request ID: {change_req.request_id}")
        console.print(
            f"  Stash: {change_req.stash.stash_key} ({change_req.stash.scope.value})"
        )
        console.print(f"  Stash path: {change_req.stash.stash_path}")
        console.print(f"  Complexity: {classification} ({score.total_score}/10)")
        console.print(f"  Proposed mode: {score.proposed_mode.value}")
        if score.recommend_specify:
            console.print()
            console.print(
                "[yellow]Warning:[/yellow] This request exceeds the complexity threshold."
            )
            console.print(
                "  Consider using [bold]/spec-kitty.specify[/bold] for full planning."
            )
        result = {
            "mode": "preview",
            "requestId": change_req.request_id,
            "stashKey": change_req.stash.stash_key,
            "stashScope": change_req.stash.scope.value,
            "complexity": score.to_dict(),
            "status": "previewed",
        }
        if json_output:
            Path(json_output).write_text(
                json_mod.dumps(result, indent=2), encoding="utf-8"
            )
        return

    # Step 4: Synthesize and create work packages
    tracker.start("plan")

    if score.recommend_specify:
        tracker.error(
            "plan",
            "High complexity - use /spec-kitty.specify or agent change apply --continue",
        )
        console.print(tracker.render())
        console.print()
        console.print(
            "[yellow]Warning:[/yellow] This request exceeds the complexity threshold."
        )
        console.print("  Use [bold]/spec-kitty.specify[/bold] for full planning, or")
        console.print(
            "  use [bold]spec-kitty agent change apply --continue[/bold] to proceed anyway."
        )
        if json_output:
            Path(json_output).write_text(
                json_mod.dumps(
                    {
                        "mode": "apply",
                        "status": "blocked_high_complexity",
                        "requestId": change_req.request_id,
                        "complexity": score.to_dict(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        raise typer.Exit(1)

    plan = synthesize_change_plan(change_req)
    tasks_dir = change_req.stash.stash_path
    wps = generate_change_work_packages(change_req, plan, tasks_dir)
    written_paths = write_change_work_packages(wps, tasks_dir)

    # Reconcile
    feature_dir = change_req.stash.stash_path.parent
    consistency = reconcile_change_stack(tasks_dir, feature_dir, wps)

    tracker.complete("plan", f"Created {len(wps)} WP(s)")

    console.print(tracker.render())
    console.print()
    for wp in wps:
        console.print(f"  Created: {wp.work_package_id} - {wp.title}")
    if consistency.issues:
        console.print()
        for issue in consistency.issues:
            console.print(f"  [yellow]Warning:[/yellow] {issue}")

    result = {
        "mode": "apply",
        "status": "applied",
        "requestId": change_req.request_id,
        "stashKey": change_req.stash.stash_key,
        "createdWorkPackages": [wp.to_dict() for wp in wps],
        "writtenFiles": [str(p) for p in written_paths],
        "complexity": score.to_dict(),
    }
    if json_output:
        Path(json_output).write_text(json_mod.dumps(result, indent=2), encoding="utf-8")


__all__ = ["change"]
