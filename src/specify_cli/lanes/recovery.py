"""Implementation crash recovery for lane worktrees.

Detects post-crash state by scanning for orphaned branches, workspace
contexts, and status events that are out of sync. Provides recovery
functions to reconcile worktrees, contexts, and status.

Recovery is conservative: it never advances WP status past in_progress.
All recovery transitions use actor="recovery" for auditability.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from specify_cli.lanes.branch_naming import parse_lane_id_from_branch
from specify_cli.status.models import Lane
from specify_cli.workspace_context import (
    WorkspaceContext,
    list_contexts,
    save_context,
)

logger = logging.getLogger(__name__)


RECOVERY_ACTOR = "recovery"

# Status lanes that recovery can advance through (never past in_progress)
_RECOVERY_CEILING = Lane.IN_PROGRESS


def _get_recovery_transitions(current_lane: Lane) -> list[Lane]:
    """Return the ordered list of Lane transitions recovery may emit from *current_lane*.

    Recovery is conservative: it never advances a WP past IN_PROGRESS.
    Uses ``validate_transition()`` from the canonical status module so that
    the transition matrix is the single source of truth.

    The progression recovery may emit is: planned -> claimed -> in_progress.
    Starting from *current_lane*, only transitions that are (a) allowed by the
    canonical matrix and (b) at or below the ceiling (IN_PROGRESS) are included.

    Guard conditions (actor, workspace_context, etc.) are not checked here
    because the actual ``emit_status_transition()`` call in ``reconcile_status``
    uses ``RECOVERY_ACTOR`` and handles guard failures by catching exceptions.
    This function only validates structural matrix membership.

    Returns an empty list when no recovery transition is possible.
    """
    from specify_cli.status.transitions import validate_transition
    from specify_cli.status.models import GuardContext

    # Ordered progression that recovery may advance through, capped at ceiling
    _PROGRESSION = [Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS]
    try:
        ceiling_index = _PROGRESSION.index(_RECOVERY_CEILING)
        start_index = _PROGRESSION.index(current_lane)
    except ValueError:
        # current_lane or ceiling not in the recovery progression
        return []

    result: list[Lane] = []
    from_lane: Lane = current_lane
    for target in _PROGRESSION[start_index + 1: ceiling_index + 1]:
        # Pass recovery context to satisfy actor/workspace guards.
        # Recovery is always authoritative and always runs in a worktree.
        ok, _err = validate_transition(
            from_lane.value,
            target.value,
            GuardContext(actor=RECOVERY_ACTOR, workspace_context="recovery"),
        )
        if ok:
            result.append(target)
            from_lane = target
        else:
            break
    return result


@dataclass
class RecoveryState:
    """Post-crash state for a single WP/lane combination."""

    wp_id: str
    lane_id: str
    branch_name: str
    branch_exists: bool
    worktree_exists: bool
    context_exists: bool
    status_lane: str  # current lane from event log
    has_commits: bool  # commits beyond base
    recovery_action: str  # "recreate_worktree" | "recreate_context" | "emit_transitions" | "no_action"
    # When consult_status_events=True and dep branches are merged-and-deleted,
    # this field records how the WP was resolved (e.g. "merged_and_deleted")
    resolution_note: str = ""


@dataclass
class RecoveryReport:
    """Summary of recovery operations performed."""

    recovered_wps: list[str]
    worktrees_recreated: int
    contexts_recreated: int
    transitions_emitted: int
    errors: list[str]
    # WPs whose dependency branches were merged-and-deleted but are ready to
    # start from the target branch tip (populated by scan_recovery_state when
    # consult_status_events=True).
    ready_to_start_from_target: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "recovered_wps": self.recovered_wps,
            "worktrees_recreated": self.worktrees_recreated,
            "contexts_recreated": self.contexts_recreated,
            "transitions_emitted": self.transitions_emitted,
            "errors": self.errors,
            "ready_to_start_from_target": self.ready_to_start_from_target,
        }


def _list_mission_branches(repo_root: Path, mission_slug: str) -> list[str]:
    """List all local branches matching kitty/mission-{slug}* pattern."""
    pattern = f"kitty/mission-{mission_slug}*"
    result = subprocess.run(
        ["git", "branch", "--list", pattern, "--format=%(refname:short)"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]


def _branch_has_commits_beyond(
    repo_root: Path, branch: str, base_branch: str,
) -> bool:
    """Check if a branch has commits beyond a base branch."""
    result = subprocess.run(
        ["git", "log", f"{base_branch}..{branch}", "--oneline", "-1"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def _worktree_exists_for_branch(repo_root: Path, branch: str) -> Path | None:
    """Check if a git worktree exists for a given branch. Returns path if found."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    current_path: str | None = None
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current_path = line[len("worktree "):]
        elif line.startswith("branch refs/heads/"):
            wt_branch = line[len("branch refs/heads/"):]
            if wt_branch == branch and current_path:
                return Path(current_path)
    return None


def _get_wp_lane_from_events(feature_dir: Path, wp_id: str) -> str:
    """Get the current lane for a WP from the status event log."""
    try:
        from specify_cli.status.reducer import reduce
        from specify_cli.status.store import read_events

        events = read_events(feature_dir)
        if events:
            snapshot = reduce(events)
            state = snapshot.work_packages.get(wp_id)
            if state:
                return str(Lane(state.get("lane", Lane.PLANNED)).value)
    except Exception:
        logger.debug("Could not read status events for %s in %s", wp_id, feature_dir)
    return str(Lane.PLANNED.value)


def _find_wp_ids_for_lane(
    feature_dir: Path, lane_id: str,
) -> list[str]:
    """Find WP IDs assigned to a lane from lanes.json."""
    try:
        from specify_cli.lanes.persistence import read_lanes_json

        manifest = read_lanes_json(feature_dir)
        if manifest is None:
            return []
        for lane in manifest.lanes:
            if lane.lane_id == lane_id:
                return list(lane.wp_ids)
    except Exception:
        logger.debug("Could not read lanes.json for %s in %s", lane_id, feature_dir)
    return []


def _find_mission_branch(feature_dir: Path) -> str:
    """Find the mission integration branch from lanes.json."""
    try:
        from specify_cli.lanes.persistence import read_lanes_json

        manifest = read_lanes_json(feature_dir)
        if manifest is not None:
            return str(manifest.mission_branch)
    except Exception:
        logger.debug("Could not read mission branch from %s", feature_dir)
    return ""


def _read_all_wp_ids_from_tasks(feature_dir: Path) -> list[str]:
    """Return all WP IDs found in the tasks/ directory."""
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return []
    import re as _re
    wp_id_re = _re.compile(r"^(WP\d{2,})", _re.IGNORECASE)
    wp_ids: list[str] = []
    for md_file in sorted(tasks_dir.glob("WP*.md")):
        m = wp_id_re.match(md_file.name)
        if m:
            wp_ids.append(m.group(1).upper())
    return wp_ids


def _read_wp_dependencies(feature_dir: Path, wp_id: str) -> list[str]:
    """Read the dependencies list from a WP file's frontmatter.

    Deliberately avoids importing anything from specify_cli.lanes.recovery
    to prevent circular import chains.
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return []
    import re as _re
    wp_id_re = _re.compile(rf"^{_re.escape(wp_id)}(?:[-_.].+)?\.md$", _re.IGNORECASE)
    for md_file in tasks_dir.glob("WP*.md"):
        if wp_id_re.match(md_file.name):
            try:
                from specify_cli.core.dependency_graph import parse_wp_dependencies
                return list(parse_wp_dependencies(md_file))
            except Exception:
                logger.debug("Could not parse dependencies from %s", md_file)
            break
    return []


def _get_all_wp_lanes_from_events(feature_dir: Path) -> dict[str, str]:
    """Return {wp_id: lane} mapping from the status event log.

    Returns an empty dict when the event log is absent or unreadable.
    """
    try:
        from specify_cli.status.reducer import reduce
        from specify_cli.status.store import read_events

        events = read_events(feature_dir)
        if not events:
            return {}
        snapshot = reduce(events)
        return {wp_id: str(state.get("lane", "planned"))
                for wp_id, state in snapshot.work_packages.items()}
    except Exception:
        logger.debug("Could not read all WP lanes from %s", feature_dir)
        return {}


def scan_recovery_state(  # noqa: C901
    repo_root: Path,
    mission_slug: str,
    *,
    consult_status_events: bool = True,
) -> list[RecoveryState]:
    """Scan for post-crash implementation state.

    Lists branches matching kitty/mission-{slug}*, cross-references
    workspace contexts and status events to detect inconsistencies.

    When ``consult_status_events=True`` (the default), the scanner also
    reads ``kitty-specs/<mission_slug>/status.events.jsonl`` and:

    - Marks WPs whose branch is absent but whose event-log lane is ``done``
      as ``merged_and_deleted`` rather than reporting them as missing.
    - Populates ``RecoveryState.ready_to_start_from_target`` for WPs whose
      declared dependencies are ALL ``done`` according to the event log.

    When ``consult_status_events=False``, only the live-branch scan runs
    (legacy path, no event-log consultation).

    Returns a list of RecoveryState objects for WPs that need attention.
    The returned list now also contains synthetic RecoveryState entries
    (recovery_action="no_action") for WPs that are ``ready_to_start_from_target``
    even though they have no live branch — callers can check the
    ``resolution_note`` field to distinguish these from real recovery cases.
    """
    feature_dir = repo_root / "kitty-specs" / mission_slug

    # Collect all lane branches (skip the mission integration branch itself)
    branches = _list_mission_branches(repo_root, mission_slug)
    lane_branches = [
        b for b in branches
        if parse_lane_id_from_branch(b) is not None
    ]

    mission_branch = _find_mission_branch(feature_dir)
    if not mission_branch:
        # Fall back to convention
        mission_branch = f"kitty/mission-{mission_slug}"

    # Build a map of existing contexts by lane_id
    contexts_by_lane: dict[str, WorkspaceContext] = {}
    for ctx in list_contexts(repo_root):
        if ctx.mission_slug == mission_slug:
            contexts_by_lane[ctx.lane_id] = ctx

    # -----------------------------------------------------------------
    # Status-events-aware path (consult_status_events=True)
    # -----------------------------------------------------------------
    # Build a full lane-snapshot so we can answer:
    # (a) Is this WP already "done" (merged-and-deleted)?
    # (b) Are all of this WP's declared deps "done"?
    all_wp_lanes: dict[str, str] = {}
    if consult_status_events:
        all_wp_lanes = _get_all_wp_lanes_from_events(feature_dir)

    recovery_states: list[RecoveryState] = []

    for branch in lane_branches:
        lane_id = parse_lane_id_from_branch(branch)
        if lane_id is None:
            continue

        # Check worktree existence
        worktree_path_from_git = _worktree_exists_for_branch(repo_root, branch)
        expected_worktree = repo_root / ".worktrees" / f"{mission_slug}-{lane_id}"
        worktree_exists = (
            worktree_path_from_git is not None
            or expected_worktree.exists()
        )

        # Check context existence
        context = contexts_by_lane.get(lane_id)
        context_exists = context is not None

        # Check if branch has commits beyond the mission branch
        has_commits = _branch_has_commits_beyond(repo_root, branch, mission_branch)

        # Get WP IDs for this lane
        wp_ids = _find_wp_ids_for_lane(feature_dir, lane_id)
        if not wp_ids:
            # If we can't find WP IDs from lanes.json, use context
            wp_ids = list(context.lane_wp_ids) if context and context.lane_wp_ids else ["unknown"]

        # Determine recovery action for each WP in the lane
        for wp_id in wp_ids:
            status_lane = _get_wp_lane_from_events(feature_dir, wp_id)

            # Determine the needed recovery action
            if not worktree_exists and not context_exists:
                # Both missing but branch exists — need full recovery
                recovery_action = "recreate_worktree"
            elif not worktree_exists and context_exists:
                # Context exists but worktree is gone
                recovery_action = "recreate_worktree"
            elif worktree_exists and not context_exists:
                # Worktree exists but context is gone
                recovery_action = "recreate_context"
            elif has_commits and bool(_get_recovery_transitions(Lane(status_lane))):
                # Everything exists but status is behind
                recovery_action = "emit_transitions"
            else:
                recovery_action = "no_action"

            recovery_states.append(
                RecoveryState(
                    wp_id=wp_id,
                    lane_id=lane_id,
                    branch_name=branch,
                    branch_exists=True,
                    worktree_exists=worktree_exists,
                    context_exists=context_exists,
                    status_lane=status_lane,
                    has_commits=has_commits,
                    recovery_action=recovery_action,
                )
            )

    if not consult_status_events:
        # Legacy path: no event-log consultation, return early.
        return recovery_states

    # -----------------------------------------------------------------
    # Extended status-events path: scan WPs with NO live branch
    # -----------------------------------------------------------------
    # Build the set of WP IDs already represented in recovery_states.
    represented_wps = {rs.wp_id for rs in recovery_states}

    # Determine the set of expected WPs from lanes.json / tasks dir.
    all_task_wp_ids = _read_all_wp_ids_from_tasks(feature_dir)
    # Also pull from lanes.json if available.
    try:
        from specify_cli.lanes.persistence import read_lanes_json
        manifest = read_lanes_json(feature_dir)
        if manifest is not None:
            for lane in manifest.lanes:
                for wid in lane.wp_ids:
                    if wid not in all_task_wp_ids:
                        all_task_wp_ids.append(wid)
    except Exception:  # noqa: BLE001
        logger.debug("Could not read lanes.json for wp enumeration in %s", feature_dir)

    # For every known WP that is NOT represented by a live branch, check
    # whether the event log says it is "done" and whether its dependents
    # are ready to start.
    for wp_id in all_task_wp_ids:
        if wp_id in represented_wps:
            continue

        event_lane = all_wp_lanes.get(wp_id, Lane.PLANNED.value)

        if event_lane == Lane.DONE.value:
            # WP is done in the event log but has no live branch →
            # it was merged-and-deleted. Record it as a synthetic
            # no-action state with a resolution_note so callers know
            # why the branch is absent.
            recovery_states.append(
                RecoveryState(
                    wp_id=wp_id,
                    lane_id="",
                    branch_name="",
                    branch_exists=False,
                    worktree_exists=False,
                    context_exists=False,
                    status_lane=event_lane,
                    has_commits=False,
                    recovery_action="no_action",
                    resolution_note="merged_and_deleted",
                )
            )

    # Build the updated represented set (now includes merged-and-deleted).
    represented_wps = {rs.wp_id for rs in recovery_states}

    # Compute ready_to_start_from_target: a WP whose branch is absent AND
    # not yet done AND all its declared deps are done (either via live
    # merged_and_deleted record above or via event-log lane == "done").
    done_wp_ids: set[str] = set()
    for rs in recovery_states:
        if rs.status_lane == Lane.DONE.value or rs.resolution_note == "merged_and_deleted":
            done_wp_ids.add(rs.wp_id)
    # Also include WPs the event-log says are done that may not appear in
    # the task files list yet.
    for wp_id_ev, lane_ev in all_wp_lanes.items():
        if lane_ev == Lane.DONE.value:
            done_wp_ids.add(wp_id_ev)

    # We only compute ready_to_start when the event log shows that at least
    # one WP has been merged-and-deleted. If the log is empty (mission not
    # started) or has no done entries, there is no "post-merge" context and
    # the ready_to_start list is meaningless.
    ready_to_start: list[str] = []
    if not done_wp_ids:
        # No done WPs → not in a post-merge state; skip ready_to_start
        pass
    else:
        for wp_id in all_task_wp_ids:
            if wp_id in done_wp_ids:
                continue  # already done
            # Skip WPs that have a live branch (being actively worked on)
            if wp_id in represented_wps:
                existing = next((rs for rs in recovery_states if rs.wp_id == wp_id), None)
                if existing and existing.resolution_note not in ("merged_and_deleted", "ready_to_start_from_target", ""):
                    continue

            deps = _read_wp_dependencies(feature_dir, wp_id)
            if deps and all(dep in done_wp_ids for dep in deps):
                # All explicit deps are done → this WP is unblocked.
                ready_to_start.append(wp_id)

    # Attach ready_to_start info as a special synthetic state (so callers
    # can retrieve it from the list return value using a well-known
    # resolution_note without changing the return type signature).
    # We ALSO embed the list into the existing entries for convenience by
    # monkey-patching the first entry; however the cleanest API is to check
    # resolution_note == "ready_to_start_from_target" on any entry.
    for wp_id in ready_to_start:
        # Avoid duplicating entries that already exist
        if any(rs.wp_id == wp_id and rs.resolution_note == "ready_to_start_from_target" for rs in recovery_states):
            continue
        recovery_states.append(
            RecoveryState(
                wp_id=wp_id,
                lane_id="",
                branch_name="",
                branch_exists=False,
                worktree_exists=False,
                context_exists=False,
                status_lane=all_wp_lanes.get(wp_id, "planned"),
                has_commits=False,
                recovery_action="no_action",
                resolution_note="ready_to_start_from_target",
            )
        )

    return recovery_states


def get_ready_to_start_from_target(states: list[RecoveryState]) -> list[str]:
    """Extract WP IDs that are ready to start from the target branch tip.

    These are WPs whose dependency lane branches have all been
    merged-and-deleted (confirmed done by the event log) and whose own
    branch does not yet exist.

    Args:
        states: Output of ``scan_recovery_state(..., consult_status_events=True)``

    Returns:
        List of WP IDs ready to start from the target branch tip.
    """
    return [rs.wp_id for rs in states if rs.resolution_note == "ready_to_start_from_target"]


def recover_worktree(
    repo_root: Path,
    mission_slug: str,
    state: RecoveryState,
) -> None:
    """Recover a lane worktree from an existing branch.

    Uses `git worktree add <path> <branch>` (WITHOUT -b) to attach
    to the pre-existing branch.
    """
    from specify_cli.lanes.worktree_allocator import _recover_lane_worktree

    worktree_path = repo_root / ".worktrees" / f"{mission_slug}-{state.lane_id}"
    _recover_lane_worktree(repo_root, worktree_path, state.branch_name)


def recover_context(
    repo_root: Path,
    mission_slug: str,
    state: RecoveryState,
) -> WorkspaceContext:
    """Recreate a workspace context from branch metadata.

    When the context file is missing but the branch and worktree exist,
    reconstruct the context from available metadata.
    """
    feature_dir = repo_root / "kitty-specs" / mission_slug
    worktree_path = repo_root / ".worktrees" / f"{mission_slug}-{state.lane_id}"

    # Get base info from lanes.json
    wp_ids = _find_wp_ids_for_lane(feature_dir, state.lane_id)
    mission_branch = _find_mission_branch(feature_dir)
    if not mission_branch:
        mission_branch = f"kitty/mission-{mission_slug}"

    # Get base commit
    result = subprocess.run(
        ["git", "rev-parse", mission_branch],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    base_commit = result.stdout.strip() if result.returncode == 0 else "unknown"

    context = WorkspaceContext(
        wp_id=state.wp_id,
        mission_slug=mission_slug,
        worktree_path=str(worktree_path.relative_to(repo_root)),
        branch_name=state.branch_name,
        base_branch=mission_branch,
        base_commit=base_commit,
        dependencies=[],
        created_at=datetime.now(UTC).isoformat(),
        created_by="recovery",
        vcs_backend="git",
        lane_id=state.lane_id,
        lane_wp_ids=wp_ids if wp_ids else [state.wp_id],
        current_wp=state.wp_id,
    )
    save_context(repo_root, context)
    return context


def reconcile_status(
    repo_root: Path,
    mission_slug: str,
    state: RecoveryState,
) -> int:
    """Emit missing status transitions to catch up with filesystem reality.

    When a branch exists with commits but status is behind, emit the
    missing transitions. Never advances past in_progress.

    Returns the number of transitions emitted.
    """
    from specify_cli.status.emit import emit_status_transition
    from specify_cli.status.models import TransitionRequest

    feature_dir = repo_root / "kitty-specs" / mission_slug
    current_lane = state.status_lane

    # Determine target lane based on evidence
    if state.has_commits:
        target = Lane.IN_PROGRESS
    elif state.context_exists:
        target = Lane.CLAIMED
    else:
        return 0

    try:
        current_lane_enum = Lane(current_lane)
    except ValueError:
        return 0
    transitions = _get_recovery_transitions(current_lane_enum)
    if not transitions:
        return 0

    emitted = 0
    for next_lane in transitions:
        try:
            emit_status_transition(TransitionRequest(
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                wp_id=state.wp_id,
                to_lane=next_lane,
                actor=RECOVERY_ACTOR,
                reason=f"Recovered after crash -- branch {state.branch_name} exists"
                + (" with commits" if state.has_commits else ""),
                execution_mode="worktree",
                repo_root=repo_root,
            ))
            emitted += 1
        except Exception:
            break

        if next_lane == target:
            break

    return emitted


def run_recovery(
    repo_root: Path,
    mission_slug: str,
) -> RecoveryReport:
    """Orchestrate full crash recovery: scan + reconcile + report.

    Performs recovery in order:
    1. Scan for post-crash state (including event-log consultation)
    2. Recover worktrees (where branches exist but worktrees don't)
    3. Recover contexts (where worktrees exist but contexts don't)
    4. Reconcile status events
    5. Report WPs ready to start from target branch tip

    Returns a RecoveryReport summarizing what was done.
    """
    states = scan_recovery_state(repo_root, mission_slug)

    # Collect WPs ready to start from target (populated by event-log path)
    ready_wps = get_ready_to_start_from_target(states)

    report = RecoveryReport(
        recovered_wps=[],
        worktrees_recreated=0,
        contexts_recreated=0,
        transitions_emitted=0,
        errors=[],
        ready_to_start_from_target=ready_wps,
    )

    if not states:
        return report

    # Filter to states that need active recovery
    needs_recovery = [s for s in states if s.recovery_action != "no_action"]

    # Track which lanes have already had worktree/context recovery
    # to avoid duplicate operations (multiple WPs share a lane worktree)
    recovered_lanes_worktree: set[str] = set()
    recovered_lanes_context: set[str] = set()

    for state in needs_recovery:
        try:
            # Step 1: Recover worktree if needed (once per lane)
            if state.recovery_action == "recreate_worktree" and state.lane_id not in recovered_lanes_worktree:
                recover_worktree(repo_root, mission_slug, state)
                report.worktrees_recreated += 1
                recovered_lanes_worktree.add(state.lane_id)

                # Also recreate context if it was missing (once per lane)
                if not state.context_exists and state.lane_id not in recovered_lanes_context:
                    recover_context(repo_root, mission_slug, state)
                    report.contexts_recreated += 1
                    recovered_lanes_context.add(state.lane_id)

            # Step 2: Recover context if needed (once per lane)
            elif state.recovery_action == "recreate_context" and state.lane_id not in recovered_lanes_context:
                recover_context(repo_root, mission_slug, state)
                report.contexts_recreated += 1
                recovered_lanes_context.add(state.lane_id)

            # Step 3: Reconcile status (per WP, not per lane)
            try:
                _status_lane_enum = Lane(state.status_lane)
            except ValueError:
                _status_lane_enum = None
            if state.has_commits and _status_lane_enum is not None and bool(_get_recovery_transitions(_status_lane_enum)):
                emitted = reconcile_status(repo_root, mission_slug, state)
                report.transitions_emitted += emitted

            if state.wp_id not in report.recovered_wps:
                report.recovered_wps.append(state.wp_id)

        except Exception as exc:
            report.errors.append(f"{state.wp_id} ({state.lane_id}): {exc}")

    return report
