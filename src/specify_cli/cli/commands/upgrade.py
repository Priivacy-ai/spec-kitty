"""Upgrade command implementation for Spec Kitty CLI.

This module exposes ``spec-kitty upgrade`` with the following flag surface
(C-006 — all existing flags preserved, new flags are additive):

Existing flags (preserved unchanged):
  --dry-run           Preview changes without applying.
  --force             Skip confirmation prompts.
  --target VERSION    Target version (defaults to current CLI version).
  --json              Output results as JSON (project-upgrade contract).
  --verbose / -v      Show detailed migration information.
  --no-worktrees      Skip upgrading worktrees.

New flags (WP09):
  --cli               Restrict to CLI guidance only (FR-014).  Works outside
                      any project; skip project-side flow entirely.
  --project           Restrict to current-project compat + migrations (FR-015).
                      Errors when invoked outside a project.
  --yes / -y          Non-interactive confirmation; alias for --force (FR-017).
  --no-nag            Suppress upgrade-nag output explicitly.

Mutual exclusion:
  --cli + --project together → exit 2 (BLOCK_INCOMPATIBLE_FLAGS).

JSON contract (--json with --cli or --project):
  Emits the compat-planner contract from
  ``contracts/compat-planner.json`` (schema_version: 1).  See R-09.

Exit codes (R-08):
  0  ALLOW / ALLOW_WITH_NAG / dry-run always 0
  2  BLOCK_INCOMPATIBLE_FLAGS (--cli + --project)
  4  BLOCK_PROJECT_MIGRATION
  5  BLOCK_CLI_UPGRADE (project too new — not overridable by --yes)
  6  BLOCK_PROJECT_CORRUPT

See also: docs/how-to/install-and-upgrade.md
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli.helpers import console, show_banner
from specify_cli.git.commit_helpers import safe_commit


def _git_status_paths(repo_path: Path) -> set[str] | None:
    """Return git status paths for *repo_path* using porcelain -z output.

    Returns ``None`` when ``git status`` fails (e.g. not a git repo) so
    callers can distinguish "no dirty files" from "unable to determine".
    """
    result = subprocess.run(
        ["git", "status", "--porcelain", "-z"],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    entries = result.stdout.decode("utf-8", errors="replace").split("\0")
    paths: set[str] = set()

    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry or len(entry) < 4:
            continue

        status = entry[:2]
        path = entry[3:]

        # With -z format, renames/copies include a second NUL-separated
        # path.  We take the *destination* (new name); the source (old name)
        # is intentionally discarded because we care about "what exists now".
        if ("R" in status or "C" in status) and i < len(entries) and entries[i]:
            path = entries[i]
            i += 1

        normalized = path.strip().replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]

        if normalized:
            paths.add(normalized)

    return paths


def _is_upgrade_commit_eligible(path: str, project_path: Path) -> bool:
    """Return True when a changed file should be included in upgrade auto-commit."""
    normalized = path.strip().replace("\\", "/")
    if not normalized:
        return False

    # Ignore paths that are outside the repo and root-level files.
    if normalized.startswith("../") or "/" not in normalized:
        return False

    # Never auto-commit ~/.kittify when users run inside their home directory.
    return not (project_path.resolve() == Path.home().resolve() and normalized.startswith(".kittify/"))


def _expand_upgrade_commit_path(project_path: Path, relative_path: str) -> list[Path]:
    """Expand a changed path into the concrete file paths git will stage.

    ``git status --porcelain -z`` may report untracked directories as a single
    path (for example ``.agents/skills/new-skill``). ``git add <dir>`` stages
    the files inside that directory, but ``safe_commit``'s backstop compares the
    staged file paths against the requested path list. Expand directories here
    so the expected set matches what git will actually stage.
    """
    normalized = relative_path.strip().replace("\\", "/")
    absolute_path = project_path / normalized

    if absolute_path.exists() and absolute_path.is_dir() and not absolute_path.is_symlink():
        return sorted(child.relative_to(project_path) for child in absolute_path.rglob("*") if not child.is_dir())

    return [Path(normalized)]


def _prepare_upgrade_commit_files(
    project_path: Path,
    baseline_paths: set[str] | None,
) -> list[Path]:
    """Collect newly changed project-directory files after an upgrade run.

    Returns an empty list when *baseline_paths* is ``None`` (git status
    failed at baseline time) to avoid accidentally committing unrelated work.
    """
    if baseline_paths is None:
        return []

    current_paths = _git_status_paths(project_path)
    if current_paths is None:
        return []

    new_paths = sorted(path for path in current_paths if path not in baseline_paths and _is_upgrade_commit_eligible(path, project_path))
    files_to_commit: list[Path] = []
    seen_paths: set[str] = set()
    for path in new_paths:
        for expanded_path in _expand_upgrade_commit_path(project_path, path):
            normalized = str(expanded_path).replace("\\", "/")
            if normalized in seen_paths:
                continue
            seen_paths.add(normalized)
            files_to_commit.append(Path(normalized))
    return files_to_commit


def _collect_manual_review_paths(migration_results: dict[str, object]) -> list[str]:
    """Return sorted preserved/archive paths that require operator review."""
    manual_review_paths: set[str] = set()
    for result in migration_results.values():
        if not getattr(result, "manual_review_required", False):
            continue
        manual_review_paths.update(getattr(result, "preserved_paths", []))
    return sorted(manual_review_paths)


def _auto_commit_upgrade_changes(
    project_path: Path,
    from_version: str,
    to_version: str,
    baseline_paths: set[str] | None,
) -> tuple[bool, list[str], str | None]:
    """Auto-commit newly introduced project-directory upgrade changes."""
    files_to_commit = _prepare_upgrade_commit_files(project_path, baseline_paths)
    if not files_to_commit:
        return False, [], None

    commit_message = f"chore: apply spec-kitty upgrade changes ({from_version} -> {to_version})"
    commit_success = safe_commit(
        repo_path=project_path,
        files_to_commit=files_to_commit,
        commit_message=commit_message,
        allow_empty=False,
    )
    committed_paths = [str(path).replace("\\", "/") for path in files_to_commit]

    if commit_success:
        return True, committed_paths, None

    return (
        False,
        committed_paths,
        "Could not auto-commit upgrade changes; please review and commit manually.",
    )


# ---------------------------------------------------------------------------
# T035 — --cli mode helper
# ---------------------------------------------------------------------------


def _run_cli_mode(
    *,
    json_output: bool,
    dry_run: bool,
    no_nag: bool,
    latest_version_provider: object = None,
) -> None:
    """Execute the --cli mode: emit CLI guidance without touching the project.

    Builds an Invocation with command_path=("upgrade",), calls compat.plan(),
    and either prints rendered_human (default) or renders_json (--json).

    This path is project-agnostic; it succeeds even outside any Spec Kitty
    project (FR-014).

    Args:
        json_output: When True, emit JSON instead of human text.
        dry_run: Passed through to exit-code logic (dry-run → always exit 0).
        no_nag: When True, set flag_no_nag in the Invocation.
        latest_version_provider: Optional override for tests.
    """
    from specify_cli.compat.planner import Invocation, is_ci_env, plan

    raw_args: tuple[str, ...] = ("--cli",)
    if dry_run:
        raw_args = raw_args + ("--dry-run",)

    # Read the real environment so that CI=1 spec-kitty upgrade --cli
    # correctly suppresses the network call (RISK-3 fix).
    invocation = Invocation(
        command_path=("upgrade",),
        raw_args=raw_args,
        is_help=False,
        is_version=False,
        flag_no_nag=no_nag,
        env_ci=is_ci_env(),
        stdout_is_tty=sys.stdout.isatty(),
    )

    kwargs: dict[str, object] = {}
    if latest_version_provider is not None:
        kwargs["latest_version_provider"] = latest_version_provider

    result = plan(invocation, **kwargs)  # type: ignore[arg-type]

    if json_output:
        exit_code = 0 if dry_run else result.exit_code
        payload = dict(result.rendered_json)
        print(json.dumps(payload, indent=2))
        raise typer.Exit(exit_code)

    if result.rendered_human:
        print(result.rendered_human)

    raise typer.Exit(0)


# ---------------------------------------------------------------------------
# T036 — helpers for project mode (skip CLI nag in output)
# ---------------------------------------------------------------------------


def _is_in_project(project_path: Path) -> bool:
    """Return True when *project_path* appears to be a Spec Kitty project."""
    return (project_path / ".kittify").exists() or (project_path / ".specify").exists()


def _check_project_not_too_new(
    project_path: Path,
    *,
    json_output: bool,
) -> None:
    """Exit 5 if the project schema is newer than this CLI supports.

    CHK037 / A-006: ``--yes`` and ``--force`` do NOT bypass this check.
    A too-new project cannot be migrated downward from the project side;
    the only fix is to upgrade the CLI.  The function always exits 5 on a
    too-new project regardless of ``--dry-run`` (see WP09 T036 spec).

    Args:
        project_path: Path to the current project directory.
        json_output: When True, emit a JSON error payload.
    """
    try:
        from specify_cli.migration.schema_version import (
            MAX_SUPPORTED_SCHEMA,
            get_project_schema_version,
        )

        schema_v = get_project_schema_version(project_path)
        if schema_v is None:
            return  # No schema_version field → LEGACY; handled elsewhere
        if not isinstance(schema_v, int):
            return  # Corrupt; handled by MigrationRunner

        if schema_v > MAX_SUPPORTED_SCHEMA:
            if json_output:
                from specify_cli.compat.planner import Invocation, plan as _plan

                inv = Invocation(
                    command_path=("upgrade",),
                    raw_args=("--project",),
                    is_help=False,
                    is_version=False,
                    flag_no_nag=True,
                    env_ci=False,
                    stdout_is_tty=False,
                )
                result = _plan(inv)
                print(json.dumps(result.rendered_json, indent=2))
            else:
                from specify_cli.compat._detect.install_method import detect_install_method
                from specify_cli.compat.upgrade_hint import build_upgrade_hint

                method = detect_install_method()
                hint = build_upgrade_hint(method)
                hint_str = hint.command if hint.command is not None else hint.note or "Upgrade your CLI."
                console.print(f"[red]Error:[/red] This project uses schema version {schema_v}, but this CLI supports up to schema {MAX_SUPPORTED_SCHEMA}.")
                console.print(f"[cyan]Upgrade the CLI:[/cyan] {hint_str}")
            raise typer.Exit(5)
    except typer.Exit:
        raise
    except Exception:  # noqa: BLE001 — fail-open; let the runner handle other errors
        pass


# ---------------------------------------------------------------------------
# Main upgrade command
# ---------------------------------------------------------------------------


def upgrade(  # noqa: C901
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompts"),
    target: str | None = typer.Option(None, "--target", help="Target version (defaults to current CLI version)"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed migration information"),
    no_worktrees: bool = typer.Option(False, "--no-worktrees", help="Skip upgrading worktrees"),
    # --- WP09 new flags (T034) ---
    cli: bool = typer.Option(False, "--cli", help="Restrict to CLI guidance only; works outside any project (FR-014)"),
    project: bool = typer.Option(False, "--project", help="Restrict to current-project compat + migrations (FR-015)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Non-interactive confirmation; alias for --force (FR-017)"),
    no_nag: bool = typer.Option(False, "--no-nag", help="Suppress upgrade-nag output explicitly"),
) -> None:
    """Upgrade a Spec Kitty project to the current version.

    Detects the project's current version and applies all necessary migrations
    to bring it up to date with the installed CLI version.

    **New flags (WP09)**:
      ``--cli``     Emit CLI upgrade guidance only.  No project detection;
                    succeeds outside any project (FR-014).
      ``--project`` Run project migrations only; suppresses CLI nag.
                    Errors outside a project.
      ``--yes``/``-y``  Non-interactive confirmation (alias for ``--force``).
                        Does NOT bypass schema-incompatibility blocks (CHK037/A-006).
      ``--no-nag``  Suppress upgrade-nag banner even when a CLI update exists.

    Mutual exclusion: ``--cli`` and ``--project`` together exit 2.

    **Exit codes** (R-08):
      0  Success / ALLOW / ALLOW_WITH_NAG / any ``--dry-run``
      2  ``--cli --project`` flag conflict
      4  Project migration required (BLOCK_PROJECT_MIGRATION)
      5  Project is too new for this CLI (BLOCK_CLI_UPGRADE) — not bypassable
      6  Project metadata corrupt (BLOCK_PROJECT_CORRUPT)
      1  General error

    See also: ``docs/how-to/install-and-upgrade.md``

    Examples:
        spec-kitty upgrade              # Upgrade to current version
        spec-kitty upgrade --dry-run    # Preview changes
        spec-kitty upgrade --target 0.6.5  # Upgrade to specific version
        spec-kitty upgrade --cli        # Show CLI upgrade hint, no project needed
        spec-kitty upgrade --project    # Project migrations only
        spec-kitty upgrade --yes        # Non-interactive (same as --force)
        spec-kitty upgrade --dry-run --json  # Machine-readable plan
    """
    # T034 — mutual exclusion check
    if cli and project:
        console.print("[red]Error:[/red] --cli and --project are mutually exclusive.")
        console.print("[dim]Use --cli for CLI guidance only, or --project for project migrations only.[/dim]")
        raise typer.Exit(2)

    # T034 — --yes aliases --force (both remain functional)
    confirm = yes or force

    # T035 — --cli mode: project-agnostic CLI guidance
    if cli:
        _run_cli_mode(
            json_output=json_output,
            dry_run=dry_run,
            no_nag=no_nag,
        )
        return  # _run_cli_mode always raises typer.Exit; belt-and-suspenders

    # --- Project-mode and default upgrade flow ---

    # T036 — in --project mode, fail fast outside a project
    project_path = Path.cwd()
    kittify_dir = project_path / ".kittify"
    specify_dir = project_path / ".specify"  # Old name

    if not kittify_dir.exists() and not specify_dir.exists():
        if project:
            # --project was explicit; surface a clear "no project" error
            if json_output:
                print(json.dumps({"error": "Not a Spec Kitty project", "case": "project_not_initialized"}))
            else:
                console.print("[red]Error:[/red] Not a Spec Kitty project.")
                console.print("[dim]Run 'spec-kitty init' to initialize a project.[/dim]")
                console.print("[dim]Tip: use 'spec-kitty upgrade --cli' for CLI guidance outside a project.[/dim]")
            raise typer.Exit(1)
        else:
            # Default mode (bare `spec-kitty upgrade` outside any project):
            # FR-014 says this should fall through to CLI guidance behavior
            # rather than erroring.  Only error when --project is explicit.
            _run_cli_mode(
                json_output=json_output,
                dry_run=dry_run,
                no_nag=no_nag,
            )
            return  # _run_cli_mode always raises typer.Exit; belt-and-suspenders

    # CHK037 / A-006 — Check if project is too new for this CLI.
    # This check runs BEFORE the existing upgrade flow so that
    # --yes / --force do NOT bypass the block.
    # The upgrade command is SAFE (remediation path), so the planner's
    # decide() would ALLOW it, but the command itself must refuse to
    # run migrations against a project with schema > MAX_SUPPORTED.
    _check_project_not_too_new(project_path, json_output=json_output)

    # T037 — --json with compat-planner contract (for --project or default with --json)
    # When --json is passed (with or without --dry-run), we emit the contract
    # from contracts/compat-planner.json in addition to (or instead of) the
    # old project-upgrade JSON.  For --project mode, the planner is always
    # consulted; for default mode, the planner runs only when --json is used.
    if json_output and (project or dry_run):
        # Emit compat-planner contract
        _run_planner_json(
            dry_run=dry_run,
            no_nag=no_nag,
        )
        return  # _run_planner_json always raises typer.Exit

    if not json_output:
        show_banner()

    baseline_changed_paths = _git_status_paths(project_path)

    # Import upgrade system (lazy to avoid circular imports)
    from specify_cli.upgrade.detector import VersionDetector
    from specify_cli.upgrade.registry import MigrationRegistry
    from specify_cli.upgrade.runner import MigrationRunner, validate_upgrade_target

    from specify_cli.upgrade.migrations import auto_discover_migrations

    auto_discover_migrations()

    # Detect current version
    detector = VersionDetector(project_path)
    current_version = detector.detect_version()

    # Determine target version
    if target is None:
        from specify_cli import __version__

        target_version = __version__
    else:
        target_version = target

    validation_error = validate_upgrade_target(current_version, target_version)
    if validation_error:
        if json_output:
            print(
                json.dumps(
                    {
                        "status": "failed",
                        "current_version": current_version,
                        "target_version": target_version,
                        "success": False,
                        "errors": [validation_error],
                        "warnings": [],
                        "auto_committed": False,
                        "auto_commit_paths": [],
                    }
                )
            )
        else:
            console.print(f"[red]Error:[/red] {validation_error}")
        raise typer.Exit(1)

    if not json_output:
        console.print(f"[cyan]Current version:[/cyan] {current_version}")
        console.print(f"[cyan]Target version:[/cyan]  {target_version}")
        console.print()

    # Get needed migrations
    # Handle "unknown" version by treating it as very old (0.0.0)
    version_for_migration = "0.0.0" if current_version == "unknown" else current_version
    migrations_needed = MigrationRegistry.get_applicable(version_for_migration, target_version, project_path=project_path)

    if not migrations_needed:
        auto_committed = False
        auto_commit_paths: list[str] = []
        auto_commit_warning: str | None = None

        # Still stamp the version even when no migrations are needed
        from specify_cli.upgrade.metadata import ProjectMetadata

        metadata = ProjectMetadata.load(kittify_dir)
        if metadata and metadata.version != target_version and not dry_run:
            metadata.version = target_version
            metadata.last_upgraded_at = datetime.now()
            metadata.save(kittify_dir)

        if not dry_run:
            auto_committed, auto_commit_paths, auto_commit_warning = _auto_commit_upgrade_changes(
                project_path=project_path,
                from_version=current_version,
                to_version=target_version,
                baseline_paths=baseline_changed_paths,
            )

        if json_output:
            warnings = [auto_commit_warning] if auto_commit_warning else []
            print(
                json.dumps(
                    {
                        "status": "up_to_date",
                        "current_version": current_version,
                        "target_version": target_version,
                        "auto_committed": auto_committed,
                        "auto_commit_paths": auto_commit_paths,
                        "warnings": warnings,
                    }
                )
            )
        else:
            console.print("[green]Project is already up to date![/green]")
            if auto_committed:
                console.print(f"[cyan]→ Auto-committed upgrade changes ({len(auto_commit_paths)} files)[/cyan]")
            if auto_commit_warning:
                console.print(f"[yellow]Warning:[/yellow] {auto_commit_warning}")
        return

    # Show migration plan
    if not json_output:
        table = Table(title="Migration Plan", show_lines=False, header_style="bold cyan")
        table.add_column("Migration", style="bright_white")
        table.add_column("Description", style="dim")
        table.add_column("Target", style="cyan")

        for migration in migrations_needed:
            table.add_row(
                migration.migration_id,
                migration.description,
                migration.target_version,
            )

        console.print(table)
        console.print()

        if verbose:
            # Show detection results
            console.print("[dim]Detection results:[/dim]")
            for migration in migrations_needed:
                detected = migration.detect(project_path)
                can_apply, reason = migration.can_apply(project_path)
                status = "[green]ready[/green]" if detected and can_apply else "[yellow]skipped[/yellow]"
                console.print(f"  {migration.migration_id}: {status}")
                if not can_apply and reason:
                    console.print(f"    [dim]{reason}[/dim]")
            console.print()

    # T034 — confirm uses `confirm` (yes or force) instead of bare `force`
    if not dry_run and not confirm:
        proceed = typer.confirm(
            f"Apply {len(migrations_needed)} migration(s)?",
            default=True,
        )
        if not proceed:
            console.print("[yellow]Upgrade cancelled.[/yellow]")
            raise typer.Exit(0)

    # Run migrations
    runner = MigrationRunner(project_path, console)
    result = runner.upgrade(
        target_version,
        dry_run=dry_run,
        force=confirm,  # pass the unified confirm flag
        include_worktrees=not no_worktrees,
    )

    auto_committed = False
    auto_commit_paths_list: list[str] = []
    auto_commit_warning: str | None = None
    manual_review_paths = _collect_manual_review_paths(result.migration_results)
    if result.success and not dry_run:
        if manual_review_paths:
            auto_commit_warning = "Skipped auto-commit because the upgrade preserved customized files that require manual review."
            result.warnings.append(auto_commit_warning)
        else:
            auto_committed, auto_commit_paths_list, auto_commit_warning = _auto_commit_upgrade_changes(
                project_path=project_path,
                from_version=result.from_version,
                to_version=result.to_version,
                baseline_paths=baseline_changed_paths,
            )
            if auto_commit_warning:
                result.warnings.append(auto_commit_warning)

    if json_output:
        # Build detailed migrations array
        migrations_detail = []
        for migration in migrations_needed:
            if migration.migration_id in result.migrations_applied:
                status = "applied"
            elif migration.migration_id in result.migrations_skipped:
                status = "skipped"
            else:
                status = "pending"
            migrations_detail.append(
                {
                    "id": migration.migration_id,
                    "description": migration.description,
                    "target_version": migration.target_version,
                    "status": status,
                    "manual_review_required": (
                        result.migration_results.get(migration.migration_id).manual_review_required if migration.migration_id in result.migration_results else False
                    ),
                    "preserved_paths": (
                        result.migration_results.get(migration.migration_id).preserved_paths if migration.migration_id in result.migration_results else []
                    ),
                }
            )

        # Surface per-migration schema-shaped JSON reports (e.g. the
        # m_3_2_3_unified_bundle contract-shaped payload). Each migration
        # emits its report as a single JSON string inside
        # ``MigrationResult.changes_made[0]``; decode it so operators see a
        # structured object rather than an opaque string.
        migration_reports: dict[str, object] = {}
        for mid, mres in result.migration_results.items():
            if not mres.changes_made:
                continue
            payload = mres.changes_made[0]
            try:
                migration_reports[mid] = json.loads(payload)
            except (TypeError, ValueError):
                # Migration emitted a non-JSON change string; skip rather
                # than break the operator contract.
                continue

        output = {
            "status": "success" if result.success else "failed",
            "current_version": result.from_version,
            "target_version": result.to_version,
            "dry_run": result.dry_run,
            "migrations": migrations_detail,
            "migrations_applied": result.migrations_applied,
            "migrations_skipped": result.migrations_skipped,
            "migration_reports": migration_reports,
            "success": result.success,
            "errors": result.errors,
            "warnings": result.warnings,
            "manual_review_required": bool(manual_review_paths),
            "manual_review_paths": manual_review_paths,
            "auto_committed": auto_committed,
            "auto_commit_paths": auto_commit_paths_list,
        }
        print(json.dumps(output))
        return

    # Display results
    console.print()

    if result.dry_run:
        console.print(
            Panel(
                "[yellow]DRY RUN[/yellow] - No changes were made",
                border_style="yellow",
            )
        )

    if result.migrations_applied:
        console.print("[green]Migrations applied:[/green]")
        for m in result.migrations_applied:
            console.print(f"  [green]✓[/green] {m}")

    if result.migrations_skipped:
        console.print("[dim]Migrations skipped (already applied or not needed):[/dim]")
        for m in result.migrations_skipped:
            console.print(f"  [dim]○[/dim] {m}")

    if result.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for w in result.warnings:
            console.print(f"  [yellow]![/yellow] {w}")

    if result.errors:
        console.print("[red]Errors:[/red]")
        for e in result.errors:
            console.print(f"  [red]✗[/red] {e}")

    if manual_review_paths:
        console.print("[yellow]Manual review required:[/yellow]")
        for path in manual_review_paths:
            console.print(f"  [yellow]![/yellow] {path}")

    console.print()
    if result.success:
        console.print(f"[bold green]Upgrade complete![/bold green] {result.from_version} -> {result.to_version}")
        if auto_committed:
            console.print(f"[cyan]→ Auto-committed upgrade changes ({len(auto_commit_paths_list)} files)[/cyan]")
    else:
        console.print("[bold red]Upgrade failed.[/bold red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# T037 — planner JSON helper (emits compat-planner.json contract)
# ---------------------------------------------------------------------------


def _run_planner_json(
    *,
    dry_run: bool,
    no_nag: bool,
    latest_version_provider: object = None,
) -> None:
    """Emit the compat-planner JSON contract to stdout and raise typer.Exit.

    Suppresses all human output.  Exit code follows R-08 unless ``dry_run``
    is True, in which case exit code is always 0.

    Args:
        dry_run: When True, always exit 0.
        no_nag: Suppress nag flag passed to the Invocation.
        latest_version_provider: Optional override for tests.
    """
    from specify_cli.compat.planner import Invocation, is_ci_env, plan

    raw_args: tuple[str, ...] = ("--project",)
    if dry_run:
        raw_args = raw_args + ("--dry-run",)

    # Read the real environment so that CI=1 spec-kitty upgrade --json
    # correctly suppresses the network call (RISK-3 fix).
    invocation = Invocation(
        command_path=("upgrade",),
        raw_args=raw_args,
        is_help=False,
        is_version=False,
        flag_no_nag=no_nag,
        env_ci=is_ci_env(),
        stdout_is_tty=sys.stdout.isatty(),
    )

    kwargs: dict[str, object] = {}
    if latest_version_provider is not None:
        kwargs["latest_version_provider"] = latest_version_provider

    result = plan(invocation, **kwargs)  # type: ignore[arg-type]

    exit_code = 0 if dry_run else result.exit_code
    print(json.dumps(result.rendered_json, indent=2))
    raise typer.Exit(exit_code)


def list_legacy_features() -> None:
    """List legacy worktrees blocking 0.11.0 upgrade."""
    from specify_cli.tasks_support import find_repo_root
    from specify_cli.upgrade.migrations.m_0_11_0_workspace_per_wp import (
        detect_legacy_worktrees,
    )

    repo_root = find_repo_root()
    legacy = detect_legacy_worktrees(repo_root)

    if not legacy:
        console.print("[green]✓[/green] No legacy worktrees found")
        console.print("Project is ready for 0.11.0 upgrade")
        return

    console.print(f"[yellow]Legacy worktrees found:[/yellow] {len(legacy)}\n")
    for worktree in legacy:
        console.print(f"  - {worktree.name}")

    console.print("\n[cyan]Action required:[/cyan]")
    console.print("  Complete: spec-kitty merge <feature>")
    console.print("  OR Delete: git worktree remove .worktrees/<feature>")


__all__ = ["upgrade", "list_legacy_features"]
