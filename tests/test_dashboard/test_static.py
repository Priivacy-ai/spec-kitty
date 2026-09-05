import json
import shutil
import subprocess
from pathlib import Path

import pytest

from specify_cli.dashboard.templates import get_dashboard_html

pytestmark = [pytest.mark.integration]

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_JS = REPO_ROOT / "src" / "specify_cli" / "dashboard" / "static" / "dashboard" / "dashboard.js"
DASHBOARD_CSS = REPO_ROOT / "src" / "specify_cli" / "dashboard" / "static" / "dashboard" / "dashboard.css"


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


def test_dashboard_css_print_media_resets_shell_overflow():
    """Regression for #323: the app-shell body/.container/.main-content stack uses
    height:100vh + overflow:hidden|auto to keep the SPA single-viewport on screen.
    Left as-is, that clips any content past one screen height when printed instead
    of flowing it onto additional pages. A `@media print` block must reset those
    elements to natural height/overflow so printed pages carry the full content.
    """
    css = DASHBOARD_CSS.read_text(encoding="utf-8")

    print_media_start = css.find("@media print")
    assert print_media_start != -1, "dashboard.css must define an @media print block"

    print_media_end = css.find("\n}", print_media_start)
    print_block = css[print_media_start:print_media_end]

    for selector in ("body", ".container", ".sidebar", ".main-content"):
        assert selector in print_block, f"@media print block must reset {selector}"
    assert "overflow: visible" in print_block


def test_render_kanban_escapes_card_fields_and_normalizes_avatar_fallback():
    """Exercise the real render function, not source-string implementation pins."""
    if shutil.which("node") is None:
        pytest.skip("node is required for dashboard.js behavior validation")

    source = DASHBOARD_JS.read_text(encoding="utf-8")
    render = source[
        source.index("function renderKanban") : source.index("\nfunction formatLaneName")
    ]
    avatar_helpers = source[
        source.index("function escapeHtml") : source.index("\nfunction showCharter")
    ]
    script = f"""
const elements = new Map();
global.document = {{
  createElement: () => ({{
    _text: '',
    set textContent(value) {{ this._text = String(value); }},
    get innerHTML() {{
      return this._text
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }},
  }}),
  getElementById: (id) => {{
    if (!elements.has(id)) elements.set(id, {{innerHTML: ''}});
    return elements.get(id);
  }},
  querySelectorAll: () => [],
}};
{avatar_helpers}
{render}
const hostileId = 'WP01<img src=x onerror="globalThis.__cardPwned=true">';
const hostileTitle = 'Unsafe <svg onload="globalThis.__cardPwned=true"> title';
const hostileAgent = '<iframe onload="globalThis.__statusPwned=true">';
const task = {{
  id: hostileId,
  title: hostileTitle,
  lane: 'planned',
  agent: hostileAgent,
  agent_profile: '   ',
  role: 'reviewer-renata',
  assignee: '',
  subtasks_total: 0,
  subtasks: [],
}};
renderKanban({{
  planned: [task], doing: [], for_review: [], in_review: [], approved: [], done: [],
}}, null);
process.stdout.write(JSON.stringify({{
  board: elements.get('kanban-board').innerHTML,
  status: elements.get('kanban-status').innerHTML,
  avatar: profileAvatarHtml(task),
  absent: profileAvatarHtml({{}}),
}}));
"""

    result = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "<img" not in payload["board"]
    assert "<svg" not in payload["board"]
    assert "&lt;img" in payload["board"]
    assert "&lt;svg" in payload["board"]
    assert "<iframe" not in payload["status"]
    assert "&lt;iframe" in payload["status"]
    assert 'title="reviewer-renata"' in payload["avatar"]
    assert ">RR</div>" in payload["avatar"]
    assert payload["absent"] == ""


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


def test_dashboard_overview_polling_includes_lifecycle_state():
    source = DASHBOARD_JS.read_text(encoding="utf-8")

    assert "next_action: item.next_action" in source
    assert "mission_status: item.mission_status" in source
    assert "kanban_stats: item.kanban_stats" in source


def test_dashboard_overview_mission_copy_uses_text_nodes():
    source = DASHBOARD_JS.read_text(encoding="utf-8")

    assert "const titleEl = document.createElement('h3');" in source
    assert "titleEl.id = 'overview-title';" in source
    assert "titleEl.textContent = `Mission Run: ${feature.name}`;" in source
    assert "introEl.textContent = purposeTldr;" in source
    assert "contextEl.textContent = purposeContext;" in source
    assert "overviewContent.replaceChildren(...overviewChildren);" in source
    assert "overviewContent.innerHTML" not in source
    assert "command.textContent = nextAction;" in source
    assert "el.innerHTML" not in source
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
