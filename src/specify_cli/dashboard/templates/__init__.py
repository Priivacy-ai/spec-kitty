"""Dashboard HTML template loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

__all__ = ["get_dashboard_html"]

_TEMPLATE_PATH = Path(__file__).with_name('index.html')
_DASHBOARD_HTML_CACHE: Optional[str] = None
_MISSION_PLACEHOLDER = "window.__INITIAL_MISSION__ = null;"


def _load_dashboard_template() -> str:
    global _DASHBOARD_HTML_CACHE
    if _DASHBOARD_HTML_CACHE is None:
        try:
            _DASHBOARD_HTML_CACHE = _TEMPLATE_PATH.read_text(encoding='utf-8')
        except OSError as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"Dashboard template missing at {_TEMPLATE_PATH}: {exc}") from exc
    return _DASHBOARD_HTML_CACHE


def get_dashboard_html(*, mission_context: Optional[Dict[str, str]] = None) -> str:
    """Return dashboard HTML with optional inline mission context."""
    base_html = _load_dashboard_template()
    if not mission_context:
        return base_html

    mission_json = json.dumps(mission_context)
    if _MISSION_PLACEHOLDER not in base_html:
        return base_html

    return base_html.replace(_MISSION_PLACEHOLDER, f"window.__INITIAL_MISSION__ = {mission_json};", 1)
