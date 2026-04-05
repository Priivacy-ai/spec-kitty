import shutil
import subprocess
from pathlib import Path

import pytest

from specify_cli.dashboard.templates import get_dashboard_html


def test_dashboard_template_references_static_assets():
    html = get_dashboard_html()
    assert '<link rel="stylesheet" href="/static/dashboard/dashboard.css">' in html
    assert '<script src="/static/dashboard/dashboard.js"></script>' in html
    assert '<link rel="icon" type="image/png" href="/static/spec-kitty.png">' in html


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


@pytest.mark.fast
def test_dashboard_javascript_has_valid_syntax():
    if shutil.which("node") is None:
        pytest.skip("node is required for dashboard.js syntax validation")

    repo_root = Path(__file__).resolve().parents[2]
    dashboard_js = repo_root / "src" / "specify_cli" / "dashboard" / "static" / "dashboard" / "dashboard.js"
    result = subprocess.run(
        ["node", "--check", str(dashboard_js)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
