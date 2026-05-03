"""Router: glossary health, terms, and full-page browser.

Transport-only migration: the legacy handler logic is recreated here
verbatim in private helpers and called from the route bodies, which
keeps each handler under the FR-009 line budget. Service extraction is
deferred to follow-up issue #954.

# TODO(follow-up): extract a glossary service object so these handlers
# become single-call adapters. Tracked at
# https://github.com/Priivacy-ai/spec-kitty/issues/954.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse

from dashboard.api.models import GlossaryHealthResponse, GlossaryTermRecord
from specify_cli.glossary.semantic_events import iter_semantic_conflicts

__all__ = ["register"]

logger = logging.getLogger(__name__)

_GLOSSARY_HTML_PATH = (
    Path(__file__).resolve().parents[3]
    / "specify_cli"
    / "dashboard"
    / "templates"
    / "glossary.html"
)


def _empty_health_response() -> dict[str, Any]:
    return {
        "total_terms": 0,
        "active_count": 0,
        "draft_count": 0,
        "deprecated_count": 0,
        "high_severity_drift_count": 0,
        "orphaned_term_count": 0,
        "entity_pages_generated": False,
        "entity_pages_path": None,
        "last_conflict_at": None,
    }


def _count_orphaned_terms(project_dir: Path) -> int:
    """Count glossary terms with no incoming vocabulary edge in the merged DRG."""
    try:
        import yaml

        drg_path = project_dir / ".kittify" / "doctrine" / "graph.yaml"
        if not drg_path.exists():
            return 0
        with drg_path.open(encoding="utf-8") as fh:
            drg_data = yaml.safe_load(fh)
        if not isinstance(drg_data, dict):
            return 0
        nodes = drg_data.get("nodes", [])
        edges = drg_data.get("edges", [])
        glossary_urns = {
            n.get("urn") or n.get("id", "")
            for n in nodes
            if isinstance(n, dict)
            and str(n.get("urn") or n.get("id", "")).startswith("glossary:")
        }
        if not glossary_urns:
            return 0
        covered: set[str] = set()
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            rel = edge.get("relation") or edge.get("type") or edge.get("rel", "")
            if str(rel).lower() == "vocabulary":
                covered.add(edge.get("target", ""))
        return len(glossary_urns - covered)
    except Exception as exc:
        logger.debug("orphaned term count unavailable: %s", exc)
        return 0


def _collect_all_senses(repo_root: Path) -> list[Any]:
    """Load all TermSense objects across every glossary scope."""
    try:
        from specify_cli.glossary.scope import GlossaryScope, load_seed_file

        senses: list[Any] = []
        for scope in GlossaryScope:
            try:
                senses.extend(load_seed_file(scope, repo_root))
            except Exception as exc:
                logger.debug("Skipping scope %s: %s", scope.value, exc)
        return senses
    except Exception as exc:
        logger.debug("Could not load glossary senses: %s", exc)
        return []


def _build_glossary_health(project_dir: Path) -> dict[str, Any]:
    """Recreate the legacy glossary-health payload."""
    try:
        senses = _collect_all_senses(project_dir)
        active = sum(1 for t in senses if t.status.value == "active")
        draft = sum(1 for t in senses if t.status.value == "draft")
        deprecated = sum(1 for t in senses if t.status.value == "deprecated")
        high_count = 0
        last_at: str | None = None
        for conflict in iter_semantic_conflicts(project_dir):
            if conflict.severity not in {"high", "critical"}:
                continue
            high_count += 1
            if conflict.timestamp:
                last_at = (
                    max(last_at, conflict.timestamp) if last_at else conflict.timestamp
                )
        entity_dir = project_dir / ".kittify" / "charter" / "compiled" / "glossary"
        entity_generated = entity_dir.exists() and any(entity_dir.iterdir())
        return {
            "total_terms": len(senses),
            "active_count": active,
            "draft_count": draft,
            "deprecated_count": deprecated,
            "high_severity_drift_count": high_count,
            "orphaned_term_count": _count_orphaned_terms(project_dir),
            "entity_pages_generated": entity_generated,
            "entity_pages_path": str(entity_dir) if entity_dir.exists() else None,
            "last_conflict_at": last_at,
        }
    except Exception as exc:
        logger.exception("glossary health error: %s", exc)
        return _empty_health_response()


def _build_glossary_terms(project_dir: Path) -> list[dict[str, Any]]:
    """Recreate the legacy glossary-terms payload."""
    try:
        senses = _collect_all_senses(project_dir)
        return [
            {
                "surface": t.surface.surface_text,
                "definition": t.definition or "",
                "status": t.status.value if t.status else "draft",
                "confidence": float(t.confidence) if t.confidence is not None else 0.0,
            }
            for t in senses
        ]
    except Exception as exc:
        logger.exception("glossary terms error: %s", exc)
        return []


def register(app: FastAPI) -> None:
    """Mount the glossary router on ``app``."""
    router = APIRouter()

    @router.get("/api/glossary-health", response_model=GlossaryHealthResponse)
    def glossary_health(request: Request):
        # TODO(follow-up): extract glossary service object — see dashboard
        # service-extraction follow-up mission (issue #954).
        return _build_glossary_health(Path(request.app.state.project_dir))

    @router.get("/api/glossary-terms", response_model=list[GlossaryTermRecord])
    def glossary_terms(request: Request):
        # TODO(follow-up): extract glossary service object — see dashboard
        # service-extraction follow-up mission (issue #954).
        return _build_glossary_terms(Path(request.app.state.project_dir))

    @router.get("/glossary", response_class=HTMLResponse)
    def glossary_page():
        # TODO(follow-up): extract glossary service object — see dashboard
        # service-extraction follow-up mission (issue #954).
        return HTMLResponse(content=_GLOSSARY_HTML_PATH.read_bytes().decode("utf-8"))

    app.include_router(router)
