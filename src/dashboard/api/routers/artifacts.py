"""Router: feature-scoped artifact reads.

Mounts seven endpoints that read research, contracts, checklists, and
named primary artifacts from a feature directory. Each endpoint is a
thin pass-through to ``DashboardFileReader``; missing files raise
``HTTPException(404)`` so the global exception machinery handles the
response shape.

``PlainTextResponse`` is the documented model-equivalent return for
non-JSON content (per the WP04 brief) — the route body never constructs
a ``Response`` directly.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from dashboard.api.models import ArtifactDirectoryResponse, ResearchResponse
from dashboard.file_reader import DashboardFileReader

__all__ = ["register"]


def _reader(request: Request) -> DashboardFileReader:
    """Build a reader bound to the configured project directory."""
    return DashboardFileReader(Path(request.app.state.project_dir))


def register(app: FastAPI) -> None:
    """Mount the artifacts router on ``app``."""
    router = APIRouter()

    @router.get("/api/research/{feature_id}", response_model=ResearchResponse)
    def get_research(feature_id: str, request: Request):
        return _reader(request).read_research(feature_id)

    @router.get("/api/research/{feature_id}/{file_name}", response_class=PlainTextResponse)
    def get_research_file(feature_id: str, file_name: str, request: Request):
        result = _reader(request).read_artifact_file(feature_id, file_name)
        if not result.found:
            raise HTTPException(status_code=404)
        return PlainTextResponse(content=result.content or "")

    @router.get("/api/contracts/{feature_id}", response_model=ArtifactDirectoryResponse)
    def list_contracts(feature_id: str, request: Request):
        return _reader(request).read_artifact_directory(feature_id, "contracts", "📝")

    @router.get("/api/contracts/{feature_id}/{file_name}", response_class=PlainTextResponse)
    def get_contract_file(feature_id: str, file_name: str, request: Request):
        result = _reader(request).read_artifact_file(feature_id, file_name)
        if not result.found:
            raise HTTPException(status_code=404)
        return PlainTextResponse(content=result.content or "")

    @router.get("/api/checklists/{feature_id}", response_model=ArtifactDirectoryResponse)
    def list_checklists(feature_id: str, request: Request):
        return _reader(request).read_artifact_directory(feature_id, "checklists", "✅")

    @router.get("/api/checklists/{feature_id}/{file_name}", response_class=PlainTextResponse)
    def get_checklist_file(feature_id: str, file_name: str, request: Request):
        result = _reader(request).read_artifact_file(feature_id, file_name)
        if not result.found:
            raise HTTPException(status_code=404)
        return PlainTextResponse(content=result.content or "")

    @router.get("/api/artifact/{feature_id}/{name}", response_class=PlainTextResponse)
    def get_artifact(feature_id: str, name: str, request: Request):
        result = _reader(request).read_named_artifact(feature_id, name)
        if not result.found:
            raise HTTPException(status_code=404)
        return PlainTextResponse(content=result.content or "")

    app.include_router(router)
