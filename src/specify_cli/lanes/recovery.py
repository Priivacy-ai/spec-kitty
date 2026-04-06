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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from specify_cli.lanes.branch_naming import parse_lane_id_from_branch
from specify_cli.workspace_context import (
    WorkspaceContext,
    list_contexts,
    save_context,
)

logger = logging.getLogger(__name__)


RECOVERY_ACTOR = "recovery"

# Status lanes that recovery can advance through (never past in_progress)
_RECOVERY_CEILING = "in_progress"
_RECOVERY_TRANSITIONS = {
    "planned": ["claimed", "in_progress"],
    "claimed": ["in_progress"],
}


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


@dataclass
class RecoveryReport:
    """Summary of recovery operations performed."""

    recovered_wps: list[str]
    worktrees_recreated: int
    contexts_recreated: int
    transitions_emitted: int
    errors: list[str]

    def to_dict(self) -> dict:
        return {
            "recovered_wps": self.recovered_wps,
            "worktrees_recreated": self.worktrees_recreated,
            "contexts_recreated": self.contexts_recreated,
            "transitions_emitted": self.transitions_emitted,
            "errors": self.errors,
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
                return str(state.get("lane", "planned"))
    except Exception:
        logger.debug("Could not read status events for %s in %s", wp_id, feature_dir)
    return "planned"


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
            return manifest.mission_branch
    except Exception:
        logger.debug("Could not read mission branch from %s", feature_dir)
    return ""


def scan_recovery_state(
    repo_root: Path,
    mission_slug: str,
) -> list[RecoveryState]:
    """Scan for post-crash implementation state.

    Lists branches matching kitty/mission-{slug}*, cross-references
    workspace contexts and status events to detect inconsistencies.

    Returns a list of RecoveryState objects for WPs that need recovery.
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
            elif has_commits and status_lane in _RECOVERY_TRANSITIONS:
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

    return recovery_states


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

    feature_dir = repo_root / "kitty-specs" / mission_slug
    current_lane = state.status_lane

    # Determine target lane based on evidence
    if state.has_commits:
        target = "in_progress"
    elif state.context_exists:
        target = "claimed"
    else:
        return 0

    transitions = _RECOVERY_TRANSITIONS.get(current_lane, [])
    if not transitions:
        return 0

    emitted = 0
    for next_lane in transitions:
        try:
            emit_status_transition(
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                wp_id=state.wp_id,
                to_lane=next_lane,
                actor=RECOVERY_ACTOR,
                reason=f"Recovered after crash -- branch {state.branch_name} exists"
                + (" with commits" if state.has_commits else ""),
                execution_mode="worktree",
                repo_root=repo_root,
            )
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
    1. Scan for post-crash state
    2. Recover worktrees (where branches exist but worktrees don't)
    3. Recover contexts (where worktrees exist but contexts don't)
    4. Reconcile status events

    Returns a RecoveryReport summarizing what was done.
    """
    states = scan_recovery_state(repo_root, mission_slug)

    report = RecoveryReport(
        recovered_wps=[],
        worktrees_recreated=0,
        contexts_recreated=0,
        transitions_emitted=0,
        errors=[],
    )

    if not states:
        return report

    # Filter to states that need recovery
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
            if state.has_commits and state.status_lane in _RECOVERY_TRANSITIONS:
                emitted = reconcile_status(repo_root, mission_slug, state)
                report.transitions_emitted += emitted

            if state.wp_id not in report.recovered_wps:
                report.recovered_wps.append(state.wp_id)

        except Exception as exc:
            report.errors.append(f"{state.wp_id} ({state.lane_id}): {exc}")

    return report
