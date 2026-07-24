"""CLI commands for runtime migration and identity backfill.

Subcommands:

- ``spec-kitty migrate`` — Migrate project .kittify/ to centralized model.
- ``spec-kitty migrate backfill-identity`` — Write ULID ``mission_id`` into
  any ``meta.json`` that lacks one.  Idempotent and non-destructive.
- ``spec-kitty migrate charter-encoding`` — Scan charter content for non-UTF-8
  encodings; normalize-or-fail-loud. Implements FR-026, FR-027, NFR-006.
- ``spec-kitty migrate backfill-provenance`` — Stamp the ``legacy_unrecorded``
  provenance sentinel onto non-``pending`` negative invariants recorded before
  the provenance schema existed. Implements FR-014.
- ``spec-kitty migrate rewrite-opposed-by`` — Rewrite a downstream/org pack's
  legacy ``opposed_by`` entries into ``in_tension_with``/``rejects`` DRG
  edges. Implements FR-015.

Usage examples::

    spec-kitty migrate --dry-run
    spec-kitty migrate backfill-identity --dry-run --json
    spec-kitty migrate backfill-identity --mission 083-foo-bar
    spec-kitty migrate charter-encoding --dry-run
    spec-kitty migrate charter-encoding --yes --json
    spec-kitty migrate backfill-provenance --dry-run --json
    spec-kitty migrate rewrite-opposed-by --pack ./org-packs/acme --dry-run
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from specify_cli.cli.console import console
from specify_cli.cli.console import err_console

from specify_cli.core.paths import locate_project_root
from specify_cli.paths import get_runtime_root, render_runtime_path
from specify_cli.paths.windows_migrate import MigrationOutcome
from specify_cli.runtime.bootstrap import ensure_runtime
from specify_cli.runtime.migrate import execute_migration

app = typer.Typer(
    name="migrate",
    help=(
        "Migration commands: update .kittify/ layout and backfill identity fields "
        "in legacy missions."
    ),
    no_args_is_help=False,
    invoke_without_command=True,
)

# Hoisted flag/help/label literals for the backfill-runtime-state command (S1192):
# option strings, help text, and summary labels would otherwise repeat across the
# command signature, the JSON payload, and the rich summary printer.
_RUNTIME_STATE_CMD = "backfill-runtime-state"
_DRY_RUN_FLAG = "--dry-run"
_MISSION_FLAG = "--mission"
_MISSION_METAVAR = "HANDLE"
_JSON_FLAG = "--json"
_DRY_RUN_HELP = "Seed nothing and flip nothing; report per-mission would-seed counts and would-flip."
_MISSION_HELP = "Scope to a single mission (mission_id / mid8 / slug). Omit to process the whole corpus."
_JSON_HELP = "Emit the per-mission cutover result list as structured JSON."
_RUNTIME_STATE_SUMMARY_TITLE = "backfill-runtime-state summary"
_LABEL_FLIPPED = "Flipped"
_LABEL_WOULD_SEED = "Would seed (verify pending)"
_LABEL_SKIPPED = "Skipped (already migrated)"
_LABEL_FAILED = "Failed"


@app.callback(invoke_without_command=True)
def migrate(  # noqa: C901
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without modifying the filesystem"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show file-by-file detail"
    ),
    force: bool = typer.Option(
        False, "--force", help="Skip confirmation prompt"
    ),
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
        console.print(
            "[red]Could not locate project root. "
            "No .kittify/ directory found in any parent directory.[/red]"
        )
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
        console.print(
            f"[bold]Step 1:[/bold] Ensuring global runtime ({runtime_path_display}/) is up to date..."
        )
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

    console.print(
        f"  {len(report.removed)} files identical to global -- {action_removed}"
    )
    if report.superseded:
        console.print(
            f"  {len(report.superseded)} files superseded (outdated defaults) -- {action_superseded}"
        )
    console.print(
        f"  {len(report.moved)} files customized -- {action_moved} to overrides/"
    )
    console.print(f"  {len(report.kept)} files project-specific -- kept")

    if report.unknown:
        console.print(
            f"  [yellow]{len(report.unknown)} files unknown -- kept with warning[/yellow]"
        )

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
        console.print(
            "\n[green]Migration complete.[/green] Zero legacy warnings expected. "
            "Run `spec-kitty config --show-origin` to verify resolution tiers."
        )

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
            help=(
                "Report what would change without writing any files. "
                "The JSON shape is identical to a live run."
            ),
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
            console.print(
                f"\n[green]Done.[/green] {len(wrote)} mission(s) received a "
                f"``mission_id``."
            )
        else:
            console.print("\n[green]Done.[/green] All missions already have a ``mission_id``.")

    if errored:
        raise typer.Exit(1)


@app.command(name="backfill-topology")
def backfill_topology(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit per-mission result list as structured JSON"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Report what would change without writing any files. "
                "The JSON shape is identical to a live run."
            ),
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
    """Persist each legacy mission's MissionTopology into its meta.json.

    Computes every mission's topology (the coordination × lanes grid cell) from
    its current on-disk signals via the single WP01 classifier and writes it to
    ``meta.json`` as the authoritative ``topology`` value. This command is
    **idempotent** — a mission that already has a valid ``topology`` is skipped
    and its value is never overwritten.

    Exit codes:

    - ``0`` — all results are ``wrote`` or ``skip``
    - ``1`` — one or more ``error`` results (corrupt / unreadable meta.json)

    Examples:

        spec-kitty migrate backfill-topology --dry-run --json

        spec-kitty migrate backfill-topology --mission 083-foo-bar

        spec-kitty migrate backfill-topology
    """
    from specify_cli.migration.backfill_topology import backfill_topology_repo

    repo_root = locate_project_root()
    if repo_root is None:
        _error("Could not locate project root. No .kittify/ directory found in any parent directory.")
        raise typer.Exit(1)

    results = backfill_topology_repo(repo_root, dry_run=dry_run, mission_slug=mission)

    wrote = [r for r in results if r.action == "wrote"]
    skipped = [r for r in results if r.action == "skip"]
    errored = [r for r in results if r.action == "error"]

    if json_output:
        payload = {
            "dry_run": dry_run,
            "summary": {
                "total": len(results),
                "wrote": len(wrote),
                "skip": len(skipped),
                "error": len(errored),
            },
            "results": [
                {
                    "slug": r.slug,
                    "action": r.action,
                    "topology": r.topology,
                    "reason": r.reason,
                }
                for r in results
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        prefix = "[dim](dry-run)[/dim] " if dry_run else ""
        console.print(f"\n{prefix}[bold]backfill-topology summary[/bold]")
        console.print(f"  Total missions scanned : {len(results)}")
        console.print(f"  Written (topology)     : {len(wrote)}")
        console.print(f"  Skipped (already set)  : {len(skipped)}")
        console.print(f"  Errors                 : {len(errored)}")

        if errored:
            console.print("\n[red]Errors:[/red]")
            for r in errored:
                console.print(f"  [red]{r.slug}:[/red] {r.reason}")

        if dry_run:
            console.print("\n[dim]Dry run — no files were modified.[/dim]")
        elif wrote:
            console.print(
                f"\n[green]Done.[/green] {len(wrote)} mission(s) received a ``topology``."
            )
        else:
            console.print("\n[green]Done.[/green] All missions already have a ``topology``.")

    if errored:
        raise typer.Exit(1)


@app.command(name="charter-encoding")
def charter_encoding(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Show what would change without writing any files.  "
                "Returns exit 0 unless ambiguous files are found."
            ),
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help=(
                "Apply normalizations without prompting.  "
                "Exits non-zero if any file is ambiguous (CI-safe).  "
                "Do NOT pass --yes to silently bypass ambiguous files — "
                "manual repair is required for those."
            ),
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit a JSON-stable summary report on stdout."),
    ] = False,
    project_root: Annotated[
        Path,
        typer.Option(
            "--project-root",
            help="Root of the Spec Kitty project (default: current working directory).",
            metavar="DIR",
        ),
    ] = Path("."),
) -> None:
    """Scan charter content for non-UTF-8 encodings; normalize-or-fail-loud.

    Walks every existing mission's charter content
    (``kitty-specs/*/charter/*.{yaml,md,txt}``) and the global charter store
    (``.kittify/charter/*.{yaml,md,txt}``), detects the encoding of each file
    via the WP06 chokepoint, and either:

    \\b
    * **skips** the file (already pure UTF-8; idempotency pre-check passes)
    * **normalizes** the file to UTF-8 in-place with a provenance record
    * **surfaces** the file as ambiguous (exits non-zero; manual repair required)

    This migration is **idempotent** (NFR-006): running it twice on an
    already-normalized corpus is a near-instant no-op — no new provenance
    records are written for already-UTF-8 files.

    Implements FR-026, FR-027, NFR-006.

    Exit codes:

    - ``0`` — corpus is fully UTF-8 compliant (all files already-UTF-8 or
      successfully normalized)
    - ``1`` — one or more files are ambiguous (manual repair required)

    Examples:

        spec-kitty migrate charter-encoding --dry-run

        spec-kitty migrate charter-encoding --yes --json

        spec-kitty migrate charter-encoding
    """
    from specify_cli.cli.commands.migrate.charter_encoding import (  # noqa: PLC0415
        run_charter_encoding_migration,
    )

    exit_code = run_charter_encoding_migration(
        project_root=project_root.resolve(),
        dry_run=dry_run,
        yes=yes,
        json_output=json_output,
    )
    if exit_code != 0:
        raise typer.Exit(exit_code)


@app.command(name="backfill-provenance")
def backfill_provenance(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Report what would be stamped without writing any files. "
                "The JSON shape is identical to a live run."
            ),
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit a JSON-stable summary report on stdout."),
    ] = False,
    project_root: Annotated[
        Path,
        typer.Option(
            "--project-root",
            help="Root of the Spec Kitty project (default: current working directory).",
            metavar="DIR",
        ),
    ] = Path("."),
) -> None:
    """FR-014: backfill provenance onto legacy acceptance-matrix.json invariants.

    Walks every ``kitty-specs/*/acceptance-matrix.json`` and, for each negative
    invariant whose ``result`` is not ``pending`` and lacks ``provenance_origin``,
    stamps the ``legacy_unrecorded`` sentinel (data-model.md NI-1 / contract
    ``negative-invariant-provenance.md`` C1). ``verified_ref`` and
    ``verified_surface_kind`` are left null for those rows — the sentinel means
    the surface a pre-schema judgement was established against is genuinely
    unknowable, not empty by omission.

    This migration is **idempotent** (NI-2 / C3): re-running it on an
    already-migrated corpus is a no-op — a row already carrying
    ``provenance_origin`` (``recorded`` or ``legacy_unrecorded``) is never
    re-stamped.

    The whole-corpus write is enrolled in a commit-or-revert transaction: on
    any failure partway through, every file already written in that run is
    restored to its pre-migration bytes — no partial migration state is left
    on disk.

    AM-4: this migration never auto-archives. A matrix it cannot parse is
    reported as an error and skipped; it never routes into an archive
    operation.

    Exit codes:

    - ``0`` — every matrix migrated cleanly (or needed no change)
    - ``1`` — one or more matrices could not be parsed (see the reported errors)

    Examples:

        spec-kitty migrate backfill-provenance --dry-run

        spec-kitty migrate backfill-provenance --json

        spec-kitty migrate backfill-provenance
    """
    from specify_cli.cli.commands.migrate.backfill_provenance import (  # noqa: PLC0415
        run_backfill_provenance_migration,
    )

    summary = run_backfill_provenance_migration(project_root.resolve(), dry_run=dry_run)

    if json_output:
        payload = {
            "dry_run": summary.dry_run,
            "result": summary.result,
            "summary": {
                "files_inspected": summary.files_inspected,
                "migrated": len(summary.migrated),
                "unchanged": len(summary.unchanged),
                "errors": len(summary.errors),
                "invariants_stamped": summary.stamped_total,
            },
            "migrated": [
                {"path": str(record.path), "invariants_stamped": record.invariants_stamped}
                for record in summary.migrated
            ],
            "errors": [
                {"path": str(error.path), "message": error.message}
                for error in summary.errors
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        prefix = "[dim](dry-run)[/dim] " if dry_run else ""
        console.print(f"\n{prefix}[bold]backfill-provenance summary[/bold]")
        console.print(f"  Matrices scanned   : {summary.files_inspected}")
        console.print(f"  Migrated (files)   : {len(summary.migrated)}")
        console.print(f"  Invariants stamped : {summary.stamped_total}")
        console.print(f"  Unchanged          : {len(summary.unchanged)}")
        console.print(f"  Errors             : {len(summary.errors)}")

        if summary.errors:
            console.print("\n[red]Errors:[/red]")
            for error in summary.errors:
                console.print(f"  [red]{error.path}:[/red] {error.message}")

        if dry_run:
            console.print("\n[dim]Dry run — no files were modified.[/dim]")
        elif summary.migrated:
            console.print(
                f"\n[green]Done.[/green] {len(summary.migrated)} matrix file(s) "
                "received the legacy_unrecorded sentinel."
            )
        else:
            console.print("\n[green]Done.[/green] Corpus already carries provenance.")

    if summary.errors:
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


@app.command(name="rewrite-opposed-by")
def rewrite_opposed_by(
    pack: Annotated[
        Path,
        typer.Option(
            "--pack",
            help="Root directory of the target pack to migrate (org pack or any "
            "directory shaped like the built-in doctrine tree).",
            metavar="PATH",
        ),
    ] = Path("."),
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Report planned rewrites without writing any files. "
                "The JSON shape is identical to a live run."
            ),
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit a structured JSON report on stdout."),
    ] = False,
) -> None:
    """Rewrite a pack's legacy ``opposed_by`` entries into DRG edges.

    Scans every ``*.directive.yaml``/``*.tactic.yaml``/``*.paradigm.yaml``
    file under ``--pack`` for ``opposed_by`` entries, classifies each as
    tension-style (rewritten to an ``in_tension_with`` edge) or
    anti-pattern-rejection-style (rewritten to a ``rejects`` edge, creating
    the target ``anti_pattern`` node if absent), writes the new edges into
    the pack's ``<kind>.graph.yaml`` fragments, and removes the migrated
    ``opposed_by`` key from the source YAML.

    This command is **idempotent** — once a pack has no remaining
    ``opposed_by`` entries, running it again is a no-op.

    **When to run:**

    - Before upgrading to a spec-kitty release that drops ``opposed_by``
      from the ``directive``/``tactic``/``paradigm`` schemas
    - As part of CI checks on an org pack that still authors ``opposed_by``

    Exit codes:

    - ``0`` — every entry was rewritten (or, in ``--dry-run``, would be)
    - ``1`` — one or more entries could not be unambiguously classified

    Examples:

        spec-kitty migrate rewrite-opposed-by --pack ./org-packs/acme --dry-run

        spec-kitty migrate rewrite-opposed-by --pack ./org-packs/acme --json

        spec-kitty migrate rewrite-opposed-by --pack ./org-packs/acme
    """
    from specify_cli.migration.rewrite_opposed_by import rewrite_opposed_by_pack

    pack_root = pack.resolve()
    if not pack_root.is_dir():
        _error(f"Pack root not found: {pack_root}")
        raise typer.Exit(1)

    result = rewrite_opposed_by_pack(pack_root, dry_run=dry_run)

    if json_output:
        payload = {
            "dry_run": dry_run,
            "pack_root": str(pack_root),
            "summary": {
                "rewritten": len(result.rewritten),
                "unclassifiable": len(result.unclassifiable),
            },
            "rewritten": [
                {
                    "source_file": str(r.source_file),
                    "source": f"{r.source_type}:{r.source_id}",
                    "target": f"{r.target_type}:{r.target_id}",
                    "relation": r.relation,
                    "reason": r.reason,
                    "created_anti_pattern_node": r.created_anti_pattern_node,
                }
                for r in result.rewritten
            ],
            "unclassifiable": [
                {
                    "source_file": str(u.source_file),
                    "source": f"{u.source_type}:{u.source_id}",
                    "target": f"{u.target_type}:{u.target_id}",
                    "message": u.message,
                }
                for u in result.unclassifiable
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        prefix = "[dim](dry-run)[/dim] " if dry_run else ""
        console.print(f"\n{prefix}[bold]rewrite-opposed-by summary[/bold]")
        console.print(f"  Pack root      : {pack_root}")
        console.print(f"  Rewritten      : {len(result.rewritten)}")
        console.print(f"  Unclassifiable : {len(result.unclassifiable)}")

        for r in result.rewritten:
            verb = "would rewrite" if dry_run else "rewrote"
            node_note = " (creates anti_pattern node)" if r.created_anti_pattern_node else ""
            console.print(
                f"  [green]{verb}[/green] {r.source_type}:{r.source_id} "
                f"--{r.relation}--> {r.target_type}:{r.target_id}{node_note}"
            )

        if result.unclassifiable:
            console.print("\n[red]Unclassifiable entries (manual review required):[/red]")
            for u in result.unclassifiable:
                console.print(f"  [red]{u.source_file}:[/red] {u.message}")

        if dry_run:
            console.print("\n[dim]Dry run — no files were modified.[/dim]")
        elif result.rewritten:
            console.print(
                f"\n[green]Done.[/green] {len(result.rewritten)} opposed_by "
                "entry(ies) rewritten to DRG edges."
            )
        else:
            console.print("\n[green]Done.[/green] No opposed_by entries found.")

    if result.unclassifiable:
        raise typer.Exit(1)


@app.command(name=_RUNTIME_STATE_CMD)
def backfill_runtime_state_cmd(
    dry_run: Annotated[bool, typer.Option(_DRY_RUN_FLAG, help=_DRY_RUN_HELP)] = False,
    mission: Annotated[
        str | None,
        typer.Option(_MISSION_FLAG, help=_MISSION_HELP, metavar=_MISSION_METAVAR),
    ] = None,
    json_output: Annotated[bool, typer.Option(_JSON_FLAG, help=_JSON_HELP)] = False,
) -> None:
    """Seed legacy runtime state as events, verify fail-closed, and flip status_phase.

    Drives the shared :func:`~specify_cli.migration.runtime_state_cutover.cutover_mission`
    helper over the corpus (or a single ``--mission``). For every mission it seeds
    the frontmatter/checkbox runtime state into the event log, verifies the reduced
    snapshot equals the OLD reader by **count + value**, and flips ``meta.json``
    ``status_phase`` to snapshot-authority **only** for missions that verify.

    Per-mission best-effort (research D-03): a mission whose verify fails is left
    un-flipped (``status_phase`` untouched) and named in the summary; other missions
    still flip. Use ``--dry-run`` to preview would-seed counts without writing.

    Exit codes:

    - ``0`` — every visited mission flipped or is already migrated (verify ok, no error)
    - ``1`` — one or more missions failed verify / errored, or ``--mission`` named an
      unknown handle

    Examples:

        spec-kitty migrate backfill-runtime-state --dry-run

        spec-kitty migrate backfill-runtime-state --mission my-mission-01ABCD

        spec-kitty migrate backfill-runtime-state --json
    """
    from specify_cli.cli.selector_resolution import resolve_mission_handle
    from specify_cli.migration.runtime_state_cutover import (
        CutoverResult,
        cutover_mission,
        cutover_repo,
    )

    repo_root = locate_project_root()
    if repo_root is None:
        _error("Could not locate project root. No .kittify/ directory found in any parent directory.")
        raise typer.Exit(1)

    if mission is not None:
        # Route --mission through the canonical handle resolver so mission_id /
        # mid8 / slug all resolve (a raw kitty-specs/<slug> join matches the
        # literal slug only). resolve_mission_handle prints + sys.exit(2)s on an
        # unknown/ambiguous handle.
        resolved = resolve_mission_handle(mission, repo_root, json_mode=json_output)
        results: list[CutoverResult] = [cutover_mission(resolved.feature_dir, dry_run=dry_run)]
    else:
        results = cutover_repo(repo_root, dry_run=dry_run)

    if json_output:
        print(json.dumps(_cutover_payload(results, dry_run=dry_run), indent=2))
    else:
        _print_cutover_summary(results, dry_run=dry_run)

    # Per-mission best-effort (D-03): a live run exits non-zero if any mission
    # failed verify / errored (that mission's status_phase is left untouched).
    # --dry-run is a non-mutating preview: an unseeded corpus verifies "not ok"
    # only because the seeds are not yet written, so a preview never fails the
    # command — the counts + any mismatch are reported for the operator.
    if not dry_run and any(_cutover_failed(r, dry_run=dry_run) for r in results):
        raise typer.Exit(1)


@app.command(name="rebaseline-dossier-hashes")
def rebaseline_dossier_hashes(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit a structured per-mission re-baseline report"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Preview which recorded snapshot hashes would be re-baselined, without writing",
        ),
    ] = False,
) -> None:
    """One-time re-baseline of recorded dossier snapshot hashes (FR-009, WP05).

    Recomputes every recorded ``.kittify/dossiers/<slug>/snapshot-latest.json``
    hash under the canonical definition (WP01/WP02) so content that did not
    change is not flagged divergent after the cutover. Idempotent (snapshots
    already in canonical ``sha256:`` form are skipped) and read-only over source
    artifacts — only the recorded snapshot cache files are written (#2263).

    Exit codes:

    - ``0`` — completed (some snapshots may be reported as errors and skipped)
    - ``1`` — project root could not be located
    """
    from specify_cli.dossier.rebaseline import rebaseline_recorded_snapshots

    repo_root = locate_project_root()
    if repo_root is None:
        _error("Could not locate project root. No .kittify/ directory found in any parent directory.")
        raise typer.Exit(1)

    outcomes = rebaseline_recorded_snapshots(repo_root, dry_run=dry_run)
    changed = [o for o in outcomes if o.changed]
    errored = [o for o in outcomes if o.error]

    if json_output:
        payload = {
            "dry_run": dry_run,
            "summary": {
                "total": len(outcomes),
                "rebaselined": len(changed),
                "skipped": len(outcomes) - len(changed) - len(errored),
                "error": len(errored),
            },
            "results": [
                {
                    "mission_slug": o.mission_slug,
                    "snapshot_path": str(o.snapshot_path),
                    "old_hash": o.old_hash,
                    "new_hash": o.new_hash,
                    "changed": o.changed,
                    "error": o.error,
                }
                for o in outcomes
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        prefix = "(dry-run) " if dry_run else ""
        console.print(
            f"{prefix}Re-baselined {len(changed)} / {len(outcomes)} recorded snapshot(s); {len(errored)} error(s)."
        )
        for o in errored:
            err_console.print(f"[yellow]skip[/yellow] {o.mission_slug}: {o.error}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _error(message: str) -> None:
    """Print an error message to stderr via Rich console."""
    err_console.print(f"[red]Error:[/red] {message}")


def _cutover_failed(result: Any, *, dry_run: bool) -> bool:
    """True iff a cutover result is a genuine failure.

    A hard abort (``MigrationOrderingError`` / backfill error -> ``error`` set) is
    ALWAYS a failure. A not-ok verify is a failure only on a **live** run: under
    ``--dry-run`` the seeds are not written, so the reduced snapshot is expectedly
    empty and ``verify`` is "not ok" pre-seed — a "would seed (verify pending)"
    preview state, NOT a failure (a healthy legacy corpus must report 0 failed).
    """
    if result.error is not None:
        return True
    if dry_run:
        return False
    return result.verify is not None and not result.verify.ok


def _cutover_detail(result: Any) -> str:
    """Human-readable failure detail for a failed cutover result."""
    if result.error is not None:
        return str(result.error)
    if result.verify is not None:
        return "; ".join(result.verify.mismatches)
    return "unknown failure"


def _cutover_payload(results: list[Any], *, dry_run: bool) -> dict[str, Any]:
    """Build the ``--json`` payload for the backfill-runtime-state command.

    ``failed`` / per-mission ``mismatches`` are dry-run-aware: under ``--dry-run`` a
    healthy legacy mission (verify not-ok only because seeds are unwritten) is NOT
    failed and emits no mismatch wall. ``verify_ok`` stays the raw verify value.
    """
    return {
        "dry_run": dry_run,
        "summary": {
            "total": len(results),
            "flipped": len([r for r in results if r.flipped]),
            "would_seed": len([r for r in results if r.seeded_count > 0]),
            "would_flip": len([r for r in results if r.would_flip]),
            "seeded": sum(r.seeded_count for r in results),
            "failed": len([r for r in results if _cutover_failed(r, dry_run=dry_run)]),
        },
        "results": [
            {
                "slug": r.slug,
                "flipped": r.flipped,
                "would_flip": r.would_flip,
                "would_seed": r.seeded_count > 0,
                "seeded_count": r.seeded_count,
                "verify_ok": None if r.verify is None else r.verify.ok,
                "failed": _cutover_failed(r, dry_run=dry_run),
                "mismatches": (
                    list(r.verify.mismatches)
                    if (r.verify is not None and _cutover_failed(r, dry_run=dry_run))
                    else []
                ),
                "error": r.error,
            }
            for r in results
        ],
    }


def _print_cutover_summary(results: list[Any], *, dry_run: bool) -> None:
    """Render the rich summary for the backfill-runtime-state command.

    Dry-run reframes the primary count as "would seed (verify pending)" and never
    prints a Failed wall for verify-pending-pre-seed missions — only genuine hard
    aborts (``error`` set) count as failed under ``--dry-run``.
    """
    failed = [r for r in results if _cutover_failed(r, dry_run=dry_run)]
    active = [r for r in results if not _cutover_failed(r, dry_run=dry_run)]
    migrated = [r for r in active if r.seeded_count > 0]
    skipped = [r for r in active if r.seeded_count == 0]
    seeded = sum(r.seeded_count for r in results)

    prefix = "[dim](dry-run)[/dim] " if dry_run else ""
    primary_label = _LABEL_WOULD_SEED if dry_run else _LABEL_FLIPPED
    console.print(f"\n{prefix}[bold]{_RUNTIME_STATE_SUMMARY_TITLE}[/bold]")
    console.print(f"  Total missions scanned : {len(results)}")
    console.print(f"  {primary_label:<27} : {len(migrated)}")
    console.print(f"  {_LABEL_SKIPPED:<27} : {len(skipped)}")
    console.print(f"  Seed events                 : {seeded}")
    console.print(f"  {_LABEL_FAILED:<27} : {len(failed)}")

    if failed:
        console.print("\n[red]Failed (status_phase left untouched):[/red]")
        for r in failed:
            console.print(f"  [red]{r.slug}:[/red] {_cutover_detail(r)}")

    if dry_run:
        console.print("\n[dim]Dry run — no seeds written; verify runs post-seed on a live run.[/dim]")


def _normalize_lifecycle_payload(results: list[Any], *, dry_run: bool) -> dict[str, Any]:
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


def _print_normalize_lifecycle_summary(results: list[Any], *, dry_run: bool) -> None:
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

    header = (
        "\n[DRY-RUN] Would migrate Spec Kitty runtime state on Windows."
        if dry_run
        else "\nMigrated Spec Kitty runtime state on Windows."
    )
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
