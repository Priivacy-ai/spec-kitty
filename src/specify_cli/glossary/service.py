"""Domain service for glossary health and terms data.

Pure domain logic — no FastAPI or Pydantic imports.
The FastAPI router delegates to this service; the legacy HTTP handler
may also call it directly.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from specify_cli.glossary.semantic_events import iter_semantic_conflicts
from specify_cli.glossary.types import GlossaryHealthResponse, GlossaryTermRecord

__all__ = ["GlossaryService"]

logger = logging.getLogger(__name__)


def _empty_health_response() -> GlossaryHealthResponse:
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


class GlossaryService:
    """Domain service for glossary health and term data.

    Usage::

        service = GlossaryService(project_dir=Path("/my/project"))
        health = service.get_health()
        terms = service.get_terms()
    """

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir

    def get_health(self) -> GlossaryHealthResponse:
        """Return a :class:`~specify_cli.glossary.types.GlossaryHealthResponse` dict."""
        try:
            senses = _collect_all_senses(self._project_dir)
            active = sum(1 for t in senses if t.status.value == "active")
            draft = sum(1 for t in senses if t.status.value == "draft")
            deprecated = sum(1 for t in senses if t.status.value == "deprecated")
            high_count = 0
            last_at: str | None = None
            for conflict in iter_semantic_conflicts(self._project_dir):
                if conflict.severity not in {"high", "critical"}:
                    continue
                high_count += 1
                if conflict.timestamp:
                    last_at = (
                        max(last_at, conflict.timestamp) if last_at else conflict.timestamp
                    )
            entity_dir = (
                self._project_dir / ".kittify" / "charter" / "compiled" / "glossary"
            )
            entity_generated = entity_dir.exists() and any(entity_dir.iterdir())
            return {
                "total_terms": len(senses),
                "active_count": active,
                "draft_count": draft,
                "deprecated_count": deprecated,
                "high_severity_drift_count": high_count,
                "orphaned_term_count": _count_orphaned_terms(self._project_dir),
                "entity_pages_generated": entity_generated,
                "entity_pages_path": str(entity_dir) if entity_dir.exists() else None,
                "last_conflict_at": last_at,
            }
        except Exception as exc:
            logger.exception("glossary health error: %s", exc)
            return _empty_health_response()

    def get_terms(self) -> list[GlossaryTermRecord]:
        """Return a list of :class:`~specify_cli.glossary.types.GlossaryTermRecord` dicts."""
        try:
            senses = _collect_all_senses(self._project_dir)
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
