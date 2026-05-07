"""Router: glossary health, terms, and full-page browser.

Each route handler delegates to :class:`~specify_cli.glossary.service.GlossaryService`,
keeping handler bodies well under the FR-009 line budget.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse

from dashboard.api.models import GlossaryHealthResponse, GlossaryTermRecord
from specify_cli.glossary.service import GlossaryService

__all__ = ["register"]

logger = logging.getLogger(__name__)

_GLOSSARY_HTML_PATH = (
    Path(__file__).resolve().parents[3]
    / "specify_cli"
    / "dashboard"
    / "templates"
    / "glossary.html"
)


def register(app: FastAPI) -> None:
    """Mount the glossary router on ``app``."""
    router = APIRouter(tags=["glossary"])

    @router.get("/api/glossary-health", response_model=GlossaryHealthResponse)
    def glossary_health(request: Request):
        project_dir = Path(request.app.state.project_dir)
        return GlossaryService(project_dir).get_health()

    @router.get("/api/glossary-terms", response_model=list[GlossaryTermRecord])
    def glossary_terms(request: Request):
        project_dir = Path(request.app.state.project_dir)
        return GlossaryService(project_dir).get_terms()

    @router.get("/glossary", response_class=HTMLResponse)
    def glossary_page():
        return HTMLResponse(content=_GLOSSARY_HTML_PATH.read_bytes().decode("utf-8"))

    app.include_router(router)
