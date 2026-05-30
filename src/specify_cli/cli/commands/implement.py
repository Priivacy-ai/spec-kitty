"""Implement command - allocate the lane worktree for a work package."""

from __future__ import annotations

import functools
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from specify_cli.cli import StepTracker
from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.git_ops import get_current_branch
from specify_cli.core.vcs import VCSBackend
from specify_cli.mission_metadata import resolve_mission_identity, set_vcs_lock
from specify_cli.frontmatter import FrontmatterError, update_fields
from specify_cli.git import safe_commit
from specify_cli.git.commit_helpers import protected_branches
from specify_cli.lanes.implement_support import create_lane_workspace
from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError, require_lanes_json
from specify_cli.status.emit import TransitionError, emit_status_transition
from specify_cli.status.models import Lane, TransitionRequest
from specify_cli.status.work_package_lifecycle import WorkPackageClaimConflict, start_implementation_status
from specify_cli.task_utils import TaskCliError, find_repo_root
from specify_cli.workspace.context import resolve_workspace_for_wp

console = Console()
_WP_ID_RE = re.compile(r"^WP\d{2}$", re.IGNORECASE)


def _protected_branch_status_commit_error(branch: str, repo_root: Path) -> str | None:
    if os.environ.get("SPEC_KITTY_TEST_MODE", "").lower() in {"1", "true", "yes"}:
        return None
    if branch not in protected_branches(repo_root):
        return None
    return (
        f"Refusing to start implementation status on protected branch '{branch}' "
        "before mutating status files. Run this ceremony from an allowed "
        "coordination/lane branch, or rerun with --no-auto-commit when you "
        "intentionally want to handle the status artifact commit manually."
    )


def _status_commit_destination_branch(repo_root: Path, fallback_branch: str) -> str:
    """Return the branch that the pre-lane status commit would target."""
    return get_current_branch(repo_root) or fallback_branch


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
) -> tuple[str | None, str]:
    """Require an explicit mission slug and return ``(mission_number, slug)``.

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
    return (match.group(1) if match else None), slug


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


def _ensure_planning_artifacts_committed_git(  # noqa: C901 -- legacy orchestration helper; unrelated to issue #1386
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

    commit_msg = (
        f"chore: planning artifacts for {mission_slug}\n\n"
        f"Auto-committed by spec-kitty before creating the lane worktree for {wp_id}"
    )

    # WP06 T026: route planning-artifact commits through
    # BookkeepingTransaction so the commit lands on the mission's
    # coordination branch (FR-005) and any write of status events is
    # atomically reversible (FR-010).
    #
    # Legacy missions (created pre-WP03) have no ``coordination_branch``
    # in meta.json. For those, fall back to the legacy raw-git path.
    # WP08 will replace this fallback with a proper legacy bridge.
    from specify_cli.mission_metadata import load_meta as _load_meta

    mission_meta: dict[str, Any] | None
    try:
        mission_meta = _load_meta(feature_dir)
    except Exception:  # noqa: BLE001 — meta missing/corrupt is legacy
        mission_meta = None

    coord_branch: str | None = None
    mission_id: str | None = None
    mid8: str | None = None
    if isinstance(mission_meta, dict):
        coord_branch = mission_meta.get("coordination_branch") or None
        mission_id = mission_meta.get("mission_id") or None
        mid8 = mission_meta.get("mid8") or (
            mission_id[:8] if isinstance(mission_id, str) and len(mission_id) >= 8 else None
        )

    # Route ALL planning-artifact commits through BookkeepingTransaction.
    # The transaction has a built-in legacy fallback (see
    # ``_is_legacy_mission`` + ``_resolve_legacy_lane_destination`` in
    # ``coordination/transaction.py``) so the pre-flight policy gate,
    # surgical rollback, and feature-status lock apply uniformly to
    # coordination-branch and legacy missions alike (FR-027).
    #
    # Modern (post-WP03) missions have ``coordination_branch``,
    # ``mission_id``, and ``mid8`` in meta; the transaction routes the
    # commit to the coord branch.
    #
    # Legacy missions lack ``coordination_branch``; the transaction
    # detects this via ``_is_legacy_mission`` and overrides the caller-
    # supplied ``destination_ref`` with the actual checked-out lane
    # branch resolved from HEAD. We synthesize ``mission_id`` / ``mid8``
    # from the slug if meta lacks them (truly pre-WP03 missions).
    from specify_cli.coordination.transaction import BookkeepingTransaction

    # Synthesize identifiers for legacy missions that lack them in meta.
    # The legacy fallback in BookkeepingTransaction overrides
    # destination_ref from HEAD, so the placeholder coord_branch value
    # below is never persisted; the routing just needs *some* shape-valid
    # ref name to satisfy the pre-flight policy gate's normalisation.
    effective_mission_id = str(mission_id) if mission_id else f"legacy-{mission_slug}"
    if mid8:
        effective_mid8 = str(mid8)
    elif mission_id and len(str(mission_id)) >= 8:
        effective_mid8 = str(mission_id)[:8]
    else:
        # Pre-WP03 mission with no mission_id at all. Derive a stable
        # 8-char prefix from the mission_slug so kitty_specs_dir_name
        # resolution stays deterministic across invocations.
        effective_mid8 = (mission_slug.replace("-", "") + "00000000")[:8]
    effective_destination_ref = (
        str(coord_branch) if coord_branch else planning_branch
    )

    is_legacy = not (coord_branch and mission_id and mid8)
    if is_legacy:
        console.print(
            f"\n[cyan]Auto-committing planning artifacts to {planning_branch}...[/cyan] "
            f"[dim](legacy path -- mission has no coordination_branch; "
            f"routed through BookkeepingTransaction for FR-020/FR-027 atomicity)[/dim]"
        )

    with BookkeepingTransaction.acquire(
        repo_root=repo_root,
        mission_id=effective_mission_id,
        mission_slug=mission_slug,
        mid8=effective_mid8,
        destination_ref=effective_destination_ref,
        operation=f"planning artifacts for {mission_slug}",
    ) as txn:
        for path_str in files_to_commit:
            p = (repo_root / path_str).resolve()
            if p.exists():
                txn.stage_path(p)
        try:
            txn.commit(commit_msg)
        except Exception as exc:  # noqa: BLE001 — surface as exit-1
            target = coord_branch or planning_branch
            console.print(
                f"[red]Error:[/red] Failed to commit planning artifacts to {target}: {exc}"
            )
            raise typer.Exit(1) from exc

    if is_legacy:
        console.print(
            f"[green]✓[/green] Planning artifacts committed to {planning_branch}"
        )
    else:
        console.print(
            f"[green]✓[/green] Planning artifacts committed to coordination branch {coord_branch}"
        )


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
    acknowledge_not_bulk_edit: Annotated[
        bool,
        typer.Option(
            "--acknowledge-not-bulk-edit",
            help="Suppress the bulk-edit inference warning when spec language resembles a bulk edit but the mission is not one.",
        ),
    ] = False,
    actor: Annotated[str | None, typer.Option("--actor", hidden=True, help="Actor identity for programmatic callers")] = None,
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
        # FR-006 caller contract (T024): charter preflight runs BEFORE
        # any worktree allocation or .kittify/ modification. On failure
        # we exit 1 with the blocked_reason — no state mutation.
        from specify_cli.charter_runtime.preflight.hook import run_preflight_or_abort

        run_preflight_or_abort(repo_root, consumer="implement")
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
        if auto_commit:
            status_destination = _status_commit_destination_branch(
                repo_root,
                fallback_branch=planning_branch,
            )
            protected_error = _protected_branch_status_commit_error(status_destination, repo_root)
            if protected_error is not None:
                raise ValueError(protected_error)
        _ensure_planning_artifacts_committed_git(
            repo_root=repo_root,
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            planning_branch=planning_branch,
            auto_commit=bool(auto_commit),
        )

        # Bulk edit occurrence classification gate (FR-006)
        from specify_cli.bulk_edit.gate import ensure_occurrence_classification_ready, render_gate_failure

        gate_result = ensure_occurrence_classification_ready(feature_dir)
        if not gate_result.passed:
            render_gate_failure(gate_result, console)
            raise typer.Exit(1)

        # Inference warning for potentially unmarked bulk edits (FR-009)
        if gate_result.change_mode is None:
            from specify_cli.bulk_edit.inference import (
                scan_spec_file,
                wp_authors_bulk_edit_planning_artifact,
            )

            inference = scan_spec_file(feature_dir)
            planning_wp = wp_authors_bulk_edit_planning_artifact(wp_file, mission_slug)
            if inference.triggered and planning_wp:
                matched = ", ".join(f"'{p}' ({w}pt)" for p, w in inference.matched_phrases)
                console.print(Panel(
                    f"This mission's spec contains language suggesting a bulk edit "
                    f"(score: {inference.score}/{inference.threshold}), but {wp_id} owns "
                    f"the occurrence-map planning artifact.\n"
                    f"  Matched: {matched}\n\n"
                    f"Continuing without --acknowledge-not-bulk-edit for this planning WP.",
                    title="[bold yellow]Bulk Edit Inference Informational[/]",
                    border_style="yellow",
                ))
            elif inference.triggered and not acknowledge_not_bulk_edit:
                matched = ", ".join(f"'{p}' ({w}pt)" for p, w in inference.matched_phrases)
                console.print(Panel(
                    f"This mission's spec contains language suggesting a bulk edit "
                    f"(score: {inference.score}/{inference.threshold}):\n"
                    f"  Matched: {matched}\n\n"
                    f"If this IS a bulk edit, set change_mode to 'bulk_edit' in meta.json.\n"
                    f"If it is NOT, re-run with --acknowledge-not-bulk-edit to suppress.",
                    title="[bold yellow]Bulk Edit Inference Warning[/]",
                    border_style="yellow",
                ))
                raise typer.Exit(1)

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
    effective_actor = actor or "implement-command"
    status_result = None
    status_execution_mode = "direct_repo" if resolved_workspace.resolution_kind == "repo_root" else "worktree"
    try:
        import os as _os

        update_fields(wp_file, {"shell_pid": str(_os.getppid())})
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

        try:
            status_result = start_implementation_status(
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                wp_id=wp_id,
                actor=effective_actor,
                workspace_context=f"{status_execution_mode}:{workspace_path}",
                execution_mode=status_execution_mode,
                repo_root=repo_root,
            )
        except WorkPackageClaimConflict as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        except TransitionError as exc:
            console.print(f"[red]Error:[/red] Could not start implementation status: {exc}")
            raise typer.Exit(1) from exc

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
        current_lane = _get_wp_lane_from_event_log(feature_dir, wp_id)
        if current_lane in {Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS}:
            try:
                emit_status_transition(TransitionRequest(
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    wp_id=wp_id,
                    to_lane=Lane.BLOCKED,
                    actor=effective_actor,
                    execution_mode=status_execution_mode,
                    reason="worktree_alloc_failed",
                    policy_metadata={"evidence": str(exc)},
                    repo_root=repo_root,
                ))
            except Exception as _blocked_exc:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not emit blocked transition after alloc failure: {_blocked_exc}"
                )
        raise typer.Exit(1) from exc

    try:
        if status_result is not None and status_result.status_changed:
            commit_msg = f"chore: {wp_id} claimed for implementation"
            if auto_commit:
                from specify_cli.cli.commands.agent.tasks import _collect_status_artifacts

                meta_file = feature_dir / "meta.json"
                config_file = repo_root / ".kittify" / "config.yaml"
                files_to_commit = [wp_file.resolve(), *[path.resolve() for path in _collect_status_artifacts(feature_dir)]]
                if meta_file.exists():
                    files_to_commit.append(meta_file.resolve())
                if config_file.exists():
                    files_to_commit.append(config_file.resolve())

                # Mechanical WP06 pre-step migration: add destination_ref +
                # worktree_root after WP01's signature change. The status
                # claim commit lands on the feature planning branch.
                from specify_cli.core.git_ops import get_current_branch as _get_cur_branch
                _cur_branch = _get_cur_branch(repo_root) or planning_branch
                try:
                    safe_commit(
                        repo_root=repo_root,
                        worktree_root=repo_root,
                        destination_ref=_cur_branch,
                        message=commit_msg,
                        paths=tuple(files_to_commit),
                    )
                    console.print(f"[cyan]→ {wp_id} moved to 'doing'[/cyan]")
                except Exception as _commit_exc:  # noqa: BLE001 — log + continue
                    console.print(
                        f"[yellow]Warning:[/yellow] Could not auto-commit lane change: {_commit_exc}"
                    )
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
                    # FR-006: surface the lane-suffixed test DB env so
                    # downstream agents / test runners can `os.environ.update`
                    # without re-deriving the helper. Empty dict for
                    # planning-artifact workspaces (lane_id is None) or
                    # when the result type doesn't carry a real dict
                    # (e.g. a MagicMock in unit tests).
                    "lane_test_env": (
                        result.lane_test_env
                        if isinstance(getattr(result, "lane_test_env", None), dict)
                        else {}
                    ),
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

    # FR-006: surface the lane-suffixed test DB env so the agent can
    # export it before running the project's test suite. Persisted to
    # WorkspaceContext for resurrection by later commands; printed here
    # so a human operator can copy/paste in their shell.
    lane_env = getattr(result, "lane_test_env", None)
    if isinstance(lane_env, dict) and lane_env:
        console.print()
        console.print("[bold cyan]Lane-specific test environment (FR-006):[/bold cyan]")
        for key, value in sorted(lane_env.items()):
            console.print(f"  export {key}={value}")
        console.print(
            "[dim]Two parallel SaaS / Django lanes will collide on a single shared test DB"
            " unless these are exported in the lane's test process.[/dim]"
        )


__all__ = ["_ensure_vcs_in_meta", "detect_feature_context", "find_wp_file", "implement"]
