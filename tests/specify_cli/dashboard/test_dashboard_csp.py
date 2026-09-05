"""Tests for the dashboard's Content-Security-Policy header (specify_cli.dashboard.csp).

Fixture rows map to m1-contract-drafts/D2.md §4: D3 (CSP present, identical
on every route) and D4 (CSP would block an inline script even if the narrow
grammar were defeated — defense-in-depth, second control layer).

This module covers the constant + shared helper (D2.md §5 WP03's "owned
data" piece, §3.3) AND, per D5 below, the structural proof that
``send_csp_header()`` is actually wired into every ``send_response()`` call
site across ``handlers/{base,api,features,glossary,lint,static}.py``
(WIRE-M2-02, HIC-M1-D5-DOMCSP) — closing what was previously tracked as
separate, still-open WP03 wiring work.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.dashboard.csp import DASHBOARD_CSP, send_csp_header


# --- D4: the policy string itself blocks inline script execution -----------


pytestmark = [pytest.mark.unit, pytest.mark.fast]  # M2 canonical integration: route via the specify-cli-rest fast shard


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


# --- D5: send_csp_header() is wired into every send_response() site --------
#
# WIRE-M2-02: structural (not per-route-fixture) proof that the shared
# helper is actually called on every response path in the six handler
# files, not just the ones exercised by today's handler-level unit tests.
# A per-route fixture test would only catch a *removed* call on a route it
# happens to cover; this gate catches a *missing* call on ANY route,
# including ones added after this test was written, without needing a new
# fixture per route (D2.md §6 decision 6: uniform, not just HTML-serving).


_HANDLERS_DIR = Path(__file__).resolve().parents[3] / "src" / "specify_cli" / "dashboard" / "handlers"
_CSP_WIRED_FILES = ("base.py", "api.py", "features.py", "glossary.py", "lint.py", "static.py")

# A send_response(...) call is "paired" when the very next statement line is
# a send_csp_header(self) call -- exactly the shape WIRE-M2-02 inserted at
# all 35 existing call sites. This intentionally does not use full AST
# control-flow analysis: the flat "next line" shape is simple to write, read,
# and keep green, and matches this repo's existing convention of structural
# regex/AST gates in tests/architectural/ for exactly this kind of
# "was the mechanical wiring actually done" property.
_PAIRED_PATTERN = re.compile(r"self\.send_response\([^\n]*\)\n[ \t]*send_csp_header\(self\)")
_SEND_RESPONSE_PATTERN = re.compile(r"self\.send_response\(")


def test_d5_every_send_response_site_is_paired_with_send_csp_header() -> None:
    """Every self.send_response(...) call site in the six handler files is
    immediately followed by a send_csp_header(self) call -- so every route
    (success, error, and bare 404 alike) carries the CSP header."""
    failures: list[str] = []
    for filename in _CSP_WIRED_FILES:
        path = _HANDLERS_DIR / filename
        source = path.read_text(encoding="utf-8")
        n_responses = len(_SEND_RESPONSE_PATTERN.findall(source))
        n_paired = len(_PAIRED_PATTERN.findall(source))
        if n_paired != n_responses:
            failures.append(
                f"{filename}: {n_responses} send_response() call(s) but only "
                f"{n_paired} immediately followed by send_csp_header(self)"
            )
    assert not failures, "Unwired dashboard response(s) missing the CSP header:\n  - " + "\n  - ".join(failures)


def test_d5_every_wired_file_imports_send_csp_header() -> None:
    """Each file with a paired call site actually imports the helper it calls."""
    for filename in _CSP_WIRED_FILES:
        path = _HANDLERS_DIR / filename
        source = path.read_text(encoding="utf-8")
        if _SEND_RESPONSE_PATTERN.search(source):
            assert "from ..csp import send_csp_header" in source, f"{filename}: missing 'from ..csp import send_csp_header'"
