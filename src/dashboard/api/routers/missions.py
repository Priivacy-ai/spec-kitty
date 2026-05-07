"""Resource-oriented mission and workpackage endpoints.

All routes call get_mission_registry() — never the scanner directly.
Per DIRECTIVE_API_DEPENDENCY_DIRECTION (mission
mission-registry-and-api-boundary-doctrine-01KQPDBB), transport-side modules
MUST consume mission/WP data exclusively through the MissionRegistry.

Tags: missions
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

# Strips a leading YAML frontmatter block (``---\n...\n---``) from a markdown
# document. WP prompt files start with frontmatter that the dashboard modal
# would otherwise render as plain text via ``marked.parse()``. The structured
# fields are already exposed on the response model; the body is what humans
# read. Pattern matches mission_renderer's _RE_FRONTMATTER but kept local to
# avoid cross-package coupling.
_RE_PROMPT_FRONTMATTER = re.compile(r"^\s*---\n(.*?)---\n?", re.DOTALL)

if TYPE_CHECKING:
    from fastapi import FastAPI

from dashboard.api.deps import get_mission_registry
from dashboard.api.models import (
    Link,
    LaneCounts,
    Mission,
    MissionStatus,
    MissionSummary,
    WorkPackage,
    WorkPackageAssignment,
    WorkPackageSummary,
)
from specify_cli.missions.registry import MissionRecord, MissionRegistry, WorkPackageRecord

router = APIRouter(tags=["missions"])

__all__ = ["router", "register"]


def register(app: "FastAPI") -> None:  # noqa: F821  — forward ref resolved at call time
    """Mount the missions router on ``app``."""
    app.include_router(router)


# ─── helpers ─────────────────────────────────────────────────────────────────


def _mission_links(mission_id: str) -> dict[str, Link]:
    return {
        "self": Link(href=f"/api/missions/{mission_id}"),
        "status": Link(href=f"/api/missions/{mission_id}/status"),
        "workpackages": Link(href=f"/api/missions/{mission_id}/workpackages"),
    }


def _wp_links(mission_id: str, wp_id: str) -> dict[str, Link]:
    return {
        "self": Link(href=f"/api/missions/{mission_id}/workpackages/{wp_id}"),
        "mission": Link(href=f"/api/missions/{mission_id}"),
        "workpackages": Link(href=f"/api/missions/{mission_id}/workpackages"),
    }


def _get_mission_or_raise(registry: MissionRegistry, mission_id: str) -> MissionRecord:
    """Resolve mission_id/mid8/slug; raise 404 or 409 appropriately.

    IMPORTANT: registry.get_mission() NEVER raises — it returns None for both
    "not found" and "ambiguous mid8" cases (registry.py:694-707).
    Ambiguity detection is done explicitly here.
    """
    record = registry.get_mission(mission_id)
    if record is not None:
        return record

    # None returned — distinguish ambiguous mid8 from not-found.
    # A mid8 handle is exactly 8 chars. Check how many missions share it.
    if len(mission_id) == 8:
        candidates = [m for m in registry.list_missions() if m.mid8 == mission_id]
        if len(candidates) > 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MISSION_AMBIGUOUS_SELECTOR",
                    "input": mission_id,
                    "candidates": [m.mission_slug for m in candidates],
                },
            )

    raise HTTPException(status_code=404, detail=f"Mission not found: {mission_id}")


def _make_lane_counts(lc: object) -> LaneCounts:
    """Convert a registry LaneCounts dataclass to the Pydantic LaneCounts model."""
    return LaneCounts(
        total=getattr(lc, "total", 0),
        planned=getattr(lc, "planned", 0),
        claimed=getattr(lc, "claimed", 0),
        in_progress=getattr(lc, "in_progress", 0),
        for_review=getattr(lc, "for_review", 0),
        in_review=getattr(lc, "in_review", 0),
        approved=getattr(lc, "approved", 0),
        done=getattr(lc, "done", 0),
        blocked=getattr(lc, "blocked", 0),
        canceled=getattr(lc, "canceled", 0),
    )


def _record_to_summary(record: MissionRecord) -> MissionSummary:
    return MissionSummary(
        mission_id=record.mission_id,
        mission_slug=record.mission_slug,
        mission_number=record.display_number,
        mid8=record.mid8,
        friendly_name=record.friendly_name,
        mission_type=record.mission_type,
        target_branch=record.target_branch,
        lane_counts=_make_lane_counts(record.lane_counts),
        weighted_percentage=record.weighted_percentage,
        is_legacy=record.is_legacy,
        **{"_links": _mission_links(record.mission_id)},
    )


def _parse_compound_agent(agent_str: str | None) -> tuple[str | None, str | None, str | None, str | None]:
    """Decompose a compact agent string into (tool, model, profile, role).

    The implement-review skill documents the canonical compact form
    `<tool>:<model>:<profile>:<role>` (e.g.
    `claude:sonnet-4-6:implementer:implementer`). Missing trailing parts
    default to None. A non-colon string is treated as a bare tool name.
    """
    if not agent_str:
        return None, None, None, None
    parts = agent_str.split(":")
    pad = parts + [""] * (4 - len(parts)) if len(parts) < 4 else parts
    tool, model, profile, role = pad[0], pad[1], pad[2], pad[3]
    return (tool or None, model or None, profile or None, role or None)


def _wp_record_to_assignment(wp: WorkPackageRecord) -> WorkPackageAssignment:
    tool, model, compound_profile, compound_role = _parse_compound_agent(wp.agent)
    return WorkPackageAssignment(
        wp_id=wp.wp_id,
        lane=wp.lane,
        agent=tool,
        model=model,
        assignee=wp.assignee,
        agent_profile=wp.agent_profile or compound_profile,
        role=wp.role or compound_role,
        claimed_at=wp.claimed_at,
        last_event_id=wp.last_event_id,
        blocked_reason=wp.blocked_reason,
        review_evidence=None,
    )


# ─── routes ──────────────────────────────────────────────────────────────────


@router.get("/api/missions", response_model=list[MissionSummary])
async def list_missions(
    registry: MissionRegistry = Depends(get_mission_registry),
) -> list[MissionSummary]:
    """List all missions with HATEOAS-LITE links."""
    records = registry.list_missions()
    return [_record_to_summary(r) for r in records]


@router.get("/api/missions/{mission_id}", response_model=Mission)
async def get_mission(
    mission_id: str,
    registry: MissionRegistry = Depends(get_mission_registry),
) -> Mission:
    """Fetch a single mission by mission_id, mid8, or mission_slug."""
    record = _get_mission_or_raise(registry, mission_id)
    return Mission(
        mission_id=record.mission_id,
        mission_slug=record.mission_slug,
        mission_number=record.display_number,
        mid8=record.mid8,
        friendly_name=record.friendly_name,
        mission_type=record.mission_type,
        target_branch=record.target_branch,
        created_at=record.created_at,
        lane_counts=_make_lane_counts(record.lane_counts),
        weighted_percentage=record.weighted_percentage,
        is_legacy=record.is_legacy,
        purpose_tldr=record.purpose_tldr,
        purpose_context=record.purpose_context,
        **{"_links": _mission_links(record.mission_id)},
    )


@router.get("/api/missions/{mission_id}/status", response_model=MissionStatus)
async def get_mission_status(
    mission_id: str,
    registry: MissionRegistry = Depends(get_mission_registry),
) -> MissionStatus:
    """Return lane counts and weighted progress for a single mission."""
    record = _get_mission_or_raise(registry, mission_id)
    lc = _make_lane_counts(record.lane_counts)
    return MissionStatus(
        mission_id=record.mission_id,
        lane_counts=lc,
        weighted_percentage=record.weighted_percentage,
        done_count=lc.done,
        total_count=lc.total,
        current_phase=2,
        **{
            "_links": {
                "self": Link(href=f"/api/missions/{record.mission_id}/status"),
                "mission": Link(href=f"/api/missions/{record.mission_id}"),
            }
        },
    )


@router.get("/api/missions/{mission_id}/workpackages", response_model=list[WorkPackageSummary])
async def list_work_packages(
    mission_id: str,
    registry: MissionRegistry = Depends(get_mission_registry),
) -> list[WorkPackageSummary]:
    """List all work packages for a mission with HATEOAS-LITE links."""
    record = _get_mission_or_raise(registry, mission_id)
    wp_registry = registry.workpackages_for(record.mission_slug)
    wps = wp_registry.list_work_packages()
    return [
        WorkPackageSummary(
            wp_id=wp.wp_id,
            title=wp.title,
            assignment=_wp_record_to_assignment(wp),
            **{
                "_links": {
                    "self": Link(href=f"/api/missions/{record.mission_id}/workpackages/{wp.wp_id}"),
                    "mission": Link(href=f"/api/missions/{record.mission_id}"),
                }
            },
        )
        for wp in wps
    ]


@router.get(
    "/api/missions/{mission_id}/workpackages/{wp_id}",
    response_model=WorkPackage,
)
async def get_work_package(
    mission_id: str,
    wp_id: str,
    registry: MissionRegistry = Depends(get_mission_registry),
) -> WorkPackage:
    """Fetch a single work package by WP ID."""
    record = _get_mission_or_raise(registry, mission_id)
    wp_registry = registry.workpackages_for(record.mission_slug)
    wp = wp_registry.get_work_package(wp_id)
    if wp is None:
        raise HTTPException(status_code=404, detail=f"Work package not found: {wp_id}")
    prompt_path_str: str | None = None
    prompt_markdown: str | None = None
    if wp.prompt_path and wp.prompt_path.exists():
        prompt_path_str = str(wp.prompt_path)
        try:
            raw = wp.prompt_path.read_text(encoding="utf-8")
            # Strip the YAML frontmatter — its fields are already structured on
            # this response (subtasks_done/total, dependencies, requirement_refs,
            # phase, assignment.*). Sending it inside prompt_markdown produces
            # an unformatted dump in the dashboard modal.
            prompt_markdown = _RE_PROMPT_FRONTMATTER.sub("", raw, count=1).lstrip()
        except OSError:
            prompt_markdown = None
    return WorkPackage(
        wp_id=wp.wp_id,
        title=wp.title,
        assignment=_wp_record_to_assignment(wp),
        subtasks_done=wp.subtasks_done,
        subtasks_total=wp.subtasks_total,
        dependencies=list(wp.dependencies),
        requirement_refs=list(wp.requirement_refs),
        phase=wp.phase,
        prompt_path=prompt_path_str,
        prompt_markdown=prompt_markdown,
        prompt_ref=prompt_path_str,
        **{"_links": _wp_links(record.mission_id, wp.wp_id)},
    )
