"""Glossary-focused dashboard HTTP handlers."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from specify_cli.glossary.semantic_events import iter_semantic_conflicts

from ..api_types import GlossaryHealthResponse, GlossaryTermRecord
from .base import DashboardHandler

__all__ = ["GlossaryHandler"]

logger = logging.getLogger(__name__)

_GLOSSARY_HTML_PATH = Path(__file__).resolve().parents[1] / "templates" / "glossary.html"
_GLOSSARY_HTML_BYTES: bytes = _GLOSSARY_HTML_PATH.read_bytes()


def _count_orphaned_terms(project_dir: Path) -> int:
    """Count glossary terms with no incoming vocabulary edge in the merged DRG.

    Returns 0 when the DRG is unavailable or has no glossary nodes (e.g. before
    WP5.1 lands). Once WP5.1 adds ``glossary:<id>`` URN nodes and ``vocabulary``
    edges this will return the true orphan count.
    """
    try:
        import yaml  # ruamel.yaml or pyyaml

        drg_path = project_dir / ".kittify" / "doctrine" / "graph.yaml"
        if not drg_path.exists():
            return 0
        with drg_path.open(encoding="utf-8") as fh:
            drg_data = yaml.safe_load(fh)
        if not isinstance(drg_data, dict):
            return 0
        nodes = drg_data.get("nodes", [])
        edges = drg_data.get("edges", [])
        # Collect all glossary URNs
        glossary_urns = {n.get("urn") or n.get("id", "") for n in nodes if isinstance(n, dict) and str(n.get("urn") or n.get("id", "")).startswith("glossary:")}
        if not glossary_urns:
            return 0  # WP5.1 not yet merged
        # Collect all URNs that have at least one incoming vocabulary edge
        covered: set[str] = set()
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            rel = edge.get("relation") or edge.get("type") or edge.get("rel", "")
            if str(rel).lower() == "vocabulary":
                target = edge.get("target", "")
                covered.add(target)
        orphans = glossary_urns - covered
        return len(orphans)
    except Exception as exc:
        logger.debug("orphaned term count unavailable: %s", exc)
        return 0


def _collect_all_senses(repo_root: Path) -> list:
    """Load all TermSense objects from seed files across all scopes.

    Returns a flat list of TermSense objects, or an empty list on any error.
    """
    try:
        from specify_cli.glossary.scope import GlossaryScope, load_seed_file

        senses = []
        for scope in GlossaryScope:
            try:
                senses.extend(load_seed_file(scope, repo_root))
            except Exception as exc:
                logger.debug("Skipping scope %s: %s", scope.value, exc)
        return senses
    except Exception as exc:
        logger.debug("Could not load glossary senses: %s", exc)
        return []


class GlossaryHandler(DashboardHandler):
    """Serve glossary health, terms list, and the full-page browser."""

    def handle_glossary_health(self) -> None:
        """Return GET /api/glossary-health with a GlossaryHealthResponse."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            project_dir = Path(self.project_dir)
            senses = _collect_all_senses(project_dir)

            active_count = sum(1 for t in senses if t.status.value == "active")
            draft_count = sum(1 for t in senses if t.status.value == "draft")
            deprecated_count = sum(1 for t in senses if t.status.value == "deprecated")

            high_count = 0
            last_at: str | None = None
            for conflict in iter_semantic_conflicts(project_dir):
                if conflict.severity not in {"high", "critical"}:
                    continue
                high_count += 1
                if conflict.timestamp:
                    last_at = max(last_at, conflict.timestamp) if last_at else conflict.timestamp

            entity_pages_dir = project_dir / ".kittify" / "charter" / "compiled" / "glossary"
            entity_pages_generated = entity_pages_dir.exists() and any(entity_pages_dir.iterdir())

            response: GlossaryHealthResponse = {
                "total_terms": len(senses),
                "active_count": active_count,
                "draft_count": draft_count,
                "deprecated_count": deprecated_count,
                "high_severity_drift_count": high_count,
                "orphaned_term_count": _count_orphaned_terms(project_dir),
                "entity_pages_generated": entity_pages_generated,
                "entity_pages_path": str(entity_pages_dir) if entity_pages_dir.exists() else None,
                "last_conflict_at": last_at,
            }
        except Exception as exc:
            logger.exception("glossary health error: %s", exc)
            response = {
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

        self.wfile.write(json.dumps(response).encode())

    def handle_glossary_terms(self) -> None:
        """Return GET /api/glossary-terms with a list of GlossaryTermRecord."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            senses = _collect_all_senses(Path(self.project_dir))
            records: list[GlossaryTermRecord] = [
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
            records = []

        self.wfile.write(json.dumps(records).encode())

    def handle_glossary_page(self) -> None:
        """Serve GET /glossary — return the static glossary browser HTML."""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_GLOSSARY_HTML_BYTES)
