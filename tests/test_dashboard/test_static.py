import shutil
import subprocess
from pathlib import Path

import pytest

from specify_cli.dashboard.templates import get_dashboard_html

pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_JS = REPO_ROOT / "src" / "specify_cli" / "dashboard" / "static" / "dashboard" / "dashboard.js"


def test_dashboard_template_references_static_assets():
    html = get_dashboard_html()
    assert '<link rel="stylesheet" href="/static/dashboard/dashboard.css">' in html
    assert '<script src="/static/dashboard/dashboard.js"></script>' in html
    assert '<link rel="icon" type="image/png" href="/static/spec-kitty.png">' in html


def test_dashboard_template_omits_mission_badge():
    html = get_dashboard_html()
    assert 'mission-display' not in html
    assert 'Mission:' not in html


def test_static_assets_exist():
    repo_root = Path(__file__).resolve().parents[2]
    dashboard_root = repo_root / "src" / "specify_cli" / "dashboard"
    static_dir = dashboard_root / "static"
    css = static_dir / "dashboard" / "dashboard.css"
    js = static_dir / "dashboard" / "dashboard.js"
    logo = static_dir / "spec-kitty.png"

    for asset in (css, js, logo):
        assert asset.exists(), f"{asset} should exist"
        assert asset.stat().st_size > 0, f"{asset} should not be empty"


def test_dashboard_javascript_has_valid_syntax():
    if shutil.which("node") is None:
        pytest.skip("node is required for dashboard.js syntax validation")

    result = subprocess.run(
        ["node", "--check", str(DASHBOARD_JS)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_dashboard_features_polling_guards_malformed_payloads():
    source = DASHBOARD_JS.read_text(encoding="utf-8")

    assert "function normalizeFeatureList(features)" in source
    assert "Array.isArray(data.features)" in source
    assert "response.ok" in source


def test_dashboard_overview_mission_copy_uses_text_nodes():
    source = DASHBOARD_JS.read_text(encoding="utf-8")

    assert "const titleEl = document.createElement('h3');" in source
    assert "titleEl.id = 'overview-title';" in source
    assert "titleEl.textContent = `Mission Run: ${feature.name}`;" in source
    assert "introEl.textContent = purposeTldr;" in source
    assert "contextEl.textContent = purposeContext;" in source
    assert "overviewContent.replaceChildren(header, statusSummary, artifactsHeading, artifactsGrid);" in source
    assert "overviewContent.innerHTML" not in source
    assert "<h3>Mission Run: ${feature.name}" not in source
    assert "${purposeTldr}</p>" not in source
    assert "${purposeContext}</p>" not in source


def test_dashboard_selector_options_use_dom_text_nodes():
    source = DASHBOARD_JS.read_text(encoding="utf-8")

    assert "document.createElement('option')" in source
    assert "option.textContent = getFeatureDisplayName(f);" in source
    assert "select.replaceChildren(options);" in source
    assert "select.innerHTML = features.map" not in source
    assert '<option value="${f.id}"' not in source
