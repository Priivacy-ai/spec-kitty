"""Top-level doctor command group for project health diagnostics."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.core.paths import locate_project_root
from specify_cli.paths import get_runtime_root, render_runtime_path
from specify_cli.runtime.home import get_kittify_home


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


def _print_overdue_details(report: object, console: Console) -> None:
    console.print()
    console.print("[bold red]Overdue shims must be resolved before release:[/bold red]")
    for e in report.entries:  # type: ignore[union-attr]
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
        f"With warnings: {summary['missions_with_warnings']}"
    )


@app.command(name="mission-state")
def mission_state(
    audit: Annotated[
        bool,
        typer.Option("--audit", help="Run mission-state audit (required to proceed)"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON report to stdout"),
    ] = False,
    mission: Annotated[
        Optional[str],
        typer.Option("--mission", help="Scope to a single mission handle"),
    ] = None,
    fail_on: Annotated[
        Optional[str],
        typer.Option("--fail-on", help="Exit 1 if any finding meets this severity (error|warning|info)"),
    ] = None,
    fixture_dir: Annotated[
        Optional[Path],
        typer.Option("--fixture-dir", help="Override scan root (for testing)"),
    ] = None,
) -> None:
    """Audit mission-state shapes across kitty-specs/."""
    from specify_cli.audit import AuditOptions, Severity, build_report_json, run_audit

    if not audit:
        typer.echo("Use --audit to run the audit. See --help for options.")
        raise typer.Exit(0)

    # Validate --fail-on
    fail_on_severity: Optional[Severity] = None
    if fail_on is not None:
        try:
            fail_on_severity = Severity(fail_on)
        except ValueError:
            valid = ", ".join(s.value for s in Severity)
            typer.echo(f"Invalid --fail-on value: {fail_on!r}. Valid values: {valid}", err=True)
            raise typer.Exit(2)

    # Resolve repo root
    try:
        repo_root = locate_project_root()
    except Exception as exc:
        console.print("[red]Error:[/red] Not in a spec-kitty project")
        raise typer.Exit(1) from exc

    if repo_root is None:
        if fixture_dir is None:
            console.print("[red]Error:[/red] Not in a spec-kitty project")
            raise typer.Exit(1)
        repo_root = fixture_dir.parent

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
            import json as _json
            sys.stdout.write(_json.dumps({"error": "MISSION_NOT_FOUND", "handle": mission}) + "\n")
            sys.stdout.flush()
        else:
            typer.echo(f"Error: Mission not found: {mission!r}", err=True)
        raise typer.Exit(1) from exc
    except AmbiguousHandleError as exc:
        if json_output:
            import json as _json
            sys.stdout.write(_json.dumps({"error": "AMBIGUOUS_HANDLE", "handle": mission}) + "\n")
            sys.stdout.flush()
        else:
            typer.echo(f"Error: Ambiguous handle: {mission!r}", err=True)
        raise typer.Exit(1) from exc

    if json_output:
        sys.stdout.write(build_report_json(report))
        sys.stdout.flush()
    else:
        _print_rich_audit_report(report)

    if fail_on_severity is not None:
        if any(
            f.severity <= fail_on_severity
            for result in report.missions
            for f in result.findings
        ):
            raise typer.Exit(1)
