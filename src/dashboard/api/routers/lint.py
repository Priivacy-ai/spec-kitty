"""Router: GET /api/charter-lint (decay watch tile data).

Delegates to :class:`~specify_cli.charter_lint.service.LintService` — the
handler body is a single-call adapter (FR-003, FR-004, FR-005, FR-006, FR-017).
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request

from dashboard.api.models import DecayWatchTileResponse
from specify_cli.charter_lint.service import LintService

__all__ = ["register"]

logger = logging.getLogger(__name__)


def register(app: FastAPI) -> None:
    """Mount the lint router on ``app``."""
    router = APIRouter(tags=["charter"])

    @router.get("/api/charter-lint", response_model=DecayWatchTileResponse)
    def charter_lint(request: Request):
        project_dir = Path(request.app.state.project_dir)
        return LintService(project_dir).get_decay_tile()

    app.include_router(router)
