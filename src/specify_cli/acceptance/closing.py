"""Acceptance-time WP closure helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from specify_cli.status.history_parser import extract_done_evidence
from specify_cli.status.lane_reader import get_wp_lane
from specify_cli.status.models import DoneEvidence, Lane, ReviewApproval
from specify_cli.status.store import EVENTS_FILENAME, read_events
from specify_cli.status.transitions import resolve_lane_alias
from specify_cli.status.wp_metadata import read_wp_frontmatter
from specify_cli.task_utils import run_git


@dataclass(frozen=True)
class AcceptanceClosureResult:
    """Result of closing approved WPs as part of mission acceptance."""

    closed_wps: list[str]
    already_done_wps: list[str]
    staged_paths: list[str]


def _wp_state_by_id(summary: Any) -> dict[str, Any]:
    return {wp.work_package_id: wp for wp in summary.work_packages}


def _wp_path(summary: Any, wp_id: str) -> Path:
    wp_state = _wp_state_by_id(summary).get(wp_id)
    if wp_state is None:
        return summary.feature_dir / "tasks" / f"{wp_id}.md"
    return summary.repo_root / wp_state.path


def _latest_approval_evidence(feature_dir: Path, wp_id: str) -> DoneEvidence | None:
    for event in reversed(read_events(feature_dir)):
        if event.wp_id != wp_id:
            continue
        if event.to_lane in {Lane.APPROVED, Lane.DONE} and event.evidence is not None:
            return event.evidence
    return None


def _reviewer_from_metadata(metadata: Any, actor: str) -> str:
    agent = getattr(metadata, "agent", None)
    if isinstance(agent, str) and agent.strip():
        return agent.strip()
    return actor.strip() or "unknown"


def _done_evidence(summary: Any, wp_id: str, actor: str) -> DoneEvidence:
    event_evidence = _latest_approval_evidence(summary.feature_dir, wp_id)
    if event_evidence is not None:
        return event_evidence

    wp_path = _wp_path(summary, wp_id)
    metadata, _body = read_wp_frontmatter(wp_path)
    frontmatter_evidence = extract_done_evidence(metadata, wp_id)
    if frontmatter_evidence is not None:
        return frontmatter_evidence

    return DoneEvidence(
        review=ReviewApproval(
            reviewer=_reviewer_from_metadata(metadata, actor),
            verdict="approved",
            reference=f"accept-approved:{wp_id}",
        )
    )


def _stage_closure_artifacts(summary: Any, closed_wps: list[str]) -> list[str]:
    paths = [
        summary.feature_dir / EVENTS_FILENAME,
        summary.feature_dir / "status.json",
        *(_wp_path(summary, wp_id) for wp_id in closed_wps),
    ]
    rel_paths = sorted(
        {
            str(path.relative_to(summary.repo_root))
            for path in paths
            if path.exists()
        }
    )
    if rel_paths:
        run_git(["add", "--", *rel_paths], cwd=summary.repo_root, check=True)
    return rel_paths


def close_approved_wps_for_acceptance(
    summary: Any,
    *,
    actor: str,
    stage_for_commit: bool = False,
) -> AcceptanceClosureResult:
    """Close all approved WPs through canonical status events."""
    from specify_cli.acceptance import AcceptanceError
    from specify_cli.status.emit import TransitionError, emit_status_transition

    approved_wps = list(summary.lanes.get("approved", []))
    already_done_wps = list(summary.lanes.get("done", []))
    if not approved_wps:
        return AcceptanceClosureResult(
            closed_wps=[],
            already_done_wps=already_done_wps,
            staged_paths=[],
        )

    closure_evidence: list[tuple[str, DoneEvidence]] = []
    for wp_id in approved_wps:
        lane = Lane(resolve_lane_alias(get_wp_lane(summary.feature_dir, wp_id)))
        if lane == Lane.DONE:
            already_done_wps.append(wp_id)
            continue
        if lane != Lane.APPROVED:
            raise AcceptanceError(
                f"{wp_id}: canonical lane is '{lane.value}', expected 'approved' before acceptance closure"
            )
        closure_evidence.append((wp_id, _done_evidence(summary, wp_id, actor)))

    closed_wps: list[str] = []
    for wp_id, evidence in closure_evidence:
        try:
            emit_status_transition(
                feature_dir=summary.feature_dir,
                mission_slug=summary.feature,
                wp_id=wp_id,
                to_lane="done",
                actor=actor,
                reason=f"Accepted mission {summary.feature}",
                evidence=evidence.to_dict(),
                workspace_context=f"accept:{summary.repo_root}",
                repo_root=summary.repo_root,
                sync_dossier=False,
            )
        except TransitionError as exc:
            raise AcceptanceError(f"Failed to close {wp_id} during acceptance: {exc}") from exc
        closed_wps.append(wp_id)

    staged_paths = _stage_closure_artifacts(summary, closed_wps) if stage_for_commit else []
    return AcceptanceClosureResult(
        closed_wps=closed_wps,
        already_done_wps=already_done_wps,
        staged_paths=staged_paths,
    )


def summary_with_closed_wps(summary: Any, closed_wps: list[str]) -> Any:
    """Return an acceptance summary with closed WPs reflected as done."""
    if not closed_wps:
        return summary

    closed = set(closed_wps)
    lanes = {lane: list(wps) for lane, wps in summary.lanes.items()}
    lanes["approved"] = [wp_id for wp_id in lanes.get("approved", []) if wp_id not in closed]
    done = list(lanes.get("done", []))
    for wp_id in closed_wps:
        if wp_id not in done:
            done.append(wp_id)
    lanes["done"] = done

    work_packages = [
        replace(wp, lane="done", latest_lane="done") if wp.work_package_id in closed else wp
        for wp in summary.work_packages
    ]
    return replace(summary, lanes=lanes, work_packages=work_packages)


__all__ = [
    "AcceptanceClosureResult",
    "close_approved_wps_for_acceptance",
    "summary_with_closed_wps",
]
