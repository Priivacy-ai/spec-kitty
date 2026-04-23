"""Glossary-focused dashboard HTTP handlers."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..api_types import GlossaryHealthResponse, GlossaryTermRecord
from .base import DashboardHandler

__all__ = ["GlossaryHandler"]

logger = logging.getLogger(__name__)

_GLOSSARY_HTML_PATH = Path(__file__).resolve().parents[1] / "templates" / "glossary.html"
_GLOSSARY_HTML_BYTES: bytes = _GLOSSARY_HTML_PATH.read_bytes()


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

            # High-severity drift count: scan _cli.events.jsonl
            event_log = project_dir / ".kittify" / "events" / "glossary" / "_cli.events.jsonl"
            high_count = 0
            last_at: str | None = None
            if event_log.exists():
                for line in event_log.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        if ev.get("event_type") == "semantic_check_evaluated" and ev.get("severity") in {"high", "critical"}:
                            high_count += 1
                            last_at = ev.get("checked_at")
                    except json.JSONDecodeError:
                        pass

            entity_pages_dir = project_dir / ".kittify" / "charter" / "compiled" / "glossary"
            entity_pages_generated = entity_pages_dir.exists() and any(entity_pages_dir.iterdir())

            response: GlossaryHealthResponse = {
                "total_terms": len(senses),
                "active_count": active_count,
                "draft_count": draft_count,
                "deprecated_count": deprecated_count,
                "high_severity_drift_count": high_count,
                "orphaned_term_count": 0,
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
