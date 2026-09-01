"""Regression tests for SonarCloud DOM-XSS hardening in dashboard.js."""

import colorsys
import re
from pathlib import Path


import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

REPO_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_JS = REPO_ROOT / "src/specify_cli/dashboard/static/dashboard/dashboard.js"
DASHBOARD_CSS = REPO_ROOT / "src/specify_cli/dashboard/static/dashboard/dashboard.css"


def test_overview_panel_avoids_innerhtml_sink() -> None:
    content = DASHBOARD_JS.read_text()
    assert "document.getElementById('overview-content').innerHTML" not in content
    assert "overviewContent.innerHTML" not in content
    assert "overviewContent.replaceChildren(...overviewChildren);" in content


def test_feature_selector_builds_options_with_dom_nodes() -> None:
    content = DASHBOARD_JS.read_text()
    assert "select.innerHTML = features.map" not in content
    assert "const option = document.createElement('option');" in content
    assert "select.replaceChildren(options);" in content


def test_card_avatar_title_uses_attribute_safe_escaping() -> None:
    """profileAvatarHtml() (issue #647) must not reuse bare escapeHtml() for
    the title/aria-label attribute values it builds.

    escapeHtml() only escapes `&`/`<`/`>` (correct for the text-node content
    it was written for); it leaves a literal `"` untouched. Interpolating
    that straight into `title="${...}"` would let an identity string like
    `x" onmouseover="alert(1)` break out of the attribute. escapeHtmlAttr()
    exists specifically to close that gap — this pins its use at both sites.
    """
    content = DASHBOARD_JS.read_text()
    assert "function escapeHtmlAttr(text) {" in content
    assert 'title="${label}" aria-label="${label}"' in content
    assert "const label = escapeHtmlAttr(identity);" in content


def test_card_avatar_falls_back_through_identity_fields_and_handles_absence() -> None:
    """profileAvatarHtml() (issue #647) must degrade gracefully.

    `KanbanTaskData` (api_types.py) populates `agent_profile`/`role`/`agent`/
    `assignee` as `""` for legacy/unassigned WPs (scanner.py's
    `_wp_identity_fields`), and its encoding-error path omits the keys
    entirely — so the avatar must fall back through the identity fields in
    order, ignore whitespace-only values, and render nothing rather than an
    empty/broken circle when none of them are set.
    """
    content = DASHBOARD_JS.read_text()
    assert "const identity = [task.agent_profile, task.role, task.agent, task.assignee]" in content
    assert ".find(value => typeof value === 'string' && value.trim())?.trim() || '';" in content
    assert "if (!identity) {\n        return '';\n    }" in content


def test_card_avatar_palette_meets_wcag_aa_text_contrast() -> None:
    """Every deterministic avatar hue keeps normal-size initials readable."""
    css = DASHBOARD_CSS.read_text()
    block_match = re.search(r"\.card-avatar\s*\{(?P<body>.*?)\}", css, re.DOTALL)
    assert block_match is not None
    block = block_match.group("body")
    foreground_match = re.search(r"color:\s*#(?P<hex>[0-9a-fA-F]{6})", block)
    background_match = re.search(
        r"background-color:\s*hsl\(var\(--avatar-hue\),\s*"
        r"(?P<saturation>\d+)%\s*,\s*(?P<lightness>\d+)%\)",
        block,
    )
    assert foreground_match is not None
    assert background_match is not None

    foreground_hex = foreground_match.group("hex")
    foreground = tuple(int(foreground_hex[index : index + 2], 16) / 255 for index in (0, 2, 4))
    saturation = int(background_match.group("saturation")) / 100
    lightness = int(background_match.group("lightness")) / 100

    def _luminance(rgb: tuple[float, float, float]) -> float:
        linear = tuple(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in rgb)
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    foreground_luminance = _luminance(foreground)
    ratios = []
    for hue in range(360):
        background = colorsys.hls_to_rgb(hue / 360, lightness, saturation)
        lighter = max(foreground_luminance, _luminance(background))
        darker = min(foreground_luminance, _luminance(background))
        ratios.append((lighter + 0.05) / (darker + 0.05))

    assert min(ratios) >= 4.5


def test_card_avatar_trims_identity_before_guard_and_initials() -> None:
    """A whitespace-only identity is absent, not a blank avatar circle."""
    content = DASHBOARD_JS.read_text()
    assert "const identity = [task.agent_profile, task.role, task.agent, task.assignee]" in content
    assert ".find(value => typeof value === 'string' && value.trim())?.trim() || '';" in content
    assert "[identity[0], identity[1] || '']" in content
