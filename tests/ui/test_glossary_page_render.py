"""Playwright render proof for the /glossary page under the dashboard CSP (issue #71).

Issue #71: glossary.html shipped its styles in an inline ``<style>`` block and
its behaviour in an inline ``<script>`` block, both of which the dashboard's own
``Content-Security-Policy`` (``style-src 'self'`` / ``script-src 'self'``,
``specify_cli/dashboard/csp.py``) blocks. The page rendered unstyled with zero
interactivity while every backend test stayed green — the same class of
browser-only failure tests/ui/test_dashboard_wp_modal.py exists to catch
(CLAUDE.md: never claim the frontend works without Playwright proof).

The structural half of the regression guard (no inline blocks, same-origin
subresources) lives in tests/specify_cli/dashboard/test_glossary_page_csp.py;
this module proves the extracted assets actually apply and run in a real
Chromium against a live dashboard server:

* no CSP "violates the following Content Security Policy" console violation on load,
* glossary.css actually applied (computed body background, sticky header),
* glossary.js actually ran (stats pills, alpha nav, term cards),
* search + filter-tab interactivity works end-to-end.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip(
    "playwright",
    reason="pytest-playwright optional dep; run `uv sync --extra test` / `playwright install chromium` to exercise tests/ui/",
)
from playwright.sync_api import Page, expect  # noqa: E402  (after importorskip)

pytestmark = pytest.mark.e2e

# --bg from static/dashboard/glossary.css — the first thing an unstyled page loses.
EXPECTED_BODY_BACKGROUND = "rgb(167, 199, 231)"  # #A7C7E7

_SEED_TERMS = [
    ("work package", "A unit of implementation.", 1.0, "active"),
    ("mission log", "A running record of mission events.", 0.5, "draft"),
    ("canonical source", "The single authoritative home of a rule.", 1.0, "active"),
]


def _write_seed(project_dir: Path) -> None:
    """Materialize a minimal spec_kitty_core seed the terms API can serve."""
    lines = ["terms:"]
    for surface, definition, confidence, status in _SEED_TERMS:
        lines.append(f"  - surface: {surface}")
        lines.append(f"    definition: {definition}")
        lines.append(f"    confidence: {confidence}")
        lines.append(f"    status: {status}")
    seed_dir = project_dir / ".kittify" / "glossaries"
    seed_dir.mkdir(parents=True)
    (seed_dir / "spec_kitty_core.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def glossary_dashboard(tmp_path: Path) -> str:
    """Boot the real dashboard in-thread against a root holding only a glossary seed.

    Same hermetic seam as tests/ui/conftest.py::dashboard —
    ``start_dashboard(..., background_process=False)`` runs the stdlib HTTP
    server on a daemon thread bound to an ephemeral port, so it dies with the
    pytest process. The glossary handlers read the seed per request, so nothing
    else needs to exist in the project root.
    """
    from specify_cli.dashboard.server import find_free_port, start_dashboard

    _write_seed(tmp_path)
    port = find_free_port()
    actual_port, _pid = start_dashboard(tmp_path, port=port, background_process=False)
    return f"http://127.0.0.1:{actual_port}"


def test_glossary_page_renders_styled_and_interactive_under_csp(page: Page, glossary_dashboard: str) -> None:
    console_messages: list[str] = []
    failed_responses: list[str] = []
    page.on("console", lambda msg: console_messages.append(msg.text))
    page.on(
        "response",
        lambda response: failed_responses.append(f"{response.status} {response.url}") if response.status >= 400 else None,
    )

    page.goto(f"{glossary_dashboard}/glossary")

    # The stylesheet must be fetched (same-origin, CSP-allowed) AND applied.
    stylesheet = page.locator('link[rel="stylesheet"][href="/static/dashboard/glossary.css"]')
    expect(stylesheet).to_have_count(1)
    expect(page.locator("body")).to_have_css("background-color", EXPECTED_BODY_BACKGROUND)
    header = page.locator("header.header")
    expect(header).to_have_css("position", "sticky")

    # The script must have fetched AND run: it fills these nodes at load time.
    expect(page.locator("#header-stats .stat-pill.total")).to_contain_text(f"{len(_SEED_TERMS)} terms")
    expect(page.locator("#alpha-nav button.alpha-btn")).to_have_count(26)
    cards = page.locator(".letter-section .card")
    expect(cards).to_have_count(len(_SEED_TERMS))

    # Interactivity the former inline script provided: live search filter.
    # render() rebuilds the board from scratch on every keystroke/tab click,
    # so matching cards simply cease to exist rather than getting .hidden.
    search = page.locator("#search")
    search.fill("work package")
    expect(page.locator("#result-count")).to_have_text("1 of 3")
    expect(page.locator(".letter-section .card .card-surface")).to_have_text(["work package"])

    # ...and the status filter tabs (clearing the query first: the two
    # filters compose, and "work package" + draft matches nothing).
    search.fill("")
    page.locator('#filter-tabs button[data-filter="draft"]').click()
    expect(page.locator(".letter-section .card .card-surface")).to_have_text(["mission log"])
    expect(page.locator("#result-count")).to_have_text("1 of 3")

    page.locator('#filter-tabs button[data-filter="all"]').click()
    expect(page.locator(".letter-section .card")).to_have_count(len(_SEED_TERMS))

    # No CSP violation was reported and nothing 404'd (a blocked/missing asset
    # shows up as a console CSP-violation message or a non-200 subresource fetch).
    csp_violations = [m for m in console_messages if "violates the following Content Security Policy" in m]
    assert csp_violations == [], f"CSP violations on /glossary: {csp_violations}"
    assert failed_responses == [], f"failed subresource fetches: {failed_responses}"
