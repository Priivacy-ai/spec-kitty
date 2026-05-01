"""Regression tests for SonarCloud DOM-XSS hardening in dashboard.js."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_JS = REPO_ROOT / "src/specify_cli/dashboard/static/dashboard/dashboard.js"


def test_overview_panel_avoids_innerhtml_sink() -> None:
    content = DASHBOARD_JS.read_text()
    assert "document.getElementById('overview-content').innerHTML" not in content
    assert "overviewContent.innerHTML" not in content
    assert "overviewContent.replaceChildren(header, statusSummary, artifactsHeading, artifactsGrid);" in content


def test_feature_selector_builds_options_with_dom_nodes() -> None:
    content = DASHBOARD_JS.read_text()
    assert "select.innerHTML = features.map" not in content
    assert "const option = document.createElement('option');" in content
    assert "select.replaceChildren(options);" in content
