"""Cross-repo drift detection and reconciliation event generation.

Scans target repositories for WP-linked branches and commits,
compares against the canonical snapshot state, and generates
StatusEvent objects to align planning with implementation reality.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ulid

from specify_cli.status.models import Lane, StatusEvent, StatusSnapshot
from specify_cli.status.reducer import reduce, SNAPSHOT_FILENAME
from specify_cli.status.store import read_events
from specify_cli.status.transitions import (
    ALLOWED_TRANSITIONS,
    is_terminal,
    validate_transition,
)
from specify_cli.status.phase import resolve_phase
from specify_cli.status.emit import emit_status_transition

logger = logging.getLogger(__name__)

# Regex for extracting WP IDs from branch names and commit messages
_WP_PATTERN = re.compile(r"\bWP(\d{2})\b")

# Subprocess timeout for git commands (seconds)
_GIT_TIMEOUT = 30
_GIT_LOG_TIMEOUT = 60


@dataclass(frozen=True)
class CommitInfo:
    """Evidence of a commit linked to a work package."""

    sha: str  # 7-40 hex chars
    branch: str  # Branch where found
    message: str  # Commit message (first line)
    author: str  # Author name
    date: str  # ISO 8601 UTC timestamp


@dataclass
class ReconcileResult:
    """Result of a reconciliation scan."""

    suggested_events: list[StatusEvent] = field(default_factory=list)
    drift_detected: bool = False
    details: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    target_repos_scanned: int = 0
    wps_analyzed: int = 0


def scan_for_wp_commits(
    repo_path: Path,
    feature_slug: str,
) -> dict[str, list[CommitInfo]]:
    """Scan a repository for WP-linked branches and commit messages.

    Uses subprocess.run with timeouts for all git operations.
    Returns mapping of WP ID -> list of CommitInfo found.
    """
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    result_map: dict[str, list[CommitInfo]] = {}
    discovered_wp_ids: set[str] = set()

    # Step 1: Branch detection -- find branches matching the feature slug
    try:
        branch_result = subprocess.run(
            ["git", "branch", "-a", "--list", f"*{feature_slug}*"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_TIMEOUT,
        )
        if branch_result.returncode == 0 and branch_result.stdout.strip():
            for raw_line in branch_result.stdout.strip().split("\n"):
                branch_name = raw_line.strip().lstrip("* ")
                # Extract WP IDs from branch name
                for match in _WP_PATTERN.finditer(branch_name):
                    wp_id = f"WP{match.group(1)}"
                    discovered_wp_ids.add(wp_id)

                    # Get the latest commit on this branch
                    display_branch = branch_name
                    if branch_name.startswith("remotes/origin/"):
                        display_branch = branch_name[len("remotes/origin/"):]

                    try:
                        log_result = subprocess.run(
                            [
                                "git", "log", "-1",
                                "--format=%H%n%s%n%an%n%aI",
                                branch_name,
                            ],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            timeout=_GIT_TIMEOUT,
                        )
                        if log_result.returncode == 0 and log_result.stdout.strip():
                            parts = log_result.stdout.strip().split("\n")
                            if len(parts) >= 4:
                                commit_info = CommitInfo(
                                    sha=parts[0][:40],
                                    branch=display_branch,
                                    message=parts[1],
                                    author=parts[2],
                                    date=parts[3],
                                )
                                result_map.setdefault(wp_id, []).append(commit_info)
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            "Timeout getting log for branch %s in %s",
                            branch_name, repo_path,
                        )
    except subprocess.TimeoutExpired:
        logger.warning("Timeout listing branches in %s", repo_path)

    # Step 2: Commit message scanning -- search for commits mentioning WP IDs
    try:
        grep_result = subprocess.run(
            [
                "git", "log", "--all", "--oneline",
                f"--grep={feature_slug}",
                "--format=%H %s",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_LOG_TIMEOUT,
        )
        if grep_result.returncode == 0 and grep_result.stdout.strip():
            for line in grep_result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                # Parse "SHA message"
                parts = line.split(" ", 1)
                if len(parts) < 2:
                    continue
                sha = parts[0]
                message = parts[1]

                for match in _WP_PATTERN.finditer(message):
                    wp_id = f"WP{match.group(1)}"
                    discovered_wp_ids.add(wp_id)

                    # Get full commit metadata
                    try:
                        detail_result = subprocess.run(
                            [
                                "git", "log", "-1",
                                "--format=%an%n%aI",
                                sha,
                            ],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            timeout=_GIT_TIMEOUT,
                        )
                        if detail_result.returncode == 0 and detail_result.stdout.strip():
                            detail_parts = detail_result.stdout.strip().split("\n")
                            if len(detail_parts) >= 2:
                                commit_info = CommitInfo(
                                    sha=sha[:40],
                                    branch="(commit-message)",
                                    message=message,
                                    author=detail_parts[0],
                                    date=detail_parts[1],
                                )
                                # Avoid duplicate SHAs per WP
                                existing_shas = {
                                    c.sha for c in result_map.get(wp_id, [])
                                }
                                if sha[:40] not in existing_shas:
                                    result_map.setdefault(wp_id, []).append(
                                        commit_info
                                    )
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            "Timeout getting commit detail for %s in %s",
                            sha[:8], repo_path,
                        )
    except subprocess.TimeoutExpired:
        logger.warning("Timeout scanning commit messages in %s", repo_path)

    return result_map


def _get_merged_wps(
    repo_path: Path,
    feature_slug: str,
) -> set[str]:
    """Check which WP branches are merged into main/master."""
    merged: set[str] = set()

    # Try main, then master
    for base_branch in ("main", "master"):
        try:
            result = subprocess.run(
                [
                    "git", "branch", "--merged", base_branch,
                    "--list", f"*{feature_slug}*",
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_GIT_TIMEOUT,
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    branch_name = line.strip().lstrip("* ")
                    for match in _WP_PATTERN.finditer(branch_name):
                        merged.add(f"WP{match.group(1)}")
                break  # Found a valid base branch
        except subprocess.TimeoutExpired:
            logger.warning(
                "Timeout checking merged branches against %s in %s",
                base_branch, repo_path,
            )

    return merged


def _get_current_lane(
    snapshot: StatusSnapshot,
    wp_id: str,
) -> Lane:
    """Get current lane for a WP from the snapshot, defaulting to PLANNED."""
    wp_state = snapshot.work_packages.get(wp_id)
    if wp_state is None:
        return Lane.PLANNED
    try:
        return Lane(wp_state["lane"])
    except (KeyError, ValueError):
        return Lane.PLANNED


def _lane_advancement_chain(
    from_lane: Lane,
    to_lane: Lane,
) -> list[tuple[Lane, Lane]]:
    """Generate legal lane transition chain from from_lane to to_lane.

    The state machine does not allow skipping lanes without force,
    so we generate intermediate transitions.
    """
    # Define the forward progression order
    progression = [
        Lane.PLANNED,
        Lane.CLAIMED,
        Lane.IN_PROGRESS,
        Lane.FOR_REVIEW,
        Lane.DONE,
    ]

    try:
        from_idx = progression.index(from_lane)
        to_idx = progression.index(to_lane)
    except ValueError:
        # Lane not in normal progression (blocked, canceled, etc.)
        return []

    if to_idx <= from_idx:
        return []  # No forward advancement needed

    chain: list[tuple[Lane, Lane]] = []
    for i in range(from_idx, to_idx):
        pair = (progression[i], progression[i + 1])
        # Verify this is an allowed transition
        if (str(pair[0]), str(pair[1])) in ALLOWED_TRANSITIONS:
            chain.append(pair)
        else:
            # Can't build a legal chain
            return []

    return chain


def _generate_reconciliation_events(
    feature_slug: str,
    snapshot: StatusSnapshot,
    commit_map: dict[str, list[CommitInfo]],
    merged_wps: set[str],
) -> tuple[list[StatusEvent], list[str]]:
    """Generate events to reconcile planning state with implementation evidence.

    Returns (events, detail_messages).
    """
    events: list[StatusEvent] = []
    details: list[str] = []
    now = datetime.now(timezone.utc).isoformat()

    for wp_id, commits in sorted(commit_map.items()):
        current_lane = _get_current_lane(snapshot, wp_id)

        # Terminal lanes: no reconciliation
        if is_terminal(str(current_lane)):
            details.append(
                f"{wp_id}: in terminal lane {current_lane}, skipping"
            )
            continue

        # Blocked lane: note but don't advance
        if current_lane == Lane.BLOCKED:
            details.append(
                f"{wp_id}: currently blocked, has {len(commits)} commit(s) "
                f"-- manual review needed"
            )
            continue

        # Determine target lane based on evidence
        wp_merged = wp_id in merged_wps

        if wp_merged and current_lane in (
            Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS,
        ):
            # Branch merged but WP not even at for_review
            target_lane = Lane.FOR_REVIEW
            evidence_summary = f"branch merged to main with {len(commits)} commit(s)"
        elif wp_merged and current_lane == Lane.FOR_REVIEW:
            # Merged and at for_review -- could suggest done, but
            # done requires reviewer approval evidence which reconcile
            # cannot fabricate. Note the drift instead.
            details.append(
                f"{wp_id}: branch merged and in for_review -- "
                f"may be ready for done (requires reviewer approval)"
            )
            continue
        elif commits and current_lane == Lane.PLANNED:
            # Has commits but still planned -> should be at least claimed
            target_lane = Lane.CLAIMED
            evidence_summary = f"{len(commits)} commit(s) found"
        elif commits and current_lane == Lane.CLAIMED:
            # Has commits and claimed -> should be in_progress
            target_lane = Lane.IN_PROGRESS
            evidence_summary = f"{len(commits)} commit(s) found"
        elif commits and current_lane == Lane.IN_PROGRESS and wp_merged:
            target_lane = Lane.FOR_REVIEW
            evidence_summary = f"branch merged with {len(commits)} commit(s)"
        else:
            # No actionable drift for this combination
            continue

        # Generate the chain of legal transitions
        chain = _lane_advancement_chain(current_lane, target_lane)
        if not chain:
            details.append(
                f"{wp_id}: cannot generate legal transition chain from "
                f"{current_lane} to {target_lane}"
            )
            continue

        details.append(
            f"{wp_id}: {current_lane} -> {target_lane} ({evidence_summary})"
        )

        for from_lane, to_lane in chain:
            event = StatusEvent(
                event_id=str(ulid.ULID()),
                feature_slug=feature_slug,
                wp_id=wp_id,
                from_lane=from_lane,
                to_lane=to_lane,
                at=now,
                actor="reconcile",
                force=False,
                execution_mode="direct_repo",
                reason=f"Reconciliation: {evidence_summary}",
            )

            # Validate the transition (skip guard conditions that require
            # human input like reviewer approval)
            ok, err = validate_transition(
                str(from_lane),
                str(to_lane),
                force=False,
                actor="reconcile",
                workspace_context="reconcile",
                subtasks_complete=True if str(to_lane) == "for_review" else None,
                implementation_evidence_present=(
                    True if str(to_lane) == "for_review" else None
                ),
            )
            if ok:
                events.append(event)
            else:
                details.append(
                    f"{wp_id}: skipping {from_lane} -> {to_lane}: {err}"
                )

    return events, details


def reconcile(
    feature_dir: Path,
    repo_root: Path,
    target_repos: list[Path],
    *,
    dry_run: bool = True,
) -> ReconcileResult:
    """Scan target repos for WP-linked commits and generate reconciliation events.

    Args:
        feature_dir: Path to the kitty-specs feature directory.
        repo_root: Root of the main repository.
        target_repos: List of repository paths to scan for evidence.
        dry_run: If True, return suggested events without persisting.
                 If False, emit events through the orchestration pipeline.

    Returns:
        ReconcileResult with suggested events, drift info, and diagnostics.
    """
    result = ReconcileResult()
    feature_slug = feature_dir.name

    # Load or materialize the current snapshot
    snapshot_path = feature_dir / SNAPSHOT_FILENAME
    if snapshot_path.exists():
        try:
            data = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot = StatusSnapshot.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            # Re-materialize from events
            try:
                events = read_events(feature_dir)
                snapshot = reduce(events)
            except Exception as inner_exc:
                result.errors.append(
                    f"Failed to load snapshot or events: {exc}; {inner_exc}"
                )
                return result
    else:
        # No snapshot file -- try materializing from event log
        try:
            events = read_events(feature_dir)
            snapshot = reduce(events)
        except Exception:
            # No events either -- empty snapshot (all WPs effectively planned)
            snapshot = StatusSnapshot(
                feature_slug=feature_slug,
                materialized_at=datetime.now(timezone.utc).isoformat(),
                event_count=0,
                last_event_id=None,
                work_packages={},
                summary={lane.value: 0 for lane in Lane},
            )

    # Scan each target repo
    all_commits: dict[str, list[CommitInfo]] = {}
    all_merged: set[str] = set()

    for repo_path in target_repos:
        if not repo_path.exists():
            result.errors.append(f"Target repo does not exist: {repo_path}")
            continue

        result.target_repos_scanned += 1

        try:
            commit_map = scan_for_wp_commits(repo_path, feature_slug)
        except FileNotFoundError as exc:
            result.errors.append(str(exc))
            continue

        # Merge results (deduplicate by SHA per WP)
        for wp_id, commits in commit_map.items():
            existing_shas = {c.sha for c in all_commits.get(wp_id, [])}
            for commit in commits:
                if commit.sha not in existing_shas:
                    all_commits.setdefault(wp_id, []).append(commit)
                    existing_shas.add(commit.sha)

        # Check merged branches
        merged = _get_merged_wps(repo_path, feature_slug)
        all_merged.update(merged)

    result.wps_analyzed = len(all_commits)

    # Generate reconciliation events
    if all_commits:
        events, details = _generate_reconciliation_events(
            feature_slug, snapshot, all_commits, all_merged,
        )
        result.suggested_events = events
        result.details = details
        result.drift_detected = len(events) > 0
    else:
        result.details.append("No WP-linked commits found in target repos")

    # Apply mode
    if not dry_run and result.suggested_events:
        phase, source = resolve_phase(repo_root, feature_slug)

        # Phase gating: phase 0 blocks apply
        if phase < 1:
            raise ValueError(
                "Cannot apply reconciliation events at Phase 0. "
                "Upgrade to Phase 1+ to enable event persistence."
            )

        applied_count = 0
        for event in result.suggested_events:
            try:
                emit_status_transition(
                    feature_dir=feature_dir,
                    feature_slug=feature_slug,
                    wp_id=event.wp_id,
                    to_lane=str(event.to_lane),
                    actor=event.actor,
                    force=event.force,
                    reason=event.reason,
                    review_ref=event.review_ref,
                    workspace_context=f"reconcile:{repo_root}",
                    subtasks_complete=(
                        True if str(event.to_lane) == "for_review" else None
                    ),
                    implementation_evidence_present=(
                        True if str(event.to_lane) == "for_review" else None
                    ),
                    execution_mode="direct_repo",
                    repo_root=repo_root,
                )
                applied_count += 1
            except Exception as exc:
                result.errors.append(
                    f"Failed to apply event for {event.wp_id} "
                    f"({event.from_lane} -> {event.to_lane}): {exc}"
                )

        if applied_count > 0:
            result.details.append(
                f"Applied {applied_count} reconciliation event(s) "
                f"(phase={phase}, source={source})"
            )

    return result


def format_reconcile_report(result: ReconcileResult) -> None:
    """Print a human-readable reconciliation report using Rich."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()

    if not result.drift_detected and not result.errors:
        console.print(
            Panel(
                "[green]No drift detected[/green] -- "
                "planning state matches implementation evidence.",
                title="Reconciliation Result",
                border_style="green",
            )
        )
        console.print(
            f"  Repos scanned: {result.target_repos_scanned}  |  "
            f"WPs analyzed: {result.wps_analyzed}"
        )
        return

    # Build suggested events table
    if result.suggested_events:
        table = Table(
            title="Suggested Reconciliation Events",
            show_header=True,
            header_style="bold magenta",
            border_style="dim",
        )
        table.add_column("WP ID", style="cyan", width=8)
        table.add_column("Current Lane", style="yellow", width=14)
        table.add_column("Suggested Lane", style="green", width=14)
        table.add_column("Evidence", width=40)
        table.add_column("Action", width=20)

        for event in result.suggested_events:
            table.add_row(
                event.wp_id,
                str(event.from_lane),
                str(event.to_lane),
                event.reason or "",
                "emit event" if result.drift_detected else "dry-run",
            )

        console.print(table)
        console.print()

    # Details
    if result.details:
        console.print("[bold]Details:[/bold]")
        for detail in result.details:
            console.print(f"  {detail}")
        console.print()

    # Errors
    if result.errors:
        console.print("[bold red]Errors:[/bold red]")
        for error in result.errors:
            console.print(f"  [red]{error}[/red]")
        console.print()

    # Summary statistics
    console.print("[bold]Summary:[/bold]")
    console.print(f"  Target repos scanned: {result.target_repos_scanned}")
    console.print(f"  WPs analyzed: {result.wps_analyzed}")
    console.print(
        f"  Drift detected: "
        f"{'[red]yes[/red]' if result.drift_detected else '[green]no[/green]'}"
    )
    console.print(f"  Suggested events: {len(result.suggested_events)}")


def reconcile_result_to_json(result: ReconcileResult) -> dict[str, Any]:
    """Convert ReconcileResult to a JSON-serializable dict."""
    return {
        "drift_detected": result.drift_detected,
        "suggested_events": [e.to_dict() for e in result.suggested_events],
        "details": result.details,
        "errors": result.errors,
        "stats": {
            "target_repos_scanned": result.target_repos_scanned,
            "wps_analyzed": result.wps_analyzed,
        },
    }
