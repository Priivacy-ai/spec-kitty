"""Regression tests for SonarCloud DOM-XSS hardening in dashboard.js."""

from pathlib import Path


import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

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
    order and render nothing rather than an empty/broken circle when none of
    them are set.
    """
    content = DASHBOARD_JS.read_text()
    assert "task.agent_profile || task.role || task.agent || task.assignee || ''" in content
    assert "if (!identity) {\n        return '';\n    }" in content


def test_card_avatar_trims_identity_before_guard_and_initials() -> None:
    """A whitespace-only identity is absent, not a blank avatar circle."""
    content = DASHBOARD_JS.read_text()
    assert "const identity = (task.agent_profile || task.role || task.agent || task.assignee || '').trim();" in content
    assert "[identity[0], identity[1] || '']" in content
