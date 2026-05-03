"""Router: GET /api/kanban/{feature_id}.

Returns kanban lanes + weighted progress for a feature. The path
parameter is captured as a typed FastAPI argument; no ``path.split``
parsing leaks into the handler body.

Per ``DIRECTIVE_API_DEPENDENCY_DIRECTION`` (mission
``mission-registry-and-api-boundary-doctrine-01KQPDBB``), the handler does
not import the scanner directly. Mission resolution happens through the
``MissionRegistry`` injected via ``Depends(get_mission_registry)``; the
service then delegates kanban-board assembly to its existing helpers.

Ambiguous mid8 handles (an 8-character handle that matches more than one
mission) produce a structured ``MISSION_AMBIGUOUS_SELECTOR`` error per
the mission-identity rule (CLAUDE.md §"Mission Identity Model (083+)"):
"ambiguous handles produce a structured error… no silent fallback".
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from dashboard.api.deps import get_mission_registry
from dashboard.api.models import KanbanResponse
from dashboard.services.mission_scan import MissionScanService
from dashboard.services.registry import MissionRecord, MissionRegistry

__all__ = ["register"]


def _ambiguous_mid8_candidates(
    registry: MissionRegistry, handle: str
) -> list[MissionRecord]:
    """Return missions whose ``mid8`` matches the 8-char handle.

    The registry's ``get_mission()`` returns ``None`` on ambiguous mid8 by
    contract (see ``MissionRegistry.get_mission`` docstring). Routers
    convert that signal into a structured error listing the candidates so
    operators can disambiguate by passing a longer prefix or the full
    mission_id. Empty list means "not a mid8 conflict — handle simply did
    not match any known mission".
    """
    if len(handle) != 8:
        return []
    return [m for m in registry.list_missions() if m.mid8 and m.mid8 == handle]


def _ambiguous_selector_response(
    handle: str, candidates: list[MissionRecord]
) -> JSONResponse:
    """Build the structured 409 ``MISSION_AMBIGUOUS_SELECTOR`` payload.

    Module-level helper (not constructed inline in the route body) per
    FR-009 / NFR-007: route handler bodies must not construct ``Response``
    instances directly.
    """
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "MISSION_AMBIGUOUS_SELECTOR",
                "message": (
                    f"Handle {handle!r} matches {len(candidates)} missions; "
                    "pass a longer prefix or the full mission_id."
                ),
                "candidates": [
                    {
                        "mission_id": m.mission_id,
                        "mission_slug": m.mission_slug,
                        "mid8": m.mid8,
                        "display_number": m.display_number,
                    }
                    for m in candidates
                ],
            }
        },
    )


def register(app: FastAPI) -> None:
    """Mount the kanban router on ``app``."""
    router = APIRouter()

    @router.get("/api/kanban/{feature_id}", response_model=KanbanResponse)
    def get_kanban(
        feature_id: str,
        request: Request,
        registry: MissionRegistry = Depends(get_mission_registry),
    ):
        project_dir = Path(request.app.state.project_dir)

        # Pre-resolve the mission through the registry so ambiguous mid8
        # handles surface a structured error rather than silently picking
        # the first match (or returning empty kanban without explanation).
        if registry.get_mission(feature_id) is None:
            candidates = _ambiguous_mid8_candidates(registry, feature_id)
            if len(candidates) > 1:
                return _ambiguous_selector_response(feature_id, candidates)
            # Unknown handle: legacy behavior is to return an empty kanban
            # (preserves wire shape parity for clients that probe by slug).

        return MissionScanService(project_dir, registry=registry).get_kanban(feature_id)

    app.include_router(router)
