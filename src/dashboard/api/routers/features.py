"""Router: GET /api/features.

Mission scan + active feature resolution. The handler delegates the
heavy lifting to ``MissionScanService.get_features_list()`` and otherwise
returns a thin success/failure pair.

Per ``DIRECTIVE_API_DEPENDENCY_DIRECTION`` (mission
``mission-registry-and-api-boundary-doctrine-01KQPDBB``), the handler does
not import the scanner directly — it pulls the ``MissionRegistry`` from
``app.state`` via the ``get_mission_registry`` Depends helper and passes it
into the service. The architectural test in
``tests/architectural/test_transport_does_not_import_scanner.py`` (WP05)
will enforce this absence at import time.

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

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from dashboard.api.deps import get_mission_registry
from dashboard.api.models import FeaturesListResponse
from dashboard.services.mission_scan import MissionScanService
from dashboard.services.registry import MissionRegistry

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
    def list_features(
        request: Request,
        registry: MissionRegistry = Depends(get_mission_registry),
    ):
        project_dir = Path(request.app.state.project_dir)
        try:
            return MissionScanService(project_dir, registry=registry).get_features_list()
        except Exception as exc:  # pragma: no cover - defensive parity branch
            return _failure(str(exc))

    app.include_router(router)
