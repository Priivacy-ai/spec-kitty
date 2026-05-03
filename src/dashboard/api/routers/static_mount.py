"""Router: ``/`` (dashboard shell) and ``/static`` (static assets).

The legacy stack served the dashboard HTML shell on ``GET /`` and any
file under ``src/specify_cli/dashboard/static/`` via the
``/static/...`` URL prefix. We preserve both behaviors here:

* ``StaticFiles`` mounted at ``/static`` serves the legacy directory tree.
* ``GET /`` returns the rendered ``index.html`` payload via
  ``HTMLResponse``, which is the documented model-equivalent return for
  HTML content (per the WP04 brief).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from specify_cli.dashboard_templates import get_dashboard_html_bytes

__all__ = ["register"]

# Resolve once at import time. Importing this router module from the
# spec-kitty install tree keeps the path stable across check-out layouts.
_STATIC_DIR = (
    Path(__file__).resolve().parents[3]
    / "specify_cli"
    / "dashboard"
    / "static"
).resolve()


def register(app: FastAPI) -> None:
    """Mount the static asset tree and the dashboard shell route."""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    def home():
        return HTMLResponse(content=get_dashboard_html_bytes().decode("utf-8"))

    app.include_router(router)
    # ``StaticFiles`` is the canonical FastAPI mount for serving a directory
    # tree; it is not a ``Response`` write inside a route body, so it does
    # not conflict with FR-009 / NFR-007.
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
