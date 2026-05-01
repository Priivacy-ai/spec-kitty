"""Tests for dashboard GlossaryHandler — /api/glossary-health, /api/glossary-terms, /glossary."""

from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.glossary.models import Provenance, SenseStatus, TermSense, TermSurface

pytestmark = pytest.mark.fast


def _make_term(surface: str, definition: str, status: str, confidence: float) -> TermSense:
    """Build a TermSense for test use."""
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


def _make_handler(tmp_path: Path) -> MagicMock:
    """Build a minimal mock handler that records HTTP method calls."""
    handler = MagicMock()
    handler.project_dir = str(tmp_path)
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = io.BytesIO()
    return handler


def _read_response(handler: MagicMock) -> object:
    """Decode JSON written to handler.wfile."""
    handler.wfile.seek(0)
    return json.loads(handler.wfile.read().decode("utf-8"))


class TestGlossaryHealth:
    """Tests for handle_glossary_health() → GET /api/glossary-health."""

    def test_health_counts_terms_by_status(self, tmp_path):
        """Returns correct totals when store has 2 active, 1 draft."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        terms = [
            _make_term("alpha", "def a", "active", 1.0),
            _make_term("beta", "def b", "active", 0.9),
            _make_term("gamma", "def g", "draft", 0.7),
        ]

        handler = _make_handler(tmp_path)

        with patch.object(gloss_module, "_collect_all_senses", return_value=terms):
            gloss_module.GlossaryHandler.handle_glossary_health(handler)

        handler.send_response.assert_called_once_with(200)
        data = _read_response(handler)
        assert data["total_terms"] == 3
        assert data["active_count"] == 2
        assert data["draft_count"] == 1
        assert data["deprecated_count"] == 0

    def test_health_returns_zero_counts_on_empty_store(self, tmp_path):
        """Returns zero counts when store is empty (no exception raised)."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        handler = _make_handler(tmp_path)

        with patch.object(gloss_module, "_collect_all_senses", return_value=[]):
            gloss_module.GlossaryHandler.handle_glossary_health(handler)

        handler.send_response.assert_called_once_with(200)
        data = _read_response(handler)
        assert data["total_terms"] == 0
        assert data["active_count"] == 0
        assert data["draft_count"] == 0
        assert data["deprecated_count"] == 0

    def test_health_returns_zero_counts_on_error(self, tmp_path):
        """Returns safe zero-count payload when _collect_all_senses raises."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        handler = _make_handler(tmp_path)

        with patch.object(gloss_module, "_collect_all_senses", side_effect=RuntimeError("boom")):
            gloss_module.GlossaryHandler.handle_glossary_health(handler)

        handler.send_response.assert_called_once_with(200)
        data = _read_response(handler)
        assert data["total_terms"] == 0
        assert data["high_severity_drift_count"] == 0
        assert data["entity_pages_generated"] is False
        assert data["last_conflict_at"] is None

    def test_health_counts_high_severity_events(self, tmp_path):
        """Reads canonical glossary event logs and counts high/critical findings."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        events_dir = tmp_path / ".kittify" / "events" / "glossary"
        events_dir.mkdir(parents=True)
        event_log = events_dir / "mission-001.events.jsonl"
        events = [
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "step-1",
                "timestamp": "2026-01-01T00:00:00Z",
                "findings": [
                    {
                        "term": {"surface_text": "alpha"},
                        "term_id": "glossary:alpha",
                        "severity": "high",
                        "conflict_type": "ambiguous",
                    }
                ],
            },
            {
                "event_type": "SemanticCheckEvaluated",
                "step_id": "step-2",
                "timestamp": "2026-01-02T00:00:00Z",
                "findings": [
                    {
                        "term": {"surface_text": "beta"},
                        "term_id": "glossary:beta",
                        "severity": "critical",
                        "conflict_type": "inconsistent",
                    },
                    {
                        "term": {"surface_text": "gamma"},
                        "term_id": "glossary:gamma",
                        "severity": "low",
                        "conflict_type": "unknown",
                    },
                ],
            },
            {"event_type": "other_event", "severity": "high", "timestamp": "2026-01-04T00:00:00Z"},
        ]
        event_log.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")

        handler = _make_handler(tmp_path)

        with patch.object(gloss_module, "_collect_all_senses", return_value=[]):
            gloss_module.GlossaryHandler.handle_glossary_health(handler)

        data = _read_response(handler)
        assert data["high_severity_drift_count"] == 2
        assert data["last_conflict_at"] == "2026-01-02T00:00:00Z"

    def test_health_missing_event_log_returns_zero_drift(self, tmp_path):
        """Returns high_severity_drift_count=0 when event log doesn't exist."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        handler = _make_handler(tmp_path)

        with patch.object(gloss_module, "_collect_all_senses", return_value=[]):
            gloss_module.GlossaryHandler.handle_glossary_health(handler)

        data = _read_response(handler)
        assert data["high_severity_drift_count"] == 0
        assert data["last_conflict_at"] is None

    def test_health_includes_all_required_fields(self, tmp_path):
        """All GlossaryHealthResponse fields are present in the response."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        handler = _make_handler(tmp_path)

        with patch.object(gloss_module, "_collect_all_senses", return_value=[]):
            gloss_module.GlossaryHandler.handle_glossary_health(handler)

        data = _read_response(handler)
        required_keys = {
            "total_terms",
            "active_count",
            "draft_count",
            "deprecated_count",
            "high_severity_drift_count",
            "orphaned_term_count",
            "entity_pages_generated",
            "entity_pages_path",
            "last_conflict_at",
        }
        assert required_keys.issubset(data.keys())


class TestGlossaryTerms:
    """Tests for handle_glossary_terms() → GET /api/glossary-terms."""

    def test_terms_returns_list_of_records(self, tmp_path):
        """Returns a list of GlossaryTermRecord-shaped dicts from the store."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        terms = [
            _make_term("lane", "kanban lane", "active", 1.0),
            _make_term("wp", "work package", "draft", 0.8),
        ]

        handler = _make_handler(tmp_path)

        with patch.object(gloss_module, "_collect_all_senses", return_value=terms):
            gloss_module.GlossaryHandler.handle_glossary_terms(handler)

        handler.send_response.assert_called_once_with(200)
        records = _read_response(handler)
        assert isinstance(records, list)
        assert len(records) == 2

        lane_rec = next(r for r in records if r["surface"] == "lane")
        assert lane_rec["definition"] == "kanban lane"
        assert lane_rec["status"] == "active"
        assert lane_rec["confidence"] == 1.0

        wp_rec = next(r for r in records if r["surface"] == "wp")
        assert wp_rec["status"] == "draft"
        assert abs(wp_rec["confidence"] - 0.8) < 1e-9

    def test_terms_returns_empty_list_on_store_error(self, tmp_path):
        """Returns [] without raising when _collect_all_senses raises."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        handler = _make_handler(tmp_path)

        with patch.object(gloss_module, "_collect_all_senses", side_effect=RuntimeError("oops")):
            gloss_module.GlossaryHandler.handle_glossary_terms(handler)

        handler.send_response.assert_called_once_with(200)
        records = _read_response(handler)
        assert records == []

    def test_terms_record_shape(self, tmp_path):
        """Each record has exactly the expected keys."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        terms = [_make_term("mission", "workflow machine", "active", 0.95)]
        handler = _make_handler(tmp_path)

        with patch.object(gloss_module, "_collect_all_senses", return_value=terms):
            gloss_module.GlossaryHandler.handle_glossary_terms(handler)

        records = _read_response(handler)
        assert len(records) == 1
        rec = records[0]
        assert set(rec.keys()) == {"surface", "definition", "status", "confidence"}


class TestGlossaryPage:
    """Tests for handle_glossary_page() → GET /glossary."""

    def test_glossary_page_returns_200_with_html(self, tmp_path):
        """Serves the glossary browser HTML with status 200 and correct content-type."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        handler = _make_handler(tmp_path)

        gloss_module.GlossaryHandler.handle_glossary_page(handler)

        handler.send_response.assert_called_once_with(200)
        # Verify content-type header was set to text/html
        ct_calls = [call for call in handler.send_header.call_args_list if call.args[0] == "Content-type"]
        assert len(ct_calls) == 1
        assert "text/html" in ct_calls[0].args[1]

        handler.wfile.seek(0)
        body = handler.wfile.read()
        assert body  # non-empty
        assert b"<!DOCTYPE html>" in body or b"<html" in body

    def test_glossary_page_uses_cached_bytes(self, tmp_path):
        """Module-level _GLOSSARY_HTML_BYTES is reused for each request."""
        from specify_cli.dashboard.handlers import glossary as gloss_module

        handler1 = _make_handler(tmp_path)
        handler2 = _make_handler(tmp_path)

        gloss_module.GlossaryHandler.handle_glossary_page(handler1)
        gloss_module.GlossaryHandler.handle_glossary_page(handler2)

        handler1.wfile.seek(0)
        handler2.wfile.seek(0)
        assert handler1.wfile.read() == handler2.wfile.read()


class TestRouterRegistration:
    """Verify the routes are wired in DashboardRouter."""

    def test_glossary_handler_in_mro(self):
        """GlossaryHandler must appear in DashboardRouter's MRO before StaticHandler."""
        from specify_cli.dashboard.handlers.router import DashboardRouter
        from specify_cli.dashboard.handlers.glossary import GlossaryHandler
        from specify_cli.dashboard.handlers.static import StaticHandler

        mro = DashboardRouter.__mro__
        glossary_idx = mro.index(GlossaryHandler)
        static_idx = mro.index(StaticHandler)
        assert glossary_idx < static_idx, "GlossaryHandler must precede StaticHandler in MRO"

    def test_router_has_glossary_methods(self):
        """DashboardRouter exposes all three glossary handler methods."""
        from specify_cli.dashboard.handlers.router import DashboardRouter

        assert hasattr(DashboardRouter, "handle_glossary_health")
        assert hasattr(DashboardRouter, "handle_glossary_terms")
        assert hasattr(DashboardRouter, "handle_glossary_page")
