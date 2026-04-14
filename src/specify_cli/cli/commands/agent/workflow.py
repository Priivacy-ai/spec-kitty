"""Action commands for AI agents - display prompts and instructions."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

import typer
from typing_extensions import Annotated

from specify_cli.cli.selector_resolution import resolve_mission_handle, resolve_selector
from specify_cli.cli.commands.implement import implement as top_level_implement
from specify_cli.charter.context import build_charter_context
from specify_cli.core.dependency_graph import build_dependency_graph, get_dependents
from specify_cli.core.paths import locate_project_root, get_main_repo_root, is_worktree_context
from specify_cli.git import safe_commit
from specify_cli.mission import get_deliverables_path, get_mission_type
from specify_cli.status.emit import emit_status_transition, TransitionError
from specify_cli.status.locking import feature_status_lock
from specify_cli.status.models import Lane
from specify_cli.status.wp_metadata import read_wp_frontmatter
from specify_cli.status.store import read_events
from specify_cli.cli.commands.agent.tasks import _collect_status_artifacts
from specify_cli.core.utils import write_text_within_directory
from specify_cli.tasks_support import (
    append_activity_log,
    build_document,
    extract_scalar,
    find_repo_root,
    locate_work_package,
    set_scalar,
    split_frontmatter,
)
from specify_cli.workspace_context import resolve_workspace_for_wp

_REVIEW_FEEDBACK_SENTINELS = frozenset({"force-override", "action-review-claim"})


def _write_prompt_to_file(
    command_type: str,
    wp_id: str,
    content: str,
) -> Path:
    """Write full prompt content to a temp file for agents with output limits.

    Args:
        command_type: "implement" or "review"
        wp_id: Work package ID (e.g., "WP01")
        content: Full prompt content to write

    Returns:
        Path to the written file
    """
    # Use system temp directory (gets cleaned up automatically)
    prompt_file = Path(tempfile.gettempdir()) / f"spec-kitty-{command_type}-{wp_id}.md"
    prompt_file.write_text(content, encoding="utf-8")
    return prompt_file


def _resolve_git_common_dir(repo_root: Path) -> Path | None:
    """Resolve absolute git common-dir path."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    raw_value = result.stdout.strip()
    if not raw_value:
        return None
    common_dir = Path(raw_value)
    if not common_dir.is_absolute():
        common_dir = (repo_root / common_dir).resolve()
    return common_dir


def _resolve_review_feedback_pointer(repo_root: Path, pointer: str) -> Path | None:
    """Resolve a review feedback pointer to a file path.

    Supports two pointer formats:
    - ``review-cycle://<mission_slug>/<wp_slug>/review-cycle-N.md``
      → ``kitty-specs/<mission_slug>/tasks/<wp_slug>/review-cycle-N.md``
    - ``feedback://<mission_slug>/<task_id>/<filename>``  (legacy)
      → ``.git/spec-kitty/feedback/<mission_slug>/<task_id>/<filename>``

    Also handles legacy absolute-path strings.
    Returns None for sentinel values such as ``"force-override"`` and
    ``"action-review-claim"``, or any
    unrecognised / non-existent pointer.
    """
    value = pointer.strip()
    if not value or value in _REVIEW_FEEDBACK_SENTINELS:
        return None

    if value.startswith("review-cycle://"):
        relative = value[len("review-cycle://") :]
        parts = [p for p in relative.split("/") if p]
        if len(parts) != 3:
            return None
        # parts: mission_slug / wp_slug / filename
        candidate = repo_root / "kitty-specs" / parts[0] / "tasks" / parts[1] / parts[2]
    elif value.startswith("feedback://"):
        relative = value[len("feedback://") :]
        parts = [p for p in relative.split("/") if p]
        if len(parts) != 3:
            return None
        common_dir = _resolve_git_common_dir(repo_root)
        if common_dir is None:
            return None
        candidate = common_dir / "spec-kitty" / "feedback" / parts[0] / parts[1] / parts[2]
    else:
        legacy = Path(value).expanduser()
        candidate = legacy if legacy.is_absolute() else (repo_root / legacy)

    candidate = candidate.resolve()
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


def _read_wp_events(feature_dir: Path, wp_id: str):
    """Return canonical status events for a single work package."""
    try:
        from specify_cli.status.store import read_events as _read_status_events

        return [event for event in _read_status_events(feature_dir) if event.wp_id == wp_id]
    except Exception:
        return []


def _latest_review_feedback_reference(
    feature_dir: Path,
    repo_root: Path,
    wp_id: str,
) -> tuple[str | None, Path | None, int | None]:
    """Return the newest canonical review feedback reference for *wp_id*.

    Operational sentinels like ``action-review-claim`` are intentionally
    skipped so implement/fix handoff uses the persisted review artifact
    instead of the transient reviewer claim marker.
    """
    wp_events = _read_wp_events(feature_dir, wp_id)
    for index in range(len(wp_events) - 1, -1, -1):
        event = wp_events[index]
        if event.review_ref is None:
            continue
        review_ref = event.review_ref.strip()
        if not review_ref or review_ref in _REVIEW_FEEDBACK_SENTINELS:
            continue
        return review_ref, _resolve_review_feedback_pointer(repo_root, review_ref), index
    return None, None, None


def _resolve_review_feedback_context(
    feature_dir: Path,
    repo_root: Path,
    wp_id: str,
    wp_frontmatter: str,
) -> tuple[bool, str | None, Path | None, str | None]:
    """Resolve review-feedback presence and the canonical readable artifact."""
    review_feedback_ref, review_feedback_file, _ = _latest_review_feedback_reference(feature_dir, repo_root, wp_id)
    if review_feedback_ref is not None:
        return True, review_feedback_ref, review_feedback_file, "canonical"

    fm_review_status = extract_scalar(wp_frontmatter, "review_status")
    fm_review_feedback = extract_scalar(wp_frontmatter, "review_feedback")
    if fm_review_status and str(fm_review_status) == "has_feedback":
        ref = str(fm_review_feedback).strip() if fm_review_feedback else None
        path = _resolve_review_feedback_pointer(repo_root, ref) if ref else None
        return True, ref, path, "frontmatter"

    return False, None, None, None


def _render_charter_context(repo_root: Path, action: str) -> str:
    """Render charter context for workflow prompts."""
    try:
        context = build_charter_context(repo_root, action=action, mark_loaded=True)
        return context.text
    except Exception as exc:
        return f"Governance: unavailable ({exc})"


def _workspace_contract_description(workspace, wp_id: str) -> str:
    """Describe the canonical execution workspace for prompt output."""
    if workspace.lane_id:
        shared = ", ".join(workspace.lane_wp_ids or [wp_id])
        return f"Workspace contract: lane {workspace.lane_id} shared by {shared}"
    return "Workspace contract: repository root planning workspace"


def _shared_artifact_guidance(workspace, repo_root: Path, mission_slug: str) -> list[str]:
    """Render workspace-specific guidance about where mission artifacts live."""
    if workspace.lane_id:
        return [
            "📚 SHARED MISSION ARTIFACTS:",
            f"   Spec, plan, tasks, and status live in main repo: {repo_root}/kitty-specs/{mission_slug}/",
            "   Use this lane workspace for code/tests; do not expect shared mission artifacts here",
        ]

    return [
        "📚 PLANNING ARTIFACTS:",
        f"   This WP runs in the repository root: {repo_root}",
        f"   Mission artifacts for this WP live here too: {repo_root}/kitty-specs/{mission_slug}/",
        "   Do not look for a separate lane worktree or workspace context file",
    ]


app = typer.Typer(name="action", help="Mission action commands that display prompts and instructions for agents", no_args_is_help=True)

_CANONICAL_STATUS_NOT_FOUND = "canonical status not found"


def _is_missing_canonical_status_error(exc: BaseException) -> bool:
    """Return True when *exc* indicates missing canonical status bootstrap."""
    return _CANONICAL_STATUS_NOT_FOUND in str(exc).lower()


def _missing_canonical_status_message(wp_id: str, mission_slug: str) -> str:
    """Return a consistent hard-fail message for missing canonical status."""
    return f"WP {wp_id} has no canonical status. Run `spec-kitty agent mission finalize-tasks --mission {mission_slug}` to initialize."


def _has_prior_rejection(
    feature_dir: Path,
    wp_slug: str,
    normalized_wp_id: str,
) -> bool:
    """Check if a WP has review-cycle artifacts from a prior rejection.

    A prior rejection is active when:
    1. Review-cycle artifact files exist in the sub-artifact directory.
    2. The newest canonical review feedback reference for this WP resolves to a
       readable artifact.
    3. The WP has not since resolved to an approved/done terminal state.

    Args:
        feature_dir: Path to kitty-specs/<mission>/ in the main repo.
        wp_slug: Full WP file stem, e.g. "WP01-some-title".
        normalized_wp_id: Canonical WP ID, e.g. "WP01".

    Returns:
        True iff both artifact files and a rejection event are present.
    """
    sub_artifact_dir = feature_dir / "tasks" / wp_slug
    if not sub_artifact_dir.exists():
        return False
    if not list(sub_artifact_dir.glob("review-cycle-*.md")):
        return False

    wp_events = _read_wp_events(feature_dir, normalized_wp_id)
    if not wp_events:
        return False

    repo_root = feature_dir.parent.parent
    review_feedback_ref, review_feedback_file, review_feedback_index = _latest_review_feedback_reference(
        feature_dir,
        repo_root,
        normalized_wp_id,
    )
    if review_feedback_ref is None or review_feedback_file is None or review_feedback_index is None:
        return False

    if any(event.to_lane in {Lane.APPROVED, Lane.DONE} for event in wp_events[review_feedback_index + 1 :]):
        return False

    latest_event = wp_events[-1]
    return latest_event.to_lane not in {Lane.APPROVED, Lane.DONE}


def _ensure_target_branch_checked_out(repo_root: Path, mission_slug: str) -> tuple[Path, str]:
    """Resolve branch context without auto-checkout (respects user's current branch).

    Returns the planning repo root and the user's current branch.
    Shows a consistent branch banner.
    """
    from specify_cli.core.git_ops import get_current_branch, resolve_target_branch

    main_repo_root = get_main_repo_root(repo_root)

    # Check for detached HEAD using robust branch detection
    current_branch = get_current_branch(main_repo_root)
    if current_branch is None:
        print("Error: Detached HEAD — checkout a branch before continuing.")
        raise typer.Exit(1)

    # Resolve branch routing (unified logic, no auto-checkout)
    resolution = resolve_target_branch(mission_slug, main_repo_root, current_branch, respect_current=True)

    # Show consistent branch banner
    if not resolution.should_notify:
        print(f"Branch: {current_branch} (target for this mission)")
    else:
        print(f"Branch: on '{resolution.current}', mission targets '{resolution.target}'")

    # Return current branch (no checkout performed)
    return main_repo_root, resolution.current


def _find_mission_slug(
    explicit_mission: str | None = None,
    explicit_feature: str | None = None,
    repo_root: Path | None = None,
) -> str:
    """Require an explicit mission slug (no auto-detection).

    When repo_root is supplied the handle is resolved via the canonical
    mission resolver which handles ambiguous numeric-prefix handles, mid8
    prefixes, and full ULID forms.

    Args:
        explicit_mission: Mission slug provided explicitly.
        explicit_feature: Mission slug provided via hidden --feature alias.
        repo_root: Repository root; if provided, enables canonical resolver.

    Returns:
        Mission slug (e.g., "008-unified-python-cli")

    Raises:
        typer.Exit: If mission slug is not provided or selectors conflict.
    """
    try:
        selector = resolve_selector(
            canonical_value=explicit_mission,
            canonical_flag="--mission",
            alias_value=explicit_feature,
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
            command_hint="--mission <slug>",
        )
    except typer.BadParameter as e:
        print(f"Error: {e}")
        raise typer.Exit(1)

    raw_handle = selector.canonical_value
    if raw_handle is not None and repo_root is not None:
        legacy_dir = get_main_repo_root(repo_root) / "kitty-specs" / raw_handle
        if legacy_dir.exists():
            return raw_handle
        try:
            resolved = resolve_mission_handle(raw_handle, repo_root)
            return resolved.mission_slug
        except (SystemExit, typer.Exit):
            if legacy_dir.exists():
                return raw_handle
            raise

    return raw_handle


def _normalize_wp_id(wp_arg: str) -> str:
    """Normalize WP ID from various formats to standard WPxx format.

    Args:
        wp_arg: User input (e.g., "wp01", "WP01", "WP01-foo-bar")

    Returns:
        Normalized WP ID (e.g., "WP01")
    """
    # Handle formats: wp01 → WP01, WP01 → WP01, WP01-foo-bar → WP01
    wp_upper = wp_arg.upper()

    # Extract just the WPxx part
    if wp_upper.startswith("WP"):
        # Split on hyphen and take first part
        return wp_upper.split("-")[0]
    else:
        # Assume it's like "01" or "1", prefix with WP
        return f"WP{wp_upper.lstrip('WP')}"


def _find_first_planned_wp(repo_root: Path, mission_slug: str) -> Optional[str]:
    """Find the first WP file with lane: "planned".

    Args:
        repo_root: Repository root path
        mission_slug: Feature slug

    Returns:
        WP ID of first planned task, or None if not found
    """
    from specify_cli.core.paths import is_worktree_context

    cwd = Path.cwd().resolve()

    # Check if we're in a worktree - if so, use worktree's kitty-specs
    if is_worktree_context(cwd):
        # We're in a worktree, look for kitty-specs relative to cwd
        if (cwd / "kitty-specs" / mission_slug).exists():
            tasks_dir = cwd / "kitty-specs" / mission_slug / "tasks"
        else:
            # Walk up to find kitty-specs
            current = cwd
            while current != current.parent:
                if (current / "kitty-specs" / mission_slug).exists():
                    tasks_dir = current / "kitty-specs" / mission_slug / "tasks"
                    break
                current = current.parent
            else:
                # Fallback to repo_root
                tasks_dir = repo_root / "kitty-specs" / mission_slug / "tasks"
    else:
        # We're in main repo
        tasks_dir = repo_root / "kitty-specs" / mission_slug / "tasks"

    if not tasks_dir.exists():
        return None

    # Find all WP files
    wp_files = sorted(tasks_dir.glob("WP*.md"))

    # Load lanes from canonical event log (lane is event-log-only)
    feature_dir = tasks_dir.parent
    try:
        from specify_cli.status.store import read_events as _fp_read_events
        from specify_cli.status.reducer import reduce as _fp_reduce

        _fp_events = _fp_read_events(feature_dir)
        _fp_snapshot = _fp_reduce(_fp_events) if _fp_events else None
        _fp_lanes: dict = {}
        if _fp_snapshot:
            for _fp_wp_id, _fp_state in _fp_snapshot.work_packages.items():
                _fp_lanes[_fp_wp_id] = Lane(_fp_state.get("lane", Lane.PLANNED))
    except Exception:
        _fp_lanes = {}

    for wp_file in wp_files:
        content = wp_file.read_text(encoding="utf-8-sig")
        frontmatter, _, _ = split_frontmatter(content)
        wp_id = extract_scalar(frontmatter, "work_package_id")
        if wp_id:
            lane = _fp_lanes.get(wp_id, Lane.PLANNED)
            if lane == Lane.PLANNED:
                return wp_id

    return None


@app.command(name="implement")
def implement(
    wp_id: Annotated[Optional[str], typer.Argument(help="Work package ID (e.g., WP01, wp01, WP01-slug) - auto-detects first planned if omitted")] = None,
    mission: Annotated[Optional[str], typer.Option("--mission", help="Mission slug")] = None,
    feature: Annotated[Optional[str], typer.Option("--feature", hidden=True, help="(deprecated) Use --mission")] = None,
    agent: Annotated[Optional[str], typer.Option("--agent", help="Agent name (required for auto-move to in_progress)")] = None,
    allow_sparse_checkout: Annotated[
        bool,
        typer.Option(
            "--allow-sparse-checkout",
            help=(
                "Proceed even if legacy sparse-checkout state is detected. "
                "Use of this override is logged. Does not bypass the commit-time "
                "data-loss backstop."
            ),
        ),
    ] = False,
) -> None:
    """Display work package prompt with implementation instructions.

    This command outputs the full work package prompt content so agents can
    immediately see what to implement, without navigating the file system.

    Automatically moves WP from planned to in_progress (requires --agent to track who is working).

    Examples:
        spec-kitty agent action implement WP01 --agent claude
        spec-kitty agent action implement WP02 --agent claude
        spec-kitty agent action implement wp01 --agent codex
        spec-kitty agent action implement --agent gemini  # auto-detects first planned WP
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            print("Error: Could not locate project root")
            raise typer.Exit(1)

        mission_slug = _find_mission_slug(explicit_mission=mission, explicit_feature=feature, repo_root=repo_root)

        # -- WP05/T021 FR-007: Sparse-checkout preflight --
        # Runs BEFORE any worktree creation or state changes. Same surface as
        # merge (see _run_lane_based_merge). If --allow-sparse-checkout is set,
        # require_no_sparse_checkout emits a structured override log and
        # returns; the WP01 commit-layer backstop still guards commits.
        from specify_cli.git.sparse_checkout import (
            SparseCheckoutPreflightError,
            require_no_sparse_checkout,
        )

        _main_repo_for_preflight = get_main_repo_root(repo_root)
        _mission_id_for_preflight: Optional[str] = None
        try:
            from specify_cli.mission_metadata import resolve_mission_identity

            _identity = resolve_mission_identity(
                _main_repo_for_preflight / "kitty-specs" / mission_slug
            )
            _mission_id_for_preflight = _identity.mission_id
        except Exception:  # noqa: BLE001 — meta.json may not exist for legacy missions
            _mission_id_for_preflight = None

        try:
            require_no_sparse_checkout(
                repo_root=_main_repo_for_preflight,
                command="spec-kitty agent action implement",
                override_flag=allow_sparse_checkout,
                actor=agent,
                mission_slug=mission_slug,
                mission_id=_mission_id_for_preflight,
            )
        except SparseCheckoutPreflightError as exc:
            # Surface as a user-facing error. No worktree is created.
            print(f"Error: {exc}")
            raise typer.Exit(1) from exc

        # Ensure planning repo is on the target branch before we start
        # (needed for auto-commits and status tracking inside this command)
        main_repo_root, target_branch = _ensure_target_branch_checked_out(repo_root, mission_slug)

        # Determine which WP to implement
        if wp_id:
            normalized_wp_id = _normalize_wp_id(wp_id)
        else:
            # Auto-detect first planned WP
            normalized_wp_id = _find_first_planned_wp(repo_root, mission_slug)
            if not normalized_wp_id:
                print("Error: No planned work packages found. Specify a WP ID explicitly.")
                raise typer.Exit(1)

        # Find WP file to read dependencies
        try:
            wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
        except RuntimeError as e:
            if _is_missing_canonical_status_error(e):
                print(f"Error: {_missing_canonical_status_message(normalized_wp_id, mission_slug)}")
                raise typer.Exit(1)
            print(f"Error locating work package: {e}")
            raise typer.Exit(1)
        except Exception as e:
            print(f"Error locating work package: {e}")
            raise typer.Exit(1)

        workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, normalized_wp_id)
        workspace_path = workspace.worktree_path
        status_execution_mode = "direct_repo" if workspace.resolution_kind == "repo_root" else "worktree"

        # Ensure workspace exists (delegate to top-level implement for creation)
        if not workspace.exists:
            cwd = Path.cwd().resolve()
            if is_worktree_context(cwd):
                print("Error: Workspace does not exist and cannot be created from a worktree.")
                print("Run this command from the main repository:")
                print(f"  spec-kitty agent action implement {normalized_wp_id} --agent <your-name>")
                raise typer.Exit(1)

            print(f"Creating workspace for {normalized_wp_id}...")
            try:
                top_level_implement(wp_id=normalized_wp_id, mission=mission_slug, json_output=False, recover=False)
            except typer.Exit:
                # Worktree creation failed - propagate error
                raise
            except Exception as e:
                print(f"Error creating worktree: {e}")
                raise typer.Exit(1)

            workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, normalized_wp_id)
            workspace_path = workspace.worktree_path
            if not workspace.exists:
                print(f"Error: implement completed but no workspace could be resolved for {normalized_wp_id}.")
                raise typer.Exit(1)

        # Load work package
        try:
            wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
            wp_meta, _ = read_wp_frontmatter(wp.path)
        except RuntimeError as e:
            if _is_missing_canonical_status_error(e):
                raise RuntimeError(_missing_canonical_status_message(normalized_wp_id, mission_slug)) from e
            raise

        subtask_ids = [str(item) for item in wp_meta.subtasks if isinstance(item, str)]
        subtask_cmd = " ".join(subtask_ids) if subtask_ids else "<subtask-ids>"

        # Resolve structured agent assignment from WP metadata (centralizes legacy coercion)
        _wp_agent_assignment = wp_meta.resolved_agent()
        logger.debug("WP agent assignment: tool=%s model=%s", _wp_agent_assignment.tool, _wp_agent_assignment.model)

        # Move to in_progress lane if not already there, and ensure agent is recorded
        # Lane is event-log-only; read from canonical event log (no frontmatter fallback)
        _wf_feature_dir = repo_root / "kitty-specs" / mission_slug
        from specify_cli.status.lane_reader import get_wp_lane as _wf_get_wp_lane
        from specify_cli.status.store import read_events as _wf_read_events
        from specify_cli.status.reducer import reduce as _wf_reduce

        _wf_events = _wf_read_events(_wf_feature_dir)
        _wf_snapshot = _wf_reduce(_wf_events) if _wf_events else None
        _wf_has_canonical = _wf_snapshot is not None and normalized_wp_id in _wf_snapshot.work_packages
        if not _wf_has_canonical:
            raise RuntimeError(_missing_canonical_status_message(normalized_wp_id, mission_slug))
        current_lane = _wf_get_wp_lane(_wf_feature_dir, normalized_wp_id)
        needs_agent_assignment = _wp_agent_assignment.tool == "unknown"
        feature_dir = main_repo_root / "kitty-specs" / mission_slug
        wp_slug = wp.path.stem
        has_feedback, review_feedback_ref, review_feedback_file, review_feedback_source = _resolve_review_feedback_context(
            feature_dir=feature_dir,
            repo_root=main_repo_root,
            wp_id=normalized_wp_id,
            wp_frontmatter=wp.frontmatter,
        )
        fix_mode_active = _has_prior_rejection(feature_dir, wp_slug, normalized_wp_id)

        if review_feedback_source == "canonical" and review_feedback_file is None:
            print(f"Error: {normalized_wp_id} review feedback artifact is missing or unreadable: {review_feedback_ref}")
            print("Re-run move-task with --review-feedback-file so the fix cycle can attach the canonical review artifact.")
            raise typer.Exit(1)

        if current_lane != Lane.IN_PROGRESS or needs_agent_assignment:
            # Require --agent parameter to track who is working
            if not agent:
                if current_lane == Lane.IN_PROGRESS and not needs_agent_assignment:
                    # Already in_progress with an agent; allow prompt display
                    pass
                else:
                    print("Error: --agent parameter required when starting implementation.")
                    print(f"  Usage: spec-kitty agent action implement {normalized_wp_id} --agent <your-name>")
                    print("  Example: spec-kitty agent action implement WP01 --agent claude")
                    print()
                    print("If you're using a generated agent command file, --agent is already included.")
                    print("This tracks WHO is working on the WP (prevents abandoned tasks).")
                    raise typer.Exit(1)

            from datetime import datetime, timezone
            import os

            review_workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, normalized_wp_id)
            status_execution_mode = "direct_repo" if review_workspace.resolution_kind == "repo_root" else "worktree"

            # Capture current shell PID
            shell_pid = str(os.getppid())  # Parent process ID (the shell running this command)

            # Emit status events (canonical lane authority)
            # Must follow allowed transitions: planned→claimed→in_progress
            try:
                from specify_cli.status.emit import emit_status_transition

                _impl_feature_dir = main_repo_root / "kitty-specs" / mission_slug
                _actor = agent or "unknown"

                if current_lane == Lane.PLANNED or current_lane == Lane.CANCELED:
                    # Two-step: planned→claimed, claimed→in_progress
                    emit_status_transition(
                        feature_dir=_impl_feature_dir,
                        mission_slug=mission_slug,
                        wp_id=normalized_wp_id,
                        to_lane=Lane.CLAIMED,
                        actor=_actor,
                        execution_mode=status_execution_mode,
                    )
                    emit_status_transition(
                        feature_dir=_impl_feature_dir,
                        mission_slug=mission_slug,
                        wp_id=normalized_wp_id,
                        to_lane=Lane.IN_PROGRESS,
                        actor=_actor,
                        execution_mode=status_execution_mode,
                    )
                elif current_lane == Lane.CLAIMED:
                    emit_status_transition(
                        feature_dir=_impl_feature_dir,
                        mission_slug=mission_slug,
                        wp_id=normalized_wp_id,
                        to_lane=Lane.IN_PROGRESS,
                        actor=_actor,
                        execution_mode=status_execution_mode,
                    )
                elif current_lane in (Lane.FOR_REVIEW, Lane.APPROVED):
                    # Re-implementing after review — force back to in_progress
                    emit_status_transition(
                        feature_dir=_impl_feature_dir,
                        mission_slug=mission_slug,
                        wp_id=normalized_wp_id,
                        to_lane=Lane.IN_PROGRESS,
                        actor=_actor,
                        force=True,
                        reason="Re-implementing after review feedback",
                        execution_mode=status_execution_mode,
                    )
                # If already in_progress, no event needed
            except Exception as _evt_err:
                logger.warning("Could not emit status event: %s", _evt_err)

            # Update operational metadata in frontmatter (NO lane — event log is sole authority)
            updated_front = wp.frontmatter
            updated_front = set_scalar(updated_front, "agent", agent)
            updated_front = set_scalar(updated_front, "shell_pid", shell_pid)

            # Build history entry (no lane= segment; event log is sole lane authority)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if current_lane != Lane.IN_PROGRESS:
                history_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – Started implementation via action command"
            else:
                history_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – Assigned agent via action command"

            # Add history entry to body
            updated_body = append_activity_log(wp.body, history_entry)

            # Build and write updated document
            updated_doc = build_document(updated_front, updated_body, wp.padding)
            wp.path.write_text(updated_doc, encoding="utf-8")

            # Auto-commit to target branch (enables instant status sync)
            actual_wp_path = wp.path.resolve()
            status_artifacts = [path.resolve() for path in _collect_status_artifacts(_impl_feature_dir)]
            commit_success = safe_commit(
                repo_path=main_repo_root,
                files_to_commit=[actual_wp_path, *status_artifacts],
                commit_message=f"chore: Start {normalized_wp_id} implementation [{agent}]",
                allow_empty=True,  # OK if already in this state
            )
            if not commit_success:
                print(f"Error: Failed to commit workflow status update for {normalized_wp_id}. Status claim aborted.")
                raise typer.Exit(1)

            print(f"✓ Claimed {normalized_wp_id} (agent: {agent}, PID: {shell_pid}, target: {target_branch})")

            # Dossier sync (fire-and-forget)
            try:
                from specify_cli.sync.dossier_pipeline import (
                    trigger_feature_dossier_sync_if_enabled,
                )

                _impl_feature_dir = repo_root / "kitty-specs" / mission_slug
                trigger_feature_dossier_sync_if_enabled(
                    _impl_feature_dir,
                    mission_slug,
                    repo_root,
                )
            except Exception:
                pass

            # Reload to get updated content
            wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
        else:
            print(f"⚠️  {normalized_wp_id} is already in lane: {current_lane}. Action implement will not move it to in_progress.")

        # Fix-mode detection: if the WP was rejected and has review-cycle artifacts,
        # generate a focused fix-mode prompt instead of the full WP prompt.
        # The fix-prompt completely replaces the full WP prompt (not appended to it).
        if fix_mode_active:
            try:
                from rich.console import Console as _RichConsole
                from specify_cli.review.artifacts import ReviewCycleArtifact as _ReviewCycleArtifact
                from specify_cli.review.fix_prompt import generate_fix_prompt as _generate_fix_prompt

                _sub_artifact_dir = feature_dir / "tasks" / wp_slug
                if review_feedback_ref and review_feedback_ref.startswith("review-cycle://") and review_feedback_file is not None:
                    _latest_artifact = _ReviewCycleArtifact.from_file(review_feedback_file)
                else:
                    _latest_artifact = _ReviewCycleArtifact.latest(_sub_artifact_dir)
                if _latest_artifact is not None:
                    _console = _RichConsole()
                    _console.print(
                        f"[bold]Fix mode[/bold]: generating focused prompt from "
                        f"review-cycle-{_latest_artifact.cycle_number} "
                        f"(Canonical feedback: {_sub_artifact_dir / f'review-cycle-{_latest_artifact.cycle_number}.md'})"
                    )
                    _fix_prompt_text = _generate_fix_prompt(
                        artifact=_latest_artifact,
                        worktree_path=workspace_path,
                        mission_slug=mission_slug,
                        wp_id=normalized_wp_id,
                    )
                    _fix_prompt_file = _write_prompt_to_file("implement", normalized_wp_id, _fix_prompt_text)
                    print()
                    print(f"📍 Workspace: cd {workspace_path}")
                    print(f"🔧 Fix mode — Cycle {_latest_artifact.cycle_number}: focused prompt from review artifact")
                    print()
                    print("▶▶▶ NEXT STEP: Read the full fix-mode prompt file now:")
                    print(f"    cat {_fix_prompt_file}")
                    print()
                    return
            except Exception as _fix_mode_err:
                logger.warning("Fix-mode prompt generation failed, falling through to full prompt: %s", _fix_mode_err)

        # Detect mission type and get deliverables_path for research missions
        mission_type = get_mission_type(feature_dir)
        deliverables_path = None
        if mission_type == "research":
            deliverables_path = get_deliverables_path(feature_dir, mission_slug)

        # Capture baseline test results (one-time, cached) before the agent starts coding
        # wp.path.stem is e.g. "WP04-baseline-test-capture"
        _wp_slug = wp.path.stem
        try:
            from specify_cli.review.baseline import capture_baseline as _capture_baseline

            _baseline = _capture_baseline(
                worktree_path=workspace_path,
                base_branch=target_branch,
                wp_id=normalized_wp_id,
                mission_slug=mission_slug,
                feature_dir=feature_dir,
                wp_slug=_wp_slug,
            )
            if _baseline is not None and _baseline.failed > 0:
                print(f"[dim]Baseline: {_baseline.failed} pre-existing test failure(s) captured[/dim]")
                # Commit the baseline artifact to the feature branch
                _baseline_artifact = feature_dir / "tasks" / _wp_slug / "baseline-tests.json"
                if _baseline_artifact.exists():
                    safe_commit(
                        repo_path=main_repo_root,
                        files_to_commit=[_baseline_artifact],
                        commit_message=f"chore: Capture baseline tests for {normalized_wp_id}",
                        allow_empty=True,
                    )
            elif _baseline is not None and _baseline.failed == -1:
                print("[yellow]Warning: baseline test capture failed — no baseline context available[/yellow]")
        except Exception as _bl_err:
            import logging as _bl_logging

            _bl_logging.getLogger(__name__).warning("Baseline capture error: %s", _bl_err)

        # Build full prompt content for file
        lines = []
        lines.append("=" * 80)
        lines.append(f"IMPLEMENT: {normalized_wp_id}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Source: {wp.path}")
        lines.append("")
        lines.append(f"Workspace: {workspace_path}")
        lines.append(_workspace_contract_description(workspace, normalized_wp_id))
        lines.append("")
        lines.append(_render_charter_context(repo_root, "implement"))
        lines.append("")

        # CRITICAL: WP isolation rules
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  🚨 CRITICAL: WORK PACKAGE ISOLATION RULES                              ║")
        lines.append("╠" + "=" * 78 + "╣")
        lines.append(f"║  YOU ARE ASSIGNED TO: {normalized_wp_id:<55} ║")
        lines.append("║                                                                          ║")
        lines.append("║  ✅ DO:                                                                  ║")
        lines.append(f"║     • Only modify status of {normalized_wp_id:<47} ║")
        lines.append(f"║     • Only mark subtasks belonging to {normalized_wp_id:<36} ║")
        lines.append("║     • Ignore git commits and status changes from other agents           ║")
        lines.append("║                                                                          ║")
        lines.append("║  ❌ DO NOT:                                                              ║")
        lines.append(f"║     • Change status of any WP other than {normalized_wp_id:<34} ║")
        lines.append("║     • React to or investigate other WPs' status changes                 ║")
        lines.append(f"║     • Mark subtasks that don't belong to {normalized_wp_id:<33} ║")
        lines.append("║                                                                          ║")
        lines.append("║  WHY: Multiple agents work in parallel. Each owns exactly ONE WP.       ║")
        lines.append("║       Git commits from other WPs are other agents - ignore them.        ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")

        # Inject worktree topology context for stacked branches
        try:
            from specify_cli.core.worktree_topology import (
                materialize_worktree_topology,
                render_topology_json,
            )

            topology = materialize_worktree_topology(repo_root, mission_slug)
            if topology.has_stacking:
                lines.extend(render_topology_json(topology, current_wp_id=normalized_wp_id))
                lines.append("")
        except Exception as exc:
            lines.append(f"[Topology unavailable: {exc}]")
            lines.append("")

        # Next steps
        lines.append("=" * 80)
        lines.append("WHEN YOU'RE DONE:")
        lines.append("=" * 80)
        lines.append(f"✓ Implementation complete and tested:")
        lines.append(f"  1. **Commit your implementation files:**")
        lines.append(f"     git status  # Check what you changed")
        lines.append(f"     git add <your-implementation-files>  # NOT WP status files")
        lines.append(f'     git commit -m "feat({normalized_wp_id}): <brief description>"')
        lines.append(f"     git log -1 --oneline  # Verify commit succeeded")
        lines.append(f"  2. Mark all subtasks as done:")
        lines.append(f"     spec-kitty agent tasks mark-status {subtask_cmd} --status done --mission {mission_slug}")
        lines.append(f"  3. Move WP to review:")
        lines.append(f'     spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --mission {mission_slug} --note "Ready for review"')
        lines.append("")
        lines.append(f"✗ Blocked or cannot complete:")
        lines.append(f'  spec-kitty agent tasks add-history {normalized_wp_id} --mission {mission_slug} --note "Blocked: <reason>"')
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"📍 WORKING DIRECTORY:")
        lines.append(f"   cd {workspace_path}")
        if workspace.lane_id:
            lines.append("   # All implementation work happens in this workspace")
            lines.append(f"   # When done, return to repo root: cd {repo_root}")
        else:
            lines.append("   # Planning-artifact work for this WP happens in the repository root")
        lines.append("")
        lines.extend(_shared_artifact_guidance(workspace, repo_root, mission_slug))
        lines.append("")
        lines.append("📋 STATUS TRACKING:")
        lines.append(f"   kitty-specs/ status is tracked in {target_branch} branch (visible to all agents)")
        lines.append(f"   Status changes auto-commit to {target_branch} branch (visible to all agents)")
        lines.append(f"   ⚠️  You will see commits from other agents - IGNORE THEM")
        lines.append("=" * 80)
        lines.append("")

        if has_feedback:
            lines.append("⚠️  This work package has review feedback.")
            if review_feedback_ref:
                lines.append(f"   Canonical feedback reference: {review_feedback_ref}")
                if review_feedback_file is not None:
                    lines.append(f'   Read it first: cat "{review_feedback_file}"')
                else:
                    lines.append("   WARNING: review feedback reference is set, but the artifact is missing/unreadable.")
                    lines.append("   Ask reviewer to re-run move-task with --review-feedback-file.")
            else:
                lines.append("   WARNING: review_status=has_feedback but no review_feedback reference is set.")
                lines.append("   Ask reviewer to re-run move-task with --review-feedback-file.")
            lines.append("")

        # Research mission: Show deliverables path prominently
        if mission_type == "research" and deliverables_path:
            lines.append("╔" + "=" * 78 + "╗")
            lines.append("║  🔬 RESEARCH MISSION - TWO ARTIFACT TYPES                                 ║")
            lines.append("╠" + "=" * 78 + "╣")
            lines.append("║                                                                          ║")
            lines.append("║  📁 RESEARCH DELIVERABLES (your output):                                 ║")
            deliv_line = f"║     {deliverables_path:<69} ║"
            lines.append(deliv_line)
            lines.append("║     ↳ Create findings, reports, data here                                ║")
            lines.append("║     ↳ Commit to worktree branch                                          ║")
            lines.append(f"║     ↳ Will merge to {target_branch:<62} ║")
            lines.append("║                                                                          ║")
            lines.append("║  📋 PLANNING ARTIFACTS (kitty-specs/):                                   ║")
            lines.append("║     ↳ evidence-log.csv, source-register.csv                              ║")
            lines.append("║     ↳ Edit in planning repo (rare during implementation)                 ║")
            lines.append("║                                                                          ║")
            lines.append("║  ⚠️  DO NOT put research deliverables in kitty-specs/!                   ║")
            lines.append("╚" + "=" * 78 + "╝")
            lines.append("")

        # WP content marker and content
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  WORK PACKAGE PROMPT BEGINS                                            ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")
        lines.append(wp.path.read_text(encoding="utf-8"))
        lines.append("")
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  WORK PACKAGE PROMPT ENDS                                              ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")

        # Completion instructions at end
        lines.append("=" * 80)
        lines.append("🎯 IMPLEMENTATION COMPLETE? RUN THESE COMMANDS:")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"✅ Implementation complete and tested:")
        lines.append(f"   1. **Commit your implementation files:**")
        lines.append(f"      git status  # Check what you changed")
        lines.append(f"      git add <your-implementation-files>  # NOT WP status files")
        lines.append(f'      git commit -m "feat({normalized_wp_id}): <brief description>"')
        lines.append(f"      git log -1 --oneline  # Verify commit succeeded")
        lines.append(f"      (Use fix: for bugs, chore: for maintenance, docs: for documentation)")
        lines.append(f"   2. Mark all subtasks as done:")
        lines.append(f"      spec-kitty agent tasks mark-status {subtask_cmd} --status done --mission {mission_slug}")
        lines.append(f"   3. Move WP to review (will check for uncommitted changes):")
        lines.append(f'      spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --mission {mission_slug} --note "Ready for review: <summary>"')
        lines.append("")
        lines.append(f"⚠️  Blocked or cannot complete:")
        lines.append(f'   spec-kitty agent tasks add-history {normalized_wp_id} --mission {mission_slug} --note "Blocked: <reason>"')
        lines.append("")
        lines.append("⚠️  NOTE: The move-task command will FAIL if you have uncommitted changes!")
        lines.append("     Commit all implementation files BEFORE moving to for_review.")
        lines.append("     Dependent work packages need your committed changes.")
        lines.append("=" * 80)

        # Write full prompt to file
        full_content = "\n".join(lines)
        prompt_file = _write_prompt_to_file("implement", normalized_wp_id, full_content)

        # Output concise summary with directive to read the prompt
        print()
        print(f"📍 Workspace: cd {workspace_path}")
        if workspace.lane_id:
            shared = ", ".join(workspace.lane_wp_ids or [normalized_wp_id])
            print(f"   Lane workspace: {workspace.lane_id} (shared by {shared})")
        else:
            print("   Repository-root planning workspace")
        if has_feedback:
            if review_feedback_ref:
                print(f"⚠️  Has review feedback - read reference: {review_feedback_ref}")
            else:
                print("⚠️  Has review feedback - but no review_feedback reference is set")
        if mission_type == "research" and deliverables_path:
            print(f"🔬 Research deliverables: {deliverables_path}")
            print(f"   (NOT in kitty-specs/ - those are planning artifacts)")
        print()
        print("▶▶▶ NEXT STEP: Read the full prompt file now:")
        print(f"    cat {prompt_file}")
        print()
        print("After implementation, run:")
        print(f'  1. git status && git add <your-files> && git commit -m "feat({normalized_wp_id}): <description>"')
        print(f"  2. spec-kitty agent tasks mark-status {subtask_cmd} --status done --mission {mission_slug}")
        print(f'  3. spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --mission {mission_slug} --note "Ready for review"')
        print(f"     (Pre-flight check will verify no uncommitted changes)")

    except Exception as e:
        print(f"Error: {e}")
        raise typer.Exit(1)


def _resolve_review_context(
    workspace_path: Path,
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    wp_frontmatter: str,
) -> dict:
    """Resolve git branch and base context for review prompts.

    Determines the WP's branch name, its base branch (what it was branched
    from), and the number of commits unique to this WP so reviewers know
    exactly what to diff against instead of guessing.

    Strategy:
    1. Get actual branch name from the worktree
    2. Extract WP dependencies from frontmatter to try dependency branches
    3. Also try common base branches (main, 2.x, master, develop)
    4. Pick the candidate with fewest commits ahead (closest ancestor)
    """
    ctx: dict = {
        "branch_name": "unknown",
        "base_branch": "unknown",
        "commit_count": 0,
    }

    if not workspace_path.exists():
        return ctx

    workspace = resolve_workspace_for_wp(repo_root, mission_slug, wp_id)
    if workspace.resolution_kind == "repo_root":
        wp_paths = sorted((repo_root / "kitty-specs" / mission_slug / "tasks").glob(f"{wp_id}*.md"))
        claim = subprocess.run(
            [
                "git",
                "log",
                "--format=%H%x00%s",
                "--",
                *(str(path) for path in wp_paths),
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        claim_commit: str | None = None
        for raw in claim.stdout.splitlines():
            commit_hash, _, subject = raw.partition("\x00")
            if not commit_hash:
                continue
            if f"Move {wp_id} to in_progress" in subject or f"{wp_id} claimed for implementation" in subject or f"Start {wp_id} implementation" in subject:
                claim_commit = commit_hash.strip()
                break
        if claim_commit is None:
            return ctx
        count = subprocess.run(
            ["git", "rev-list", "--count", f"{claim_commit}..HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        commit_count = int(count.stdout.strip()) if count.returncode == 0 and count.stdout.strip().isdigit() else 1
        ctx["branch_name"] = "HEAD"
        ctx["base_branch"] = claim_commit
        ctx["commit_count"] = commit_count
        return ctx

    # Get actual branch name from worktree
    from specify_cli.core.git_ops import get_current_branch

    branch = get_current_branch(workspace_path)
    if branch:
        ctx["branch_name"] = branch
    else:
        return ctx

    branch = ctx["branch_name"]

    # Build candidate base branches
    candidates: list[str] = []

    if workspace.context and workspace.context.base_branch:
        candidates.append(workspace.context.base_branch)

    # From WP dependencies (e.g., dependencies: ["WP01"]). Skip dependencies
    # whose workspace has no branch — that's the case for planning-artifact
    # WPs that resolve to the repository root (FR-002/FR-004). Their lack of
    # a branch is intentional and they cannot serve as a merge-base candidate
    # for the current code-change branch. Letting None flow into the
    # candidates list crashes git merge-base with TypeError.
    dep_match = re.search(r"dependencies:\s*\[([^\]]*)\]", wp_frontmatter)
    if dep_match:
        dep_content = dep_match.group(1).strip()
        if dep_content:
            dep_ids = re.findall(r'"?(WP\d+)"?', dep_content)
            for dep_id in dep_ids:
                try:
                    dep_workspace = resolve_workspace_for_wp(repo_root, mission_slug, dep_id)
                except (ValueError, FileNotFoundError):
                    # A malformed or missing dependency workspace must not
                    # poison the review-context resolution for the current WP.
                    continue
                dep_branch = dep_workspace.branch_name
                if dep_branch and dep_branch != branch:
                    candidates.append(dep_branch)

    # Common base branches
    candidates.extend(["main", "2.x", "master", "develop"])

    # Find closest ancestor (fewest commits ahead = most specific base)
    best_base = None
    best_count = -1

    for candidate in candidates:
        mb = subprocess.run(
            ["git", "merge-base", branch, candidate],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if mb.returncode != 0:
            continue

        count_r = subprocess.run(
            ["git", "rev-list", "--count", f"{mb.stdout.strip()}..{branch}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if count_r.returncode != 0:
            continue

        count = int(count_r.stdout.strip())
        if best_count == -1 or count < best_count:
            best_count = count
            best_base = candidate

    if best_base:
        ctx["base_branch"] = best_base
        ctx["commit_count"] = best_count

    return ctx


def _find_first_for_review_wp(repo_root: Path, mission_slug: str) -> Optional[str]:
    """Find the first WP file with lane: "for_review".

    Args:
        repo_root: Repository root path
        mission_slug: Feature slug

    Returns:
        WP ID of first for_review task, or None if not found
    """
    from specify_cli.core.paths import is_worktree_context

    cwd = Path.cwd().resolve()

    # Check if we're in a worktree - if so, use worktree's kitty-specs
    if is_worktree_context(cwd):
        # We're in a worktree, look for kitty-specs relative to cwd
        if (cwd / "kitty-specs" / mission_slug).exists():
            tasks_dir = cwd / "kitty-specs" / mission_slug / "tasks"
        else:
            # Walk up to find kitty-specs
            current = cwd
            while current != current.parent:
                if (current / "kitty-specs" / mission_slug).exists():
                    tasks_dir = current / "kitty-specs" / mission_slug / "tasks"
                    break
                current = current.parent
            else:
                # Fallback to repo_root
                tasks_dir = repo_root / "kitty-specs" / mission_slug / "tasks"
    else:
        # We're in main repo
        tasks_dir = repo_root / "kitty-specs" / mission_slug / "tasks"

    if not tasks_dir.exists():
        return None

    # Find all WP files
    wp_files = sorted(tasks_dir.glob("WP*.md"))

    # Load lanes from canonical event log (lane is event-log-only)
    feature_dir = tasks_dir.parent
    _fr_events = []
    try:
        from specify_cli.status.store import read_events as _fr_read_events
        from specify_cli.status.reducer import reduce as _fr_reduce

        _fr_events = _fr_read_events(feature_dir)
        _fr_snapshot = _fr_reduce(_fr_events) if _fr_events else None
        _fr_lanes: dict = {}
        if _fr_snapshot:
            for _fr_wp_id, _fr_state in _fr_snapshot.work_packages.items():
                _fr_lanes[_fr_wp_id] = Lane(_fr_state.get("lane", Lane.PLANNED))
    except Exception:
        _fr_lanes = {}

    def _is_review_claimed(_wp_id: str) -> bool:
        for _event in reversed(_fr_events):
            if getattr(_event, "wp_id", None) == _wp_id:
                return bool(_event.to_lane == Lane.IN_PROGRESS and _event.review_ref == "action-review-claim")
        return False

    for wp_file in wp_files:
        content = wp_file.read_text(encoding="utf-8-sig")
        frontmatter, _, _ = split_frontmatter(content)
        wp_id = extract_scalar(frontmatter, "work_package_id")
        if wp_id and _fr_lanes.get(wp_id, Lane.PLANNED) == Lane.FOR_REVIEW:
            return wp_id

    for wp_file in wp_files:
        content = wp_file.read_text(encoding="utf-8-sig")
        frontmatter, _, _ = split_frontmatter(content)
        wp_id = extract_scalar(frontmatter, "work_package_id")
        if wp_id and _fr_lanes.get(wp_id, Lane.PLANNED) == Lane.IN_PROGRESS and _is_review_claimed(wp_id):
            return wp_id

    return None


@app.command(name="review")
def review(
    wp_id: Annotated[Optional[str], typer.Argument(help="Work package ID (e.g., WP01) - auto-detects first for_review if omitted")] = None,
    mission: Annotated[Optional[str], typer.Option("--mission", help="Mission slug")] = None,
    feature: Annotated[Optional[str], typer.Option("--feature", hidden=True, help="(deprecated) Use --mission")] = None,
    agent: Annotated[Optional[str], typer.Option("--agent", help="Agent name (required for auto-move to in_progress)")] = None,
) -> None:
    """Display work package prompt with review instructions.

    This command outputs the full work package prompt (including any review
    feedback from previous reviews) so agents can review the implementation.

    Automatically moves WP from for_review to in_progress (requires --agent to track who is reviewing).

    Examples:
        spec-kitty agent action review WP01 --agent claude
        spec-kitty agent action review wp02 --agent codex
        spec-kitty agent action review --agent gemini  # auto-detects first for_review WP
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            print("Error: Could not locate project root")
            raise typer.Exit(1)

        mission_slug = _find_mission_slug(explicit_mission=mission, explicit_feature=feature, repo_root=repo_root)

        # Ensure planning repo is on the target branch before we start
        # (needed for auto-commits and status tracking inside this command)
        main_repo_root, target_branch = _ensure_target_branch_checked_out(repo_root, mission_slug)

        # Determine which WP to review
        if wp_id:
            normalized_wp_id = _normalize_wp_id(wp_id)
        else:
            # Auto-detect first for_review WP
            normalized_wp_id = _find_first_for_review_wp(repo_root, mission_slug)
            if not normalized_wp_id:
                print("Error: No work packages ready for review. Specify a WP ID explicitly.")
                raise typer.Exit(1)

        # Load work package
        try:
            wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
        except RuntimeError as e:
            if _is_missing_canonical_status_error(e):
                raise RuntimeError(_missing_canonical_status_message(normalized_wp_id, mission_slug)) from e
            raise

        # Move to in_progress lane if not already there.
        # Explicit WP review requests must target for_review (or already review-claimed in_progress).
        # Lane is event-log-only; read from canonical event log (no frontmatter fallback)
        feature_dir = main_repo_root / "kitty-specs" / mission_slug
        from specify_cli.status.lane_reader import get_wp_lane as _rv_get_wp_lane
        from specify_cli.status.store import read_events as _rv_read_events
        from specify_cli.status.reducer import reduce as _rv_reduce

        _rv_events = _rv_read_events(feature_dir)
        _rv_snapshot = _rv_reduce(_rv_events) if _rv_events else None
        _rv_has_canonical = _rv_snapshot is not None and normalized_wp_id in _rv_snapshot.work_packages
        if not _rv_has_canonical:
            raise RuntimeError(_missing_canonical_status_message(normalized_wp_id, mission_slug))
        current_lane = _rv_get_wp_lane(feature_dir, normalized_wp_id)
        review_workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, normalized_wp_id)
        status_execution_mode = "direct_repo" if review_workspace.resolution_kind == "repo_root" else "worktree"
        latest_event = None
        for _event in reversed(_rv_events):
            if getattr(_event, "wp_id", None) == normalized_wp_id:
                latest_event = _event
                break
        is_review_claimed = bool(latest_event is not None and latest_event.to_lane == Lane.IN_PROGRESS and latest_event.review_ref == "action-review-claim")
        if current_lane == Lane.IN_PROGRESS and not is_review_claimed:
            print(f"Error: {normalized_wp_id} is still being implemented, not claimed for review.")
            print("Only work packages in 'for_review' (or already review-claimed in_progress) can start workflow review.")
            print(f"Move it first: spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --mission {mission_slug}")
            raise typer.Exit(1)
        if current_lane not in {Lane.FOR_REVIEW, Lane.IN_PROGRESS}:
            print(f"Error: {normalized_wp_id} is in lane '{current_lane}', not 'for_review'.")
            print("Only work packages in 'for_review' can start workflow review.")
            print(f"Move it first: spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --mission {mission_slug}")
            raise typer.Exit(1)

        # Bulk edit occurrence classification gate — artifact admissibility (FR-006)
        from specify_cli.bulk_edit.gate import (
            check_review_diff_compliance,
            ensure_occurrence_classification_ready,
            render_diff_check_failure,
            render_gate_failure,
        )
        from rich.console import Console as _RichConsole
        _rich_console = _RichConsole()
        _gate_result = ensure_occurrence_classification_ready(feature_dir)
        if not _gate_result.passed:
            render_gate_failure(_gate_result, _rich_console)
            raise typer.Exit(1)

        # Bulk edit diff compliance — per-file category enforcement (FR-007, FR-008).
        # When this is a bulk_edit mission, inspect the WP's diff against its lane
        # base branch and reject modifications to forbidden or unclassified surfaces.
        if _gate_result.change_mode == "bulk_edit":
            # The mission branch is the canonical base for a WP lane diff. If the
            # review is running from the main repo (not a lane worktree), this
            # still resolves because the mission branch exists until merge
            # cleanup. If the branch cannot be resolved, fall back to the
            # target_branch captured earlier in this function.
            _base_ref = f"kitty/mission-{mission_slug}"
            _diff_result = check_review_diff_compliance(
                feature_dir=feature_dir,
                repo_root=main_repo_root,
                base_ref=_base_ref,
                head_ref="HEAD",
            )
            if _diff_result is None:
                # Non-bulk-edit mission — skip silently. check_review_diff_compliance
                # returns None when change_mode is not bulk_edit, which shouldn't
                # happen here given the outer guard, but belt-and-braces.
                pass
            elif not _diff_result.passed:
                render_diff_check_failure(_diff_result, _rich_console)
                raise typer.Exit(1)
            elif _diff_result.warnings:
                # Surface manual_review notes but don't block.
                for _w in _diff_result.warnings:
                    _rich_console.print(f"[yellow]manual_review:[/] {_w}")

        if current_lane != Lane.IN_PROGRESS:
            # Require --agent parameter to track who is reviewing
            if not agent:
                print("Error: --agent parameter required when starting review.")
                print(f"  Usage: spec-kitty agent action review {normalized_wp_id} --agent <your-name>")
                print("  Example: spec-kitty agent action review WP01 --agent claude")
                print()
                print("If you're using a generated agent command file, --agent is already included.")
                print("This tracks WHO is reviewing the WP (prevents abandoned reviews).")
                raise typer.Exit(1)

            from datetime import datetime, timezone
            import os

            # Capture current shell PID
            shell_pid = str(os.getppid())  # Parent process ID (the shell running this command)

            with feature_status_lock(main_repo_root, mission_slug):
                # Emit the actual for_review -> in_progress transition
                emit_status_transition(
                    feature_dir=feature_dir,
                    mission_slug=mission_slug,
                    wp_id=normalized_wp_id,
                    to_lane=Lane.IN_PROGRESS,
                    actor=agent,
                    force=True,  # review claim is always allowed
                    reason="Started review via action command",
                    review_ref="action-review-claim",
                    workspace_context=f"action-review:{main_repo_root}",
                    execution_mode=status_execution_mode,
                    repo_root=main_repo_root,
                )

                # Post-emit: apply operational metadata fields to WP file (lane is event-log-only)
                wp_content = wp.path.read_text(encoding="utf-8-sig")
                updated_front, updated_body, updated_padding = split_frontmatter(wp_content)
                updated_front = set_scalar(updated_front, "agent", agent)
                updated_front = set_scalar(updated_front, "shell_pid", shell_pid)

                # Build history entry (no lane= segment; event log is sole lane authority)
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                history_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – Started review via action command"

                # Add history entry to body
                updated_body = append_activity_log(updated_body, history_entry)

                # Build and write updated document
                updated_doc = build_document(updated_front, updated_body, updated_padding)
                write_text_within_directory(wp.path, updated_doc, root=main_repo_root, encoding="utf-8")

                # Atomic commit: WP file + all status artifacts (#211, #212)
                actual_wp_path = wp.path.resolve()
                status_artifacts = _collect_status_artifacts(feature_dir)
                commit_success = safe_commit(
                    repo_path=main_repo_root,
                    files_to_commit=[actual_wp_path] + status_artifacts,
                    commit_message=f"chore: Start {normalized_wp_id} review [{agent}]",
                    allow_empty=True,  # OK if already in this state
                )
                if not commit_success:
                    print(f"Error: Failed to commit workflow status update for {normalized_wp_id}. Review claim aborted.")
                    raise typer.Exit(1)

            print(f"✓ Claimed {normalized_wp_id} for review (agent: {agent}, PID: {shell_pid}, target: {target_branch})")

            # Reload to get updated content
            wp = locate_work_package(repo_root, mission_slug, normalized_wp_id)
        else:
            print(f"⚠️  {normalized_wp_id} is already in lane: {current_lane}. Workflow review will not move it to in_progress.")

        workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, normalized_wp_id)
        workspace_path = workspace.worktree_path

        # Concurrent review isolation: acquire review lock or apply env-var isolation
        from specify_cli.review.lock import ReviewLock, ReviewLockError, _get_isolation_config, _apply_env_var_isolation

        isolation_config = _get_isolation_config(main_repo_root)
        if isolation_config and isolation_config.get("strategy") == "env_var":
            _apply_env_var_isolation(isolation_config, agent or "unknown", normalized_wp_id)
        else:
            try:
                ReviewLock.acquire(Path(workspace_path), normalized_wp_id, agent or "unknown")
            except ReviewLockError as e:
                print(f"[red]{e}[/red]")
                raise typer.Exit(1)

        # Ensure workspace exists (attach to the real branch if needed).
        if not workspace.exists:
            # Ensure .worktrees directory exists
            worktrees_dir = main_repo_root / ".worktrees"
            worktrees_dir.mkdir(parents=True, exist_ok=True)

            branch_name = workspace.branch_name
            branch_exists = subprocess.run(
                ["git", "rev-parse", "--verify", branch_name],
                cwd=main_repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if branch_exists.returncode == 0:
                worktree_cmd = ["git", "worktree", "add", str(workspace_path), branch_name]
            else:
                worktree_cmd = ["git", "worktree", "add", str(workspace_path), "-b", branch_name]
            result = subprocess.run(worktree_cmd, cwd=main_repo_root, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

            if result.returncode != 0:
                print(f"Warning: Could not create workspace: {result.stderr}")
            else:
                print(f"✓ Created workspace: {workspace_path}")
                workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, normalized_wp_id)

        # Resolve git context (branch name, base branch, commit count)
        review_ctx = _resolve_review_context(workspace_path, main_repo_root, mission_slug, normalized_wp_id, wp.frontmatter)

        # Capture dependency warning for both file and summary
        dependents_warning = []
        feature_dir = repo_root / "kitty-specs" / mission_slug
        graph = build_dependency_graph(feature_dir)
        dependents = get_dependents(normalized_wp_id, graph)
        if dependents:
            # Load lanes from event log (lane is event-log-only)
            try:
                from specify_cli.status.store import read_events as _rw_read_events
                from specify_cli.status.reducer import reduce as _rw_reduce

                _rw_events = _rw_read_events(feature_dir)
                _rw_snapshot = _rw_reduce(_rw_events) if _rw_events else None
                _rw_lanes: dict = {}
                if _rw_snapshot:
                    for _rw_wp_id, _rw_state in _rw_snapshot.work_packages.items():
                        _rw_lanes[_rw_wp_id] = Lane(_rw_state.get("lane", Lane.PLANNED))
            except Exception:
                _rw_lanes = {}

            incomplete: list[str] = []
            for dependent_id in dependents:
                lane = _rw_lanes.get(dependent_id, Lane.PLANNED)
                if lane in {Lane.PLANNED, Lane.IN_PROGRESS, Lane.FOR_REVIEW}:
                    incomplete.append(dependent_id)
            if incomplete:
                dependents_list = ", ".join(sorted(incomplete))
                dependents_warning.append(f"⚠️  Dependency Alert: {dependents_list} depend on {normalized_wp_id} (not yet done)")
                dependents_warning.append("   If you request changes, notify those agents to rebase.")

        # Build full prompt content for file
        lines = []
        lines.append("=" * 80)
        lines.append(f"REVIEW: {normalized_wp_id}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Source: {wp.path}")
        lines.append("")
        lines.append(f"Workspace: {workspace_path}")
        lines.append(_workspace_contract_description(workspace, normalized_wp_id))
        lines.append("")
        lines.append(_render_charter_context(repo_root, "review"))
        lines.append("")

        # Add dependency warning to file
        if dependents_warning:
            lines.extend(dependents_warning)
            lines.append("")

        # CRITICAL: WP isolation rules
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  🚨 CRITICAL: WORK PACKAGE ISOLATION RULES                              ║")
        lines.append("╠" + "=" * 78 + "╣")
        lines.append(f"║  YOU ARE REVIEWING: {normalized_wp_id:<56} ║")
        lines.append("║                                                                          ║")
        lines.append("║  ✅ DO:                                                                  ║")
        lines.append(f"║     • Only modify status of {normalized_wp_id:<47} ║")
        lines.append("║     • Ignore git commits and status changes from other agents           ║")
        lines.append("║                                                                          ║")
        lines.append("║  ❌ DO NOT:                                                              ║")
        lines.append(f"║     • Change status of any WP other than {normalized_wp_id:<34} ║")
        lines.append("║     • React to or investigate other WPs' status changes                 ║")
        lines.append(f"║     • Review or approve any WP other than {normalized_wp_id:<32} ║")
        lines.append("║                                                                          ║")
        lines.append("║  WHY: Multiple agents work in parallel. Each owns exactly ONE WP.       ║")
        lines.append("║       Git commits from other WPs are other agents - ignore them.        ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")

        # Inject worktree topology context for stacked branches
        try:
            from specify_cli.core.worktree_topology import (
                materialize_worktree_topology,
                render_topology_json,
            )

            topology = materialize_worktree_topology(repo_root, mission_slug)
            if topology.has_stacking:
                lines.extend(render_topology_json(topology, current_wp_id=normalized_wp_id))
                lines.append("")
        except Exception as exc:
            lines.append(f"[Topology unavailable: {exc}]")
            lines.append("")

        # Git review context — tells reviewer exactly what to diff against
        if review_ctx["base_branch"] != "unknown":
            base = review_ctx["base_branch"]
            branch_ref = review_ctx["branch_name"]
            review_paths = ""
            if workspace.resolution_kind == "repo_root":
                wp_meta, _ = read_wp_frontmatter(wp.path)
                if wp_meta.owned_files:
                    review_pathspecs = list(wp_meta.owned_files)
                    mission_root = f"kitty-specs/{mission_slug}/"
                    if any(path.startswith(mission_root) for path in review_pathspecs):
                        review_pathspecs.extend(
                            [
                                f":(exclude){mission_root}tasks/**",
                                f":(exclude){mission_root}tasks.md",
                                f":(exclude){mission_root}status.events.jsonl",
                                f":(exclude){mission_root}status.json",
                            ]
                        )
                    review_paths = " -- " + " ".join(review_pathspecs)
            lines.append("─── GIT REVIEW CONTEXT " + "─" * 57)
            lines.append(f"Branch:      {branch_ref}")
            lines.append(f"Base branch: {base} ({review_ctx['commit_count']} commits ahead)")
            lines.append("")
            lines.append("Review commands (run in the workspace):")
            lines.append(f"  cd {workspace_path}")
            lines.append(f"  git log {base}..{branch_ref} --oneline{review_paths}           # WP commits only")
            lines.append(f"  git diff {base}..{branch_ref} --stat{review_paths}             # Changed files")
            lines.append(f"  git diff {base}..{branch_ref}{review_paths}                    # Full diff")
            lines.append("─" * 80)
            lines.append("")
        elif workspace.resolution_kind == "repo_root":
            lines.append("─── GIT REVIEW CONTEXT " + "─" * 57)
            lines.append("Review commands unavailable: no deterministic implementation claim commit found for this WP.")
            lines.append("Re-run review after the WP has a committed implementation claim on this mission.")
            lines.append("─" * 80)
            lines.append("")

        # Baseline Test Context — load cached baseline and surface pre-existing failures
        _rv_wp_slug = wp.path.stem
        _rv_feature_dir = main_repo_root / "kitty-specs" / mission_slug
        try:
            from specify_cli.review.baseline import BaselineTestResult as _BaselineTestResult

            _rv_baseline_path = _rv_feature_dir / "tasks" / _rv_wp_slug / "baseline-tests.json"
            _rv_baseline = _BaselineTestResult.load(_rv_baseline_path)
            if _rv_baseline is not None and _rv_baseline.failed > 0:
                lines.append("─── BASELINE TEST CONTEXT " + "─" * 54)
                lines.append(
                    f"**{_rv_baseline.failed} test failure(s) existed BEFORE this WP** (base: {_rv_baseline.base_branch} @ {_rv_baseline.base_commit[:7]}):"
                )
                lines.append("")
                lines.append("| Test | Error | File |")
                lines.append("|------|-------|------|")
                for _rv_f in _rv_baseline.failures:
                    lines.append(f"| {_rv_f.test} | {_rv_f.error[:80]} | {_rv_f.file} |")
                lines.append("")
                lines.append("**These failures are NOT regressions introduced by this WP.** Only flag test failures that are NOT in this list.")
                lines.append("─" * 80)
                lines.append("")
            elif _rv_baseline is not None and _rv_baseline.failed == -1:
                lines.append("─── BASELINE TEST CONTEXT " + "─" * 54)
                lines.append(
                    "**Warning**: Baseline test capture failed at implement time. "
                    "Cannot distinguish pre-existing failures from regressions. "
                    "Exercise caution when attributing test failures to this WP."
                )
                lines.append("─" * 80)
                lines.append("")
        except Exception as _rv_bl_err:
            import logging as _rv_bl_log

            _rv_bl_log.getLogger(__name__).warning("Baseline load error in review: %s", _rv_bl_err)

        # Determine the writable in-repo feedback path.
        # Derive wp_slug from the WP file stem (e.g. "WP03-external-reviewer-handoff").
        wp_slug = wp.path.stem  # e.g. "WP03-external-reviewer-handoff"
        sub_artifact_dir = main_repo_root / "kitty-specs" / mission_slug / "tasks" / wp_slug
        sub_artifact_dir.mkdir(parents=True, exist_ok=True)

        # Determine the next review cycle number based on existing files.
        existing_cycles = sorted(sub_artifact_dir.glob("review-cycle-*.md"))
        next_cycle = len(existing_cycles) + 1
        review_feedback_path = sub_artifact_dir / f"review-cycle-{next_cycle}.md"

        # Next steps
        lines.append("=" * 80)
        lines.append("WHEN YOU'RE DONE:")
        lines.append("=" * 80)
        lines.append("✓ Review passed, no issues:")
        lines.append(f'  spec-kitty agent tasks move-task {normalized_wp_id} --to approved --mission {mission_slug} --note "Review passed"')
        lines.append("")
        lines.append(f"⚠️  Changes requested:")
        lines.append(f"  1. Write feedback to (in-repo, committed with the project):")
        lines.append(f"     {review_feedback_path}")
        lines.append(
            f"  2. spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file {review_feedback_path} --mission {mission_slug}"
        )
        lines.append("  3. move-task stores feedback reference in the event log and WP frontmatter")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"📍 WORKING DIRECTORY:")
        lines.append(f"   cd {workspace_path}")
        if workspace.lane_id:
            lines.append("   # Review the implementation in this workspace")
            lines.append("   # Read code, run tests, check against requirements")
            lines.append(f"   # When done, return to repo root: cd {repo_root}")
        else:
            lines.append("   # Review the planning-artifact changes directly in the repository root")
        lines.append("")
        lines.extend(_shared_artifact_guidance(workspace, repo_root, mission_slug))
        lines.append("")
        lines.append("📋 STATUS TRACKING:")
        lines.append(f"   kitty-specs/ status is tracked in {target_branch} branch (visible to all agents)")
        lines.append(f"   Status changes auto-commit to {target_branch} branch (visible to all agents)")
        lines.append(f"   ⚠️  You will see commits from other agents - IGNORE THEM")
        lines.append("=" * 80)
        lines.append("")
        lines.append("Review the implementation against the requirements below.")
        lines.append("Check code quality, tests, documentation, and adherence to spec.")
        lines.append("")

        # WP content marker and content
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  WORK PACKAGE PROMPT BEGINS                                            ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")
        lines.append(wp.path.read_text(encoding="utf-8"))
        lines.append("")
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  WORK PACKAGE PROMPT ENDS                                              ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")

        # Completion instructions at end
        lines.append("=" * 80)
        lines.append("🎯 REVIEW COMPLETE? RUN ONE OF THESE COMMANDS:")
        lines.append("=" * 80)
        lines.append("")
        lines.append("✅ APPROVE (no issues found):")
        lines.append(f'   spec-kitty agent tasks move-task {normalized_wp_id} --to approved --mission {mission_slug} --note "Review passed: <summary>"')
        lines.append("")
        lines.append(f"❌ REQUEST CHANGES (issues found):")
        lines.append(f"   1. Write feedback to the in-repo path (committed with the project):")
        lines.append(f"      cat > {review_feedback_path} <<'EOF'")
        lines.append(f"**Issue 1**: <description and how to fix>")
        lines.append(f"**Issue 2**: <description and how to fix>")
        lines.append(f"EOF")
        lines.append("")
        lines.append(f"   2. Move to planned with feedback:")
        lines.append(
            f"      spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file {review_feedback_path} --mission {mission_slug}"
        )
        lines.append("")
        lines.append("⚠️  NOTE: You MUST run one of these commands to complete the review!")
        lines.append("     The Python script handles all file updates automatically.")
        lines.append("=" * 80)

        # Write full prompt to file
        full_content = "\n".join(lines)
        prompt_file = _write_prompt_to_file("review", normalized_wp_id, full_content)

        # Output concise summary with directive to read the prompt
        print()
        if dependents_warning:
            for line in dependents_warning:
                print(line)
            print()
        print(f"📍 Workspace: cd {workspace_path}")
        if workspace.lane_id:
            shared = ", ".join(workspace.lane_wp_ids or [normalized_wp_id])
            print(f"   Lane workspace: {workspace.lane_id} (shared by {shared})")
        else:
            print("   Repository-root planning workspace")
        if review_ctx["base_branch"] != "unknown":
            base = review_ctx["base_branch"]
            print(f"🔀 Branch: {review_ctx['branch_name']} (based on {base}, {review_ctx['commit_count']} commits)")
            if workspace.resolution_kind == "repo_root":
                wp_meta, _ = read_wp_frontmatter(wp.path)
                review_pathspecs = list(wp_meta.owned_files)
                mission_root = f"kitty-specs/{mission_slug}/"
                if any(path.startswith(mission_root) for path in review_pathspecs):
                    review_pathspecs.extend(
                        [
                            f":(exclude){mission_root}tasks/**",
                            f":(exclude){mission_root}tasks.md",
                            f":(exclude){mission_root}status.events.jsonl",
                            f":(exclude){mission_root}status.json",
                        ]
                    )
                review_paths = " -- " + " ".join(review_pathspecs) if review_pathspecs else ""
                print(f"   Review diff: git log {base}..{review_ctx['branch_name']} --oneline{review_paths}")
            else:
                print(f"   Review diff: git log {base}..{review_ctx['branch_name']} --oneline")
        elif workspace.resolution_kind == "repo_root":
            print("🔀 Review diff unavailable: no deterministic implementation claim commit found for this WP")
        print()
        print("▶▶▶ NEXT STEP: Read the full prompt file now:")
        print(f"    cat {prompt_file}")
        print()
        print("After review, run:")
        print(f'  ✅ spec-kitty agent tasks move-task {normalized_wp_id} --to approved --mission {mission_slug} --note "Review passed"')
        print(f"  ❌ spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file {review_feedback_path} --mission {mission_slug}")

    except Exception as e:
        print(f"Error: {e}")
        raise typer.Exit(1)
