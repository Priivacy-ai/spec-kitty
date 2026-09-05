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

The page's behaviour and styling now live in the extracted
``glossary.js``/``glossary.css`` assets, not just ``glossary.html`` — the
regex scans below cover those files too (issue #96), so re-homed code can't
quietly reintroduce an inline style/script construct or a foreign
subresource reference that the template-only scan would miss.
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


_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
# Negative lookbehind for ':' so `://` inside a URL literal (http://, https://)
# is not mistaken for a `//` line-comment start — a bare `//.*` truncated the
# rest of the source line, silently hiding any markup sharing that line with a
# same-origin URL literal. See test_strip_js_comments_preserves_markup_after_url_literal.
_JS_LINE_COMMENT_RE = re.compile(r"(?<!:)//.*")


def _strip_css_comments(css: str) -> str:
    return _BLOCK_COMMENT_RE.sub("", css)


def _strip_js_comments(js: str) -> str:
    """Drop ``/* … */`` and ``// …`` JS comments before scanning.

    Both extracted-asset headers document, in prose, the exact inline
    ``<script>``/``style=`` constructs they replace (see the file headers) —
    without stripping comments those doc strings would trip these guards on
    their own prose, not on actual code."""
    return _JS_LINE_COMMENT_RE.sub("", _BLOCK_COMMENT_RE.sub("", js))


def test_strip_js_comments_preserves_markup_after_url_literal() -> None:
    """A same-origin URL literal sharing a line with markup must not have the
    markup after it silently swallowed as if `://` started a line comment
    (squad finding on PR #361, issue #96 fix round)."""
    js = 'main.innerHTML = `<a href="https://good.example/a">x</a><div style="color:red"></div>`;'
    stripped = _strip_js_comments(js)
    assert 'style="color:red"' in stripped
    assert _STYLE_ATTRIBUTE_RE.search(stripped) is not None


def test_glossary_static_assets_have_no_inline_style_attribute() -> None:
    """The same style= scan that guards the template also guards the
    extracted assets: a future edit that builds an HTML string with a
    ``style="…"`` attribute inside glossary.js (e.g. an innerHTML template
    literal), or that smuggles one into glossary.css as a literal string,
    should still trip this guard."""
    css = _strip_css_comments(GLOSSARY_CSS.read_text(encoding="utf-8"))
    js = _strip_js_comments(GLOSSARY_JS.read_text(encoding="utf-8"))
    for label, text in (("glossary.css", css), ("glossary.js", js)):
        match = _STYLE_ATTRIBUTE_RE.search(text)
        assert match is None, f"inline style= attribute at offset {match.start():d} in {label}"


def test_glossary_javascript_does_not_construct_inline_markup() -> None:
    """glossary.js builds DOM markup via ``innerHTML`` template literals
    (see ``render()``); none of those literals may embed an inline
    ``<style>`` block or an inline (non-``src``) ``<script>`` tag, since the
    CSP would block either just as it would in the template itself."""
    js = _strip_js_comments(GLOSSARY_JS.read_text(encoding="utf-8"))
    assert "<style" not in js.lower()
    match = _INLINE_SCRIPT_RE.search(js)
    assert match is None, f"inline <script> construct at offset {match.start():d} in glossary.js"


_JS_URL_LITERAL_RE = re.compile(r"""\bfetch\(\s*['"]([^'"]+)['"]|\.src\s*=\s*['"]([^'"]+)['"]""")


def test_glossary_javascript_subresources_are_same_origin() -> None:
    """Every ``fetch(...)`` call and ``.src`` assignment literal in
    glossary.js must be same-origin: a CDN URL there would be blocked by the
    CSP exactly like a foreign ``<script src>`` in the template.

    ``.href`` assignments (e.g. ``location.href = '…'``, an anchor's
    ``href``) are deliberately excluded: like the template's anchor ``href``
    navigations (see ``:71-77`` above), they are top-level navigations, not
    CSP-restricted subresources, and ``DASHBOARD_CSP`` sets no
    ``navigate-to``/``form-action`` restriction that would apply."""
    js = _strip_js_comments(GLOSSARY_JS.read_text(encoding="utf-8"))
    urls = [first or second for first, second in _JS_URL_LITERAL_RE.findall(js)]
    assert urls, "glossary.js should reference at least one URL literal"
    foreign = [url for url in urls if not (url.startswith("/") or url.startswith("data:"))]
    assert foreign == [], f"non-same-origin URL literal(s) blocked by the CSP: {foreign}"


def test_glossary_javascript_href_navigation_is_not_flagged_as_subresource() -> None:
    """A ``.href`` navigation assignment must not be misdiagnosed as a
    blocked subresource (squad finding, issue #385): unlike ``.src``, an
    ``href`` assignment is a navigation, and navigations are excluded from
    this same-origin subresource scan exactly as anchor ``href`` is excluded
    from the template scan at ``:71-77``."""
    js = "location.href = 'https://external.example/docs';"
    urls = [first or second for first, second in _JS_URL_LITERAL_RE.findall(js)]
    assert urls == []


def test_glossary_javascript_url_scan_ignores_comment_prose() -> None:
    js = _strip_js_comments(
        """
        // This file no longer does fetch('https://old-cdn.example.com/glossary.json').
        const resp = await fetch('/api/glossary-terms');
        """
    )
    urls = [first or second for first, second in _JS_URL_LITERAL_RE.findall(js)]
    assert urls == ["/api/glossary-terms"]


_CSS_URL_RE = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""")


def test_glossary_css_has_no_foreign_url_reference() -> None:
    """glossary.css carries no ``url(...)`` references today; this guards
    against one being added later that points off-origin (e.g. a CDN font
    or background image), which the CSP would block at load time."""
    css = _strip_css_comments(GLOSSARY_CSS.read_text(encoding="utf-8"))
    urls = _CSS_URL_RE.findall(css)
    foreign = [url for url in urls if not (url.startswith("/") or url.startswith("data:"))]
    assert foreign == [], f"non-same-origin url() reference(s) blocked by the CSP: {foreign}"


def test_glossary_css_url_scan_ignores_comment_prose() -> None:
    css = _strip_css_comments(
        """
        /* The pre-#71 draft used url(https://old-cdn.example.com/font.woff2). */
        .logo { background-image: url('/static/dashboard/logo.png'); }
        """
    )
    assert _CSS_URL_RE.findall(css) == ["/static/dashboard/logo.png"]


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
