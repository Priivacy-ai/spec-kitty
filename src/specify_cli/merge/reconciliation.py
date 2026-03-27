"""Post-merge reconciliation: emit done events from actual git ancestry.

Implements T041: after merging WP branches into the target branch, verify
which WP branches are reachable (``git branch --merged``) in the merge
workspace and emit ``done`` status events for those that have not yet been
marked done.

This is the authoritative, git-backed source of truth for "was this WP
actually integrated?" — it does NOT rely on in-memory tracking from the
merge loop.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.status.models import StatusEvent

__all__ = [
    "get_merged_branches",
    "reconcile_done_state",
]

logger = logging.getLogger(__name__)


def get_merged_branches(target_branch: str, workspace_path: Path) -> set[str]:
    """Return the set of branch names that have been merged into target_branch.

    Uses ``git branch --merged <target>`` executed inside *workspace_path*.

    Args:
        target_branch: The branch that WPs were merged into (e.g. "main").
        workspace_path: Path to the git worktree used for merge operations.

    Returns:
        Set of branch names (strings) that are fully merged into target_branch.
    """
    result = subprocess.run(
        ["git", "branch", "--merged", target_branch],
        cwd=str(workspace_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        logger.warning(
            "git branch --merged %s failed in %s: %s",
            target_branch,
            workspace_path,
            result.stderr.strip(),
        )
        return set()

    branches: set[str] = set()
    for line in result.stdout.splitlines():
        branch = line.strip().lstrip("* ").strip()
        if branch:
            branches.add(branch)
    return branches


def _get_merge_commit(branch: str, target_branch: str, workspace_path: Path) -> str | None:
    """Return the merge commit hash for a branch into target_branch.

    Uses ``git log`` to find the first merge commit that brought the branch tip
    into the ancestry of target_branch.
    """
    result = subprocess.run(
        [
            "git", "log", "--merges", "--format=%H",
            f"{branch}..{target_branch}",
            "--ancestry-path",
            "-1",
        ],
        cwd=str(workspace_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().splitlines()[0]
    return None


def _get_files_touched(branch: str, workspace_path: Path) -> list[str]:
    """Return list of files changed in the given branch (vs its merge base)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{branch}^..{branch}"],
        cwd=str(workspace_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]

    # Fallback: diff between branch tip and its parent
    result2 = subprocess.run(
        ["git", "diff", "--name-only", f"{branch}^1..{branch}"],
        cwd=str(workspace_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result2.returncode == 0 and result2.stdout.strip():
        return [f.strip() for f in result2.stdout.splitlines() if f.strip()]
    return []


def reconcile_done_state(
    feature_dir: Path,
    merged_branches: list[str],
    target_branch: str,
    workspace_path: Path,
) -> list[StatusEvent]:
    """Emit done events for WPs confirmed merged via git ancestry.

    For each branch in *merged_branches*, this function:
    1. Verifies the branch is in ``git branch --merged <target>`` inside the
       workspace.
    2. Checks the current lane of the corresponding WP from the event log.
    3. If the WP is not already ``done`` or ``canceled``, emits a ``done``
       event with repo evidence (merge commit hash, branch, files touched).

    Args:
        feature_dir: Path to the feature directory containing the event log
                     (``kitty-specs/<feature-slug>/``).
        merged_branches: List of branch names that were merged by the engine.
        target_branch: Branch that was merged into (e.g. "main").
        workspace_path: Path to the merge workspace (git worktree).

    Returns:
        List of StatusEvent objects that were emitted.
    """
    from specify_cli.status.emit import emit_status_transition, TransitionError
    from specify_cli.status.store import read_events
    from specify_cli.status.reducer import reduce

    if not merged_branches:
        return []

    # Build current lane snapshot from event log
    events = read_events(feature_dir)
    snapshot = reduce(events)
    wp_lanes: dict[str, str] = {}
    for wp_id, wp_state in snapshot.work_packages.items():
        lane = wp_state.get("lane", "planned")
        if isinstance(lane, str):
            wp_lanes[wp_id] = lane

    # Determine which branches are actually in git ancestry
    actually_merged = get_merged_branches(target_branch, workspace_path)

    feature_slug = feature_dir.name
    emitted: list[StatusEvent] = []

    for branch in merged_branches:
        if branch not in actually_merged:
            logger.warning(
                "Branch %r is NOT in merged ancestry of %s — skipping reconciliation.",
                branch,
                target_branch,
            )
            continue

        # Derive WP id from branch name (e.g. "057-feature-WP03" → "WP03")
        wp_id: str | None = None
        import re
        match = re.search(r"-(WP\d{2,})$", branch)
        if match:
            wp_id = match.group(1)

        if wp_id is None:
            logger.debug("Cannot derive WP id from branch %r; skipping.", branch)
            continue

        current_lane = wp_lanes.get(wp_id, "planned")
        if current_lane in ("done", "canceled"):
            logger.debug("WP %s already in lane %r; skipping reconciliation.", wp_id, current_lane)
            continue

        # Gather git evidence
        merge_commit = _get_merge_commit(branch, target_branch, workspace_path) or "unknown"
        files_touched = _get_files_touched(branch, workspace_path)

        evidence = {
            "review": {
                "reviewer": "merge-reconciliation",
                "verdict": "approved",
                "reference": f"git-merge:{merge_commit}",
            },
            "repos": [
                {
                    "repo": str(workspace_path),
                    "branch": branch,
                    "commit": merge_commit,
                    "files_touched": files_touched,
                }
            ],
        }

        try:
            # If not yet approved, step through approved first
            if current_lane not in ("approved", "for_review"):
                # Emit approved intermediate step only when lane allows it
                if current_lane in ("planned", "claimed", "in_progress"):
                    try:
                        event = emit_status_transition(
                            feature_dir=feature_dir,
                            feature_slug=feature_slug,
                            wp_id=wp_id,
                            to_lane="approved",
                            actor="merge-reconciliation",
                            reason=f"Branch {branch} confirmed merged into {target_branch}",
                            evidence=evidence,
                            workspace_context=f"reconcile:{workspace_path}",
                            repo_root=workspace_path.parents[3]
                            if len(workspace_path.parts) > 3 else None,
                        )
                        emitted.append(event)
                        current_lane = "approved"
                    except TransitionError as exc:
                        logger.debug(
                            "Could not emit approved for %s: %s — trying done directly.",
                            wp_id, exc,
                        )

            event = emit_status_transition(
                feature_dir=feature_dir,
                feature_slug=feature_slug,
                wp_id=wp_id,
                to_lane="done",
                actor="merge-reconciliation",
                reason=f"Branch {branch} confirmed merged into {target_branch}",
                evidence=evidence,
                workspace_context=f"reconcile:{workspace_path}",
                repo_root=None,
            )
            emitted.append(event)
            logger.info("Reconciliation: emitted done event for %s (branch: %s)", wp_id, branch)

        except TransitionError as exc:
            logger.warning(
                "Reconciliation: could not emit done for WP %s (branch %r): %s",
                wp_id, branch, exc,
            )

    return emitted
