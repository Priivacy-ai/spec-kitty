"""Accept command implementation."""

from __future__ import annotations

import json
from typing import List, Optional

import typer
from rich.table import Table

from specify_cli.acceptance import (
    AcceptanceError,
    AcceptanceResult,
    AcceptanceSummary,
    choose_mode,
    collect_feature_summary,
    detect_feature_slug,
    perform_acceptance,
)
from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import console, show_banner
from specify_cli.tasks_support import LANES, TaskCliError, find_repo_root


def _print_acceptance_summary(summary: AcceptanceSummary) -> None:
    table = Table(title="Work Packages by Lane", header_style="cyan")
    table.add_column("Lane")
    table.add_column("Count", justify="right")
    table.add_column("Work Packages", justify="left")
    for lane in LANES:
        items = summary.lanes.get(lane, [])
        display = ", ".join(items) if items else "-"
        table.add_row(lane, str(len(items)), display)
    console.print(table)

    outstanding = summary.outstanding()
    if outstanding:
        console.print("\n[bold red]Outstanding items[/bold red]")
        for key, values in outstanding.items():
            console.print(f"[red]- {key}[/red]")
            for value in values:
                console.print(f"    • {value}")
    else:
        console.print("\n[green]No outstanding acceptance issues detected.[/green]")

    if summary.optional_missing:
        console.print(
            "\n[yellow]Optional artifacts missing:[/yellow] "
            + ", ".join(summary.optional_missing)
        )
        console.print()


def _print_acceptance_result(result: AcceptanceResult) -> None:
    console.print(
        "\n[bold]Acceptance metadata[/bold]\n"
        f"• Feature: {result.summary.feature}\n"
        f"• Accepted at: {result.accepted_at}\n"
        f"• Accepted by: {result.accepted_by}"
    )
    if result.accept_commit:
        console.print(f"• Acceptance commit: {result.accept_commit}")
    if result.parent_commit:
        console.print(f"• Parent commit: {result.parent_commit}")
    if not result.commit_created:
        console.print("• Commit status: no changes were committed (dry-run)")

    if result.instructions:
        console.print("\n[bold]Next steps[/bold]")
        for idx, instruction in enumerate(result.instructions, start=1):
            console.print(f"  {idx}. {instruction}")

    if result.cleanup_instructions:
        console.print("\n[bold]Cleanup[/bold]")
        for idx, instruction in enumerate(result.cleanup_instructions, start=1):
            console.print(f"  {idx}. {instruction}")

    if result.notes:
        console.print("\n[bold]Notes[/bold]")
        for note in result.notes:
            console.print(f"  - {note}")


def accept(
    feature: Optional[str] = typer.Option(None, "--feature", help="Feature slug to accept (auto-detected by default)"),
    mode: str = typer.Option("auto", "--mode", case_sensitive=False, help="Acceptance mode: auto, pr, local, or checklist"),
    actor: Optional[str] = typer.Option(None, "--actor", help="Name to record as the acceptance actor"),
    test: List[str] = typer.Option([], "--test", help="Validation command executed (repeatable)", show_default=False),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of formatted text"),
    lenient: bool = typer.Option(False, "--lenient", help="Skip strict metadata validation"),
    no_commit: bool = typer.Option(False, "--no-commit", help="Skip auto-commit; report only"),
    allow_fail: bool = typer.Option(False, "--allow-fail", help="Return checklist even when issues remain"),
) -> None:
    """Validate feature readiness before merging to main."""

    show_banner()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    tracker = StepTracker("Feature Acceptance")
    tracker.add("detect", "Identify feature slug")
    tracker.add("verify", "Run readiness checks")
    console.print()

    tracker.start("detect")
    try:
        feature_slug = (feature or detect_feature_slug(repo_root)).strip()
    except AcceptanceError as exc:
        tracker.error("detect", str(exc))
        console.print(tracker.render())
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
    tracker.complete("detect", feature_slug)

    requested_mode = (mode or "auto").lower()
    actual_mode = choose_mode(requested_mode, repo_root)
    commit_required = actual_mode != "checklist" and not no_commit
    if commit_required:
        tracker.add("commit", "Record acceptance metadata")
    tracker.add("guide", "Share next steps")

    tracker.start("verify")
    summary = collect_feature_summary(
        repo_root,
        feature_slug,
        strict_metadata=not lenient,
    )
    tracker.complete("verify", "ready" if summary.ok else "issues found")

    if actual_mode == "checklist":
        if json_output:
            console.print(json.dumps(summary.to_dict(), indent=2))
        else:
            _print_acceptance_summary(summary)
        raise typer.Exit(0 if summary.ok else 1)

    if not summary.ok:
        if json_output:
            console.print(json.dumps(summary.to_dict(), indent=2))
        else:
            _print_acceptance_summary(summary)
        if not allow_fail:
            console.print(
                "\n[red]Outstanding acceptance issues detected. Resolve them before merging or rerun with --allow-fail for a checklist-only report.[/red]"
            )
            raise typer.Exit(1)
        raise typer.Exit(1)

    acceptance_tests = list(test)

    try:
        if commit_required:
            tracker.start("commit")
        result = perform_acceptance(
            summary,
            mode=actual_mode,
            actor=actor,
            tests=acceptance_tests,
            auto_commit=commit_required,
        )
        if commit_required:
            detail = "commit created" if result.commit_created else "no changes"
            tracker.complete("commit", detail)
    except AcceptanceError as exc:
        if commit_required:
            tracker.error("commit", str(exc))
            console.print(tracker.render())
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    tracker.start("guide")
    tracker.complete("guide", "instructions ready")
    console.print(tracker.render())

    if json_output:
        console.print(json.dumps(result.to_dict(), indent=2))
        return

    _print_acceptance_summary(result.summary)
    _print_acceptance_result(result)


__all__ = ["accept"]
