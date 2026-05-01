"""Decay watch tile handler — reads .kittify/lint-report.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..api_types import DecayWatchTileResponse
from .base import DashboardHandler

__all__ = ["LintTileHandler"]

logger = logging.getLogger(__name__)

_EMPTY_RESPONSE: DecayWatchTileResponse = {
    "has_data": False,
    "scanned_at": None,
    "orphan_count": 0,
    "contradiction_count": 0,
    "staleness_count": 0,
    "reference_integrity_count": 0,
    "high_severity_count": 0,
    "total_count": 0,
    "feature_scope": None,
    "duration_seconds": None,
}


class LintTileHandler(DashboardHandler):
    """Serve the decay watch tile data from .kittify/lint-report.json."""

    def handle_charter_lint(self) -> None:
        """Return GET /api/charter-lint with a DecayWatchTileResponse."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            if self.project_dir is None:
                raise RuntimeError("dashboard project_dir is not configured")
            report_path = Path(self.project_dir) / ".kittify" / "lint-report.json"

            if not report_path.exists():
                response: DecayWatchTileResponse = dict(_EMPTY_RESPONSE)  # type: ignore[assignment]
            else:
                data = json.loads(report_path.read_text(encoding="utf-8"))
                findings = data.get("findings", [])
                response = {
                    "has_data": True,
                    "scanned_at": data.get("scanned_at"),
                    "orphan_count": sum(
                        1 for f in findings if f.get("category") == "orphan"
                    ),
                    "contradiction_count": sum(
                        1 for f in findings if f.get("category") == "contradiction"
                    ),
                    "staleness_count": sum(
                        1 for f in findings if f.get("category") == "staleness"
                    ),
                    "reference_integrity_count": sum(
                        1 for f in findings if f.get("category") == "reference_integrity"
                    ),
                    "high_severity_count": sum(
                        1
                        for f in findings
                        if f.get("severity") in {"high", "critical"}
                    ),
                    "total_count": len(findings),
                    "feature_scope": data.get("feature_scope"),
                    "duration_seconds": data.get("duration_seconds"),
                }
        except Exception as exc:
            logger.exception("lint tile error: %s", exc)
            response = dict(_EMPTY_RESPONSE)  # type: ignore[assignment]

        self.wfile.write(json.dumps(response).encode())
