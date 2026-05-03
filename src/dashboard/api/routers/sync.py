"""Router: POST /api/sync/trigger.

Token validation runs in ``Depends(verify_project_token)``. The handler
body is a single service call; the HTTP status code piggybacks on the
``Response`` parameter (a FastAPI dependency injection, not a
hand-written ``Response(...)`` write — this pattern is allowed by the
WP04 brief).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Response

from dashboard.api.deps import verify_project_token
from dashboard.api.models import SyncTriggerResponse
from dashboard.services.sync import SyncService

__all__ = ["register"]


def register(app: FastAPI) -> None:
    """Mount the sync-trigger router on ``app``."""
    router = APIRouter()

    @router.post("/api/sync/trigger", response_model=SyncTriggerResponse)
    def trigger_sync(
        response: Response,
        token: str | None = Depends(verify_project_token),
    ) -> dict[str, Any]:
        result = SyncService().trigger_sync(token=token)
        response.status_code = result.http_status
        return result.body()

    app.include_router(router)
