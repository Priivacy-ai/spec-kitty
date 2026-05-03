"""Router: dossier overview, artifacts, and snapshot export.

Each endpoint instantiates ``DossierAPIHandler`` and dispatches to the
matching method. The handler returns either a Pydantic response model
or an error dict shaped like ``{"error": ..., "status_code": int}``;
when an error dict comes back we surface it via ``JSONResponse`` with
the recorded status. That branch is the documented exception to FR-009
because the legacy handler emits this exact shape on per-route errors.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from specify_cli.dossier.api import DossierAPIHandler

__all__ = ["register"]

logger = logging.getLogger(__name__)


def _missing_feature() -> HTTPException:
    """Build the 400 response the legacy stack returned for missing slug."""
    return HTTPException(status_code=400, detail={"error": "Missing feature parameter"})


def _to_response(payload: Any) -> Any:
    """Convert a dossier handler payload to a route return value.

    Error dicts (with ``error`` + optional ``status_code``) become
    ``JSONResponse``; success payloads are returned as-is so FastAPI
    can serialize them via the configured response model.
    """
    if isinstance(payload, dict) and "error" in payload:
        status_code = int(payload.get("status_code", 500))
        return JSONResponse(status_code=status_code, content=payload)
    return payload


def _collect_artifact_filters(
    artifact_class: str | None,
    wp_id: str | None,
    step_id: str | None,
    required_only: str | None,
) -> dict[str, Any]:
    """Build the filter kwargs the dossier handler expects."""
    filters: dict[str, Any] = {}
    if artifact_class is not None:
        filters["class"] = artifact_class
    if wp_id is not None:
        filters["wp_id"] = wp_id
    if step_id is not None:
        filters["step_id"] = step_id
    if required_only is not None:
        filters["required_only"] = required_only
    return filters


def register(app: FastAPI) -> None:
    """Mount the dossier router on ``app``."""
    router = APIRouter()

    @router.get("/api/dossier/overview")
    def get_overview(request: Request, mission_slug: str | None = Query(default=None, alias="feature")):
        if not mission_slug:
            raise _missing_feature()
        handler = DossierAPIHandler(repo_root=Path(request.app.state.project_dir).resolve())
        return _to_response(handler.handle_dossier_overview(mission_slug))

    @router.get("/api/dossier/artifacts")
    def list_artifacts(
        request: Request,
        mission_slug: str | None = Query(default=None, alias="feature"),
        artifact_class: str | None = Query(default=None, alias="class"),
        wp_id: str | None = Query(default=None),
        step_id: str | None = Query(default=None),
        required_only: str | None = Query(default=None),
    ):
        if not mission_slug:
            raise _missing_feature()
        filters = _collect_artifact_filters(artifact_class, wp_id, step_id, required_only)
        handler = DossierAPIHandler(repo_root=Path(request.app.state.project_dir).resolve())
        return _to_response(handler.handle_dossier_artifacts(mission_slug, **filters))

    @router.get("/api/dossier/artifacts/{artifact_key}")
    def get_artifact_detail(
        artifact_key: str,
        request: Request,
        mission_slug: str | None = Query(default=None, alias="feature"),
    ):
        if not mission_slug:
            raise _missing_feature()
        handler = DossierAPIHandler(repo_root=Path(request.app.state.project_dir).resolve())
        return _to_response(handler.handle_dossier_artifact_detail(mission_slug, artifact_key))

    @router.get("/api/dossier/snapshots/export")
    def export_snapshot(request: Request, mission_slug: str | None = Query(default=None, alias="feature")):
        if not mission_slug:
            raise _missing_feature()
        handler = DossierAPIHandler(repo_root=Path(request.app.state.project_dir).resolve())
        return _to_response(handler.handle_dossier_snapshot_export(mission_slug))

    app.include_router(router)
