"""Regression tests for WP02 dashboard wording alignment.

Asserts:
1. No user-visible `Feature` string remains on the mission selection / current
   mission surfaces of the local dashboard.
2. Backend identifiers (CSS classes, HTML IDs, API route segments, cookie keys,
   JS function names, Python diagnostic keys) stay unchanged — FR-004 / C-007.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD = REPO_ROOT / "src/specify_cli/dashboard"

# --- File paths under test ---
INDEX_HTML = DASHBOARD / "templates/index.html"
DASHBOARD_JS = DASHBOARD / "static/dashboard/dashboard.js"
DIAGNOSTICS_PY = DASHBOARD / "diagnostics.py"


class TestUserVisibleMissionRunWording:
    """FR-003 — user-visible strings use Mission Run / mission vocabulary."""

    def test_index_html_selector_label_is_mission_run(self) -> None:
        content = INDEX_HTML.read_text()
        assert '<label for="feature-select">Mission Run:</label>' in content
        assert "<label>Feature:</label>" not in content

    def test_index_html_overview_heading(self) -> None:
        content = INDEX_HTML.read_text()
        assert ">Mission Run Overview<" in content
        assert ">Feature Overview<" not in content

    def test_index_html_analysis_heading(self) -> None:
        content = INDEX_HTML.read_text()
        assert ">Mission Run Analysis<" in content
        assert ">Feature Analysis<" not in content

    def test_index_html_empty_state_uses_mission(self) -> None:
        content = INDEX_HTML.read_text()
        assert "create your first mission" in content
        assert "create your first feature" not in content

    def test_index_html_empty_state_heading_uses_missions(self) -> None:
        """The empty-state <h2> heading shown when the mission selector has
        no missions must use Mission vocabulary (FR-003 / SC-002)."""
        content = INDEX_HTML.read_text()
        assert ">No Missions Found<" in content
        assert ">No Features Found<" not in content

    def test_dashboard_js_feature_heading_renamed(self) -> None:
        content = DASHBOARD_JS.read_text()
        assert "title.textContent = `Mission Run: ${feature.name}`;" in content
        assert "<h3>Feature: ${feature.name}" not in content

    def test_dashboard_js_unknown_fallback_renamed(self) -> None:
        content = DASHBOARD_JS.read_text()
        assert "'Unknown mission'" in content
        assert "'Unknown feature'" not in content

    def test_dashboard_js_single_feature_text_renamed(self) -> None:
        content = DASHBOARD_JS.read_text()
        assert "`Mission Run: ${getFeatureDisplayName(" in content
        assert "`Feature: ${getFeatureDisplayName(" not in content

    def test_dashboard_js_current_feature_label_renamed(self) -> None:
        content = DASHBOARD_JS.read_text()
        assert "<strong>Mission Run:</strong>" in content
        assert "<strong>Feature:</strong>" not in content

    def test_dashboard_js_table_header_renamed(self) -> None:
        content = DASHBOARD_JS.read_text()
        assert ">Mission Run</th>" in content
        assert ">Feature</th>" not in content

    def test_diagnostics_py_no_feature_context_message(self) -> None:
        content = DIAGNOSTICS_PY.read_text()
        assert '"no mission context"' in content
        assert '"no feature context"' not in content


class TestBackendIdentifiersPreserved:
    """FR-004 / C-007 — backend identifiers MUST NOT change."""

    def test_index_html_ids_preserved(self) -> None:
        content = INDEX_HTML.read_text()
        assert 'id="feature-selector-container"' in content
        assert 'id="feature-select"' in content
        assert 'id="single-feature-name"' in content
        assert 'id="diagnostics-features"' in content
        assert 'id="no-features-message"' in content

    def test_index_html_classes_preserved(self) -> None:
        content = INDEX_HTML.read_text()
        assert 'class="feature-selector"' in content

    def test_dashboard_js_globals_preserved(self) -> None:
        content = DASHBOARD_JS.read_text()
        assert "let currentFeature" in content
        assert "let allFeatures" in content
        assert "let featureSelectActive" in content

    def test_dashboard_js_function_names_preserved(self) -> None:
        content = DASHBOARD_JS.read_text()
        assert "function switchFeature(" in content
        assert "function getFeatureDisplayName(" in content
        assert "function updateFeatureList(" in content
        assert "function setFeatureSelectActive(" in content

    def test_dashboard_js_api_routes_preserved(self) -> None:
        content = DASHBOARD_JS.read_text()
        assert "`/api/kanban/${currentFeature}`" in content
        assert "`/api/artifact/${currentFeature}/" in content

    def test_dashboard_js_cookie_key_preserved(self) -> None:
        content = DASHBOARD_JS.read_text()
        assert "lastFeature=" in content

    def test_diagnostics_py_field_name_preserved(self) -> None:
        content = DIAGNOSTICS_PY.read_text()
        assert '"active_mission":' in content
