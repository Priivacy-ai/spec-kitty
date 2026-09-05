"""Dashboard HTML template loader."""

from __future__ import annotations

import json
from pathlib import Path

__all__ = ["get_dashboard_html", "get_dashboard_html_bytes"]

_TEMPLATE_PATH = Path(__file__).with_name('index.html')
# The shell carries the optional mission context in an inert
# `<script type="application/json">` data island: the dashboard CSP
# (`script-src 'self'`) blocks executable inline scripts, so a
# `window.__INITIAL_MISSION__ = …` assignment would never run. JSON inside a
# non-executing script block is not touched by `script-src`.
_MISSION_PLACEHOLDER = '<script type="application/json" id="initial-mission">null</script>'


def _read_dashboard_html_bytes() -> bytes:
    try:
        return _TEMPLATE_PATH.read_bytes()
    except OSError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Dashboard template missing at {_TEMPLATE_PATH}: {exc}") from exc


_DASHBOARD_HTML_BYTES = _read_dashboard_html_bytes()
_DASHBOARD_HTML = _DASHBOARD_HTML_BYTES.decode("utf-8")


def get_dashboard_html(*, mission_context: dict[str, str] | None = None) -> str:
    """Return dashboard HTML with optional inline mission context.

    The context lands in the shell's inert
    ``<script type="application/json" id="initial-mission">`` data island --
    never as an executable script assignment, which the dashboard's
    ``Content-Security-Policy: script-src 'self'`` would block.
    """
    base_html = _DASHBOARD_HTML
    if not mission_context:
        return base_html

    # Encode as HTML-safe JSON: escape characters that would break a <script> block
    # (<, >, & must be Unicode-escaped so a value like "</script>" can't inject markup).
    mission_json = (
        json.dumps(mission_context)
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
        .replace("&", r"\u0026")
    )
    if _MISSION_PLACEHOLDER not in base_html:
        return base_html

    injected = (
        '<script type="application/json" id="initial-mission">'
        f"{mission_json}</script>"
    )
    return base_html.replace(_MISSION_PLACEHOLDER, injected, 1)


def get_dashboard_html_bytes() -> bytes:
    """Return the static dashboard shell as UTF-8 bytes."""
    return _DASHBOARD_HTML_BYTES
