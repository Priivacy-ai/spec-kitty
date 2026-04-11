"""Implement command - allocate the lane worktree for a work package."""

from __future__ import annotations

import functools
import json
import re
import subprocess
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console

from specify_cli.cli import StepTracker
from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.vcs import VCSBackend
from specify_cli.mission_metadata import resolve_mission_identity, set_vcs_lock
from specify_cli.frontmatter import FrontmatterError, update_fields
from specify_cli.git import safe_commit
from specify_cli.lanes.implement_support import create_lane_workspace
from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError, require_lanes_json
from specify_cli.status.emit import emit_status_transition
from specify_cli.status.models import Lane
from specify_cli.tasks_support import TaskCliError, find_repo_root
from specify_cli.workspace_context import resolve_workspace_for_wp
from specify_cli.cli.commands.agent.tasks import _collect_status_artifacts

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
                return Lane(state.get("lane", Lane.PLANNED))
    except Exception:  # noqa: S110 — best-effort lane lookup, fallback is safe
        pass
    return Lane.PLANNED


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
                lines = [line.rstrip() for line in (capture_buffer.getvalue() if capture_buffer else "").splitlines() if line.strip()]
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
            raise typer.Exit(1) from exc
        finally:
            console.quiet = previous_quiet
            # Reset _file to None so the console uses sys.stdout dynamically.
            # Restoring previous_file can leave the console pointing at a closed
            # pytest capsys buffer when tests run in sequence.
            console._file = None

    return wrapper


def detect_feature_context(
    mission_flag: str | None = None,
    feature_flag: str | None = None,
    repo_root: Path | None = None,
) -> tuple[str, str]:
    """Require an explicit mission slug and return (number, slug).

    Uses the canonical mission resolver (resolve_mission_handle) when
    repo_root is supplied, falling back to bare slug parsing otherwise.
    The repo_root is always available in the callers that matter.
    """
    import re as _re

    raw_handle = mission_flag or feature_flag
    if raw_handle is None:
        console.print("[red]Error:[/red] --mission <slug> is required")
        raise typer.Exit(1)

    if repo_root is not None:
        # Use canonical resolver — handles ambiguity, mid8, full ULID, etc.
        resolved = resolve_mission_handle(raw_handle, repo_root)
        slug = resolved.mission_slug
    else:
        # Bare-slug fallback for callers without a repo_root (e.g., unit tests).
        slug = raw_handle

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


def _validate_base_ref(repo_root: Path, base_ref: str) -> str:
    """Validate that a base ref resolves locally and return its full SHA.

    Raises typer.Exit(1) with a clear error message if the ref is unknown.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--verify", base_ref],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        console.print(f"[red]Error:[/red] Base ref '{base_ref}' does not resolve. Try 'git fetch' or 'git branch -a' to see available refs.")
        raise typer.Exit(1)
    return result.stdout.strip()


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


def _ensure_vcs_in_meta(feature_dir: Path, _repo_root: Path) -> VCSBackend:
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
        raise typer.Exit(1) from exc

    if "vcs" not in meta:
        now_iso = datetime.now(UTC).isoformat()
        set_vcs_lock(feature_dir, vcs_type="git", locked_at=now_iso)
        console.print("[cyan]→ VCS locked to git in meta.json[/cyan]")

    return VCSBackend.GIT


def _run_recover_mode(
    _wp_id: str,
    mission: str | None,
    feature: str | None,
    json_output: bool,
) -> None:
    """Run crash recovery for the given mission.

    Orchestrates scan + worktree/context/status reconciliation + reporting.
    The _wp_id argument is accepted but ignored for recovery -- all WPs in
    the mission are scanned.
    """
    from rich.table import Table

    from specify_cli.lanes.recovery import run_recovery, scan_recovery_state

    try:
        repo_root = find_repo_root()
        _feature_number, mission_slug = detect_feature_context(mission, feature, repo_root=repo_root)
    except (TaskCliError, typer.Exit) as exc:
        if json_output:
            print(json.dumps({"status": "error", "error": str(exc)}))
        raise typer.Exit(1) from None

    # First, show what we found
    states = scan_recovery_state(repo_root, mission_slug)
    needs_recovery = [s for s in states if s.recovery_action != "no_action"]

    if not needs_recovery:
        if json_output:
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "message": "No crashed implementation sessions found.",
                        "recovered_wps": [],
                        "worktrees_recreated": 0,
                        "transitions_emitted": 0,
                        "errors": [],
                    }
                )
            )
        else:
            console.print("[green]No crashed implementation sessions found.[/green]")
        return

    if not json_output:
        table = Table(title="Recovery Scan Results")
        table.add_column("WP", style="cyan")
        table.add_column("Lane", style="blue")
        table.add_column("Branch", style="dim")
        table.add_column("Worktree", style="green")
        table.add_column("Context", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Action", style="bold")

        for s in needs_recovery:
            table.add_row(
                s.wp_id,
                s.lane_id,
                s.branch_name,
                "yes" if s.worktree_exists else "[red]NO[/red]",
                "yes" if s.context_exists else "[red]NO[/red]",
                s.status_lane,
                s.recovery_action,
            )
        console.print(table)
        console.print()

    # Run recovery
    report = run_recovery(repo_root, mission_slug)

    if json_output:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "recovered_wps": report.recovered_wps,
                    "worktrees_recreated": report.worktrees_recreated,
                    "transitions_emitted": report.transitions_emitted,
                    "errors": report.errors,
                }
            )
        )
    else:
        console.print("[bold green]Recovery complete[/bold green]")
        console.print(f"  WPs recovered: {', '.join(report.recovered_wps) or 'none'}")
        console.print(f"  Worktrees recreated: {report.worktrees_recreated}")
        console.print(f"  Contexts recreated: {report.contexts_recreated}")
        console.print(f"  Status transitions emitted: {report.transitions_emitted}")
        if report.errors:
            console.print("  [red]Errors:[/red]")
            for err in report.errors:
                console.print(f"    - {err}")


@_json_safe_output
@require_main_repo
def implement(  # noqa: C901 — orchestration function, complexity inherent
    wp_id: str = typer.Argument(..., help="Work package ID (for example, WP01)"),
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug (for example, 001-my-feature)")] = None,
    feature: Annotated[str | None, typer.Option("--feature", hidden=True, help="(deprecated) Use --mission")] = None,
    auto_commit: Annotated[
        bool | None,
        typer.Option("--auto-commit/--no-auto-commit", help="Auto-commit status and planning changes (default: from project config)"),
    ] = None,
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    recover: bool = typer.Option(False, "--recover", help="Recover from crashed implementation session"),
    base: Annotated[
        str | None,
        typer.Option(
            "--base",
            help=(
                "Explicit base ref for the lane workspace (default: auto-detect). "
                "Use this when upstream dependency branches have been merged-and-deleted "
                "and you want to start from the current target branch tip, e.g. --base main."
            ),
        ),
    ] = None,
) -> None:
    """Internal — allocate or reuse the lane worktree for a work package.

    This command is internal infrastructure, used by ``spec-kitty agent action implement``
    for workspace creation. It is not the canonical user-facing implementation path for
    spec-kitty 3.1.1.

    Canonical user workflow::

      spec-kitty next --agent <name> --mission <slug>   (loop entry)
      spec-kitty agent action implement <WP> --agent <name>  (per-WP verb)

    This command remains available as a compatibility surface for direct callers.
    See FR-503 and D-4 in the 3.1.1 spec.
    """
    from specify_cli.core.agent_config import get_auto_commit_default
    from specify_cli.core.dependency_graph import parse_wp_dependencies
    from specify_cli.sync.events import emit_wp_status_changed

    if recover:
        _run_recover_mode(wp_id, mission, feature, json_output)
        return

    tracker = StepTracker(f"Implement {wp_id}")
    tracker.add("detect", "Detect feature context")
    tracker.add("validate", "Validate planning state")
    tracker.add("create", "Resolve execution workspace")
    console.print()

    tracker.start("detect")
    try:
        repo_root = find_repo_root()
        if auto_commit is None:
            auto_commit = get_auto_commit_default(repo_root)
        _feature_number, mission_slug = detect_feature_context(mission, feature, repo_root=repo_root)
        feature_dir = repo_root / "kitty-specs" / mission_slug
        wp_file = find_wp_file(repo_root, mission_slug, wp_id)
        declared_deps = parse_wp_dependencies(wp_file)
        tracker.complete("detect", f"Feature: {mission_slug}")
    except (TaskCliError, FileNotFoundError, FrontmatterError, ValidationError, typer.Exit) as exc:
        tracker.error("detect", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1) from exc

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
        resolved_workspace = resolve_workspace_for_wp(repo_root, mission_slug, wp_id)

        lanes_manifest = None
        lane = None
        from specify_cli.lanes.compute import PLANNING_LANE_ID
        if resolved_workspace.lane_id != PLANNING_LANE_ID:
            lanes_manifest = require_lanes_json(feature_dir)
            lane = lanes_manifest.lane_for_wp(wp_id)
            if lane is None:
                raise ValueError(f"{wp_id} is not assigned to any lane in lanes.json")
            tracker.complete("validate", f"Lane: {lane.lane_id}")
        else:
            tracker.complete("validate", "Execution: repository root planning workspace")
    except (CorruptLanesError, MissingLanesError, ValueError, typer.Exit) as exc:
        tracker.error("validate", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1) from exc
    except Exception as exc:
        tracker.error("validate", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1) from exc

    tracker.start("create")
    try:
        vcs_backend = _ensure_vcs_in_meta(feature_dir, repo_root)

        # When --base is provided, validate the ref and build a patched
        # LanesManifest that uses it as the mission_branch so the worktree
        # allocator branches from the explicit base instead of auto-detecting.
        active_lanes_manifest = lanes_manifest
        if base is not None and resolved_workspace.lane_id != PLANNING_LANE_ID:
            _validate_base_ref(repo_root, base)
            # Shallow-patch the manifest's mission_branch so
            # allocate_lane_worktree branches from the explicit ref.
            from dataclasses import replace as _dc_replace

            active_lanes_manifest = _dc_replace(lanes_manifest, mission_branch=base)
            console.print(f"[cyan]→ Using explicit base ref: {base}[/cyan]")
        elif base is not None:
            console.print("[yellow]Warning:[/yellow] --base is ignored for repository-root planning work")

        result = create_lane_workspace(
            repo_root=repo_root,
            mission_slug=mission_slug,
            wp_id=wp_id,
            wp_file=wp_file,
            resolved_workspace=resolved_workspace,
            lanes_manifest=active_lanes_manifest,
            declared_deps=declared_deps,
            vcs_backend_value=vcs_backend.value,
        )
        workspace_path = result.workspace_path
        branch_name = result.branch_name

        if result.lane_id is None:
            tracker.complete("create", f"Repository root: {workspace_path.relative_to(repo_root)}")
        elif result.is_reuse:
            tracker.complete("create", f"Reused lane {result.lane_id}: {workspace_path.relative_to(repo_root)}")
        else:
            tracker.complete("create", f"Lane {result.lane_id}: {workspace_path.relative_to(repo_root)}")
        console.print(tracker.render())
        if result.mission_branch:
            console.print(f"[cyan]→ Mission branch: {result.mission_branch}[/cyan]")
        if result.branch_name:
            console.print(f"[cyan]→ Lane branch: {result.branch_name}[/cyan]")
        else:
            console.print("[cyan]→ Workspace contract: repository root planning workspace[/cyan]")
    except typer.Exit:
        console.print(tracker.render())
        raise
    except Exception as exc:
        tracker.error("create", f"workspace allocation failed: {exc}")
        console.print(tracker.render())
        console.print(f"\n[red]Error:[/red] Workspace allocation failed: {exc}")
        raise typer.Exit(1) from exc

    try:
        import os

        current_lane = _get_wp_lane_from_event_log(feature_dir, wp_id)
        if current_lane == Lane.PLANNED:
            shell_pid = str(os.getppid())
            commit_msg = f"chore: {wp_id} claimed for implementation"
            status_execution_mode = "direct_repo" if resolved_workspace.resolution_kind == "repo_root" else "worktree"

            update_fields(wp_file, {"shell_pid": shell_pid})

            try:
                emit_status_transition(
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    wp_id=wp_id,
                    to_lane=Lane.CLAIMED,
                    actor="implement-command",
                    execution_mode=status_execution_mode,
                    repo_root=repo_root,
                )
                emit_status_transition(
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    wp_id=wp_id,
                    to_lane=Lane.IN_PROGRESS,
                    actor="implement-command",
                    execution_mode=status_execution_mode,
                    repo_root=repo_root,
                )
            except Exception as exc:
                console.print(f"[red]Error:[/red] Could not emit canonical status transition: {exc}")
                raise typer.Exit(1) from exc

            if auto_commit:
                meta_file = feature_dir / "meta.json"
                config_file = repo_root / ".kittify" / "config.yaml"
                files_to_commit = [wp_file.resolve(), *[path.resolve() for path in _collect_status_artifacts(feature_dir)]]
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
    except Exception as exc:
        console.print(f"[yellow]Warning:[/yellow] Could not update WP status: {exc}")

    if json_output:
        result_execution_mode = result.execution_mode if isinstance(result.execution_mode, str) else resolved_workspace.execution_mode
        workspace_rel = str(workspace_path.relative_to(repo_root))
        identity = resolve_mission_identity(feature_dir)
        print(
            json.dumps(
                {
                    "workspace": workspace_rel,
                    "workspace_path": workspace_rel,
                    "branch": branch_name,
                    "mission_slug": identity.mission_slug,
                    "mission_number": identity.mission_number,
                    "mission_type": identity.mission_type,
                    "wp_id": wp_id,
                    "lane_id": result.lane_id,
                    "execution_mode": result_execution_mode,
                    "status": "created",
                }
            )
        )
        return

    if result.lane_id is None:
        console.print("\n[bold green]✓ Repository-root workspace ready[/bold green]")
        console.print()
        console.print("[bold yellow]" + "=" * 72 + "[/bold yellow]")
        console.print("[bold yellow]Planning-artifact work for this WP happens in the repository root[/bold yellow]")
        console.print("[bold yellow]" + "=" * 72 + "[/bold yellow]")
        console.print()
        console.print(f"  [bold]cd {workspace_path}[/bold]")
        console.print()
        console.print("[dim]This WP does not get a lane worktree or workspace context file.[/dim]")
        console.print("[dim]Make planning-artifact changes directly in the repository root.[/dim]")
        return

    console.print("\n[bold green]✓ Lane worktree ready[/bold green]")
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
