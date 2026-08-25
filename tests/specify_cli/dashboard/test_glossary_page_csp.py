"""CSP-conformance regression guard for the /glossary page (issue #71).

The dashboard sends ``Content-Security-Policy: … style-src 'self'; script-src
'self' …`` (:data:`specify_cli.dashboard.csp.DASHBOARD_CSP`) on every route,
including ``GET /glossary``. A policy without ``'unsafe-inline'`` blocks not
only inline ``<script>`` blocks but also inline ``<style>`` blocks and
``style=`` attributes, so a template that carries its styles/scripts inline
renders unstyled and inert — the exact failure glossary.html shipped with
(issue #71, same regression class #66 fixed for index.html).

These tests are structural: they fail if the template regresses to any inline
style/script source, or references a non-same-origin subresource. The render
proof that the extracted assets actually work in a browser lives in
``tests/ui/test_glossary_page_render.py``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

REPO_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = REPO_ROOT / "src" / "specify_cli" / "dashboard"
GLOSSARY_HTML = DASHBOARD_DIR / "templates" / "glossary.html"
GLOSSARY_CSS = DASHBOARD_DIR / "static" / "dashboard" / "glossary.css"
GLOSSARY_JS = DASHBOARD_DIR / "static" / "dashboard" / "glossary.js"

_INLINE_SCRIPT_RE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.IGNORECASE)
_STYLE_ATTRIBUTE_RE = re.compile(r"""\sstyle\s*=\s*["']""", re.IGNORECASE)


def _template_text() -> str:
    return GLOSSARY_HTML.read_text(encoding="utf-8")


def test_glossary_template_has_no_inline_style_block() -> None:
    assert "<style" not in _template_text().lower()


def test_glossary_template_has_no_inline_script_block() -> None:
    match = _INLINE_SCRIPT_RE.search(_template_text())
    assert match is None, f"inline <script> block at offset {match.start():d}"


def test_glossary_template_has_no_inline_style_attribute() -> None:
    match = _STYLE_ATTRIBUTE_RE.search(_template_text())
    assert match is None, f"inline style= attribute at offset {match.start():d}"


def test_glossary_template_references_extracted_assets() -> None:
    html = _template_text()
    assert '<link rel="stylesheet" href="/static/dashboard/glossary.css">' in html
    assert '<script src="/static/dashboard/glossary.js"></script>' in html


def test_glossary_subresources_are_same_origin_or_data_uris() -> None:
    """Every stylesheet/script/image the page pulls must survive the CSP.

    ``default-src 'self'`` allows only same-origin URLs (plus the one
    deliberate ``img-src 'self' data:`` relaxation for inline SVG/PNG icons);
    a CDN <script> like the one index.html still carries would be blocked.
    Anchor ``href`` navigations are not CSP-restricted and are excluded.
    """
    html = _template_text()
    subresources = re.findall(r'<(?:link|script|img)\b[^>]*?\b(?:href|src)="([^"]+)"', html)
    assert subresources, "glossary template should reference at least one asset"
    foreign = [url for url in subresources if not (url.startswith("/") or url.startswith("data:"))]
    assert foreign == [], f"non-same-origin subresources blocked by the CSP: {foreign}"


def test_glossary_static_assets_exist_and_are_non_empty() -> None:
    for asset in (GLOSSARY_CSS, GLOSSARY_JS):
        assert asset.is_file(), f"{asset} should exist"
        assert asset.stat().st_size > 0, f"{asset} should not be empty"


def test_glossary_css_carries_the_page_styles() -> None:
    """Spot-check the selectors the template's own markup depends on."""
    css = GLOSSARY_CSS.read_text(encoding="utf-8")
    for selector in (
        ":root",
        ".header {",
        ".sidebar-item",
        ".search-input",
        ".alpha-btn",
        ".letter-section",
        '.card[data-status="active"]',
        ".logo-wrap img",  # replaces the former inline object-fit attribute
    ):
        assert selector in css, f"glossary.css is missing {selector!r}"


def test_glossary_javascript_has_valid_syntax() -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for glossary.js syntax validation")

    result = subprocess.run(
        ["node", "--check", str(GLOSSARY_JS)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_glossary_javascript_keeps_the_interactive_entry_points() -> None:
    js = GLOSSARY_JS.read_text(encoding="utf-8")
    assert "async function loadTerms()" in js
    assert "document.getElementById('search')" in js
    assert "document.getElementById('filter-tabs')" in js
    assert "document.addEventListener('DOMContentLoaded', loadTerms)" in js
