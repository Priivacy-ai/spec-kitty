"""Router: GET /api/features (retired).

This route is permanently retired (HTTP 410 Gone). Clients should migrate
to ``GET /api/missions``. The route is kept registered so existing integrations
receive a structured error rather than a 404, but it is hidden from the
OpenAPI schema (``include_in_schema=False``).
"""
from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

__all__ = ["register"]


def _gone_response(deprecated_path: str, successor_path: str) -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={"error": "endpoint_retired", "successor": successor_path},
    )


def register(app: FastAPI) -> None:
    """Mount the features router on ``app``."""
    router = APIRouter(tags=["kanban"])

    @router.get("/api/features", include_in_schema=False)
    def list_features():
        return _gone_response("/api/features", "/api/missions")

    app.include_router(router)
