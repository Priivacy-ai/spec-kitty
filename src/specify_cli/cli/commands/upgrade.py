"""Upgrade command implementation for Spec Kitty CLI."""

from __future__ import annotations

import json
import subprocess
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
        return sorted(
            child.relative_to(project_path)
            for child in absolute_path.rglob("*")
            if not child.is_dir()
        )

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

    new_paths = sorted(
        path for path in current_paths if path not in baseline_paths and _is_upgrade_commit_eligible(path, project_path)
    )
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


def upgrade(  # noqa: C901
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompts"),
    target: str | None = typer.Option(None, "--target", help="Target version (defaults to current CLI version)"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed migration information"),
    no_worktrees: bool = typer.Option(False, "--no-worktrees", help="Skip upgrading worktrees"),
) -> None:
    """Upgrade a Spec Kitty project to the current version.

    Detects the project's current version and applies all necessary migrations
    to bring it up to date with the installed CLI version.

    Examples:
        spec-kitty upgrade              # Upgrade to current version
        spec-kitty upgrade --dry-run    # Preview changes
        spec-kitty upgrade --target 0.6.5  # Upgrade to specific version
    """
    if not json_output:
        show_banner()

    project_path = Path.cwd()
    baseline_changed_paths = _git_status_paths(project_path)
    kittify_dir = project_path / ".kittify"
    specify_dir = project_path / ".specify"  # Old name

    # Check if this is a Spec Kitty project
    if not kittify_dir.exists() and not specify_dir.exists():
        if json_output:
            print(json.dumps({"error": "Not a Spec Kitty project"}))
        else:
            console.print("[red]Error:[/red] Not a Spec Kitty project.")
            console.print("[dim]Run 'spec-kitty init' to initialize a project.[/dim]")
        raise typer.Exit(1)

    # Import upgrade system (lazy to avoid circular imports)
    from specify_cli.upgrade.detector import VersionDetector
    from specify_cli.upgrade.registry import MigrationRegistry
    from specify_cli.upgrade.runner import MigrationRunner, validate_upgrade_target

    # Import migrations to register them
    from specify_cli.upgrade import migrations  # noqa: F401

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
    migrations_needed = MigrationRegistry.get_applicable(
        version_for_migration, target_version, project_path=project_path
    )

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

    # Confirm if not dry-run and not forced
    if not dry_run and not force:
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
        force=force,
        include_worktrees=not no_worktrees,
    )

    auto_committed = False
    auto_commit_paths: list[str] = []
    auto_commit_warning: str | None = None
    if result.success and not dry_run:
        auto_committed, auto_commit_paths, auto_commit_warning = _auto_commit_upgrade_changes(
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
            "auto_committed": auto_committed,
            "auto_commit_paths": auto_commit_paths,
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

    console.print()
    if result.success:
        console.print(f"[bold green]Upgrade complete![/bold green] {result.from_version} -> {result.to_version}")
        if auto_committed:
            console.print(f"[cyan]→ Auto-committed upgrade changes ({len(auto_commit_paths)} files)[/cyan]")
    else:
        console.print("[bold red]Upgrade failed.[/bold red]")
        raise typer.Exit(1)


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
