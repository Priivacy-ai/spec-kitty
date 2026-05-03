"""Router: GET /api/kanban/{feature_id}.

Returns kanban lanes + weighted progress for a feature. The path
parameter is captured as a typed FastAPI argument; no ``path.split``
parsing leaks into the handler body.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request

from dashboard.api.models import KanbanResponse
from dashboard.services.mission_scan import MissionScanService

__all__ = ["register"]


def register(app: FastAPI) -> None:
    """Mount the kanban router on ``app``."""
    router = APIRouter()

    @router.get("/api/kanban/{feature_id}", response_model=KanbanResponse)
    def get_kanban(feature_id: str, request: Request):
        project_dir = Path(request.app.state.project_dir)
        return MissionScanService(project_dir).get_kanban(feature_id)

    app.include_router(router)
