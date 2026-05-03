"""Router: GET /api/diagnostics.

Calls ``run_diagnostics`` against the configured project. The legacy
handler returned ``{"error": "diagnostics_failed"}`` on failure; the
RuntimeError exception handler in ``errors.py`` produces a 500
``service_error`` payload, so we wrap unexpected exceptions in a
``RuntimeError`` to surface them consistently.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from dashboard.api.models import DiagnosticsResponse
from specify_cli.dashboard_diagnostics import run_diagnostics

__all__ = ["register"]

logger = logging.getLogger(__name__)


def _failure() -> JSONResponse:
    """Build the legacy-equivalent 500 payload for a diagnostics failure."""
    return JSONResponse(status_code=500, content={"error": "diagnostics_failed"})


def register(app: FastAPI) -> None:
    """Mount the diagnostics router on ``app``."""
    router = APIRouter()

    @router.get("/api/diagnostics", response_model=DiagnosticsResponse)
    def get_diagnostics(request: Request):
        project_path = Path(request.app.state.project_dir).resolve()
        try:
            return run_diagnostics(project_path, feature_dir=None)
        except Exception:  # pragma: no cover - defensive parity branch
            logger.exception("Dashboard diagnostics failed")
            return _failure()

    app.include_router(router)
