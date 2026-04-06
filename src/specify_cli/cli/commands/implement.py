"""Implement command - allocate the lane worktree for a work package."""

from __future__ import annotations

import functools
import json
import re
import subprocess
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import typer
from rich.console import Console
from typing_extensions import Annotated

from specify_cli.cli import StepTracker
from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.vcs import VCSBackend
from specify_cli.mission_metadata import set_vcs_lock
from specify_cli.frontmatter import update_fields
from specify_cli.git import safe_commit
from specify_cli.lanes.implement_support import create_lane_workspace
from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError, require_lanes_json
from specify_cli.tasks_support import TaskCliError, find_repo_root

console = Console()
_WP_ID_RE = re.compile(r"^WP\d{2}$", re.IGNORECASE)


def _get_wp_lane_from_event_log(feature_dir: Path, wp_id: str) -> str:
    """Get the canonical WP lane, defaulting to planned when unbootstrapped."""
    try:
        from specify_cli.status.reducer import reduce
        from specify_cli.status.store import read_events

        events = read_events(feature_dir)
        if events:
            snapshot = reduce(events)
            state = snapshot.work_packages.get(wp_id)
            if state:
                return str(state.get("lane", "planned"))
    except Exception:
        pass
    return "planned"


def _json_safe_output(func):
    """Ensure --json mode stays machine-readable on both success and failure."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        json_output = bool(kwargs.get("json_output", False))
        previous_quiet = console.quiet
        previous_file = console.file
        capture_buffer: StringIO | None = None
        if json_output:
            capture_buffer = StringIO()
            console.file = capture_buffer
            console.quiet = False

        wp_id = kwargs.get("wp_id")
        if wp_id is None and args:
            wp_id = args[0]

        try:
            return func(*args, **kwargs)
        except typer.Exit as exc:
            if json_output and getattr(exc, "exit_code", 1):
                lines = [
                    line.rstrip()
                    for line in (capture_buffer.getvalue() if capture_buffer else "").splitlines()
                    if line.strip()
                ]
                summary = "\n".join(lines[-20:]).strip() if lines else "implement command failed"
                payload = {"status": "error", "error": summary or "implement command failed"}
                if wp_id:
                    payload["wp_id"] = str(wp_id)
                print(json.dumps(payload))
            raise
        except Exception as exc:  # pragma: no cover - defensive
            if json_output:
                payload = {"status": "error", "error": str(exc)}
                if wp_id:
                    payload["wp_id"] = str(wp_id)
                print(json.dumps(payload))
            raise typer.Exit(1)
        finally:
            console.quiet = previous_quiet
            console.file = previous_file

    return wrapper


def detect_feature_context(feature_flag: str | None = None) -> tuple[str, str]:
    """Require an explicit feature slug and return (number, slug)."""
    import re as _re

    from specify_cli.core.paths import require_explicit_feature

    try:
        slug = require_explicit_feature(feature_flag, command_hint="--mission <slug>")
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    match = _re.match(r"^(\d{3})-", slug)
    if not match:
        console.print(f"[red]Error:[/red] Invalid feature slug format: {slug}\nExpected format: ###-feature-name (for example, 010-lane-only-runtime)")
        raise typer.Exit(1)

    return match.group(1), slug


def find_wp_file(repo_root: Path, mission_slug: str, wp_id: str) -> Path:
    """Find the markdown file for a work package."""
    tasks_dir = repo_root / "kitty-specs" / mission_slug / "tasks"
    if not tasks_dir.exists():
        raise FileNotFoundError(f"Tasks directory not found: {tasks_dir}")

    normalized_wp_id = wp_id.strip().upper()
    if not _WP_ID_RE.fullmatch(normalized_wp_id):
        raise FileNotFoundError(f"Invalid work package ID: {wp_id}. Expected format WP## (for example, WP01).")

    wp_name_re = re.compile(rf"^{re.escape(normalized_wp_id)}(?:[-_.].+)?\.md$", re.IGNORECASE)
    wp_files = sorted(path for path in tasks_dir.glob("WP*.md") if wp_name_re.match(path.name))
    if not wp_files:
        raise FileNotFoundError(f"WP file not found for {normalized_wp_id} in {tasks_dir}")
    return wp_files[0]


def resolve_feature_target_branch(mission_slug: str, repo_root: Path) -> str:
    """Resolve the feature's configured target branch from metadata."""
    from specify_cli.core.git_ops import resolve_target_branch

    resolution = resolve_target_branch(
        mission_slug=mission_slug,
        repo_path=repo_root,
        respect_current=True,
    )
    return resolution.target


def _ensure_planning_artifacts_committed_git(
    repo_root: Path,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    planning_branch: str,
    *,
    auto_commit: bool,
) -> None:
    """Ensure planning artifacts are committed on the feature planning branch."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    current_branch = result.stdout.strip() if result.returncode == 0 else ""

    result = subprocess.run(
        ["git", "status", "--porcelain", str(feature_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return

    files_to_commit: list[str] = []
    for line in result.stdout.strip().splitlines():
        if len(line) >= 4:
            files_to_commit.append(line[3:].strip())

    if not files_to_commit:
        return

    console.print("\n[cyan]Planning artifacts not committed:[/cyan]")
    for file_path in files_to_commit:
        console.print(f"  {file_path}")

    if current_branch != planning_branch:
        console.print(f"\n[red]Error:[/red] Planning artifacts must be committed on {planning_branch}.")
        console.print(f"Current branch: {current_branch}")
        raise typer.Exit(1)

    if not auto_commit:
        console.print("\n[yellow]Auto-commit disabled.[/yellow] Commit planning artifacts first:")
        console.print(f"  git add -f {feature_dir}")
        console.print(f'  git commit -m "chore: planning artifacts for {mission_slug}"')
        raise typer.Exit(1)

    console.print(f"\n[cyan]Auto-committing planning artifacts to {planning_branch}...[/cyan]")
    result = subprocess.run(
        ["git", "add", "-f", str(feature_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        console.print("[red]Error:[/red] Failed to stage planning artifacts")
        console.print(result.stderr)
        raise typer.Exit(1)

    commit_msg = f"chore: planning artifacts for {mission_slug}\n\nAuto-committed by spec-kitty before creating the lane worktree for {wp_id}"
    result = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-m", commit_msg],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        console.print("[red]Error:[/red] Failed to commit planning artifacts")
        console.print(result.stderr)
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Planning artifacts committed to {planning_branch}")


def _ensure_vcs_in_meta(feature_dir: Path, repo_root: Path) -> VCSBackend:
    """Ensure VCS is selected and locked in meta.json."""
    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        console.print(f"[red]Error:[/red] meta.json not found in {feature_dir}")
        console.print("Run /spec-kitty.specify first to create feature structure")
        raise typer.Exit(1)

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        console.print(f"[red]Error:[/red] Invalid JSON in meta.json: {exc}")
        raise typer.Exit(1)

    if "vcs" not in meta:
        now_iso = datetime.now(timezone.utc).isoformat()
        set_vcs_lock(feature_dir, vcs_type="git", locked_at=now_iso)
        console.print("[cyan]→ VCS locked to git in meta.json[/cyan]")

    return VCSBackend.GIT


@_json_safe_output
@require_main_repo
def implement(
    wp_id: str = typer.Argument(..., help="Work package ID (for example, WP01)"),
    feature: str = typer.Option(None, "--feature", help="Mission slug (for example, 001-my-feature)"),
    auto_commit: Annotated[
        bool | None,
        typer.Option("--auto-commit/--no-auto-commit", help="Auto-commit status and planning changes (default: from project config)"),
    ] = None,
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
) -> None:
    """Allocate or reuse the lane worktree for a work package."""
    from specify_cli.core.agent_config import get_auto_commit_default
    from specify_cli.core.dependency_graph import parse_wp_dependencies
    from specify_cli.sync.events import emit_wp_status_changed

    tracker = StepTracker(f"Implement {wp_id}")
    tracker.add("detect", "Detect feature context")
    tracker.add("validate", "Validate planning state")
    tracker.add("create", "Allocate lane worktree")
    console.print()

    tracker.start("detect")
    try:
        repo_root = find_repo_root()
        if auto_commit is None:
            auto_commit = get_auto_commit_default(repo_root)
        _feature_number, mission_slug = detect_feature_context(feature)
        feature_dir = repo_root / "kitty-specs" / mission_slug
        wp_file = find_wp_file(repo_root, mission_slug, wp_id)
        declared_deps = parse_wp_dependencies(wp_file)
        tracker.complete("detect", f"Feature: {mission_slug}")
    except (TaskCliError, FileNotFoundError, typer.Exit) as exc:
        tracker.error("detect", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)

    tracker.start("validate")
    try:
        planning_branch = resolve_feature_target_branch(mission_slug, repo_root)
        _ensure_planning_artifacts_committed_git(
            repo_root=repo_root,
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            planning_branch=planning_branch,
            auto_commit=bool(auto_commit),
        )
        lanes_manifest = require_lanes_json(feature_dir)
        lane = lanes_manifest.lane_for_wp(wp_id)
        if lane is None:
            raise ValueError(f"{wp_id} is not assigned to any lane in lanes.json")
        tracker.complete("validate", f"Lane: {lane.lane_id}")
    except (CorruptLanesError, MissingLanesError, ValueError, typer.Exit) as exc:
        tracker.error("validate", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)
    except Exception as exc:
        tracker.error("validate", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)

    tracker.start("create")
    try:
        vcs_backend = _ensure_vcs_in_meta(feature_dir, repo_root)
        result = create_lane_workspace(
            repo_root=repo_root,
            mission_slug=mission_slug,
            wp_id=wp_id,
            wp_file=wp_file,
            lanes_manifest=lanes_manifest,
            declared_deps=declared_deps,
            vcs_backend_value=vcs_backend.value,
        )
        workspace_path = result.workspace_path
        branch_name = result.branch_name

        if result.is_reuse:
            tracker.complete("create", f"Reused lane {result.lane_id}: {workspace_path.relative_to(repo_root)}")
        else:
            tracker.complete("create", f"Lane {result.lane_id}: {workspace_path.relative_to(repo_root)}")
        console.print(tracker.render())
        console.print(f"[cyan]→ Mission branch: {result.mission_branch}[/cyan]")
        console.print(f"[cyan]→ Lane branch: {result.branch_name}[/cyan]")
    except typer.Exit:
        console.print(tracker.render())
        raise
    except Exception as exc:
        tracker.error("create", f"lane allocation failed: {exc}")
        console.print(tracker.render())
        console.print(f"\n[red]Error:[/red] Lane worktree allocation failed: {exc}")
        raise typer.Exit(1)

    try:
        import os

        current_lane = _get_wp_lane_from_event_log(feature_dir, wp_id)
        if current_lane == "planned":
            shell_pid = str(os.getppid())
            commit_msg = f"chore: {wp_id} claimed for implementation"

            update_fields(wp_file, {"shell_pid": shell_pid})

            if auto_commit:
                meta_file = feature_dir / "meta.json"
                config_file = repo_root / ".kittify" / "config.yaml"
                files_to_commit = [wp_file.resolve()]
                if meta_file.exists():
                    files_to_commit.append(meta_file.resolve())
                if config_file.exists():
                    files_to_commit.append(config_file.resolve())

                commit_success = safe_commit(
                    repo_path=repo_root,
                    files_to_commit=files_to_commit,
                    commit_message=commit_msg,
                    allow_empty=True,
                )
                if commit_success:
                    console.print(f"[cyan]→ {wp_id} moved to 'doing'[/cyan]")
                else:
                    console.print("[yellow]Warning:[/yellow] Could not auto-commit lane change")
            else:
                console.print(f"[cyan]→ {wp_id} moved to 'doing' (auto-commit disabled, changes staged only)[/cyan]")

            try:
                emit_wp_status_changed(
                    wp_id=wp_id,
                    from_lane=current_lane,
                    to_lane="in_progress",
                    mission_slug=mission_slug,
                )
            except Exception as exc:
                console.print(f"[yellow]Warning:[/yellow] Could not emit WPStatusChanged: {exc}")
    except Exception as exc:
        console.print(f"[yellow]Warning:[/yellow] Could not update WP status: {exc}")

    if json_output:
        workspace_rel = str(workspace_path.relative_to(repo_root))
        print(
            json.dumps(
                {
                    "workspace": workspace_rel,
                    "workspace_path": workspace_rel,
                    "branch": branch_name,
                    "feature": mission_slug,
                    "wp_id": wp_id,
                    "lane_id": result.lane_id,
                    "status": "created",
                }
            )
        )
        return

    console.print(f"\n[bold green]✓ Lane worktree ready[/bold green]")
    console.print()
    console.print("[bold yellow]" + "=" * 72 + "[/bold yellow]")
    console.print("[bold yellow]CRITICAL: Change to the lane worktree before editing files[/bold yellow]")
    console.print("[bold yellow]" + "=" * 72 + "[/bold yellow]")
    console.print()
    console.print(f"  [bold]cd {workspace_path}[/bold]")
    console.print()
    console.print("[dim]All file edits, writes, and commits MUST happen in this directory.[/dim]")
    console.print("[dim]Writing to the main repository instead of the lane worktree is a critical error.[/dim]")


__all__ = ["_ensure_vcs_in_meta", "detect_feature_context", "find_wp_file", "implement"]
