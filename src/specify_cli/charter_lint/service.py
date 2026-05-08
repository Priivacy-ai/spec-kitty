"""LintService: domain service for the charter-lint decay watch tile.

Reads ``.kittify/lint-report.json`` and returns a :class:`DecayWatchTileResponse`
dict.  No FastAPI or Pydantic imports — pure domain logic.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from specify_cli.charter_lint.types import DecayWatchTileResponse

__all__ = ["LintService"]

logger = logging.getLogger(__name__)

_EMPTY_RESPONSE: dict[str, Any] = {
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


class LintService:
    """Domain service for the decay watch tile payload.

    Parameters
    ----------
    project_dir:
        Path to the repository root (must contain ``.kittify/``).
    """

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir

    def get_decay_tile(self) -> DecayWatchTileResponse:
        """Return the decay watch tile payload from the lint report.

        Returns an empty-response dict when the report is absent or unreadable.
        """
        try:
            report_path = self._project_dir / ".kittify" / "lint-report.json"
            if not report_path.exists():
                return dict(_EMPTY_RESPONSE)  # type: ignore[return-value]
            data = json.loads(report_path.read_text(encoding="utf-8"))
            findings = data.get("findings", [])
            return {
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
                    1
                    for f in findings
                    if f.get("category") == "reference_integrity"
                ),
                "high_severity_count": sum(
                    1
                    for f in findings
                    if f.get("severity") in {"high", "critical"}
                ),
                "total_count": len(findings),
                "feature_scope": data.get("feature_scope"),
                "duration_seconds": data.get("duration_seconds"),
            }  # type: ignore[return-value]
        except Exception as exc:
            logger.exception("lint tile error: %s", exc)
            return dict(_EMPTY_RESPONSE)  # type: ignore[return-value]
