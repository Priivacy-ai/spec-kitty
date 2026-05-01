"""CLI commands for runtime migration and identity backfill.

Subcommands:

- ``spec-kitty migrate`` — Migrate project .kittify/ to centralized model.
- ``spec-kitty migrate backfill-identity`` — Write ULID ``mission_id`` into
  any ``meta.json`` that lacks one.  Idempotent and non-destructive.

Usage examples::

    spec-kitty migrate --dry-run
    spec-kitty migrate backfill-identity --dry-run --json
    spec-kitty migrate backfill-identity --mission 083-foo-bar
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from specify_cli.core.paths import locate_project_root
from specify_cli.paths import get_runtime_root, render_runtime_path
from specify_cli.paths.windows_migrate import MigrationOutcome
from specify_cli.runtime.bootstrap import ensure_runtime
from specify_cli.runtime.migrate import execute_migration

app = typer.Typer(
    name="migrate",
    help=("Migration commands: update .kittify/ layout and backfill identity fields in legacy missions."),
    no_args_is_help=False,
    invoke_without_command=True,
)
console = Console()


@app.callback(invoke_without_command=True)
def migrate(  # noqa: C901
    ctx: typer.Context,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without modifying the filesystem"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show file-by-file detail"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
) -> None:
    """Migrate project .kittify/ to centralized model.

    First ensures the global runtime is up to date, then classifies
    per-project files as identical (removed), customized (moved to
    overrides/), or project-specific (kept). Use --dry-run to preview
    changes before applying.

    Running this command multiple times is safe (idempotent). After the
    first successful run, subsequent invocations are a near-instant no-op.

    Examples:
        spec-kitty migrate --dry-run    # Preview
        spec-kitty migrate --force      # Apply without confirmation
    """
    # If a subcommand was invoked, don't run the migrate callback body.
    if ctx.invoked_subcommand is not None:
        return

    # Windows-only: run legacy state migration BEFORE any tracker/sync/daemon reads.
    # This ensures post-upgrade invocations pick up state from the correct root.
    # --dry-run is plumbed through: in preview mode the function computes outcomes
    # without performing any filesystem moves (FR-006, contracts/cli-migrate.md).
    if sys.platform == "win32":
        from specify_cli.paths.windows_migrate import migrate_windows_state  # noqa: PLC0415

        try:
            outcomes = migrate_windows_state(dry_run=dry_run)
        except TimeoutError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(69) from exc
        _render_windows_migration_summary(console, outcomes, dry_run=dry_run)

    project_dir = locate_project_root()
    if project_dir is None:
        console.print("[red]Could not locate project root. No .kittify/ directory found in any parent directory.[/red]")
        raise typer.Exit(1)

    if not (project_dir / ".kittify").exists():
        console.print("[red]No .kittify/ directory found in current project.[/red]")
        raise typer.Exit(1)

    if not dry_run and not force:
        confirmed = typer.confirm("Migrate .kittify/ to centralized model?")
        if not confirmed:
            raise typer.Abort()

    # Step 1: Ensure global runtime is installed and current.
    # This is idempotent -- fast-path returns immediately if version matches.
    if dry_run:
        console.print("[bold]Step 1:[/bold] Global runtime check (no changes in dry-run)")
    else:
        runtime_root = get_runtime_root()
        runtime_path_display = render_runtime_path(runtime_root.base)
        console.print(f"[bold]Step 1:[/bold] Ensuring global runtime ({runtime_path_display}/) is up to date...")
        ensure_runtime()
        console.print("  [green]Global runtime is current.[/green]")

    # Step 2: Per-project migration.
    console.print("[bold]Step 2:[/bold] Per-project .kittify/ cleanup...")
    report = execute_migration(project_dir, dry_run=dry_run, verbose=verbose)

    # Display results
    if dry_run:
        console.print("[bold]Dry run -- no changes made[/bold]")

    action_removed = "would remove" if dry_run else "removed"
    action_moved = "would move" if dry_run else "moved"
    action_superseded = "would remove" if dry_run else "removed"

    console.print(f"  {len(report.removed)} files identical to global -- {action_removed}")
    if report.superseded:
        console.print(f"  {len(report.superseded)} files superseded (outdated defaults) -- {action_superseded}")
    console.print(f"  {len(report.moved)} files customized -- {action_moved} to overrides/")
    console.print(f"  {len(report.kept)} files project-specific -- kept")

    if report.unknown:
        console.print(f"  [yellow]{len(report.unknown)} files unknown -- kept with warning[/yellow]")

    if verbose:
        for path in report.removed:
            console.print(f"    [dim]removed: {path}[/dim]")
        for path in report.superseded:
            console.print(f"    [dim]superseded: {path}[/dim]")
        for src, dst in report.moved:
            console.print(f"    [blue]moved: {src} -> {dst}[/blue]")
        for path in report.kept:
            console.print(f"    [green]kept: {path}[/green]")
        for path in report.unknown:
            console.print(f"    [yellow]unknown: {path}[/yellow]")

    if not dry_run:
        console.print("\n[green]Migration complete.[/green] Zero legacy warnings expected. Run `spec-kitty config --show-origin` to verify resolution tiers.")

    # Credential path decision: auth credentials stay in the runtime auth/ subdir.
    # This is a security boundary decision -- credentials have a different
    # lifecycle and permission model from runtime assets.  Documented here
    # per WP08 acceptance criteria.


@app.command(name="backfill-identity")
def backfill_identity(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit per-mission result list as structured JSON"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=("Report what would change without writing any files. The JSON shape is identical to a live run."),
        ),
    ] = False,
    mission: Annotated[
        str | None,
        typer.Option(
            "--mission",
            help="Scope to a single mission slug (e.g. 083-foo-bar). Omit to process all.",
            metavar="SLUG",
        ),
    ] = None,
) -> None:
    """Write a ULID mission_id into any meta.json that lacks one.

    This command is **idempotent** — running it twice produces identical
    state.  Existing ``mission_id`` values are never overwritten.  The
    command also coerces legacy string-typed ``mission_number`` values
    (e.g. ``"042"`` → ``42``) while walking each mission.

    After writing, the dossier parity hash is recomputed for every mission
    that was modified.  Individual dossier failures are logged as warnings
    and do not abort the run.

    **When to run:**

    - After upgrading from a spec-kitty version that predates ``mission_id``
    - After pulling a clone that has legacy missions (no ``mission_id``)
    - As part of CI checks on legacy repositories

    Exit codes:

    - ``0`` — all results are ``wrote`` or ``skip``
    - ``1`` — one or more ``error`` results (corrupt JSON, sentinel strings, …)

    Examples:

        spec-kitty migrate backfill-identity --dry-run --json

        spec-kitty migrate backfill-identity --mission 083-foo-bar

        spec-kitty migrate backfill-identity
    """
    from specify_cli.migration.backfill_identity import backfill_repo

    repo_root = locate_project_root()
    if repo_root is None:
        _error("Could not locate project root. No .kittify/ directory found in any parent directory.")
        raise typer.Exit(1)

    results = backfill_repo(repo_root, dry_run=dry_run, mission_slug=mission)

    wrote = [r for r in results if r.action == "wrote"]
    skipped = [r for r in results if r.action == "skip"]
    errored = [r for r in results if r.action == "error"]
    coerced = [r for r in results if r.number_coerced]
    warned = [r for r in results if r.dossier_warning]

    if json_output:
        payload = {
            "dry_run": dry_run,
            "summary": {
                "total": len(results),
                "wrote": len(wrote),
                "skip": len(skipped),
                "error": len(errored),
                "number_coerced": len(coerced),
                "dossier_warnings": len(warned),
            },
            "results": [
                {
                    "slug": r.slug,
                    "action": r.action,
                    "mission_id": r.mission_id,
                    "number_coerced": r.number_coerced,
                    "reason": r.reason,
                    "dossier_warning": r.dossier_warning,
                }
                for r in results
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        prefix = "[dim](dry-run)[/dim] " if dry_run else ""
        console.print(f"\n{prefix}[bold]backfill-identity summary[/bold]")
        console.print(f"  Total missions scanned : {len(results)}")
        console.print(f"  Written (mission_id)   : {len(wrote)}")
        console.print(f"  Skipped (already set)  : {len(skipped)}")
        console.print(f"  Errors                 : {len(errored)}")
        console.print(f"  Number coerced         : {len(coerced)}")
        if warned:
            console.print(f"  [yellow]Dossier warnings       : {len(warned)}[/yellow]")

        if errored:
            console.print("\n[red]Errors:[/red]")
            for r in errored:
                console.print(f"  [red]{r.slug}:[/red] {r.reason}")

        if dry_run:
            console.print("\n[dim]Dry run — no files were modified.[/dim]")
        elif wrote:
            console.print(f"\n[green]Done.[/green] {len(wrote)} mission(s) received a ``mission_id``.")
        else:
            console.print("\n[green]Done.[/green] All missions already have a ``mission_id``.")

    if errored:
        raise typer.Exit(1)


@app.command(name="normalize-lifecycle")
def normalize_lifecycle(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit a structured per-mission normalization report"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Preview lifecycle normalization without modifying the filesystem",
        ),
    ] = False,
    mission: Annotated[
        str | None,
        typer.Option(
            "--mission",
            help="Scope to a single mission slug (e.g. 083-foo-bar). Omit to process all.",
            metavar="SLUG",
        ),
    ] = None,
) -> None:
    """Normalize legacy ``kitty-specs`` missions for the MVP lifecycle model.

    This command repairs enough historical mission state to make the canonical
    lifecycle model reliable across old repositories. It backfills identity
    where needed, rebuilds missing event logs from legacy state, and regenerates
    status/progress/lifecycle projections used by the CLI and Teamspace.

    Exit codes:

    - ``0`` — all targeted missions normalized or skipped cleanly
    - ``1`` — one or more missions hit an unrecoverable error
    """
    from specify_cli.migration.normalize_mission_lifecycle import normalize_repo

    repo_root = locate_project_root()
    if repo_root is None:
        _error("Could not locate project root. No .kittify/ directory found in any parent directory.")
        raise typer.Exit(1)

    results = normalize_repo(repo_root, dry_run=dry_run, mission_slug=mission)
    payload = _normalize_lifecycle_payload(results, dry_run=dry_run)

    if json_output:
        print(json.dumps(payload, indent=2))
    else:
        _print_normalize_lifecycle_summary(results, dry_run=dry_run)

    if payload["summary"]["error"]:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _error(message: str) -> None:
    """Print an error message to stderr via Rich console."""
    err_console = Console(stderr=True)
    err_console.print(f"[red]Error:[/red] {message}")


def _normalize_lifecycle_payload(results: list, *, dry_run: bool) -> dict[str, object]:
    normalized = [r for r in results if r.status == "normalized"]
    skipped = [r for r in results if r.status == "skipped"]
    errored = [r for r in results if r.status == "error"]
    warned = [r for r in results if r.warnings]
    return {
        "dry_run": dry_run,
        "summary": {
            "total": len(results),
            "normalized": len(normalized),
            "skipped": len(skipped),
            "error": len(errored),
            "warnings": len(warned),
        },
        "results": [
            {
                "slug": r.slug,
                "status": r.status,
                "lifecycle_state": r.lifecycle_state,
                "actions": r.actions,
                "warnings": r.warnings,
                "error": r.error,
            }
            for r in results
        ],
    }


def _print_normalize_lifecycle_summary(results: list, *, dry_run: bool) -> None:
    normalized = [r for r in results if r.status == "normalized"]
    skipped = [r for r in results if r.status == "skipped"]
    errored = [r for r in results if r.status == "error"]
    warned = [r for r in results if r.warnings]

    prefix = "[dim](dry-run)[/dim] " if dry_run else ""
    console.print(f"\n{prefix}[bold]normalize-lifecycle summary[/bold]")
    console.print(f"  Total missions scanned : {len(results)}")
    console.print(f"  Normalized             : {len(normalized)}")
    console.print(f"  Skipped                : {len(skipped)}")
    console.print(f"  Errors                 : {len(errored)}")
    if warned:
        console.print(f"  [yellow]Warnings               : {len(warned)}[/yellow]")

    for entry in normalized:
        lifecycle = f" ({entry.lifecycle_state})" if entry.lifecycle_state else ""
        console.print(f"  [green]{entry.slug}[/green]{lifecycle}")
        for action in entry.actions:
            console.print(f"    - {action}")
        for warning in entry.warnings:
            console.print(f"    [yellow]- {warning}[/yellow]")

    if skipped:
        console.print("\n[dim]Skipped:[/dim]")
        for entry in skipped:
            console.print(f"  {entry.slug}")
            for warning in entry.warnings:
                console.print(f"    [yellow]- {warning}[/yellow]")

    if errored:
        console.print("\n[red]Errors:[/red]")
        for entry in errored:
            console.print(f"  [red]{entry.slug}:[/red] {entry.error}")
            for warning in entry.warnings:
                console.print(f"    [yellow]- {warning}[/yellow]")

    if dry_run:
        console.print("\n[dim]Dry run — no files were modified.[/dim]")
    elif not errored:
        console.print("\n[green]Done.[/green] Lifecycle normalization is current.")


def _render_windows_migration_summary(
    con: Console,
    outcomes: list[MigrationOutcome],
    *,
    dry_run: bool = False,
) -> None:
    """Render the Windows runtime state migration summary per contracts/cli-migrate.md.

    Uses ``render_runtime_path`` for every path shown to the user.
    Exits with code 78 if ``%LOCALAPPDATA%`` is unresolvable.
    (Lock-contention exit-69 is handled at the call site before this function.)

    When ``dry_run`` is True, the header labels each reported move as a preview
    so users understand that no filesystem changes have occurred.
    """
    if not outcomes:
        return

    # Check for unresolvable %LOCALAPPDATA% error
    localappdata_errors = [o for o in outcomes if o.status == "error" and o.dest_path is None]
    if localappdata_errors:
        con.print(
            "[red]Could not resolve %LOCALAPPDATA% on this machine. "
            "Spec Kitty needs a writable Windows app-data directory to store runtime state.\n"
            "Diagnose with: echo %LOCALAPPDATA% (cmd.exe) or $env:LOCALAPPDATA (PowerShell).[/red]"
        )
        raise typer.Exit(78)

    moved = [o for o in outcomes if o.status == "moved"]
    quarantined = [o for o in outcomes if o.status == "quarantined"]
    errors = [o for o in outcomes if o.status == "error"]

    if not moved and not quarantined and not errors:
        # All absent — idempotent no-op, nothing to show
        return

    # Determine canonical destination from any non-absent outcome
    canonical_dest: str | None = None
    for o in outcomes:
        if o.dest_path is not None:
            canonical_dest = render_runtime_path(Path(o.dest_path))
            break

    header = "\n[DRY-RUN] Would migrate Spec Kitty runtime state on Windows." if dry_run else "\nMigrated Spec Kitty runtime state on Windows."
    con.print(header)
    if canonical_dest:
        con.print(f"  Canonical location: {canonical_dest}")

    move_verb = "Would move" if dry_run else "Moved"
    for o in moved:
        legacy_display = render_runtime_path(Path(o.legacy_path))
        dest_display = render_runtime_path(Path(o.dest_path)) if o.dest_path else canonical_dest or ""
        con.print(f"  {move_verb}: {legacy_display} -> {dest_display}")

    if quarantined:
        quarantine_header = (
            "  Destination already contains state; legacy trees would be preserved as backups:"
            if dry_run
            else "  Destination already contained state; legacy trees preserved as backups:"
        )
        con.print(quarantine_header)
        for o in quarantined:
            legacy_display = render_runtime_path(Path(o.legacy_path))
            bak_display = render_runtime_path(Path(o.quarantine_path)) if o.quarantine_path else "?"
            con.print(f"    {legacy_display} -> {bak_display}")
        if not dry_run:
            con.print("  Review the canonical location and delete the backup directories when safe.")

    for o in errors:
        legacy_display = render_runtime_path(Path(o.legacy_path))
        con.print(f"  [yellow]Warning:[/yellow] Could not migrate {legacy_display}: {o.error}")
