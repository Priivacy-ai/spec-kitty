from pathlib import Path

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
