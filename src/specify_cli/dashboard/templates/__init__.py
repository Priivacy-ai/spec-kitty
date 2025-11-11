"""Dashboard HTML template loader."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

__all__ = ["get_dashboard_html"]

_TEMPLATE_PATH = Path(__file__).with_name('index.html')
_DASHBOARD_HTML_CACHE: Optional[str] = None


def get_dashboard_html() -> str:
    """Load the dashboard HTML template from disk."""
    global _DASHBOARD_HTML_CACHE
    if _DASHBOARD_HTML_CACHE is None:
        try:
            _DASHBOARD_HTML_CACHE = _TEMPLATE_PATH.read_text(encoding='utf-8')
        except OSError as exc:
            raise RuntimeError(f"Dashboard template missing at {_TEMPLATE_PATH}: {exc}") from exc
    return _DASHBOARD_HTML_CACHE
