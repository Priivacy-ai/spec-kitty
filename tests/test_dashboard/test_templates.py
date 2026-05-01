"""Template-level tests for the dashboard shell."""

from __future__ import annotations

from specify_cli.dashboard.templates import get_dashboard_html


def test_dashboard_glossary_interactions_use_native_links() -> None:
    html = get_dashboard_html()

    assert '<a class="sidebar-item" href="/glossary" title="Glossary">' in html
    assert (
        '<a class="content-card content-card-link" id="glossary-tile" '
        'href="/glossary" style="margin-top: 16px;">'
    ) in html


def test_dashboard_html_injects_safe_mission_context() -> None:
    html = get_dashboard_html(mission_context={"mission": "</script>"})

    assert 'window.__INITIAL_MISSION__ = {"mission": "\\u003c/script\\u003e"};' in html
