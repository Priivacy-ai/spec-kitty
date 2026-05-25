"""Top-level doctor command group for project health diagnostics."""

from __future__ import annotations

import enum as _enum
import json
import os
import sys
from pathlib import Path
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.core.paths import locate_project_root
from specify_cli.paths import get_runtime_root, render_runtime_path
from specify_cli.runtime.home import get_kittify_home

if TYPE_CHECKING:
    from specify_cli.audit import Severity
    from specify_cli.compat.doctor import ShimRegistryReport


# CI env-vars that should force non-interactive behaviour even when stdin
# happens to be a TTY. Conservative list per WP04 Risks: a false positive
# here would block an operator from remediating in a real local shell, so
# only well-known names are included.
_CI_ENV_VARS = (
    "CI",
    "GITHUB_ACTIONS",
    "GITLAB_CI",
    "BUILDKITE",
    "JENKINS_URL",
    "CIRCLECI",
)


def _is_interactive_environment() -> bool:
    """Return True iff stdin is a TTY AND no common CI env var is set.

    Matches the FR-023 contract: in CI / non-interactive environments,
    ``doctor sparse-checkout --fix`` must print a remediation pointer and
    exit non-zero rather than prompting.
    """
    if not sys.stdin.isatty():
        return False
    return all(
        os.environ.get(var, "").lower() not in ("true", "1", "yes")
        for var in _CI_ENV_VARS
    )

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
    from specify_cli.state.contract import StateRoot

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
        StateRoot.GLOBAL_RUNTIME: f"Global Runtime ({render_runtime_path(get_kittify_home())})",
        StateRoot.GLOBAL_SYNC: f"Global Sync ({render_runtime_path(get_runtime_root().base)})",
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


def _render_sparse_finding(report: object) -> None:
    """Render Quickstart Flow 1 finding output to the console.

    Kept separate from the command callback so tests can exercise the
    reporting surface directly. Uses ``soft_wrap=True`` to keep file
    paths on a single line regardless of terminal width — the doctor
    output contract is that affected paths are grep-able verbatim.
    """
    # Local import avoids circular-import edge cases during module load.
    from specify_cli.git.sparse_checkout import SparseCheckoutScanReport

    assert isinstance(report, SparseCheckoutScanReport)

    console.print(
        "[yellow]⚠ Legacy sparse-checkout state detected[/yellow]",
        soft_wrap=True,
    )
    if report.primary.is_active:
        console.print(f"  Primary: {report.primary.path}", soft_wrap=True)
        console.print("    core.sparseCheckout = true", soft_wrap=True)
        if report.primary.pattern_file_present and report.primary.pattern_file_path is not None:
            pf_rel = report.primary.pattern_file_path
            console.print(
                f"    pattern file: {pf_rel} ({report.primary.pattern_line_count} lines)",
                soft_wrap=True,
            )
    active_wts = [w for w in report.worktrees if w.is_active]
    if active_wts:
        console.print(
            f"  Lane worktrees: {len(active_wts)} affected", soft_wrap=True
        )
        for wt in active_wts:
            console.print(f"    {wt.path}", soft_wrap=True)
    console.print()
    console.print("  Why this matters:", soft_wrap=True)
    console.print(
        "    spec-kitty v3.0+ removed sparse-checkout support but does not ship a",
        soft_wrap=True,
    )
    console.print(
        "    migration. This state can cause silent data loss during mission merge",
        soft_wrap=True,
    )
    console.print(
        "    and broken lane worktrees on agent action implement.", soft_wrap=True
    )
    console.print("    See Priivacy-ai/spec-kitty#588.", soft_wrap=True)
    console.print()
    console.print("  Fix:", soft_wrap=True)
    console.print("    spec-kitty doctor sparse-checkout --fix", soft_wrap=True)


def _render_remediation_plan(report: object) -> None:
    """Print the numbered step-by-step plan operators see before consenting."""
    from specify_cli.git.sparse_checkout import SparseCheckoutScanReport

    assert isinstance(report, SparseCheckoutScanReport)

    console.print("Proceed? This will:")
    step = 1
    console.print(f"  {step}. git sparse-checkout disable (primary)")
    step += 1
    console.print(f"  {step}. git config --unset core.sparseCheckout (primary)")
    step += 1
    console.print(f"  {step}. rm {report.primary.path}/.git/info/sparse-checkout (primary)")
    step += 1
    console.print(f"  {step}. git checkout HEAD -- . (primary)")
    for wt in report.worktrees:
        if not wt.is_active:
            continue
        step += 1
        console.print(f"  {step}. repeat steps 1–4 in {wt.path}")


@app.command(name="sparse-checkout")
def sparse_checkout(
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            help="Apply remediation (disable sparse-checkout on primary + worktrees).",
        ),
    ] = False,
) -> None:
    """Detect and optionally remediate legacy sparse-checkout state.

    Without ``--fix``: scans the repo and prints a warning finding
    describing any active sparse-checkout state (primary + lane
    worktrees). Exits 0 when clean, 1 when state is present.

    With ``--fix``: in an interactive TTY, prints a step-by-step plan,
    prompts once for consent, and calls WP03's ``remediate()``. In
    non-interactive / CI environments, prints a remediation pointer and
    exits non-zero without mutating state (FR-023).

    Examples:
        spec-kitty doctor sparse-checkout
        spec-kitty doctor sparse-checkout --fix
    """
    # Local imports keep module import cheap for unrelated doctor subcommands.
    from specify_cli.git.sparse_checkout import scan_repo
    from specify_cli.git.sparse_checkout_remediation import remediate

    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc

    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    report = scan_repo(repo_root)

    # No state detected — emit the "nothing to do" message in both modes
    # and exit cleanly.
    if not report.any_active:
        if fix:
            console.print("No sparse-checkout state to remediate.")
        else:
            console.print(
                "[green]✓ No legacy sparse-checkout state detected.[/green]"
            )
        raise typer.Exit(0)

    # Detection-only surface: print the finding and exit non-zero so CI
    # scripts that invoke `doctor sparse-checkout` can gate on the result.
    if not fix:
        _render_sparse_finding(report)
        raise typer.Exit(1)

    # --fix path: route by interactivity.
    if not _is_interactive_environment():
        # FR-023: CI/non-TTY surface is a single deterministic pointer line so
        # scripts can grep it reliably. No state mutation; non-zero exit.
        # Bypass Rich's auto-wrapping (which splits on terminal width and
        # breaks grep) by using the stdlib print.
        print(
            "sparse-checkout --fix requires an interactive terminal; "
            "run 'spec-kitty doctor sparse-checkout --fix' from a local TTY to remediate."
        )
        raise typer.Exit(1)

    # Interactive mode: show the plan, prompt once, then remediate.
    _render_remediation_plan(report)
    try:
        response = input("[y/N] ").strip().lower()
    except EOFError:
        response = ""
    if response != "y":
        console.print("Aborted — no changes made.")
        raise typer.Exit(0)

    # We already obtained operator consent for the whole plan; pass
    # ``interactive=False`` so WP03 does not re-prompt per path.
    rep = remediate(report, interactive=False, confirm=None)

    # Render per-path results matching Quickstart Flow 1.
    results = [rep.primary_result, *rep.worktree_results]

    # Dirty-tree refusal: surface the specific "commit or stash" message.
    if any(r.dirty_before_remediation for r in results):
        console.print(
            "[red]✗ Cannot remediate: uncommitted changes detected.[/red]"
        )
        for r in results:
            if r.dirty_before_remediation:
                console.print(f"  {r.path}")
        console.print()
        console.print("  Commit or stash your changes and retry:")
        console.print("    git stash push -u")
        console.print("    spec-kitty doctor sparse-checkout --fix")
        raise typer.Exit(1)

    any_failure = False
    for r in results:
        if r.success:
            steps = len(r.steps_completed)
            console.print(f"[green]✓[/green] {r.path}: remediated ({steps} steps, clean verify)")
        else:
            any_failure = True
            detail = r.error_detail or "unknown error"
            step = r.error_step or "unknown step"
            console.print(f"[red]✗[/red] {r.path}: failed at {step} — {detail}")

    raise typer.Exit(0 if rep.overall_success and not any_failure else 1)


def _print_overdue_details(report: ShimRegistryReport, console: Console) -> None:
    console.print()
    console.print("[bold red]Overdue shims must be resolved before release:[/bold red]")
    for e in report.entries:
        if e.status.value == "overdue":
            canonical = (
                ", ".join(e.entry.canonical_import)
                if isinstance(e.entry.canonical_import, list)
                else e.entry.canonical_import
            )
            console.print(f"\n  [red]{e.entry.legacy_path}[/red]")
            console.print(f"    Canonical import : {canonical}")
            console.print(f"    Removal target   : {e.entry.removal_target_release}")
            console.print(f"    Tracker          : {e.entry.tracker_issue}")
            console.print("    Remediation:")
            console.print(
                f"      Option A: Delete src/specify_cli/{e.entry.legacy_path.replace('.', '/')}.py"
                " (or __init__.py)"
            )
            console.print(
                "      Option B: Extend removal_target_release in"
                " architecture/2.x/shim-registry.yaml with extension_rationale"
            )


@app.command(name="shim-registry")
def shim_registry(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """Check for overdue compatibility shims in the shim registry.

    Reads architecture/2.x/shim-registry.yaml and compares each entry's
    removal_target_release against the current project version. Fails with
    exit code 1 if any shim is overdue (removal release has shipped but
    shim file still exists on disk).

    Exit codes:
      0  All entries are pending, removed, or grandfathered.
      1  At least one entry is overdue — shim must be deleted or window extended.
      2  Configuration error (registry file or pyproject.toml missing/invalid).

    Examples:
        spec-kitty doctor shim-registry
        spec-kitty doctor shim-registry --json
    """
    from collections import Counter

    from specify_cli.compat import (
        RegistrySchemaError,
        ShimStatus,
        check_shim_registry,
    )

    repo_root = locate_project_root()
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(2)

    try:
        report = check_shim_registry(repo_root)
    except FileNotFoundError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(2) from exc
    except RegistrySchemaError as exc:
        console.print("[red]Registry schema error:[/red]")
        for err in exc.errors:
            console.print(f"  {err}")
        raise typer.Exit(2) from exc
    except KeyError as exc:
        console.print(f"[red]Configuration error:[/red] missing key {exc} in pyproject.toml")
        raise typer.Exit(2) from exc

    if json_output:
        output = {
            "project_version": report.project_version,
            "registry_path": str(report.registry_path),
            "entries": [
                {
                    "legacy_path": e.entry.legacy_path,
                    "canonical_import": e.entry.canonical_import,
                    "removal_target_release": e.entry.removal_target_release,
                    "grandfathered": e.entry.grandfathered,
                    "tracker_issue": e.entry.tracker_issue,
                    "status": e.status.value,
                    "shim_exists": e.shim_exists,
                }
                for e in report.entries
            ],
            "has_overdue": report.has_overdue,
            "exit_code": report.recommended_exit_code,
        }
        console.print_json(json.dumps(output, indent=2))
        raise typer.Exit(report.recommended_exit_code)

    if not report.entries:
        console.print("[green]Shim Registry[/green]: registry is empty — no shims to check.")
        raise typer.Exit(0)

    console.print(
        f"\n[bold]Shim Registry[/bold] — {len(report.entries)} entry/entries"
        f" (project version: {report.project_version})\n"
    )

    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("Legacy Path", style="cyan", min_width=24)
    table.add_column("Canonical Import", min_width=20)
    table.add_column("Removal Target", min_width=14)
    table.add_column("Status", min_width=12)

    _status_styles: dict[ShimStatus, str] = {
        ShimStatus.PENDING: "[cyan]pending[/cyan]",
        ShimStatus.OVERDUE: "[bold red]OVERDUE[/bold red]",
        ShimStatus.GRANDFATHERED: "[yellow]grandfathered[/yellow]",
        ShimStatus.REMOVED: "[dim]removed[/dim]",
    }

    for e in report.entries:
        canonical = (
            ", ".join(e.entry.canonical_import)
            if isinstance(e.entry.canonical_import, list)
            else e.entry.canonical_import
        )
        table.add_row(
            e.entry.legacy_path,
            canonical,
            e.entry.removal_target_release,
            _status_styles[e.status],
        )

    console.print(table)
    console.print()

    counts = Counter(e.status.value for e in report.entries)
    parts = [f"{v} {k}" for k, v in sorted(counts.items())]
    console.print(f"Summary: {', '.join(parts)}")

    if report.has_overdue:
        _print_overdue_details(report, console)

    console.print()
    raise typer.Exit(report.recommended_exit_code)


@app.command(name="invocation-pairing")
def invocation_pairing(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """List orphan profile-invocation lifecycle records.

    WP05 (#843) wiring: scans
    ``.kittify/events/profile-invocation-lifecycle.jsonl`` for ``started``
    records with no paired ``completed`` or ``failed`` partner. Mid-cycle
    agent crashes show up here. The check observes; it does not remediate.

    Exit codes:
      0  No orphans observed.
      1  At least one orphan found.

    Examples:
        spec-kitty doctor invocation-pairing
        spec-kitty doctor invocation-pairing --json
    """
    from specify_cli.invocation.lifecycle import doctor_orphan_report

    repo_root = locate_project_root()
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    report = doctor_orphan_report(repo_root)
    orphan_count_raw = report.get("orphan_count", 0)
    orphan_count = orphan_count_raw if isinstance(orphan_count_raw, int) else 0
    pairing_rate_raw = report.get("pairing_rate", 1.0)
    pairing_rate = pairing_rate_raw if isinstance(pairing_rate_raw, (int, float)) else 1.0
    total_groups_raw = report.get("total_groups", 0)
    total_groups = total_groups_raw if isinstance(total_groups_raw, int) else 0
    orphans_raw = report.get("orphans", [])
    orphans_list: list[dict[str, object]] = (
        [o for o in orphans_raw if isinstance(o, dict)] if isinstance(orphans_raw, list) else []
    )

    if json_output:
        console.print_json(json.dumps(report, indent=2, sort_keys=True))
        raise typer.Exit(1 if orphan_count else 0)

    if orphan_count == 0:
        console.print(
            "[green]Invocation Pairing[/green]: no orphan started records "
            f"(pairing rate: {pairing_rate:.0%}, "
            f"groups: {total_groups})."
        )
        raise typer.Exit(0)

    console.print(
        f"\n[bold]Invocation Pairing[/bold] — {orphan_count} orphan "
        f"started record(s)\n"
    )
    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("Canonical Action ID", style="cyan", min_width=24)
    table.add_column("Agent", min_width=10)
    table.add_column("Mission ID", min_width=10)
    table.add_column("WP", min_width=6)
    table.add_column("Started At", min_width=20)
    for entry in orphans_list:
        table.add_row(
            str(entry.get("canonical_action_id", "")),
            str(entry.get("agent", "")),
            str(entry.get("mission_id", "")),
            str(entry.get("wp_id") or "-"),
            str(entry.get("started_at", "")),
        )
    console.print(table)
    console.print(
        f"\nPairing rate: {pairing_rate:.0%} "
        f"across {total_groups} group(s)."
    )
    console.print()
    raise typer.Exit(1)


def _print_rich_audit_report(report: object) -> None:
    """Print a Rich table summarising audit findings per mission."""
    from specify_cli.audit import RepoAuditReport

    assert isinstance(report, RepoAuditReport)

    missions_with_findings = [r for r in report.missions if r.findings]

    if not missions_with_findings:
        console.print("[green]No findings — all missions are clean.[/green]")
        return

    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("Mission", style="cyan", min_width=28)
    table.add_column("Errors", justify="right", min_width=7)
    table.add_column("Warnings", justify="right", min_width=9)
    table.add_column("Info", justify="right", min_width=6)
    table.add_column("Codes")

    for result in missions_with_findings:
        from specify_cli.audit.models import Severity

        errors = sum(1 for f in result.findings if f.severity == Severity.ERROR)
        warnings = sum(1 for f in result.findings if f.severity == Severity.WARNING)
        infos = sum(1 for f in result.findings if f.severity == Severity.INFO)
        codes = ", ".join(sorted({f.code for f in result.findings}))

        err_str = f"[red]{errors}[/red]" if errors else str(errors)
        warn_str = f"[yellow]{warnings}[/yellow]" if warnings else str(warnings)
        table.add_row(result.mission_slug, err_str, warn_str, str(infos), codes)

    console.print(table)
    console.print()

    summary = report.repo_summary
    console.print(
        f"Total missions: {summary['total_missions']} | "
        f"With errors: {summary['missions_with_errors']} | "
        f"With warnings: {summary['missions_with_warnings']} | "
        f"TeamSpace blockers: {summary['teamspace_blockers']}"
    )


def _audit_fixture_root() -> Path:
    """Return the packaged mission-state audit fixture root."""
    return Path(__file__).resolve().parents[2] / "audit" / "fixtures"


# ---------------------------------------------------------------------------
# mission_state helpers — extracted per refactoring-extract-first-order-concept
# ---------------------------------------------------------------------------


class _MissionStateMode(_enum.Enum):
    """Dispatch mode for the mission-state command."""

    AUDIT = "audit"
    FIX = "fix"
    TEAMSPACE_DRY_RUN = "teamspace_dry_run"


def _validate_modes(audit: bool, fix: bool, teamspace_dry_run: bool) -> _MissionStateMode:
    """Validate mutually exclusive mode flags and return the active Mode.

    Raises typer.Exit(0) if no mode was selected (with usage hint).
    Raises typer.Exit(2) if more than one mode was selected.
    """
    selected_modes = sum(1 for selected in (audit, fix, teamspace_dry_run) if selected)
    if selected_modes == 0:
        typer.echo("Use --audit, --fix, or --teamspace-dry-run. See --help for options.")
        raise typer.Exit(0)
    if selected_modes > 1:
        typer.echo("Choose exactly one of --audit, --fix, or --teamspace-dry-run.", err=True)
        raise typer.Exit(2)
    if fix:
        return _MissionStateMode.FIX
    if teamspace_dry_run:
        return _MissionStateMode.TEAMSPACE_DRY_RUN
    return _MissionStateMode.AUDIT


def _resolve_fail_on(fail_on: str | None) -> tuple[Severity | None, bool]:
    """Parse --fail-on into (severity, teamspace_blocker_flag).

    Returns (None, False) when fail_on is None.
    Raises typer.Exit(2) on invalid values.
    """
    from specify_cli.audit import Severity

    if fail_on is None:
        return None, False
    if fail_on == "teamspace-blocker":
        return None, True
    try:
        return Severity(fail_on), False
    except ValueError:
        valid = ", ".join([*(s.value for s in Severity), "teamspace-blocker"])
        typer.echo(
            f"Invalid --fail-on value: {fail_on!r}. Valid values: {valid}",
            err=True,
        )
        raise typer.Exit(2) from None


def _resolve_audit_root(
    fixture_dir: Path | None,
    include_fixtures: bool,
) -> tuple[Path, Path | None]:
    """Resolve the effective (repo_root, fixture_dir) pair.

    Handles --include-fixtures / --fixture-dir interplay and project-root
    discovery. Returns (repo_root, fixture_dir).

    Raises typer.Exit(1) if no repo root can be found.
    Raises typer.Exit(2) if --include-fixtures and --fixture-dir conflict,
    or the bundled fixture root is missing.
    """
    resolved_fixture_dir = fixture_dir
    if include_fixtures:
        if resolved_fixture_dir is not None:
            typer.echo("Use only one of --include-fixtures or --fixture-dir.", err=True)
            raise typer.Exit(2)
        resolved_fixture_dir = _audit_fixture_root()
        if not resolved_fixture_dir.is_dir():
            typer.echo(f"Bundled audit fixtures not found: {resolved_fixture_dir}", err=True)
            raise typer.Exit(2)

    try:
        resolved_repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc

    if resolved_repo_root is None:
        if resolved_fixture_dir is None:
            console.print("[red]Error:[/red] Not in a spec-kitty project")
            raise typer.Exit(1)
        resolved_repo_root = resolved_fixture_dir.parent

    return resolved_repo_root, resolved_fixture_dir


def _emit_mission_state(report: object, *, json_output: bool, pretty_renderer: Callable[[object], None]) -> None:
    """Emit a mission-state report as JSON or via a pretty renderer.

    Collapses the triplicated 'if json_output: dump JSON else: pretty-print'
    pattern across the three dispatch arms.
    """
    if json_output:
        sys.stdout.write(report.to_json())  # type: ignore[attr-defined]
        sys.stdout.flush()
    else:
        pretty_renderer(report)


def _run_mission_repair(
    repo_root: Path,
    fixture_dir: Path | None,
    mission: str | None,
    manifest_path: Path | None,
    allow_dirty: bool,
    json_output: bool,
) -> None:
    """Execute the --fix dispatch arm: repair repo and emit the manifest."""
    from specify_cli.migration.mission_state import MissionStateRepairError, repair_repo

    try:
        report = repair_repo(
            repo_root,
            scan_root=fixture_dir,
            mission=mission,
            manifest_path=manifest_path,
            allow_dirty=allow_dirty,
        )
    except MissionStateRepairError as exc:
        if json_output:
            sys.stdout.write(json.dumps({"error": "MISSION_STATE_REPAIR_FAILED", "message": str(exc)}) + "\n")
            sys.stdout.flush()
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    def _pretty_repair(r: object) -> None:
        summary = r.to_dict()["summary"]  # type: ignore[attr-defined]
        assert isinstance(summary, dict)
        console.print(
            "[green]Mission-state repair complete[/green] "
            f"(updated={summary['missions_updated']}, "
            f"unchanged={summary['missions_unchanged']}, "
            f"errors={summary['missions_error']})."
        )
        console.print(f"Manifest: {r.manifest_path}")  # type: ignore[attr-defined]

    _emit_mission_state(report, json_output=json_output, pretty_renderer=_pretty_repair)
    if any(result.status == "error" for result in report.missions):
        raise typer.Exit(1)


def _run_teamspace_dry_run_mode(
    repo_root: Path,
    fixture_dir: Path | None,
    mission: str | None,
    json_output: bool,
) -> None:
    """Execute the --teamspace-dry-run dispatch arm: synthesize and validate envelopes."""
    from specify_cli.migration.mission_state import MissionStateDryRunError
    from specify_cli.migration.mission_state import teamspace_dry_run as run_teamspace_dry_run

    try:
        dry_run_report = run_teamspace_dry_run(
            repo_root,
            scan_root=fixture_dir,
            mission=mission,
        )
    except MissionStateDryRunError as exc:
        if json_output:
            sys.stdout.write(json.dumps({"error": "TEAMSPACE_DRY_RUN_FAILED", "message": str(exc)}) + "\n")
            sys.stdout.flush()
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    def _pretty_dry_run(r: object) -> None:
        # The runtime contract for pretty_renderer types the report as ``object`` so the
        # same callable shape works for the repair and dry-run reports; attribute access
        # below is structurally valid on the concrete TeamSpaceDryRunReport type.
        if r.valid:  # type: ignore[attr-defined]
            console.print(
                "[green]TeamSpace dry-run valid[/green] "
                f"({r.envelope_count} envelopes, "  # type: ignore[attr-defined]
                f"spec-kitty-events {r.events_package_version})."
            )
        else:
            console.print(
                "[red]TeamSpace dry-run failed[/red] "
                f"({len(r.errors)} validation errors)."  # type: ignore[attr-defined]
            )

    _emit_mission_state(dry_run_report, json_output=json_output, pretty_renderer=_pretty_dry_run)
    if not dry_run_report.valid:
        raise typer.Exit(1)


def _emit_json_error(error_code: str, **extra: object) -> None:
    """Write a JSON error envelope to stdout and flush."""
    payload = {"error": error_code, **extra}
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def _audit_fail_gate(
    report: object,
    fail_on_severity: Severity | None,
    fail_on_teamspace_blocker: bool,
) -> None:
    """Raise typer.Exit(1) if any finding meets the --fail-on gate."""
    from specify_cli.audit.models import is_teamspace_blocker

    if fail_on_severity is not None and any(
        f.severity <= fail_on_severity
        for result in report.missions  # type: ignore[attr-defined]
        for f in result.findings
    ):
        raise typer.Exit(1)
    if fail_on_teamspace_blocker and any(
        is_teamspace_blocker(f)
        for result in report.missions  # type: ignore[attr-defined]
        for f in result.findings
    ):
        raise typer.Exit(1)


def _run_audit_mode(
    repo_root: Path,
    fixture_dir: Path | None,
    mission: str | None,
    fail_on_severity: Severity | None,
    fail_on_teamspace_blocker: bool,
    json_output: bool,
) -> None:
    """Execute the --audit dispatch arm: run the audit engine and emit findings."""
    from specify_cli.audit import AuditOptions, build_report_json, run_audit
    from specify_cli.context.mission_resolver import AmbiguousHandleError, MissionNotFoundError

    options = AuditOptions(
        repo_root=repo_root,
        scan_root=fixture_dir,
        mission_filter=mission,
        fail_on=fail_on_severity,
    )
    try:
        report = run_audit(options)
    except MissionNotFoundError as exc:
        if json_output:
            _emit_json_error("MISSION_NOT_FOUND", handle=mission)
        else:
            typer.echo(f"Error: Mission not found: {mission!r}", err=True)
        raise typer.Exit(1) from exc
    except AmbiguousHandleError as exc:
        if json_output:
            _emit_json_error("AMBIGUOUS_HANDLE", handle=mission)
        else:
            typer.echo(f"Error: Ambiguous handle: {mission!r}", err=True)
        raise typer.Exit(1) from exc

    if json_output:
        sys.stdout.write(build_report_json(report))
        sys.stdout.flush()
    else:
        _print_rich_audit_report(report)

    _audit_fail_gate(report, fail_on_severity, fail_on_teamspace_blocker)


@app.command(name="orphan-daemons")
def orphan_daemons(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Machine-readable JSON output"),
    ] = False,
) -> None:
    """List orphan daemon owner records and emit retirement hints.

    Implements FR-010 of the identity-boundary mission: an orphan
    daemon owner record is one whose recorded PID is dead OR whose
    recorded executable path no longer exists on disk. Each orphan
    is printed with a copy-pasteable retirement command that removes
    the on-disk ``owner.json`` so the next ``sync status --check``
    returns clean.

    Exit codes:
      0  No orphan records.
      1  At least one orphan record found.

    Examples:
        spec-kitty doctor orphan-daemons
        spec-kitty doctor orphan-daemons --json
    """
    from specify_cli.sync.owner import list_orphan_records, owner_record_path

    orphans = list_orphan_records()
    record_path = owner_record_path()
    retire_hint = f"rm {record_path}"

    if json_output:
        payload = {
            "orphan_count": len(orphans),
            "owner_record_path": str(record_path),
            "retirement_command": retire_hint if orphans else None,
            "orphans": [
                {
                    "pid": r.pid,
                    "port": r.port,
                    "package_version": r.package_version,
                    "executable_path": r.executable_path,
                    "source_checkout_path": r.source_checkout_path,
                    "server_url": r.server_url,
                    "auth_scope": r.auth_scope,
                    "queue_db_path": r.queue_db_path,
                    "started_at": r.started_at,
                }
                for r in orphans
            ],
        }
        console.print_json(json.dumps(payload, indent=2, sort_keys=True))
        raise typer.Exit(1 if orphans else 0)

    if not orphans:
        console.print(
            "[green]Orphan Daemons[/green]: no orphan daemon owner records detected."
        )
        raise typer.Exit(0)

    console.print(
        f"\n[bold]Orphan Daemons[/bold] — {len(orphans)} record(s)\n"
    )
    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("PID", style="yellow", justify="right", min_width=6)
    table.add_column("Port", justify="right", min_width=6)
    table.add_column("Version", min_width=10)
    table.add_column("Executable", overflow="fold")
    table.add_column("Started At", min_width=20)
    for record in orphans:
        table.add_row(
            str(record.pid),
            str(record.port),
            record.package_version,
            record.executable_path,
            record.started_at,
        )
    console.print(table)
    console.print()
    console.print(
        f"[bold]Retirement hint:[/bold] [cyan]{retire_hint}[/cyan]"
    )
    console.print()
    raise typer.Exit(1)


@app.command(name="restart-daemon")
def restart_daemon_cmd(
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit a single JSON object instead of human-readable text.",
        ),
    ] = False,
) -> None:
    """Stop the registered sync daemon and respawn it at the foreground.

    Composes the existing daemon stop + launch primitives so the operator
    has a one-shot remedy when the foreground process and the registered
    daemon disagree on any of the six canonical D-3 fields (version,
    executable, source, server URL, team/user, or queue DB path).

    Exit codes:
      0  Daemon restarted (or stale owner record cleaned and respawned).
      1  No registered daemon — run ``spec-kitty sync now`` to launch one.
      2  Daemon stop succeeded but respawn failed; system is stopped.
      3  Daemon stop failed (unresponsive); owner record left intact.

    Examples:
        spec-kitty doctor restart-daemon
        spec-kitty doctor restart-daemon --json
    """
    from specify_cli.sync.restart import (
        render_restart_result,
        restart_daemon,
    )

    # ``repo_root`` is accepted by ``restart_daemon`` for API symmetry
    # with the rest of the preflight surface; the function does not
    # currently consult the repo for any field. We resolve it
    # best-effort so a future refactor that reads repo-relative state
    # picks it up automatically without a CLI change.
    repo_root: Path
    try:
        located = locate_project_root()
    except Exception:  # noqa: BLE001 — restart never needs a repo today
        located = None
    repo_root = located if located is not None else Path.cwd()

    result = restart_daemon(repo_root)
    output = render_restart_result(result, json_output=json_output)
    # Use stdout directly so ``--json`` emits one line, no Rich markup.
    sys.stdout.write(output + "\n")
    sys.stdout.flush()
    raise typer.Exit(code=result.exit_code)


@app.command(name="mission-state")
def mission_state(  # noqa: C901
    audit: Annotated[
        bool,
        typer.Option("--audit", help="Run mission-state audit (required to proceed)"),
    ] = False,
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Repair mission-state artifacts in place and write a migration manifest"),
    ] = False,
    teamspace_dry_run: Annotated[
        bool,
        typer.Option(
            "--teamspace-dry-run",
            help="Synthesize canonical TeamSpace envelopes from local state and validate them",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON report to stdout"),
    ] = False,
    mission: Annotated[
        str | None,
        typer.Option("--mission", help="Scope to a single mission handle"),
    ] = None,
    fail_on: Annotated[
        str | None,
        typer.Option(
            "--fail-on",
            help=(
                "Exit 1 if findings meet a gate "
                "(error|warning|info|teamspace-blocker)"
            ),
        ),
    ] = None,
    fixture_dir: Annotated[
        Path | None,
        typer.Option("--fixture-dir", help="Override scan root (for testing)"),
    ] = None,
    include_fixtures: Annotated[
        bool,
        typer.Option(
            "--include-fixtures",
            help="Audit the bundled mission-state survey fixtures",
        ),
    ] = False,
    manifest_path: Annotated[
        Path | None,
        typer.Option("--manifest-path", help="Path for --fix migration manifest"),
    ] = None,
    allow_dirty: Annotated[
        bool,
        typer.Option("--allow-dirty", help="Allow --fix when relevant git paths are already dirty"),
    ] = False,
) -> None:
    """Audit, repair, or TeamSpace-validate mission-state shapes."""
    mode = _validate_modes(audit, fix, teamspace_dry_run)
    fail_on_severity, fail_on_teamspace_blocker = _resolve_fail_on(fail_on)
    resolved_root, resolved_fixture_dir = _resolve_audit_root(fixture_dir, include_fixtures)

    if mode == _MissionStateMode.FIX:
        _run_mission_repair(resolved_root, resolved_fixture_dir, mission, manifest_path, allow_dirty, json_output)
        return
    if mode == _MissionStateMode.TEAMSPACE_DRY_RUN:
        _run_teamspace_dry_run_mode(resolved_root, resolved_fixture_dir, mission, json_output)
        return
    _run_audit_mode(resolved_root, resolved_fixture_dir, mission, fail_on_severity, fail_on_teamspace_blocker, json_output)


# ---------------------------------------------------------------------------
# WP07 T035 + T048: `spec-kitty doctor doctrine` — org-layer snapshot health.
# ---------------------------------------------------------------------------


_ORG_ARTIFACT_DIRS: tuple[str, ...] = (
    "directives",
    "tactics",
    "styleguides",
    "toolguides",
    "paradigms",
    "procedures",
    "agent_profiles",
    "mission_step_contracts",
)


def _resolve_pack_version(snapshot_path: Path) -> tuple[str, str | None, bool]:
    """Return ``(pack_version, fetched_at, is_git_pack)`` for an org snapshot.

    For git-managed snapshots, ``pack_version`` is the ``git describe --tags
    --always`` output; ``fetched_at`` is ``None``.  For non-git snapshots, the
    version + timestamp are read from ``pack-manifest.yaml`` when present.
    Falls back to ``"unknown"`` if neither source yields a value.
    """
    import subprocess as _sp

    is_git_pack = (snapshot_path / ".git").exists()
    if is_git_pack:
        try:
            version = _sp.check_output(
                ["git", "-C", str(snapshot_path), "describe", "--tags", "--always"],
                stderr=_sp.DEVNULL,
                text=True,
            ).strip()
            return version or "git (version unavailable)", None, True
        except (_sp.CalledProcessError, FileNotFoundError, OSError):
            return "git (version unavailable)", None, True

    manifest_path = snapshot_path / "pack-manifest.yaml"
    if manifest_path.exists():
        try:
            from ruamel.yaml import YAML

            yaml = YAML(typ="safe")
            data = yaml.load(manifest_path.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            return "unknown", None, False
        if isinstance(data, dict):
            version = str(data.get("pack_version") or "unknown")
            fetched_at = data.get("fetched_at")
            return version, str(fetched_at) if fetched_at else None, False
    return "unknown", None, False


def _count_pack_artifacts(snapshot_path: Path) -> dict[str, int]:
    """Return per-artifact YAML counts for an org snapshot directory."""
    counts: dict[str, int] = {}
    for artifact_type in _ORG_ARTIFACT_DIRS:
        adir = snapshot_path / artifact_type
        if adir.exists():
            counts[artifact_type] = len(list(adir.glob("*.yaml")))
    return counts


def _summarize_org_charter(snapshot_path: Path) -> dict[str, object]:
    """Inspect ``org-charter.yaml`` in *snapshot_path* and return a JSON-able summary.

    Gracefully degrades when the optional
    ``specify_cli.doctrine.org_charter`` module is not yet shipped (WP09).
    """
    charter_path = snapshot_path / "org-charter.yaml"
    if not charter_path.exists():
        return {"present": False}

    try:
        from specify_cli.doctrine.org_charter import load_org_charter_policy
    except ImportError:
        # Module not yet shipped — surface presence without policy details.
        return {"present": True, "module_available": False}

    try:
        policy = load_org_charter_policy(snapshot_path)
    except Exception:  # noqa: BLE001
        return {"present": True, "module_available": True, "load_error": True}
    if policy is None:
        return {"present": False}

    return {
        "present": True,
        "module_available": True,
        "interview_defaults_count": len(getattr(policy, "interview_defaults", {}) or {}),
        "required_directives_count": len(getattr(policy, "required_directives", []) or []),
        "governance_policies_count": len(getattr(policy, "governance_policies", []) or []),
    }


def _render_doctrine_pack(pack_entry: dict[str, object], pack_index: int) -> None:
    """Render one pack entry to the Rich console (human output for ``doctor doctrine``)."""
    name = pack_entry.get("name") or f"pack#{pack_index}"
    local_path = pack_entry.get("local_path")
    if not pack_entry.get("snapshot_present"):
        console.print(
            f"[yellow]Pack:[/yellow] {name}  (snapshot missing at {local_path})"
        )
        return

    version = pack_entry.get("pack_version", "unknown")
    is_git = pack_entry.get("is_git_pack", False)
    counts = pack_entry.get("artifact_counts") or {}
    summary_parts = [f"git {version}" if is_git else f"v{version}"]
    if isinstance(counts, dict):
        for artifact_type, count in counts.items():
            summary_parts.append(f"{count} {artifact_type}")
    console.print(f"[green]Pack:[/green] {name}  ({', '.join(summary_parts)})")

    charter = pack_entry.get("org_charter") or {}
    if isinstance(charter, dict) and charter.get("present"):
        if charter.get("module_available", True):
            counts_msg = (
                f"{charter.get('interview_defaults_count', 0)} interview defaults, "
                f"{charter.get('required_directives_count', 0)} required directives, "
                f"{charter.get('governance_policies_count', 0)} governance policies"
            )
            console.print(f"  org-charter.yaml: {counts_msg}")
        else:
            console.print(
                "  org-charter.yaml: present (policy module not yet shipped)"
            )
    else:
        console.print("  org-charter.yaml: [dim]not present[/dim]")


@app.command(name="doctrine")
def doctrine_check(
    json_output: Annotated[
        bool, typer.Option("--json", help="Machine-readable JSON output")
    ] = False,
) -> None:
    """Check org doctrine snapshot status and list installed pack artifacts.

    Exit code is always 0 — this surface is a diagnostic, not a gate.  It
    enumerates each configured org pack (from ``.kittify/config.yaml``), prints
    its on-disk version (``git describe`` for git-managed packs, otherwise the
    ``pack-manifest.yaml`` ``pack_version``), per-artifact YAML counts, and
    ``org-charter.yaml`` policy status when present.

    Examples:
        spec-kitty doctor doctrine
        spec-kitty doctor doctrine --json
    """
    from specify_cli.doctrine.config import load_pack_registry

    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc
    if repo_root is None:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1)

    registry = load_pack_registry(repo_root)

    if not registry.packs:
        # WP09 T050 / FR-018: the Selections diagnostic is independent of
        # whether org packs are configured.  A project with built-in +
        # project-only doctrine still has selections to audit, so emit
        # the section in both human and JSON shapes before exiting.
        selection_block = _build_selection_block(repo_root)
        if json_output:
            console.print_json(
                json.dumps(
                    {
                        "org_configured": False,
                        "packs": [],
                        "selections": selection_block,
                        # WP07 FR-007: always include org_drg key so callers can rely on it
                        "org_drg": _collect_org_layer_data(repo_root),
                    },
                    indent=2,
                    default=str,
                )
            )
        else:
            console.print("[yellow]No org doctrine configured.[/yellow]")
            console.print(
                "Add a 'doctrine.org' block to .kittify/config.yaml to register a pack."
            )
            console.print()
            for line in _render_selection_block_lines(selection_block):
                console.print(line)
        raise typer.Exit(0)

    pack_entries: list[dict[str, object]] = []
    for pack in registry.packs:
        snapshot_path = pack.local_path
        entry: dict[str, object] = {
            "name": pack.name,
            "local_path": str(snapshot_path),
            "source_type": pack.source_type,
            "url": pack.url,
            "ref": pack.ref,
            "snapshot_present": snapshot_path.exists(),
        }
        if snapshot_path.exists():
            version, fetched_at, is_git = _resolve_pack_version(snapshot_path)
            entry["pack_version"] = version
            entry["fetched_at"] = fetched_at
            entry["is_git_pack"] = is_git
            entry["artifact_counts"] = _count_pack_artifacts(snapshot_path)
            entry["org_charter"] = _summarize_org_charter(snapshot_path)
        pack_entries.append(entry)

    # Detect override collisions across the full resolved doctrine surface
    # (FR-003 wording + ADR 2026-05-16-1). We instantiate a DoctrineService
    # rooted at the configured packs and trigger lazy loading of every repo,
    # capturing DoctrineLayerCollisionWarning emissions.
    collision_summaries = _collect_doctrine_collisions(repo_root)

    # WP09 T050 / FR-018: build the Selections section so operators can audit
    # which globally-selected artifacts are active across project + org +
    # mission-type-profile layers, each annotated with its resolved source.
    selection_block = _build_selection_block(repo_root)

    # WP07 T037 (FR-007): collect org-layer DRG state for JSON output.
    org_layer_data = _collect_org_layer_data(repo_root)

    if json_output:
        payload = {
            "org_configured": True,
            "packs": pack_entries,
            "collisions": collision_summaries,
            "selections": selection_block,
            # WP07 FR-007: org-layer DRG state (configured packs, node/edge counts, collisions)
            "org_drg": org_layer_data,
        }
        console.print_json(json.dumps(payload, indent=2, default=str))
        raise typer.Exit(0)

    console.print(
        f"\n[bold]Org Doctrine[/bold] — {len(pack_entries)} pack(s) configured\n"
    )
    for idx, entry in enumerate(pack_entries):
        _render_doctrine_pack(entry, idx)

    if collision_summaries:
        console.print(
            f"\n[bold]Collisions[/bold] — {len(collision_summaries)} override(s) detected\n"
        )
        for collision in collision_summaries:
            console.print(
                f"  • [yellow]{collision['kind']}[/yellow] "
                f"{collision['item_id']}: "
                f"{collision['higher_layer']} shadowed {collision['lower_layer']} "
                f"({collision['replaced']} replaced, {collision['inherited']} inherited)"
            )
    else:
        console.print(
            "\n[dim]Collisions:[/dim] none — every artifact resolves from a single layer."
        )

    # WP07 T037 (FR-007): surface org-layer DRG state in human-readable output.
    _render_org_layer_section(repo_root, console)

    # FR-018 / WP09 T050: render the Selections section verbatim so the
    # snapshot test in tests/cli/test_doctor_doctrine_selections_snapshot.py
    # can pin the operator-facing format byte-for-byte.
    console.print()
    for line in _render_selection_block_lines(selection_block):
        console.print(line)
    console.print()
    raise typer.Exit(0)


def _collect_doctrine_collisions(repo_root: Path) -> list[dict[str, object]]:
    """Run the doctrine resolver and collect any layer-collision warnings.

    Returns a list of structured collision descriptors (kind, item_id,
    higher_layer, lower_layer, replaced, inherited) for surfacing via
    ``doctor doctrine`` (FR-003 wording per ADR 2026-05-16-1).
    """
    import re
    import warnings as _warnings

    from doctrine.base import DoctrineLayerCollisionWarning
    from doctrine.service import DoctrineService
    from specify_cli.doctrine.config import resolve_org_roots

    org_roots = resolve_org_roots(repo_root)
    project_doctrine = repo_root / ".kittify" / "doctrine"
    project_root = project_doctrine if project_doctrine.exists() else None

    service = DoctrineService(
        org_roots=list(org_roots),
        project_root=project_root,
    )

    # Touch every repository so each one runs through its loader and emits
    # any collision warnings.
    accessors = (
        "directives",
        "tactics",
        "styleguides",
        "toolguides",
        "paradigms",
        "procedures",
        "mission_step_contracts",
        "agent_profiles",
    )

    collisions: list[dict[str, object]] = []
    pattern = re.compile(
        r"Doctrine override: (?P<kind>\S+) (?P<item_id>\S+) "
        r"from (?P<higher>\S+) shadowed (?P<lower>\S+) "
        r"\((?P<replaced>\d+) field\(s\) replaced; "
        r"(?P<inherited>\d+) field\(s\) inherited\)\."
    )

    with _warnings.catch_warnings(record=True) as captured:
        _warnings.simplefilter("always")
        for name in accessors:
            try:
                getattr(service, name)
            except Exception:  # noqa: BLE001, S112 — doctor must not fail on a single repo's load error
                continue
    for w in captured:
        if not isinstance(w.message, DoctrineLayerCollisionWarning):
            continue
        m = pattern.match(str(w.message))
        if not m:
            continue
        collisions.append(
            {
                "kind": m.group("kind"),
                "item_id": m.group("item_id"),
                "higher_layer": m.group("higher"),
                "lower_layer": m.group("lower"),
                "replaced": int(m.group("replaced")),
                "inherited": int(m.group("inherited")),
            }
        )
    return collisions


# ---------------------------------------------------------------------------
# WP07 T037 — Organisation Layer section (FR-007)
# ---------------------------------------------------------------------------


def _render_org_layer_section(repo_root: Path, console: Console) -> None:
    """Surface organisation-tier DRG state in ``doctor doctrine`` (FR-007).

    Lists each configured pack with its fetched/missing status, node/edge
    counts, and any collision warnings from ``merge_three_layers``.

    Diagnostic commands are READ-ONLY and must never crash on operator
    misconfiguration.  All exceptions are caught and rendered as findings
    so ``doctor doctrine`` always returns a usable report.
    """
    from charter.drg import (  # noqa: PLC0415
        OrgDRGConflictError,
        OrgPackMissingError,
        load_org_drg,
        merge_three_layers,
    )
    from charter.catalog import resolve_doctrine_root  # noqa: PLC0415
    from doctrine.drg.loader import load_graph_or_dir  # noqa: PLC0415

    console.print("\n[bold]Organisation Layer[/bold] (WP07 / FR-007)")

    try:
        fragments = load_org_drg(repo_root)
    except OrgPackMissingError as exc:
        console.print(f"  [red]org pack missing:[/red] {exc}")
        return
    except Exception as exc:  # noqa: BLE001
        console.print(f"  [red]org-DRG load error:[/red] {exc}")
        return

    if not fragments:
        console.print("  (no organisation packs configured)")
        return

    for frag in fragments:
        node_count = len(frag.nodes)
        edge_count = len(frag.edges)
        console.print(
            f"  - [green]{frag.pack_name}[/green] "
            f"[{frag.source_kind}: {frag.source_ref}] "
            f"✓ loaded ({node_count} nodes, {edge_count} edges)"
        )

    # Merge with built-in layer to surface collision warnings.
    # Truncate to ≤3 lines per the WP07 risk table (risk 4: verbosity mitigation).
    try:
        built_in = load_graph_or_dir(resolve_doctrine_root())
        merge_three_layers(built_in=built_in, org_fragments=fragments, project=None)
        console.print("  collisions: none")
    except OrgDRGConflictError as exc:
        shown = exc.conflicts[:3]
        console.print(f"  collisions: {len(exc.conflicts)} built-in invariant override(s)")
        for conflict in shown:
            console.print(
                f"    [yellow]•[/yellow] {conflict.kind} "
                f"target={conflict.target_id} "
                f"resolution={conflict.resolution_applied}"
            )
        if len(exc.conflicts) > 3:
            console.print(f"    … and {len(exc.conflicts) - 3} more (run charter lint for details)")
    except Exception as exc:  # noqa: BLE001 — doctor must not crash
        console.print(f"  [yellow]collision check skipped:[/yellow] {exc}")


def _collect_org_layer_data(repo_root: Path) -> dict[str, object]:
    """Return structured org-layer data for ``doctor doctrine --json`` (FR-007).

    Mirrors the human-readable output of :func:`_render_org_layer_section`
    but as a dict suitable for JSON serialisation.  Always returns a dict
    with an ``"org_drg"`` key so callers can rely on its presence.
    """
    from charter.drg import (  # noqa: PLC0415
        OrgDRGConflictError,
        OrgPackMissingError,
        load_org_drg,
        merge_three_layers,
    )
    from charter.catalog import resolve_doctrine_root  # noqa: PLC0415
    from doctrine.drg.loader import load_graph_or_dir  # noqa: PLC0415

    result: dict[str, object] = {
        "configured_packs": [],
        "collision_warnings": [],
        "errors": [],
    }

    try:
        fragments = load_org_drg(repo_root)
    except OrgPackMissingError as exc:
        result["errors"] = [str(exc)]  # type: ignore[assignment]
        return result
    except Exception as exc:  # noqa: BLE001
        result["errors"] = [f"org-DRG load error: {exc}"]  # type: ignore[assignment]
        return result

    packs = []
    for frag in fragments:
        packs.append(
            {
                "name": frag.pack_name,
                "source_kind": frag.source_kind,
                "source_ref": frag.source_ref,
                "layer_index": frag.layer_index,
                "node_count": len(frag.nodes),
                "edge_count": len(frag.edges),
                "fetched": True,
            }
        )
    result["configured_packs"] = packs  # type: ignore[assignment]

    if not fragments:
        return result

    try:
        built_in = load_graph_or_dir(resolve_doctrine_root())
        merge_three_layers(built_in=built_in, org_fragments=fragments, project=None)
    except OrgDRGConflictError as exc:
        result["collision_warnings"] = [  # type: ignore[assignment]
            {
                "kind": c.kind,
                "target_id": c.target_id,
                "conflicting_layers": c.conflicting_layers,
                "resolution": c.resolution_applied,
            }
            for c in exc.conflicts
        ]
    except Exception:  # noqa: BLE001
        pass

    return result


# ---------------------------------------------------------------------------
# WP09 T050 — Selections section (FR-018)
# ---------------------------------------------------------------------------

#: Canonical artifact-kind plurals as surfaced by ``doctor doctrine`` in the
#: Selections section.  Ordering is the operator-facing reading order from
#: the WP09 plan (directives first, agent_profiles last so the audit ends
#: on the "who can drive" surface).
_SELECTION_KIND_PLURALS: tuple[str, ...] = (
    "directives",
    "tactics",
    "paradigms",
    "styleguides",
    "toolguides",
    "procedures",
    "mission_step_contracts",
    "agent_profiles",
)


def _resolve_artifact_source(
    item_id: str,
    plural: str,
    service: object,
    org_required: dict[str, list[str]],
    project_selected: set[str],
) -> str:
    """Return a stable ``source: <token>`` annotation for *item_id*.

    The annotation tokens are deliberately compact so the snapshot test
    can pin them byte-for-byte:

    * ``built-in`` — artifact comes from the built-in doctrine layer
    * ``project`` — artifact lives under ``.kittify/doctrine/``
    * ``org`` — artifact lives in an org pack (per-pack attribution is
      not yet tracked at the repository layer; see ``_collect_org_source_map``
      in charter.context for the same limitation)
    * ``charter`` — declared selected in the project charter but the
      DoctrineService does not (yet) know about it (e.g. typo or
      missing snapshot)
    * ``org-required`` — required by an org pack's ``org-charter.yaml``
      but not present in the resolved catalog
    """
    repo = getattr(service, plural, None)
    if repo is not None:
        try:
            provenance = repo.get_provenance(item_id)  # type: ignore[attr-defined]
        except (AttributeError, KeyError):
            provenance = None
        if provenance == "builtin":
            return "built-in"
        if provenance == "project":
            return "project"
        if provenance == "org":
            return "org"
    # Not loaded — distinguish "project charter declared it" vs "org pack
    # required it" so the operator can find the right config file.
    if item_id in project_selected:
        return "charter"
    if item_id in (org_required.get(plural) or []):
        return "org-required"
    return "unknown"


def _build_selection_block(repo_root: Path) -> dict[str, list[dict[str, str]]]:
    """Return ``{plural: [{"id": ..., "source": ...}, ...]}`` for FR-018.

    Composes the union of project charter ``selected_<kind>`` and merged
    org ``required_<kind>`` lists, dedupes per-kind (preserving order:
    project-charter ids first, org-required ids appended), and tags each
    entry with the resolved source layer.

    Mission-type-profile selections are intentionally excluded here:
    profiles apply per-mission (gated by ``meta.json mission_type``)
    while ``doctor doctrine`` is a project-wide diagnostic.  The
    selections block reflects the *globally* active set so the operator
    can audit charter intent without picking a specific mission.
    """
    from doctrine.service import DoctrineService
    from specify_cli.doctrine.config import resolve_org_roots

    # Project charter selections (best-effort; missing/malformed → empty).
    # We intentionally bypass ``charter.sync.load_governance_config`` here:
    # that loader runs the charter auto-sync pipeline (and requires a git
    # repository).  The Selections section is a diagnostic — it MUST work
    # in any working tree, including freshly-bootstrapped tmp fixtures and
    # non-git operator workspaces.  Reading the YAML directly preserves
    # accuracy while keeping the diagnostic side-effect-free.
    project_selections: dict[str, list[str]] = {kind: [] for kind in _SELECTION_KIND_PLURALS}
    governance_yaml = repo_root / ".kittify" / "charter" / "governance.yaml"
    if governance_yaml.exists():
        try:
            from ruamel.yaml import YAML as _YAML

            data = _YAML(typ="safe").load(governance_yaml.read_text(encoding="utf-8"))
            doctrine_block = (data or {}).get("doctrine") or {}
            for kind in _SELECTION_KIND_PLURALS:
                value = doctrine_block.get(f"selected_{kind}")
                if isinstance(value, list):
                    project_selections[kind] = [str(v) for v in value]
        except Exception:  # noqa: BLE001 — diagnostics must never crash on malformed yaml
            pass

    # Merged org-charter required_<kind> (best-effort).
    org_required: dict[str, list[str]] = {kind: [] for kind in _SELECTION_KIND_PLURALS}
    try:
        from specify_cli.doctrine.org_charter import load_org_charter_policies

        policy = load_org_charter_policies(repo_root)
        for kind in _SELECTION_KIND_PLURALS:
            org_required[kind] = list(getattr(policy, f"required_{kind}", []) or [])
    except Exception:  # noqa: BLE001 — diagnostics must never crash on missing/invalid org
        pass

    # DoctrineService instance for provenance lookup.
    org_roots = resolve_org_roots(repo_root)
    project_doctrine = repo_root / ".kittify" / "doctrine"
    project_root = project_doctrine if project_doctrine.exists() else None
    service = DoctrineService(
        org_roots=list(org_roots),
        project_root=project_root,
    )

    result: dict[str, list[dict[str, str]]] = {}
    for kind in _SELECTION_KIND_PLURALS:
        seen: set[str] = set()
        ordered: list[str] = []
        for item_id in project_selections[kind] + org_required[kind]:
            if item_id in seen:
                continue
            seen.add(item_id)
            ordered.append(item_id)
        project_set = set(project_selections[kind])
        entries: list[dict[str, str]] = []
        for item_id in ordered:
            entries.append({
                "id": item_id,
                "source": _resolve_artifact_source(
                    item_id, kind, service, org_required, project_set
                ),
            })
        result[kind] = entries
    return result


def _render_selection_block_lines(
    selections: dict[str, list[dict[str, str]]],
) -> list[str]:
    """Render the Selections block as a list of pinned-format lines.

    The exact layout is pinned by the snapshot test
    ``tests/cli/test_doctor_doctrine_selections_snapshot.py``.  Every
    change to spacing, punctuation, or per-kind ordering MUST update the
    snapshot fixture in the same commit.
    """
    lines: list[str] = ["Selections (active globally-selected artifacts):"]
    for kind in _SELECTION_KIND_PLURALS:
        entries = selections.get(kind, [])
        if not entries:
            lines.append(f"  {kind}: (none)")
            continue
        lines.append(f"  {kind}:")
        for entry in entries:
            lines.append(f"    - {entry['id']:<24}(source: {entry['source']})")
    return lines
