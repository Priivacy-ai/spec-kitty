"""Sync commands - workspace synchronization and connection status.

This module provides two groups of sync functionality:
1. Workspace sync: updates workspace with changes from base branch
2. Connection status: shows WebSocket sync connection state
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from specify_cli.core.vcs import (
    ChangeInfo,
    ConflictInfo,
    SyncResult,
    SyncStatus,
    VCSBackend,
    get_vcs,
)

from specify_cli.sync.queue import QueueStats
from specify_cli.sync.feature_flags import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)

console = Console()


@dataclass
class _DossierUploadRecord:
    """Content push payload for one indexed dossier artifact."""

    mission_slug: str
    artifact_path: str
    content_hash: str
    content_body: str


@dataclass
class _DossierEmissionSummary:
    """Aggregated dossier emission counters for CLI reporting."""

    features: int = 0
    indexed_events: int = 0
    missing_events: int = 0
    snapshot_events: int = 0
    upload_records: list[_DossierUploadRecord] = field(default_factory=list)


def humanize_timedelta(td: "timedelta") -> str:
    """Convert a timedelta into a concise human-readable string.

    Examples: '2s', '45s', '3m 12s', '2h 5m', '1d 4h', '3d'
    """
    from datetime import timedelta  # noqa: F811 - local re-import for type narrowing

    total_seconds = int(td.total_seconds())
    if total_seconds < 0:
        return "0s"

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        if hours > 0:
            return f"{days}d {hours}h"
        return f"{days}d"
    if hours > 0:
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"
    if minutes > 0:
        if seconds > 0:
            return f"{minutes}m {seconds}s"
        return f"{minutes}m"
    return f"{seconds}s"


def format_queue_health(stats: QueueStats, target_console: Console) -> None:
    """Render queue health metrics as Rich panels/tables.

    Displays:
    - Summary panel with queue depth, retried count, and oldest event age
    - Retry distribution table (bucketed)
    - Top event types table (up to 5)

    Args:
        stats: Aggregate queue statistics from OfflineQueue.get_queue_stats()
        target_console: Rich Console to print to (allows testing with captured output)
    """
    # --- Summary panel ---
    summary_lines: list[str] = []
    summary_lines.append(f"[bold]Queue Depth:[/bold] {stats.total_queued:,} event(s)")
    summary_lines.append(f"[bold]Retried:[/bold]    {stats.total_retried:,}")
    if stats.oldest_event_age is not None:
        age_str = humanize_timedelta(stats.oldest_event_age)
        summary_lines.append(f"[bold]Oldest Event:[/bold] {age_str} ago")

    target_console.print(
        Panel(
            "\n".join(summary_lines),
            title="Queue Health",
            border_style="cyan",
            expand=False,
        )
    )

    # --- Retry distribution ---
    if stats.retry_distribution:
        retry_table = Table(
            title="Retry Distribution",
            show_header=True,
            header_style="bold",
            show_lines=False,
            expand=False,
        )
        retry_table.add_column("Bucket", style="dim")
        retry_table.add_column("Count", justify="right")

        # Ensure deterministic bucket order
        bucket_order = ["0 retries", "1-3 retries", "4+ retries"]
        for bucket in bucket_order:
            if bucket in stats.retry_distribution:
                retry_table.add_row(bucket, str(stats.retry_distribution[bucket]))

        target_console.print(retry_table)

    # --- Top event types ---
    if stats.top_event_types:
        type_table = Table(
            title="Top Event Types",
            show_header=True,
            header_style="bold",
            show_lines=False,
            expand=False,
        )
        type_table.add_column("Event Type", style="cyan")
        type_table.add_column("Count", justify="right")

        for event_type, count in stats.top_event_types:
            type_table.add_row(event_type, str(count))

        target_console.print(type_table)


def _resolve_feature_dirs(repo_root: Path, feature_slugs: Optional[list[str]]) -> list[Path]:
    """Resolve feature slugs to directories, defaulting to all numeric `kitty-specs` entries."""
    kitty_specs_dir = repo_root / "kitty-specs"
    if not kitty_specs_dir.is_dir():
        return []

    if feature_slugs:
        resolved: list[Path] = []
        for feature_slug in feature_slugs:
            feature_dir = kitty_specs_dir / feature_slug
            if feature_dir.is_dir():
                resolved.append(feature_dir)
        return resolved

    discovered: list[Path] = []
    for child in sorted(kitty_specs_dir.iterdir()):
        if not child.is_dir():
            continue
        if re.match(r"^\d{3}-", child.name):
            discovered.append(child)
    return discovered


def _emit_dossier_for_feature(feature_dir: Path, step_id: Optional[str]) -> _DossierEmissionSummary:
    """Index one feature and emit MissionDossier* events to the sync queue."""
    from specify_cli.dossier.events import (
        emit_artifact_indexed,
        emit_artifact_missing,
        emit_snapshot_computed,
    )
    from specify_cli.dossier.indexer import Indexer
    from specify_cli.dossier.manifest import ManifestRegistry
    from specify_cli.dossier.snapshot import compute_snapshot, save_snapshot
    from specify_cli.mission import get_feature_mission_key

    summary = _DossierEmissionSummary(features=1)
    mission_key = get_feature_mission_key(feature_dir)

    indexer = Indexer(manifest_registry=ManifestRegistry)
    dossier = indexer.index_feature(feature_dir=feature_dir, mission_type=mission_key, step_id=step_id)
    snapshot = compute_snapshot(dossier)
    save_snapshot(snapshot, feature_dir)

    manifest_version = "1"
    if isinstance(dossier.manifest, dict):
        manifest_version = str(dossier.manifest.get("manifest_version", "1"))

    for artifact in dossier.artifacts:
        if artifact.is_present:
            emitted = emit_artifact_indexed(
                feature_slug=dossier.feature_slug,
                artifact_key=artifact.artifact_key,
                artifact_class=artifact.artifact_class,
                relative_path=artifact.relative_path,
                content_hash_sha256=artifact.content_hash_sha256,
                size_bytes=artifact.size_bytes,
                wp_id=artifact.wp_id,
                step_id=artifact.step_id,
                required_status=artifact.required_status,
                mission_slug=dossier.feature_slug,
                manifest_version=manifest_version,
                actor="spec-kitty-cli",
            )
            if emitted:
                summary.indexed_events += 1

            artifact_path = feature_dir / artifact.relative_path
            try:
                content_body = artifact_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                # Non-text or unreadable artifacts remain metadata-only in SaaS.
                continue
            summary.upload_records.append(
                _DossierUploadRecord(
                    mission_slug=dossier.feature_slug,
                    artifact_path=artifact.relative_path,
                    content_hash=f"sha256:{artifact.content_hash_sha256}",
                    content_body=content_body,
                )
            )
            continue

        if artifact.required_status != "required":
            continue

        reason_code = artifact.error_reason or "not_found"
        if reason_code not in {"not_found", "unreadable", "invalid_format", "deleted_after_scan"}:
            reason_code = "not_found"

        emitted = emit_artifact_missing(
            feature_slug=dossier.feature_slug,
            artifact_key=artifact.artifact_key,
            artifact_class=artifact.artifact_class,
            expected_path_pattern=artifact.relative_path,
            reason_code=reason_code,
            reason_detail=None,
            blocking=True,
            mission_slug=dossier.feature_slug,
            manifest_version=manifest_version,
            step_id=artifact.step_id,
            actor="spec-kitty-cli",
        )
        if emitted:
            summary.missing_events += 1

    emitted_snapshot = emit_snapshot_computed(
        feature_slug=dossier.feature_slug,
        parity_hash_sha256=snapshot.parity_hash_sha256,
        total_artifacts=snapshot.total_artifacts,
        required_artifacts=snapshot.required_artifacts,
        required_present=snapshot.required_present,
        required_missing=snapshot.required_missing,
        optional_artifacts=snapshot.optional_artifacts,
        optional_present=snapshot.optional_present,
        completeness_status=snapshot.completeness_status,
        snapshot_id=snapshot.snapshot_id,
        mission_slug=dossier.feature_slug,
        manifest_version=manifest_version,
        actor="spec-kitty-cli",
    )
    if emitted_snapshot:
        summary.snapshot_events += 1

    return summary


def _push_dossier_content(upload_records: list[_DossierUploadRecord]) -> tuple[int, int, int]:
    """Push artifact bodies to SaaS sidecar endpoint using JWT auth."""
    from specify_cli.sync.auth import AuthClient, AuthenticationError
    from specify_cli.sync.config import SyncConfig

    if not upload_records:
        return (0, 0, 0)

    auth = AuthClient()
    token = auth.get_access_token()
    if not token:
        raise AuthenticationError("Not authenticated. Run `spec-kitty auth login` before pushing dossier content.")

    try:
        server_url = auth.server_url
    except AuthenticationError:
        server_url = SyncConfig().get_server_url()

    endpoint = f"{server_url.rstrip('/')}/api/v1/dossier/content/"
    headers = {"Authorization": f"Bearer {token}"}

    pushed = 0
    pending = 0
    failed = 0

    with httpx.Client(timeout=15.0) as client:
        for upload in upload_records:
            response = client.post(
                endpoint,
                headers=headers,
                json={
                    "content_hash": upload.content_hash,
                    "hash_algorithm": "sha256",
                    "content_body": upload.content_body,
                    "mission_slug": upload.mission_slug,
                    "artifact_path": upload.artifact_path,
                },
            )
            if response.status_code in (200, 201):
                pushed += 1
            elif response.status_code == 404:
                # Index rows are not present yet (or sync failed); retry later.
                pending += 1
            else:
                failed += 1

    return (pushed, pending, failed)


# Create a Typer app for sync subcommands
app = typer.Typer(
    help="Synchronization commands",
    no_args_is_help=True,
)


def _detect_workspace_context() -> tuple[Path, str | None]:
    """Detect current workspace and feature context.

    Returns:
        Tuple of (workspace_path, feature_slug)
        If not in a workspace, returns (cwd, None)
    """
    cwd = Path.cwd()

    # Check if we're in a .worktrees directory
    parts = cwd.parts
    for i, part in enumerate(parts):
        if part == ".worktrees" and i + 1 < len(parts):
            # Found a worktree path like: /repo/.worktrees/010-feature-WP01
            workspace_name = parts[i + 1]
            # Extract feature slug from workspace name (###-feature-WP##)
            match = re.match(r"^(\d{3}-[a-zA-Z0-9-]+)-WP\d+$", workspace_name)
            if match:
                return cwd, match.group(1)

    # Try to detect from git branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            cwd=cwd,
        )
        if result.returncode == 0:
            branch_name = result.stdout.strip()
            # Check if branch matches WP pattern (###-feature-WP##)
            match = re.match(r"^(\d{3}-[a-zA-Z0-9-]+)-WP\d+$", branch_name)
            if match:
                return cwd, match.group(1)
    except (FileNotFoundError, OSError):
        pass

    # Not in a recognized workspace
    return cwd, None


def _display_changes_integrated(changes: list[ChangeInfo]) -> None:
    """Display changes that were integrated during sync."""
    if not changes:
        return

    console.print(f"\n[cyan]Changes integrated ({len(changes)}):[/cyan]")
    for change in changes[:5]:  # Show first 5 changes
        short_id = change.commit_id[:7] if change.commit_id else "unknown"
        # Truncate message to 50 chars
        msg = change.message[:50] + "..." if len(change.message) > 50 else change.message
        console.print(f"  • [dim]{short_id}[/dim] {msg}")

    if len(changes) > 5:
        console.print(f"  [dim]... and {len(changes) - 5} more[/dim]")


def _display_conflicts(conflicts: list[ConflictInfo]) -> None:
    """Display conflicts with actionable details.

    Shows:
    - File path
    - Line ranges (if available)
    - Conflict type
    - Resolution hints
    """
    if not conflicts:
        return

    console.print(f"\n[yellow]Conflicts ({len(conflicts)} files):[/yellow]")

    # Create a table for better formatting
    table = Table(show_header=True, header_style="bold yellow", show_lines=False)
    table.add_column("File", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Lines", style="dim")

    for conflict in conflicts:
        # Format line ranges
        if conflict.line_ranges:
            lines = ", ".join(f"{start}-{end}" for start, end in conflict.line_ranges)
        else:
            lines = "entire file"

        table.add_row(
            str(conflict.file_path),
            conflict.conflict_type.value,
            lines,
        )

    console.print(table)

    # Show resolution hints
    console.print("\n[dim]To resolve conflicts:[/dim]")
    console.print("[dim]  1. Edit the conflicted files to resolve markers[/dim]")
    console.print("[dim]  2. Continue your work (jj) or commit resolution (git)[/dim]")


def _git_repair(workspace_path: Path) -> bool:
    """Attempt git workspace recovery.

    This is a best-effort recovery that tries:
    1. Abort any in-progress rebase/merge
    2. Reset to HEAD

    Returns:
        True if recovery succeeded, False otherwise

    Note: This may lose uncommitted work.
    """
    try:
        # First, try to abort any in-progress operations
        for abort_cmd in [
            ["git", "rebase", "--abort"],
            ["git", "merge", "--abort"],
            ["git", "cherry-pick", "--abort"],
        ]:
            subprocess.run(
                abort_cmd,
                cwd=workspace_path,
                capture_output=True,
                check=False,
                timeout=10,
            )

        # Reset to HEAD (keeping changes in working tree)
        result = subprocess.run(
            ["git", "reset", "--mixed", "HEAD"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )

        return result.returncode == 0

    except (subprocess.TimeoutExpired, OSError):
        return False


def _jj_repair(workspace_path: Path) -> bool:
    """Attempt jj workspace recovery via operation undo.

    Jujutsu has much better recovery capabilities via the operation log.
    This function tries to undo the last operation.

    Returns:
        True if recovery succeeded, False otherwise
    """
    try:
        # Try to undo the last operation
        result = subprocess.run(
            ["jj", "undo"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )

        if result.returncode == 0:
            return True

        # If undo fails, try to update the workspace
        result = subprocess.run(
            ["jj", "workspace", "update-stale"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )

        return result.returncode == 0

    except (subprocess.TimeoutExpired, OSError):
        return False


@app.command(name="workspace")
def sync_workspace(
    repair: bool = typer.Option(
        False,
        "--repair",
        "-r",
        help="Attempt workspace recovery (may lose uncommitted work)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed sync output",
    ),
) -> None:
    """Synchronize workspace with upstream changes.

    Updates the current workspace with changes from its base branch or parent.
    This is equivalent to:
    - git: `git rebase <base-branch>`
    - jj: `jj workspace update-stale` + auto-rebase

    Key difference between VCS backends:
    - git: Sync may FAIL on conflicts (must resolve before continuing)
    - jj: Sync always SUCCEEDS (conflicts stored, resolve later)

    Examples:
        # Sync current workspace
        spec-kitty sync workspace

        # Sync with verbose output
        spec-kitty sync workspace --verbose

        # Attempt recovery from broken state
        spec-kitty sync workspace --repair
    """
    console.print()

    # Detect workspace context
    workspace_path, feature_slug = _detect_workspace_context()

    if feature_slug is None:
        console.print("[yellow]⚠ Not in a recognized workspace[/yellow]")
        console.print("Run this command from a worktree directory:")
        console.print("  cd .worktrees/<feature>-WP##/")
        raise typer.Exit(1)

    console.print(f"[cyan]Workspace:[/cyan] {workspace_path.name}")

    # Get VCS implementation
    try:
        vcs = get_vcs(workspace_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to detect VCS: {e}")
        raise typer.Exit(1)

    console.print(f"[cyan]Backend:[/cyan] git")
    console.print()

    # Handle repair mode
    if repair:
        console.print("[yellow]Attempting workspace recovery...[/yellow]")
        console.print("[dim]Note: This may lose uncommitted work[/dim]")
        console.print()

        if vcs.backend == VCSBackend.JUJUTSU:
            success = _jj_repair(workspace_path)
        else:
            success = _git_repair(workspace_path)

        if success:
            console.print("[green]✓ Recovery successful[/green]")
            console.print("Workspace state has been reset.")
        else:
            console.print("[red]✗ Recovery failed[/red]")
            console.print("Manual intervention may be required.")
            console.print()
            if vcs.backend == VCSBackend.GIT:
                console.print("[dim]Try these commands manually:[/dim]")
                console.print("  git status")
                console.print("  git rebase --abort")
                console.print("  git reset --hard HEAD")
            else:
                console.print("[dim]Try these commands manually:[/dim]")
                console.print("  jj status")
                console.print("  jj op log")
                console.print("  jj undo")
            raise typer.Exit(1)

        return

    # Perform sync
    console.print("[cyan]Syncing workspace...[/cyan]")

    result: SyncResult = vcs.sync_workspace(workspace_path)

    # Display result based on status
    if result.status == SyncStatus.UP_TO_DATE:
        console.print("\n[green]✓ Already up to date[/green]")
        if result.message:
            console.print(f"[dim]{result.message}[/dim]")

    elif result.status == SyncStatus.SYNCED:
        stats_parts = []
        if result.files_updated > 0:
            stats_parts.append(f"{result.files_updated} updated")
        if result.files_added > 0:
            stats_parts.append(f"{result.files_added} added")
        if result.files_deleted > 0:
            stats_parts.append(f"{result.files_deleted} deleted")

        stats = ", ".join(stats_parts) if stats_parts else "no file changes"
        console.print(f"\n[green]✓ Synced[/green] - {stats}")

        if verbose:
            _display_changes_integrated(result.changes_integrated)

        if result.message:
            console.print(f"[dim]{result.message}[/dim]")

    elif result.status == SyncStatus.CONFLICTS:
        # jj: This means sync succeeded but there are conflicts to resolve
        console.print("\n[yellow]⚠ Synced with conflicts[/yellow]")

        if vcs.backend == VCSBackend.JUJUTSU:
            console.print("[dim]Conflicts are stored in the commit.[/dim]")
            console.print("[dim]You can continue working and resolve later.[/dim]")
        else:
            console.print("[dim]You must resolve conflicts before continuing.[/dim]")

        _display_conflicts(result.conflicts)

        if verbose:
            _display_changes_integrated(result.changes_integrated)

    elif result.status == SyncStatus.FAILED:
        console.print(f"\n[red]✗ Sync failed[/red]")
        if result.message:
            console.print(f"[dim]{result.message}[/dim]")

        # Show conflicts if any
        if result.conflicts:
            _display_conflicts(result.conflicts)

        console.print()
        console.print("[dim]Try:[/dim]")
        console.print("  spec-kitty sync workspace --repair")
        raise typer.Exit(1)

    console.print()


def _check_server_connection(server_url: str) -> tuple[str, str]:
    """Probe the batch endpoint using the user's real auth token.

    Returns:
        Tuple of (rich-formatted status string, detail message).
    """
    if not is_saas_sync_enabled():
        return (
            "[dim]Disabled[/dim]",
            saas_sync_disabled_message(),
        )

    import httpx
    from specify_cli.sync.auth import AuthClient, AuthenticationError, CredentialStore

    # Step 1: Check if credentials exist at all
    store = CredentialStore()
    if not store.exists():
        return (
            "[yellow]Not authenticated[/yellow]",
            "Run `spec-kitty auth login` to connect.",
        )

    # Step 2: Get a valid access token (with auto-refresh if expired)
    auth = AuthClient()
    try:
        access_token = auth.get_access_token()
    except AuthenticationError:
        access_token = None
    except Exception as exc:
        return (
            "[red]Error[/red]",
            f"Authentication probe failed: {str(exc)[:80]}",
        )

    if not access_token:
        # Access token expired and refresh also failed
        return (
            "[yellow]Session expired[/yellow]",
            "Run `spec-kitty auth login` to re-authenticate.",
        )

    # Step 3: Probe the batch endpoint with an empty events list
    batch_url = f"{server_url.rstrip('/')}/api/v1/events/batch/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = b'{"events": []}'

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(batch_url, content=payload, headers=headers)

        if response.status_code == 200:
            return (
                "[green]Connected[/green]",
                "Server reachable, authentication valid.",
            )
        elif response.status_code == 401:
            return (
                "[yellow]Authentication failed[/yellow]",
                "Run `spec-kitty auth login` to re-authenticate.",
            )
        elif response.status_code == 403:
            return (
                "[yellow]Permission denied[/yellow]",
                "Check team membership for this project.",
            )
        else:
            return (
                "[yellow]Unexpected[/yellow]",
                f"Server returned HTTP {response.status_code}.",
            )
    except httpx.TimeoutException:
        return (
            "[red]Unreachable[/red]",
            "Connection timeout (server may be down). Events will be queued for later sync.",
        )
    except httpx.ConnectError:
        return (
            "[red]Unreachable[/red]",
            "Connection refused. Events will be queued for later sync.",
        )
    except Exception as e:
        return (
            "[red]Error[/red]",
            f"Probe failed: {str(e)[:80]}",
        )


@app.command(name="server")
def sync_server(
    url: str | None = typer.Argument(
        None,
        help="Sync server URL to set (must be https://...)",
    ),
) -> None:
    """Show or set sync server URL.

    Examples:
        spec-kitty sync server
        spec-kitty sync server https://spec-kitty-dev.fly.dev
    """
    from specify_cli.sync.config import SyncConfig

    config = SyncConfig()
    if url is None:
        console.print(f"Server URL: [cyan]{config.get_server_url()}[/cyan]")
        console.print(f"Config File: [dim]{config.config_file}[/dim]")
        return

    normalized_url = url.strip().rstrip("/")
    parsed = urlparse(normalized_url)
    if parsed.scheme != "https" or not parsed.netloc:
        console.print(
            "[red]Error:[/red] Invalid server URL. Use a full HTTPS URL, "
            "for example: https://spec-kitty-dev.fly.dev"
        )
        raise typer.Exit(1)

    config.set_server_url(normalized_url)
    console.print(f"[green]✓[/green] Sync server set to [cyan]{normalized_url}[/cyan]")
    console.print(
        "[dim]If you switched environments, run "
        "'spec-kitty auth login --force' to refresh credentials.[/dim]"
    )


@app.command(name="dossier")
def sync_dossier(
    feature: Optional[list[str]] = typer.Option(
        None,
        "--feature",
        "-f",
        help="Feature slug to index (repeatable). Defaults to all kitty-specs features.",
    ),
    step_id: Optional[str] = typer.Option(
        None,
        "--step-id",
        help="Optional mission step for step-aware completeness checks.",
    ),
    sync_events: bool = typer.Option(
        True,
        "--sync-events/--no-sync-events",
        help="Upload emitted MissionDossier events immediately after indexing.",
    ),
    push_content: bool = typer.Option(
        True,
        "--push-content/--no-push-content",
        help="Push artifact markdown bodies after event sync.",
    ),
    strict: bool = typer.Option(
        True,
        "--strict/--no-strict",
        help="Exit non-zero if any dossier stage fails.",
    ),
) -> None:
    """Index feature artifacts and publish MissionDossier data to SaaS."""
    from specify_cli.sync.background import get_sync_service
    from specify_cli.sync.batch import format_sync_summary
    from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR, is_saas_sync_enabled, saas_sync_disabled_message
    from specify_cli.sync.auth import AuthenticationError
    from specify_cli.tasks_support import TaskCliError, find_repo_root

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    feature_dirs = _resolve_feature_dirs(repo_root, feature)
    if not feature_dirs:
        console.print("[yellow]No feature directories found to index.[/yellow]")
        if strict:
            raise typer.Exit(1)
        return

    aggregate = _DossierEmissionSummary()
    emission_failures = 0

    for feature_dir in feature_dirs:
        try:
            summary = _emit_dossier_for_feature(feature_dir=feature_dir, step_id=step_id)
        except Exception as exc:
            emission_failures += 1
            console.print(f"[red]Failed:[/red] {feature_dir.name} ({exc})")
            continue

        aggregate.features += summary.features
        aggregate.indexed_events += summary.indexed_events
        aggregate.missing_events += summary.missing_events
        aggregate.snapshot_events += summary.snapshot_events
        aggregate.upload_records.extend(summary.upload_records)
        console.print(
            f"[green]Indexed[/green] {feature_dir.name}: "
            f"{summary.indexed_events} indexed, "
            f"{summary.missing_events} missing, "
            f"{summary.snapshot_events} snapshot"
        )

    console.print(
        f"[cyan]Dossier events queued:[/cyan] "
        f"{aggregate.indexed_events + aggregate.missing_events + aggregate.snapshot_events}"
    )

    sync_error_count = 0
    if sync_events:
        if not is_saas_sync_enabled():
            console.print(f"[yellow]{saas_sync_disabled_message()}[/yellow]")
            console.print(f"[dim]Set {SAAS_SYNC_ENV_VAR}=1 to enable upload.[/dim]")
            sync_error_count = 1
        else:
            service = get_sync_service()
            queue_size = service.queue.size()
            if queue_size > 0:
                console.print(f"[cyan]Syncing[/cyan] {queue_size} queued event(s)...")
                result = service.sync_now()
                sync_error_count = result.error_count
                summary = format_sync_summary(result)
                for line in summary.split("\n"):
                    if line.startswith("  "):
                        console.print(f"  [yellow]{line.strip()}[/yellow]")
                    else:
                        console.print(
                            f"[green]Synced:[/green] {result.synced_count}  "
                            f"[dim]Duplicates:[/dim] {result.duplicate_count}  "
                            f"[red]Errors:[/red] {result.error_count}"
                        )
            else:
                console.print("[dim]Queue is empty after dossier indexing.[/dim]")

    pushed = pending = failed = 0
    if push_content and aggregate.upload_records:
        if sync_events and sync_error_count > 0:
            console.print("[yellow]Skipping content push because event sync reported errors.[/yellow]")
            failed = 1
        else:
            try:
                pushed, pending, failed = _push_dossier_content(aggregate.upload_records)
            except AuthenticationError as exc:
                console.print(f"[red]Content push auth failed:[/red] {exc}")
                failed = len(aggregate.upload_records)
            except httpx.HTTPError as exc:
                console.print(f"[red]Content push failed:[/red] {exc}")
                failed = len(aggregate.upload_records)
            console.print(
                f"[cyan]Dossier content push:[/cyan] "
                f"stored={pushed} pending={pending} failed={failed}"
            )

    if strict and (emission_failures > 0 or sync_error_count > 0 or failed > 0):
        raise typer.Exit(1)


@app.command()
def now(
    report: Optional[Path] = typer.Option(
        None,
        "--report",
        help="Export per-event failure details to a JSON file",
    ),
    strict: bool = typer.Option(
        True,
        "--strict/--no-strict",
        help="Exit non-zero on sync errors (default: strict)",
    ),
) -> None:
    """Trigger immediate sync of all queued events.

    Drains the offline queue completely, uploading events to the server
    in batches of 1000 until the queue is empty or all remaining events
    have exceeded their retry limit.

    Examples:
        spec-kitty sync now
        spec-kitty sync now --report failures.json
        spec-kitty sync now --no-strict
    """
    from specify_cli.sync.background import get_sync_service
    from specify_cli.sync.batch import format_sync_summary, write_failure_report

    if not is_saas_sync_enabled():
        console.print(f"[yellow]{saas_sync_disabled_message()}[/yellow]")
        console.print(f"[dim]Set {SAAS_SYNC_ENV_VAR}=1 to enable upload.[/dim]")
        return

    service = get_sync_service()
    queue_size = service.queue.size()

    if queue_size == 0:
        console.print("[dim]Queue is empty, nothing to sync.[/dim]")
        return

    console.print(f"Syncing {queue_size} queued event(s)...")
    result = service.sync_now()

    # Print actionable summary instead of bare counts
    summary = format_sync_summary(result)
    for line in summary.split("\n"):
        if line.startswith("  "):
            console.print(f"  [yellow]{line.strip()}[/yellow]")
        else:
            console.print(
                f"[green]Synced:[/green] {result.synced_count}  "
                f"[dim]Duplicates:[/dim] {result.duplicate_count}  "
                f"[red]Errors:[/red] {result.error_count}"
            )

    # Write failure report if requested and there are failures
    if report and result.failed_results:
        write_failure_report(report, result)
        console.print(f"\n[cyan]Failure report written to {report}[/cyan]")
    elif report and not result.failed_results:
        console.print("\n[dim]No failures to report.[/dim]")

    # Strict exit: fail on sync errors or unauthenticated non-empty queue
    if strict:
        if result.error_count > 0:
            raise typer.Exit(1)
        # Detect auth-missing: queue was non-empty but nothing progressed
        if queue_size > 0 and result.synced_count == 0 and result.duplicate_count == 0 and result.error_count == 0:
            console.print("[red]Strict mode:[/red] queue non-empty but no events processed (likely not authenticated)")
            raise typer.Exit(1)


@app.command()
def status(
    check_connection: bool = typer.Option(
        False,
        "--check",
        "-c",
        help="Test connection to server (may be slow if server is unreachable)",
    ),
) -> None:
    """Show sync queue status, connection state, and auth info.

    Displays:
    - Offline queue size
    - Connection / emitter status
    - Last sync timestamp
    - Auth status
    - Server URL configuration

    Use --check to test actual connectivity (adds 3s timeout if server unreachable).

    Examples:
        # Show status (fast)
        spec-kitty sync status

        # Test connection to server
        spec-kitty sync status --check
    """
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.events import get_emitter
    from specify_cli.sync.background import get_sync_service

    console.print()
    console.print("[cyan]Spec Kitty Sync Status[/cyan]")
    console.print()

    # Load configuration
    config = SyncConfig()
    server_url = config.get_server_url()
    saas_enabled = is_saas_sync_enabled()

    emitter = get_emitter()
    service = get_sync_service()

    # Display status
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")

    # Queue size
    queue_size = service.queue.size()
    queue_color = "green" if queue_size == 0 else "yellow"
    table.add_row("Queue", f"[{queue_color}]{queue_size} event(s)[/{queue_color}]")

    # Feature flag
    if saas_enabled:
        table.add_row("SaaS Sync", "[green]Enabled[/green]")
    else:
        table.add_row("SaaS Sync", f"[yellow]Disabled[/yellow] ({SAAS_SYNC_ENV_VAR}=1)")

    # Connection status
    conn_status = emitter.get_connection_status()
    conn_color = "green" if conn_status == "Connected" else "yellow"
    table.add_row("Connection", f"[{conn_color}]{conn_status}[/{conn_color}]")

    # Last sync
    if service.last_sync:
        table.add_row("Last Sync", service.last_sync.strftime("%Y-%m-%d %H:%M:%S UTC"))
    else:
        table.add_row("Last Sync", "[dim]Never[/dim]")

    # Background service
    bg_status = "[green]Running[/green]" if service.is_running else "[dim]Stopped[/dim]"
    table.add_row("Background", bg_status)

    if service.consecutive_failures > 0:
        table.add_row("Failures", f"[yellow]{service.consecutive_failures} consecutive[/yellow]")

    # Auth status
    if saas_enabled:
        auth_ok = emitter.auth.is_authenticated()
        auth_text = "[green]Authenticated[/green]" if auth_ok else "[yellow]Not authenticated[/yellow]"
    else:
        auth_text = "[dim]Disabled by feature flag[/dim]"
    table.add_row("Auth", auth_text)

    # Server URL
    table.add_row("Server URL", server_url)
    table.add_row("Config File", str(config.config_file))

    # Optionally test connection if --check flag is provided
    if check_connection:
        connection_status, connection_note = _check_server_connection(server_url)
        table.add_row("Ping", connection_status)
        if connection_note:
            table.add_row("", f"[dim]{connection_note}[/dim]")

    console.print(table)
    console.print()

    # --- Queue health section (T022/T023) ---
    queue_stats = service.queue.get_queue_stats()
    if queue_stats.total_queued > 0:
        format_queue_health(queue_stats, console)
        console.print()
    else:
        console.print("[green]Queue empty -- all events synced.[/green]")
        console.print()

    if not check_connection:
        console.print("[dim]Use 'spec-kitty sync status --check' to test connectivity.[/dim]")
        console.print()


@app.command()
def diagnose(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON instead of Rich table",
    ),
) -> None:
    """Validate queued events locally against the event schema.

    Reads all pending events from the offline queue and validates each one
    against the Pydantic Event model and per-event-type payload rules.

    Valid events are reported as passing; malformed events show specific
    field errors grouped by error category.

    Examples:
        spec-kitty sync diagnose
        spec-kitty sync diagnose --json
    """
    import json as json_mod

    from specify_cli.sync.diagnose import diagnose_events
    from specify_cli.sync.queue import OfflineQueue

    queue = OfflineQueue()
    pending = queue.drain_queue(limit=queue.MAX_QUEUE_SIZE)

    if not pending:
        if json_output:
            console.print(json_mod.dumps({"total": 0, "valid": 0, "invalid": 0, "results": []}))
        else:
            console.print("[green]No pending events in queue.[/green]")
        return

    results = diagnose_events(pending)

    valid_count = sum(1 for r in results if r.valid)
    invalid_count = sum(1 for r in results if not r.valid)

    if json_output:
        output = {
            "total": len(results),
            "valid": valid_count,
            "invalid": invalid_count,
            "results": [
                {
                    "event_id": r.event_id,
                    "event_type": r.event_type,
                    "valid": r.valid,
                    "errors": r.errors,
                    "error_category": r.error_category,
                }
                for r in results
            ],
        }
        console.print(json_mod.dumps(output, indent=2))
        return

    # Rich output
    console.print()
    console.print(
        f"Validated [cyan]{len(results)}[/cyan] event(s): "
        f"[green]{valid_count} valid[/green], "
        f"[red]{invalid_count} invalid[/red]"
    )

    # Show valid events (brief)
    for r in results:
        if r.valid:
            console.print(f"  [green]VALID[/green]   {r.event_id} ({r.event_type})")

    # Show invalid events (detailed)
    for r in results:
        if not r.valid:
            category_label = f" [{r.error_category}]" if r.error_category else ""
            console.print(
                f"\n  [red]INVALID[/red] {r.event_id} ({r.event_type}){category_label}"
            )
            for err in r.errors:
                console.print(f"    - {err}")

    console.print()


__all__ = ["app"]
