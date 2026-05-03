"""Router: GET /api/health.

The legacy handler echoed the configured project token in the response
when one was present. We mirror that by reading ``app.state.project_token``
through the request and forwarding it to ``ProjectStateService.get_health``.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request

from dashboard.api.models import HealthResponse
from dashboard.services.project_state import ProjectStateService

__all__ = ["register"]


def register(app: FastAPI) -> None:
    """Mount the health router on ``app``."""
    router = APIRouter()

    @router.get("/api/health", response_model=HealthResponse)
    def get_health(request: Request):
        project_dir = Path(request.app.state.project_dir)
        token = getattr(request.app.state, "project_token", None)
        return ProjectStateService(project_dir).get_health(token=token)

    app.include_router(router)
