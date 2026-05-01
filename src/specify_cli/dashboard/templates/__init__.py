"""Dashboard HTML template loader."""

from __future__ import annotations

import json
from pathlib import Path

__all__ = ["get_dashboard_html", "get_dashboard_html_bytes"]

_TEMPLATE_PATH = Path(__file__).with_name("index.html")
_MISSION_PLACEHOLDER = "window.__INITIAL_MISSION__ = null;"


def _read_dashboard_html_bytes() -> bytes:
    try:
        return _TEMPLATE_PATH.read_bytes()
    except OSError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Dashboard template missing at {_TEMPLATE_PATH}: {exc}") from exc


_DASHBOARD_HTML_BYTES = _read_dashboard_html_bytes()
_DASHBOARD_HTML = _DASHBOARD_HTML_BYTES.decode("utf-8")


def get_dashboard_html(*, mission_context: dict[str, str] | None = None) -> str:
    """Return dashboard HTML with optional inline mission context."""
    base_html = _DASHBOARD_HTML
    if not mission_context:
        return base_html

    # Encode as HTML-safe JSON: escape characters that would break a <script> block
    # (<, >, & must be Unicode-escaped so a value like "</script>" can't inject markup).
    mission_json = json.dumps(mission_context).replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026")
    if _MISSION_PLACEHOLDER not in base_html:
        return base_html

    return base_html.replace(_MISSION_PLACEHOLDER, f"window.__INITIAL_MISSION__ = {mission_json};", 1)


def get_dashboard_html_bytes() -> bytes:
    """Return the static dashboard shell as UTF-8 bytes."""
    return _DASHBOARD_HTML_BYTES
