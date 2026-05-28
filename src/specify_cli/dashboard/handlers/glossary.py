"""Glossary-focused dashboard HTTP handlers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from specify_cli.glossary.exceptions import SeedFileValidationError
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
        glossary_urns = {
            n.get("urn") or n.get("id", "")
            for n in nodes
            if isinstance(n, dict) and str(n.get("urn") or n.get("id", "")).startswith("glossary:")
        }
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


def _collect_all_senses(repo_root: Path) -> list[Any]:
    """Load all TermSense objects from seed files across all scopes.

    Returns a flat list of TermSense objects, or an empty list on any error.
    Raises ``SeedFileValidationError`` if any scope has an invalid seed file
    and per-term recovery yields nothing usable.
    """
    senses, validation_errors = _collect_all_senses_with_errors(repo_root)
    if not senses and validation_errors:
        raise validation_errors[0]
    return senses


def _collect_all_senses_with_errors(repo_root: Path) -> tuple[list[Any], list[SeedFileValidationError]]:
    """Load glossary senses and retain validation errors for health reporting."""
    try:
        from specify_cli.glossary.scope import GlossaryScope, load_seed_file

        senses = []
        validation_errors: list[SeedFileValidationError] = []
        for scope in GlossaryScope:
            try:
                senses.extend(load_seed_file(scope, repo_root))
            except SeedFileValidationError as exc:
                # File-level validation rejected this scope as a whole. Try
                # per-term recovery so a handful of bad entries cannot blank
                # the entire glossary view in the dashboard.
                recovered = _recover_valid_senses(scope, repo_root, exc)
                if recovered:
                    senses.extend(recovered)
                validation_errors.append(exc)
            except Exception as exc:
                logger.debug("Skipping scope %s: %s", scope.value, exc)
        return senses, validation_errors
    except Exception as exc:
        logger.debug("Could not load glossary senses: %s", exc)
        return [], []


def _recover_valid_senses(
    scope: Any,
    repo_root: Path,
    original_error: SeedFileValidationError,
) -> list[Any]:
    """Best-effort per-term load when file-level validation has failed.

    Returns the subset of terms that pass schema validation individually.
    Logs a warning naming the scope, the number recovered, and the indices
    skipped so operators can see exactly which entries are malformed.
    """
    try:
        if any(e.term_index is None for e in original_error.errors):
            logger.warning(
                "glossary scope %s: refusing per-term recovery after file-level "
                "validation failure: %s",
                scope.value, original_error,
            )
            return []

        from datetime import datetime

        from ruamel.yaml import YAML

        from specify_cli.glossary.models import (
            Provenance,
            TermSense,
            TermSurface,
        )
        from specify_cli.glossary.scope import _parse_sense_status
        from specify_cli.glossary.seed_schema import GlossarySeedTerm

        seed_path = repo_root / ".kittify" / "glossaries" / f"{scope.value}.yaml"
        if not seed_path.exists():
            return []
        yaml = YAML()
        yaml.preserve_quotes = True
        data = yaml.load(seed_path)
        raw_terms = (data or {}).get("terms") or []

        recovered: list[Any] = []
        skipped: list[int] = []
        for idx, term_data in enumerate(raw_terms):
            try:
                GlossarySeedTerm.model_validate(term_data)
            except Exception:
                skipped.append(idx)
                continue
            recovered.append(
                TermSense(
                    surface=TermSurface(term_data["surface"]),
                    scope=scope.value,
                    definition=term_data["definition"],
                    provenance=Provenance(
                        actor_id="system:seed_file",
                        timestamp=datetime.now(),
                        source="seed_file",
                    ),
                    confidence=term_data.get("confidence", 1.0),
                    status=_parse_sense_status(term_data.get("status")),
                )
            )
        if skipped:
            logger.warning(
                "glossary scope %s: recovered %d/%d terms; skipped indices %s "
                "(file-level validation failed: %s)",
                scope.value, len(recovered), len(raw_terms), skipped, original_error,
            )
        return recovered
    except Exception as exc:
        logger.debug("per-term recovery failed for scope %s: %s", scope.value, exc)
        return []


def _format_validation_errors(
    validation_errors: list[SeedFileValidationError],
) -> list[dict[str, Any]] | None:
    """Convert validation exceptions into the dashboard health JSON shape."""
    if not validation_errors:
        return None
    return [
        {
            "file": str(error.file_path),
            "term_index": item.term_index,
            "term_surface": item.term_surface,
            "field": item.field,
            "message": item.message,
        }
        for error in validation_errors
        for item in error.errors
    ]


class GlossaryHandler(DashboardHandler):
    """Serve glossary health, terms list, and the full-page browser."""

    def handle_glossary_health(self) -> None:
        """Return GET /api/glossary-health with a GlossaryHealthResponse."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            if self.project_dir is None:
                raise RuntimeError("dashboard project_dir is not configured")
            project_dir = Path(self.project_dir)
            senses, validation_errors = _collect_all_senses_with_errors(project_dir)

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
                "validation_errors": _format_validation_errors(validation_errors),
            }
        except SeedFileValidationError as exc:
            logger.warning("glossary health: validation error in %s: %s", exc.file_path, exc)
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
                "validation_errors": _format_validation_errors([exc]),
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
                "validation_errors": None,
            }

        self.wfile.write(json.dumps(response).encode())

    def handle_glossary_terms(self) -> None:
        """Return GET /api/glossary-terms with a list of GlossaryTermRecord."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            if self.project_dir is None:
                raise RuntimeError("dashboard project_dir is not configured")
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
        except SeedFileValidationError as exc:
            logger.warning(
                "glossary terms: validation error in %s: %s",
                exc.file_path, exc,
            )
            records = []
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
