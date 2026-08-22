"""Tests for the dashboard's Content-Security-Policy header (specify_cli.dashboard.csp).

Fixture rows map to m1-contract-drafts/D2.md §4: D3 (CSP present, identical
on every route) and D4 (CSP would block an inline script even if the narrow
grammar were defeated — defense-in-depth, second control layer).

This module covers the constant + shared helper only (D2.md §5 WP03's
"owned data" piece, §3.3). Wiring ``send_csp_header()`` into each of the six
existing per-handler-file ``send_header`` call sites so every live route
carries the header is tracked as separate, still-open WP03 work (see the
D2-T1 handoff) — a larger, independently reviewable mechanical change across
``handlers/{base,api,features,glossary,lint,static}.py``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from specify_cli.dashboard.csp import DASHBOARD_CSP, send_csp_header


# --- D4: the policy string itself blocks inline script execution -----------


def test_d4_script_src_has_no_unsafe_inline() -> None:
    assert "script-src 'self'" in DASHBOARD_CSP
    assert "unsafe-inline" not in DASHBOARD_CSP
    assert "unsafe-eval" not in DASHBOARD_CSP


def test_d4_default_src_self_only() -> None:
    assert "default-src 'self'" in DASHBOARD_CSP


def test_d4_frame_ancestors_and_base_uri_locked_down() -> None:
    assert "frame-ancestors 'none'" in DASHBOARD_CSP
    assert "base-uri 'none'" in DASHBOARD_CSP


def test_d4_img_src_allows_self_hosted_data_uri_only() -> None:
    # dashboard.css already ships inline SVG icons as data: URIs (D2.md
    # §3.3): this is the one deliberate relaxation, not a general opening.
    assert "img-src 'self' data:" in DASHBOARD_CSP


def test_d4_no_external_host_in_policy() -> None:
    assert "http://" not in DASHBOARD_CSP
    assert "https://" not in DASHBOARD_CSP
    assert "cdn." not in DASHBOARD_CSP


# --- D3: the shared helper sends the exact header on any handler -----------


def test_d3_send_csp_header_sends_exact_policy_string() -> None:
    handler = MagicMock()
    handler.send_header = MagicMock()

    send_csp_header(handler)

    handler.send_header.assert_called_once_with("Content-Security-Policy", DASHBOARD_CSP)
