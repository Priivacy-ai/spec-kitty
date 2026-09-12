"""Content-Security-Policy for the dashboard's loopback-only HTTP surface.

D2 replaces the current zero-CSP posture (no ``Content-Security-Policy``,
``X-Frame-Options``, or ``X-Content-Type-Options`` header anywhere in
``src/specify_cli/dashboard/``, per m1-contract-drafts/D2.md §2.1) with one
constant policy string and one shared helper, applied uniformly to every
route rather than only the HTML-serving ones (D2.md §6 decision 6).

This is defense-in-depth, not the primary control: dashboard routes must not
emit untrusted raw HTML. Even if an input-encoding defect were introduced,
``script-src 'self'`` with no ``'unsafe-inline'``/``'unsafe-eval'`` means an
injected inline ``<script>`` still could not execute (D2.md §4 rows D3-D4).
"""

from __future__ import annotations

from typing import Protocol

__all__ = ["DASHBOARD_CSP", "send_csp_header"]

DASHBOARD_CSP: str = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"


class _SendsHeaders(Protocol):
    """Matches ``http.server.BaseHTTPRequestHandler.send_header``'s signature."""

    def send_header(self, keyword: str, value: str) -> None: ...


def send_csp_header(handler: _SendsHeaders) -> None:
    """Send the dashboard's :data:`DASHBOARD_CSP` header on ``handler``.

    One shared helper *function*, meant to be called from each of the six
    existing per-file ``send_header`` call sites in
    ``handlers/{base,api,features,glossary,lint,static}.py`` — headers are
    not centralized in a base-class method today (D2.md §2.1, §6 decision
    6), so a single call site added once would miss routes.
    """
    handler.send_header("Content-Security-Policy", DASHBOARD_CSP)
