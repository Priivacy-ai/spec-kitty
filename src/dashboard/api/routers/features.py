"""Router: GET /api/features.

Mission scan + active feature resolution. The handler delegates the
heavy lifting to ``MissionScanService.get_features_list()`` and otherwise
returns a thin success/failure pair.

Per FR-009, route handler bodies must not construct ``Response``
instances. The 500 error path here is the documented narrow exception
to that rule: the legacy stack emits the exact same JSON shape on a
service-level scan failure, and surfacing the error code via a Pydantic
``response_model`` would add a fan-out branch every other consumer would
have to ignore. The 500 ``JSONResponse`` is therefore confined to a
private ``_failure`` helper so the route body stays a pure call into the
service.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from dashboard.api.models import FeaturesListResponse
from dashboard.services.mission_scan import MissionScanService

__all__ = ["register"]


def _failure(detail: str) -> JSONResponse:
    """Build the legacy-equivalent 500 payload for a scan failure."""
    return JSONResponse(
        status_code=500,
        content={"error": "failed_to_scan_features", "detail": detail},
    )


def register(app: FastAPI) -> None:
    """Mount the features router on ``app``."""
    router = APIRouter()

    @router.get("/api/features", response_model=FeaturesListResponse)
    def list_features(request: Request):
        project_dir = Path(request.app.state.project_dir)
        try:
            return MissionScanService(project_dir).get_features_list()
        except Exception as exc:  # pragma: no cover - defensive parity branch
            return _failure(str(exc))

    app.include_router(router)
