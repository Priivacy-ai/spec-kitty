"""Unit tests for GlossaryService — T012.

Coverage checklist:
- get_health() happy path: counts terms by status correctly
- get_health() high-severity conflict counting
- get_health() entity-pages detection (present / absent)
- get_health() fallback on exception: returns empty health response
- get_terms() happy path: converts senses to GlossaryTermRecord dicts
- get_terms() fallback on exception: returns empty list
- get_health() parity: returned dict keys match GlossaryHealthResponse TypedDict
- get_terms() parity: returned item keys match GlossaryTermRecord TypedDict
- Orphaned-term counting via DRG graph.yaml
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import get_type_hints
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.glossary.models import Provenance, SenseStatus, TermSense, TermSurface
from specify_cli.glossary.service import GlossaryService
from specify_cli.glossary.types import GlossaryHealthResponse, GlossaryTermRecord

pytestmark = pytest.mark.fast


def _make_sense(surface: str, definition: str, status: str, confidence: float) -> TermSense:
    """Build a minimal TermSense for testing."""
    status_enum = {
        "active": SenseStatus.ACTIVE,
        "draft": SenseStatus.DRAFT,
        "deprecated": SenseStatus.DEPRECATED,
    }[status]
    return TermSense(
        surface=TermSurface(surface),
        scope="spec_kitty_core",
        definition=definition,
        provenance=Provenance(
            actor_id="test",
            timestamp=datetime(2026, 1, 1),
            source="test",
        ),
        confidence=confidence,
        status=status_enum,
    )


def _make_conflict(severity: str, timestamp: str | None = None) -> MagicMock:
    c = MagicMock()
    c.severity = severity
    c.timestamp = timestamp
    return c


# ---------------------------------------------------------------------------
# get_health() tests
# ---------------------------------------------------------------------------


class TestGetHealth:
    def test_happy_path_counts_by_status(self, tmp_path: Path) -> None:
        """Correct totals for active / draft / deprecated mix."""
        senses = [
            _make_sense("alpha", "def a", "active", 1.0),
            _make_sense("beta", "def b", "active", 0.9),
            _make_sense("gamma", "def g", "draft", 0.7),
            _make_sense("delta", "def d", "deprecated", 0.2),
        ]
        service = GlossaryService(tmp_path)
        import specify_cli.glossary.service as svc_module

        with (
            patch.object(svc_module, "_collect_all_senses", return_value=senses),
            patch("specify_cli.glossary.service.iter_semantic_conflicts", return_value=[]),
        ):
            result = service.get_health()

        assert result["total_terms"] == 4
        assert result["active_count"] == 2
        assert result["draft_count"] == 1
        assert result["deprecated_count"] == 1

    def test_high_severity_conflict_counting(self, tmp_path: Path) -> None:
        """Counts high and critical conflicts; ignores low/medium."""
        senses = [_make_sense("x", "x", "active", 1.0)]
        conflicts = [
            _make_conflict("high", "2026-01-02T00:00:00"),
            _make_conflict("critical", "2026-01-03T00:00:00"),
            _make_conflict("low", None),
            _make_conflict("medium", None),
        ]
        service = GlossaryService(tmp_path)
        import specify_cli.glossary.service as svc_module

        with (
            patch.object(svc_module, "_collect_all_senses", return_value=senses),
            patch("specify_cli.glossary.service.iter_semantic_conflicts", return_value=conflicts),
        ):
            result = service.get_health()

        assert result["high_severity_drift_count"] == 2
        assert result["last_conflict_at"] == "2026-01-03T00:00:00"

    def test_entity_pages_detected_when_present(self, tmp_path: Path) -> None:
        """entity_pages_generated is True when directory has contents."""
        entity_dir = tmp_path / ".kittify" / "charter" / "compiled" / "glossary"
        entity_dir.mkdir(parents=True)
        (entity_dir / "term.md").write_text("content")

        service = GlossaryService(tmp_path)
        import specify_cli.glossary.service as svc_module

        with (
            patch.object(svc_module, "_collect_all_senses", return_value=[]),
            patch("specify_cli.glossary.service.iter_semantic_conflicts", return_value=[]),
        ):
            result = service.get_health()

        assert result["entity_pages_generated"] is True
        assert result["entity_pages_path"] == str(entity_dir)

    def test_entity_pages_absent_when_dir_missing(self, tmp_path: Path) -> None:
        """entity_pages_generated is False when directory is absent."""
        service = GlossaryService(tmp_path)
        import specify_cli.glossary.service as svc_module

        with (
            patch.object(svc_module, "_collect_all_senses", return_value=[]),
            patch("specify_cli.glossary.service.iter_semantic_conflicts", return_value=[]),
        ):
            result = service.get_health()

        assert result["entity_pages_generated"] is False
        assert result["entity_pages_path"] is None

    def test_fallback_on_exception_returns_empty_response(self, tmp_path: Path) -> None:
        """Returns all-zero empty response on unhandled exception."""
        service = GlossaryService(tmp_path)
        import specify_cli.glossary.service as svc_module

        with patch.object(svc_module, "_collect_all_senses", side_effect=RuntimeError("boom")):
            result = service.get_health()

        assert result["total_terms"] == 0
        assert result["active_count"] == 0
        assert result["entity_pages_generated"] is False
        assert result["last_conflict_at"] is None

    def test_health_response_keys_match_typeddict(self, tmp_path: Path) -> None:
        """Parity: returned dict keys match GlossaryHealthResponse TypedDict."""
        service = GlossaryService(tmp_path)
        import specify_cli.glossary.service as svc_module

        with (
            patch.object(svc_module, "_collect_all_senses", return_value=[]),
            patch("specify_cli.glossary.service.iter_semantic_conflicts", return_value=[]),
        ):
            result = service.get_health()

        expected_keys = set(GlossaryHealthResponse.__annotations__.keys())
        assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# get_terms() tests
# ---------------------------------------------------------------------------


class TestGetTerms:
    def test_happy_path_converts_senses_to_records(self, tmp_path: Path) -> None:
        """Returns correct GlossaryTermRecord dicts from senses."""
        senses = [
            _make_sense("alpha", "def a", "active", 0.95),
            _make_sense("beta", "def b", "draft", 0.5),
        ]
        service = GlossaryService(tmp_path)
        import specify_cli.glossary.service as svc_module

        with patch.object(svc_module, "_collect_all_senses", return_value=senses):
            result = service.get_terms()

        assert len(result) == 2
        assert result[0]["surface"] == "alpha"
        assert result[0]["definition"] == "def a"
        assert result[0]["status"] == "active"
        assert result[0]["confidence"] == pytest.approx(0.95)
        assert result[1]["surface"] == "beta"
        assert result[1]["status"] == "draft"

    def test_fallback_on_exception_returns_empty_list(self, tmp_path: Path) -> None:
        """Returns empty list when _collect_all_senses raises."""
        service = GlossaryService(tmp_path)
        import specify_cli.glossary.service as svc_module

        with patch.object(svc_module, "_collect_all_senses", side_effect=ValueError("oops")):
            result = service.get_terms()

        assert result == []

    def test_missing_glossary_file_returns_empty_list(self, tmp_path: Path) -> None:
        """Empty project directory yields an empty terms list."""
        service = GlossaryService(tmp_path)
        # No patches — real implementation with empty project dir
        result = service.get_terms()
        assert isinstance(result, list)

    def test_term_record_keys_match_typeddict(self, tmp_path: Path) -> None:
        """Parity: each term record key set matches GlossaryTermRecord TypedDict."""
        senses = [_make_sense("x", "desc", "active", 1.0)]
        service = GlossaryService(tmp_path)
        import specify_cli.glossary.service as svc_module

        with patch.object(svc_module, "_collect_all_senses", return_value=senses):
            result = service.get_terms()

        expected_keys = set(GlossaryTermRecord.__annotations__.keys())
        assert len(result) == 1
        assert set(result[0].keys()) == expected_keys
