"""Template-level tests for the dashboard shell."""

from __future__ import annotations

from specify_cli.dashboard.templates import get_dashboard_html


import pytest

pytestmark = [pytest.mark.integration]

def test_dashboard_glossary_interactions_use_native_links() -> None:
    html = get_dashboard_html()

    assert '<a class="sidebar-item" href="/glossary" title="Glossary">' in html
    assert (
        '<a class="content-card content-card-link" id="glossary-tile" '
        'href="/glossary" style="margin-top: 16px;">'
    ) in html


def test_dashboard_html_injects_safe_mission_context() -> None:
    html = get_dashboard_html(mission_context={"mission": "</script>"})

    # Injected into the inert application/json data island (the dashboard CSP
    # blocks executable inline scripts), with </script> Unicode-escaped so the
    # payload cannot close the block early.
    assert (
        '<script type="application/json" id="initial-mission">'
        '{"mission": "\\u003c/script\\u003e"}</script>'
    ) in html


def test_dashboard_shell_without_context_keeps_null_data_island() -> None:
    html = get_dashboard_html()

    assert '<script type="application/json" id="initial-mission">null</script>' in html
    assert "__INITIAL_MISSION__" not in html
