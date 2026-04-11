"""Top-level doctor command group for project health diagnostics."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.core.paths import locate_project_root

if TYPE_CHECKING:
    from specify_cli.status.identity_audit import IdentityState

app = typer.Typer(name="doctor", help="Project health diagnostics")
console = Console()


@app.command(name="command-files")
def command_files(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Check all agent command files for correctness.

    Verifies that every configured agent has the correct command files:
    - Full rendered prompts for prompt-driven commands (specify, plan, tasks, ...)
    - Thin shims for CLI-driven commands (implement, review, merge, ...)
    - Current version markers on all files

    Examples:
        spec-kitty doctor command-files
        spec-kitty doctor command-files --json
    """
    from specify_cli.runtime.doctor import check_command_file_health

    try:
        project_path = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc

    if project_path is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    issues = check_command_file_health(project_path)

    if json_output:
        console.print_json(json.dumps(issues, indent=2))
        raise typer.Exit(1 if issues else 0)

    if not issues:
        console.print("[green]Command Files[/green]: all files healthy")
        raise typer.Exit(0)

    console.print(f"\n[bold]Command Files[/bold] — {len(issues)} issue(s) found\n")

    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("Agent", style="cyan", min_width=12)
    table.add_column("Command", min_width=16)
    table.add_column("File", min_width=40)
    table.add_column("Severity", min_width=8)
    table.add_column("Issue")

    for issue in issues:
        severity = issue["severity"]
        severity_display = (
            f"[red]{severity}[/red]" if severity == "error" else f"[yellow]{severity}[/yellow]"
        )
        table.add_row(
            issue["agent"],
            issue["command"],
            issue["file"],
            severity_display,
            issue["issue"],
        )

    console.print(table)
    console.print()
    raise typer.Exit(1)


@app.command(name="state-roots")
def state_roots(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Show state roots, surface classification, and safety warnings.

    Displays the three state roots with resolved paths, all registered
    state surfaces grouped by root with authority and Git classification,
    and warnings for any runtime surfaces not covered by .gitignore.

    Examples:
        spec-kitty doctor state-roots
        spec-kitty doctor state-roots --json
    """
    from specify_cli.state.doctor import check_state_roots
    from specify_cli.state_contract import StateRoot

    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc

    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    report = check_state_roots(repo_root)

    if json_output:
        console.print_json(json.dumps(report.to_dict(), indent=2))
        raise typer.Exit(0 if report.healthy else 1)

    # Human-readable output
    # 1. State roots table
    console.print("\n[bold]State Roots[/bold]")
    for root_info in report.roots:
        status = (
            "[green]exists[/green]"
            if root_info.exists
            else "[dim]absent[/dim]"
        )
        console.print(
            f"  {root_info.name:<20} {root_info.resolved_path}  {status}"
        )

    # 2. Surfaces by root
    console.print()
    root_order = [
        StateRoot.PROJECT,
        StateRoot.FEATURE,
        StateRoot.GLOBAL_RUNTIME,
        StateRoot.GLOBAL_SYNC,
        StateRoot.GIT_INTERNAL,
    ]
    root_labels = {
        StateRoot.PROJECT: "Project Surfaces (.kittify/)",
        StateRoot.FEATURE: "Feature Surfaces (kitty-specs/)",
        StateRoot.GLOBAL_RUNTIME: "Global Runtime (~/.kittify/)",
        StateRoot.GLOBAL_SYNC: "Global Sync (~/.spec-kitty/)",
        StateRoot.GIT_INTERNAL: "Git-Internal (.git/spec-kitty/)",
    }

    for root in root_order:
        root_surfaces = [s for s in report.surfaces if s.surface.root == root]
        if not root_surfaces:
            continue

        console.print(f"[bold]{root_labels.get(root, root.value)}[/bold]")
        table = Table(box=None, padding=(0, 2), show_edge=False)
        table.add_column("Name", style="cyan", min_width=28)
        table.add_column("Authority", min_width=16)
        table.add_column("Git Policy", min_width=22)
        table.add_column("Present", justify="center", min_width=8)

        for check in root_surfaces:
            present_icon = "[green]Y[/green]" if check.present else "[dim]N[/dim]"
            authority = check.surface.authority.value
            git_class = check.surface.git_class.value
            if check.warning:
                authority = f"[yellow]{authority}[/yellow]"
                git_class = f"[yellow]{git_class}[/yellow]"
            table.add_row(check.surface.name, authority, git_class, present_icon)

        console.print(table)
        console.print()

    # 3. Warnings
    if report.warnings:
        console.print("[bold yellow]Warnings[/bold yellow]")
        for w in report.warnings:
            console.print(f"  [yellow]![/yellow] {w}")
    else:
        console.print(
            "[green]No warnings -- all runtime surfaces are properly covered.[/green]"
        )

    console.print()
    raise typer.Exit(0 if report.healthy else 1)


def _scope_to_mission(
    repo_root: Path,
    all_states: list[IdentityState],
    mission: str,
) -> list[IdentityState]:
    """Filter states to a single mission slug (or classify it directly)."""
    from specify_cli.status.identity_audit import classify_mission

    filtered = [s for s in all_states if s.slug == mission]
    if filtered:
        return filtered
    target_dir = repo_root / "kitty-specs" / mission
    if target_dir.is_dir():
        return [classify_mission(target_dir)]
    return []


def _scope_prefixes(
    duplicate_prefixes: dict[str, list[IdentityState]],
    mission: str,
) -> dict[str, list[IdentityState]]:
    """Narrow duplicate_prefixes to the prefix of the scoped mission."""
    import re as _re

    m = _re.match(r"^(\d{3})-", mission)
    if not m:
        return {}
    prefix = m.group(1)
    return {prefix: duplicate_prefixes[prefix]} if prefix in duplicate_prefixes else {}


def _print_dup_and_ambig(
    duplicate_prefixes: dict[str, list[IdentityState]],
    ambiguous_selectors: dict[str, list[IdentityState]],
) -> None:
    """Print duplicate-prefix and ambiguous-selector sections."""
    if duplicate_prefixes:
        console.print("[bold yellow]Duplicate Prefixes[/bold yellow]")
        for prefix, items in sorted(duplicate_prefixes.items()):
            console.print(f"  [yellow]{prefix}[/yellow] — {len(items)} collision(s):")
            for s in items:
                mid = s.mission_id or "[dim]no mission_id[/dim]"
                console.print(f"    {s.slug}  mission_id={mid}  state={s.state}")
        console.print()

    if ambiguous_selectors:
        console.print("[bold yellow]Ambiguous Selectors[/bold yellow]")
        for handle, items in sorted(ambiguous_selectors.items()):
            console.print(f"  [yellow]{handle!r}[/yellow] → {len(items)} candidate(s):")
            for s in items:
                console.print(f"    {s.slug}")
        console.print()

    if not duplicate_prefixes and not ambiguous_selectors:
        console.print("[green]No duplicate prefixes or ambiguous selectors.[/green]\n")


def _print_identity_human(
    all_states: list[IdentityState],
    duplicate_prefixes: dict[str, list[IdentityState]],
    ambiguous_selectors: dict[str, list[IdentityState]],
    summary: dict[str, object],
    fail_on_states: set[str],
    fail_on_triggered: bool,
    fail_on: str | None,
) -> None:
    """Render the human-readable identity report to the console."""
    counts_dict: dict[str, int] = summary["counts"]  # type: ignore[assignment]
    total = len(all_states)
    console.print(f"\n[bold]Mission Identity Audit[/bold] — {total} mission(s)\n")

    summary_table = Table(box=None, padding=(0, 2), show_edge=False)
    summary_table.add_column("State", style="cyan", min_width=10)
    summary_table.add_column("Count", justify="right", min_width=6)
    _state_styles = {"assigned": "[green]", "pending": "[yellow]", "legacy": "[red]", "orphan": "[red]"}
    for state_name in ("assigned", "pending", "legacy", "orphan"):
        count = counts_dict.get(state_name, 0)
        styled = f"{_state_styles.get(state_name, '')}{state_name}[/]"
        summary_table.add_row(styled, str(count))
    console.print(summary_table)
    console.print()

    _print_dup_and_ambig(duplicate_prefixes, ambiguous_selectors)

    legacy_paths: list[str] = summary["legacy_paths"]  # type: ignore[assignment]
    orphan_paths: list[str] = summary["orphan_paths"]  # type: ignore[assignment]
    if legacy_paths:
        console.print("[bold red]Legacy missions (need backfill):[/bold red]")
        for p in legacy_paths:
            console.print(f"  {p}")
        console.print()
    if orphan_paths:
        console.print("[bold red]Orphan missions (need triage):[/bold red]")
        for p in orphan_paths:
            console.print(f"  {p}")
        console.print()

    if fail_on_triggered:
        console.print(
            f"[bold red]FAIL:[/bold red] --fail-on {fail_on!r} triggered "
            f"(one or more missions in: {', '.join(sorted(fail_on_states))})"
        )


@app.command(name="identity")
def identity(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit structured JSON output (suitable for CI)"),
    ] = False,
    mission: Annotated[
        str | None,
        typer.Option("--mission", help="Scope report to a single mission slug"),
    ] = None,
    fail_on: Annotated[
        str | None,
        typer.Option(
            "--fail-on",
            help=(
                "Exit non-zero if any mission is in the given state(s). "
                "Comma-separated list of: assigned, pending, legacy, orphan."
            ),
        ),
    ] = None,
) -> None:
    """Report mission-identity health across kitty-specs/.

    Classifies every mission into one of four states (FR-045):

    \\b
    - assigned: mission_id present AND mission_number non-null (fully migrated)
    - pending:  mission_id present AND mission_number null (pre-merge)
    - legacy:   mission_id missing AND mission_number present (needs backfill)
    - orphan:   both fields missing or meta.json unreadable (needs triage)

    Also reports duplicate numeric prefixes (FR-011) and ambiguous selectors
    that would resolve to multiple missions (FR-012).

    Examples:
        spec-kitty doctor identity
        spec-kitty doctor identity --json
        spec-kitty doctor identity --mission 083-foo
        spec-kitty doctor identity --fail-on legacy,orphan
    """
    from specify_cli.status.identity_audit import (
        audit_repo,
        find_ambiguous_selectors,
        find_duplicate_prefixes,
        summarize,
    )

    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc

    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    all_states = audit_repo(repo_root)

    if mission is not None:
        scoped = _scope_to_mission(repo_root, all_states, mission)
        if not scoped:
            console.print(f"[red]Error:[/red] Mission not found: {mission!r}")
            raise typer.Exit(1)
        all_states = scoped

    _summary = summarize(all_states)
    dup_prefixes = find_duplicate_prefixes(repo_root)
    if mission is not None:
        dup_prefixes = _scope_prefixes(dup_prefixes, mission)
    ambig_selectors = find_ambiguous_selectors(all_states)

    fail_on_states: set[str] = (
        {s.strip() for s in fail_on.split(",") if s.strip()} if fail_on else set()
    )
    fail_on_triggered = bool(
        fail_on_states and any(s.state in fail_on_states for s in all_states)
    )

    if json_output:
        report = {
            "summary": _summary["counts"],
            "missions": [s.to_dict() for s in all_states],
            "duplicate_prefixes": {
                prefix: [s.to_dict() for s in items]
                for prefix, items in dup_prefixes.items()
            },
            "ambiguous_selectors": {
                handle: [s.to_dict() for s in items]
                for handle, items in ambig_selectors.items()
            },
            "fail_on_triggered": fail_on_triggered,
        }
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
        sys.stdout.flush()
        raise typer.Exit(1 if fail_on_triggered else 0)

    _print_identity_human(
        all_states,
        dup_prefixes,
        ambig_selectors,
        _summary,
        fail_on_states,
        fail_on_triggered,
        fail_on,
    )
    raise typer.Exit(1 if fail_on_triggered else 0)
