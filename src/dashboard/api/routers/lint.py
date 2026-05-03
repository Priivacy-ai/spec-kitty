"""Router: GET /api/charter-lint (decay watch tile data).

Transport-only migration: the legacy logic in
``specify_cli/dashboard/handlers/lint.py`` is recreated here verbatim
in a private helper. Service extraction is deferred to follow-up
issue #955.

# TODO(follow-up): extract a lint service object so this handler
# becomes a single-call adapter. Tracked at
# https://github.com/Priivacy-ai/spec-kitty/issues/955.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, Request

from dashboard.api.models import DecayWatchTileResponse

__all__ = ["register"]

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


def _build_charter_lint(project_dir: Path) -> dict[str, Any]:
    """Recreate the legacy decay-watch tile payload."""
    try:
        report_path = project_dir / ".kittify" / "lint-report.json"
        if not report_path.exists():
            return dict(_EMPTY_RESPONSE)
        data = json.loads(report_path.read_text(encoding="utf-8"))
        findings = data.get("findings", [])
        return {
            "has_data": True,
            "scanned_at": data.get("scanned_at"),
            "orphan_count": sum(1 for f in findings if f.get("category") == "orphan"),
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
                1 for f in findings if f.get("severity") in {"high", "critical"}
            ),
            "total_count": len(findings),
            "feature_scope": data.get("feature_scope"),
            "duration_seconds": data.get("duration_seconds"),
        }
    except Exception as exc:
        logger.exception("lint tile error: %s", exc)
        return dict(_EMPTY_RESPONSE)


def register(app: FastAPI) -> None:
    """Mount the lint router on ``app``."""
    router = APIRouter()

    @router.get("/api/charter-lint", response_model=DecayWatchTileResponse)
    def charter_lint(request: Request):
        # TODO(follow-up): extract lint service object — see dashboard
        # service-extraction follow-up mission (issue #955).
        return _build_charter_lint(Path(request.app.state.project_dir))

    app.include_router(router)
