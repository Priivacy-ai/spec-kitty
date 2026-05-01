"""Tests for dashboard LintTileHandler — /api/charter-lint."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.fast


def _make_handler(tmp_path: Path) -> MagicMock:
    """Build a minimal mock handler that records HTTP method calls."""
    handler = MagicMock()
    handler.project_dir = str(tmp_path)
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = io.BytesIO()
    return handler


def _read_response(handler: MagicMock) -> dict:
    """Decode JSON written to handler.wfile."""
    handler.wfile.seek(0)
    return json.loads(handler.wfile.read().decode("utf-8"))


def _write_lint_report(tmp_path: Path, findings: list, **extra) -> None:
    """Write a lint-report.json fixture under .kittify/."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    report = {
        "findings": findings,
        "scanned_at": "2026-04-23T05:00:00Z",
        "feature_scope": None,
        "duration_seconds": 1.24,
        **extra,
    }
    (kittify / "lint-report.json").write_text(json.dumps(report), encoding="utf-8")


class TestLintTileHandlerReportExists:
    """Report exists with findings → has_data: true, correct counts."""

    def test_report_with_findings_returns_correct_counts(self, tmp_path):
        """2 orphan + 1 contradiction findings → correct category counts."""
        from specify_cli.dashboard.handlers.lint import LintTileHandler

        _write_lint_report(
            tmp_path,
            findings=[
                {"category": "orphan", "severity": "medium", "id": "ADR-1"},
                {"category": "orphan", "severity": "low", "id": "ADR-2"},
                {"category": "contradiction", "severity": "high", "id": "FEAT-3"},
            ],
        )

        handler = _make_handler(tmp_path)
        LintTileHandler.handle_charter_lint(handler)

        handler.send_response.assert_called_once_with(200)
        data = _read_response(handler)

        assert data["has_data"] is True
        assert data["orphan_count"] == 2
        assert data["contradiction_count"] == 1
        assert data["staleness_count"] == 0
        assert data["reference_integrity_count"] == 0
        assert data["total_count"] == 3

    def test_report_includes_metadata_fields(self, tmp_path):
        """scanned_at, feature_scope, and duration_seconds are forwarded."""
        from specify_cli.dashboard.handlers.lint import LintTileHandler

        _write_lint_report(
            tmp_path,
            findings=[],
            scanned_at="2026-04-23T05:00:00Z",
            feature_scope="my-feature",
            duration_seconds=2.5,
        )

        handler = _make_handler(tmp_path)
        LintTileHandler.handle_charter_lint(handler)

        data = _read_response(handler)
        assert data["has_data"] is True
        assert data["scanned_at"] == "2026-04-23T05:00:00Z"
        assert data["feature_scope"] == "my-feature"
        assert data["duration_seconds"] == pytest.approx(2.5)
        assert data["total_count"] == 0


class TestLintTileHandlerReportMissing:
    """No lint-report.json → has_data: false, all counts 0."""

    def test_missing_report_returns_has_data_false(self, tmp_path):
        """Returns has_data=false when lint-report.json does not exist."""
        from specify_cli.dashboard.handlers.lint import LintTileHandler

        handler = _make_handler(tmp_path)
        LintTileHandler.handle_charter_lint(handler)

        handler.send_response.assert_called_once_with(200)
        data = _read_response(handler)

        assert data["has_data"] is False
        assert data["orphan_count"] == 0
        assert data["contradiction_count"] == 0
        assert data["staleness_count"] == 0
        assert data["reference_integrity_count"] == 0
        assert data["high_severity_count"] == 0
        assert data["total_count"] == 0
        assert data["scanned_at"] is None
        assert data["feature_scope"] is None
        assert data["duration_seconds"] is None


class TestLintTileHandlerCorruptReport:
    """Corrupt JSON → has_data: false, no exception raised."""

    def test_corrupt_json_returns_has_data_false_no_exception(self, tmp_path):
        """Corrupt lint-report.json must not crash the handler."""
        from specify_cli.dashboard.handlers.lint import LintTileHandler

        kittify = tmp_path / ".kittify"
        kittify.mkdir(parents=True, exist_ok=True)
        (kittify / "lint-report.json").write_text("{not valid json!!!", encoding="utf-8")

        handler = _make_handler(tmp_path)
        # Must not raise
        LintTileHandler.handle_charter_lint(handler)

        handler.send_response.assert_called_once_with(200)
        data = _read_response(handler)
        assert data["has_data"] is False
        assert data["total_count"] == 0


class TestLintTileHandlerHighSeverity:
    """high + critical → high_severity_count; medium/low excluded."""

    def test_high_severity_count_sums_high_and_critical(self, tmp_path):
        """1 high + 1 critical + 1 medium → high_severity_count == 2."""
        from specify_cli.dashboard.handlers.lint import LintTileHandler

        _write_lint_report(
            tmp_path,
            findings=[
                {"category": "orphan", "severity": "high", "id": "A"},
                {"category": "orphan", "severity": "critical", "id": "B"},
                {"category": "orphan", "severity": "medium", "id": "C"},
            ],
        )

        handler = _make_handler(tmp_path)
        LintTileHandler.handle_charter_lint(handler)

        data = _read_response(handler)
        assert data["has_data"] is True
        assert data["high_severity_count"] == 2
        assert data["total_count"] == 3

    def test_only_high_severity_excludes_medium_low(self, tmp_path):
        """Only 1 high finding → high_severity_count == 1, total_count == 2."""
        from specify_cli.dashboard.handlers.lint import LintTileHandler

        _write_lint_report(
            tmp_path,
            findings=[
                {"category": "staleness", "severity": "high", "id": "X"},
                {"category": "staleness", "severity": "medium", "id": "Y"},
            ],
        )

        handler = _make_handler(tmp_path)
        LintTileHandler.handle_charter_lint(handler)

        data = _read_response(handler)
        assert data["high_severity_count"] == 1
        assert data["total_count"] == 2


class TestRouterRegistration:
    """Verify LintTileHandler is wired into DashboardRouter."""

    def test_lint_handler_in_mro(self):
        """LintTileHandler must appear in DashboardRouter's MRO before StaticHandler."""
        from specify_cli.dashboard.handlers.router import DashboardRouter
        from specify_cli.dashboard.handlers.lint import LintTileHandler
        from specify_cli.dashboard.handlers.static import StaticHandler

        mro = DashboardRouter.__mro__
        lint_idx = mro.index(LintTileHandler)
        static_idx = mro.index(StaticHandler)
        assert lint_idx < static_idx, "LintTileHandler must precede StaticHandler in MRO"

    def test_router_has_handle_charter_lint(self):
        """DashboardRouter exposes handle_charter_lint method."""
        from specify_cli.dashboard.handlers.router import DashboardRouter

        assert hasattr(DashboardRouter, "handle_charter_lint")
