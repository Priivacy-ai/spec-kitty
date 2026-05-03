"""Router: GET /api/charter.

Serves the project charter as plain text. Returns 404 when no charter
is configured for the project. ``PlainTextResponse(content=...)`` is
the documented model-equivalent return for non-JSON content (it is not
an arbitrary ``Response`` write, per the WP04 brief).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from specify_cli.dashboard_charter_path import resolve_project_charter_path

__all__ = ["register"]


def register(app: FastAPI) -> None:
    """Mount the charter router on ``app``."""
    router = APIRouter()

    @router.get("/api/charter", response_class=PlainTextResponse)
    def get_charter(request: Request):
        project_dir = Path(request.app.state.project_dir)
        charter_path = resolve_project_charter_path(project_dir)
        if charter_path is None:
            raise HTTPException(status_code=404, detail="Charter not found")
        content = charter_path.read_text(encoding="utf-8")
        return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8")

    app.include_router(router)
