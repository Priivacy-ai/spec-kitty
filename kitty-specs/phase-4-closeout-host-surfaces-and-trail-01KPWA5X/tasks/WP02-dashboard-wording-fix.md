---
work_package_id: WP02
title: Dashboard User-Visible Wording Fix
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Current planning base is main; completed work merges into main. Execution worktree is resolved from lanes.json at implement time.
subtasks:
- T005
- T006
- T007
- T008
- T009
history:
- event: created
  at: '2026-04-23T05:10:00Z'
  note: Initial generation from /spec-kitty.tasks
authoritative_surface: src/specify_cli/dashboard/
execution_mode: code_change
owned_files:
- src/specify_cli/dashboard/templates/index.html
- src/specify_cli/dashboard/static/dashboard/dashboard.js
- src/specify_cli/dashboard/diagnostics.py
- tests/specify_cli/dashboard/test_dashboard_wording.py
tags: []
---

# WP02 — Dashboard User-Visible Wording Fix

## Objective

Replace every user-visible `Feature` string on the local dashboard's mission-selection and current-mission surfaces with `Mission Run` / mission terminology, matching the Phase 4 runtime model. Preserve every backend identifier (CSS classes, HTML IDs, API route segments, cookie keys, JSON field names, Python function names) per FR-004 and C-007.

This is the smallest code-touching chunk in Tranche A and is the implementation anchor that proves the `Feature` → `Mission Run` wording scope is tightly bounded.

## Context

Phase 4 shipped the profile-invocation runtime; the concept formerly called `feature` in the dashboard has been renamed to `mission run` in the runtime vocabulary. The dashboard was left unchanged at 3.2.0a5. `#496` calls this out explicitly.

**Why backend identifiers stay**: Renaming them would cascade into `api_types.py`, `scanner.py`, HTTP route handlers, cookie-migration logic, and clients that call the dashboard API. C-007 explicitly rejects a broad `Feature` rename.

**User-visible scope, verified during planning**: exactly three files contain the user-visible strings. `dashboard.css` only contains CSS class names, which stay. No other dashboard templates exist.

## Branch Strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: allocated from `lanes.json` at implement time. WP02 depends on WP01 only for audit confirmation; no files are shared.

## Subtask Guidance

### T005 — `src/specify_cli/dashboard/templates/index.html`

**Purpose**: Five user-visible strings to update.

**Changes** (line numbers from baseline `eb32cf0a`; the implementer should grep to confirm post-merge of any prior WPs):

| Line | Old | New |
|------|-----|-----|
| 25 | `<label>Feature:</label>` | `<label>Mission Run:</label>` |
| 93 | `<h2>Feature Overview</h2>` | `<h2>Mission Run Overview</h2>` |
| 195 | `<h3 style="color: var(--grassy-green); margin-bottom: 15px;">Feature Analysis</h3>` | `<h3 style="color: var(--grassy-green); margin-bottom: 15px;">Mission Run Analysis</h3>` |
| 223 | `<li>Run <code style="…">/spec-kitty.specify</code> to create your first feature</li>` | `<li>Run <code style="…">/spec-kitty.specify</code> to create your first mission</li>` |
| 235 | `<p>Create your first feature using <code>/spec-kitty.specify</code></p>` | `<p>Create your first mission using <code>/spec-kitty.specify</code></p>` |

**Preserve**:
- All element IDs: `feature-selector-container`, `feature-select`, `single-feature-name`, `diagnostics-features`, `no-features-message`.
- All CSS class usage: `feature-selector`, `no-features`.

### T006 — `src/specify_cli/dashboard/static/dashboard/dashboard.js`

**Purpose**: Six user-visible string updates + the "Unknown feature" fallback.

**Changes**:

| Line | Old | New |
|------|-----|-----|
| 354 | `` `<h3>Feature: ${feature.name} ${mergeBadge}</h3>` `` | `` `<h3>Mission Run: ${feature.name} ${mergeBadge}</h3>` `` |
| 1095 | `return feature.display_name \|\| feature.name \|\| feature.id \|\| 'Unknown feature';` | `return feature.display_name \|\| feature.name \|\| feature.id \|\| 'Unknown mission';` |
| 1152 | `` singleFeatureName.textContent = `Feature: ${getFeatureDisplayName(features[0])}`; `` | `` singleFeatureName.textContent = `Mission Run: ${getFeatureDisplayName(features[0])}`; `` |
| 1397 | `` `<div><strong>Feature:</strong> ${data.current_feature.name}</div>` `` | `` `<div><strong>Mission Run:</strong> ${data.current_feature.name}</div>` `` |
| 1420 | `` `<th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Feature</th>` `` | `` `<th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Mission Run</th>` `` |

**Preserve** (do NOT rename):
- JavaScript globals: `currentFeature`, `allFeatures`, `featureSelectActive`, `featureSelectIdleTimer`.
- Cookie keys: `lastFeature`.
- Function names: `switchFeature`, `getFeatureDisplayName`, `computeFeatureWorktreeStatus`, `updateFeatureList`, `setFeatureSelectActive`, `saveState(feature, page)`.
- API route templates: `/api/kanban/${currentFeature}`, `/api/artifact/${currentFeature}/${artifactName}`, `/api/contracts/${currentFeature}`, `/api/checklists/${currentFeature}`, `/api/research/${currentFeature}`.
- JSON field accessors: `feature.name`, `feature.display_name`, `feature.id`, `feature.branch_merged`, `feature.branch_exists`, `data.current_feature.name`, `feature.artifacts`, `feature.kanban_stats`, `feature.purpose_tldr`, `feature.purpose_context`, `feature.meta`.
- Comments that reference "feature-level worktrees" (they describe historical behaviour accurately).
- Variable names in handlers: `const feature = allFeatures.find(...)`, etc.

### T007 — `src/specify_cli/dashboard/diagnostics.py`

**Purpose**: One user-visible string.

**Change**:

| Line | Old | New |
|------|-----|-----|
| 177 | `"active_mission": mission_type \|\| "no feature context"` | `"active_mission": mission_type \|\| "no mission context"` |

**Preserve**:
- The function name and the `active_mission` key — these are internal diagnostic output field names.

### T008 — Snapshot test for wording + backend identifier preservation

**Purpose**: Regression guard against both directions: user-visible `Feature` must stay gone, and backend identifiers must stay present.

**File**: `tests/specify_cli/dashboard/test_dashboard_wording.py` (new).

**Test structure**:

```python
"""Regression tests for WP02 dashboard wording alignment.

Asserts:
1. No user-visible `Feature` string remains on the mission selection / current
   mission surfaces of the local dashboard.
2. Backend identifiers (CSS classes, HTML IDs, API route segments, cookie keys,
   JS function names, Python diagnostic keys) stay unchanged — FR-004 / C-007.
"""
from pathlib import Path
import pytest

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
        assert "<label>Mission Run:</label>" in content
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

    def test_dashboard_js_feature_heading_renamed(self) -> None:
        content = DASHBOARD_JS.read_text()
        assert "<h3>Mission Run: ${feature.name}" in content
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
```

### T009 — Live dashboard visual verification

**Purpose**: Confirm the changes render correctly in a real browser against a real mission.

**Steps**:
1. Start the dashboard: `spec-kitty dashboard` from repo root.
2. Open the served URL in a browser.
3. Verify each item in quickstart.md §2.2 (5 user-visible strings in HTML, 5 in JS, 1 in diagnostics).
4. Verify the backend items in quickstart.md §2.3 (DevTools check: IDs, classes, cookies, routes, JSON field names).
5. Record the verification in the implementation commit message or PR description.

## Definition of Done

- [ ] All 11 user-visible strings replaced across the three files per T005–T007.
- [ ] `tests/specify_cli/dashboard/test_dashboard_wording.py` exists and passes both test classes (`TestUserVisibleMissionRunWording`, `TestBackendIdentifiersPreserved`).
- [ ] Live dashboard verification per T009 completed and recorded.
- [ ] `pytest tests/specify_cli/dashboard/test_dashboard_wording.py -v` passes green.
- [ ] `mypy --strict` on the new test file passes.
- [ ] No backend identifier (CSS class, HTML ID, JS global, function name, cookie, API route, JSON field) has changed.

## Risks

- **Hidden user-visible strings**: If a user-visible `Feature` exists in a template path not yet grepped (e.g., a dynamically loaded component), the backend-preservation test would not catch it. Mitigation: T009 visual verification + the explicit grep assertions in T008 `TestUserVisibleMissionRunWording`.
- **CSS cascade**: Changing a heading label to a longer string ("Mission Run Overview") may cause layout reflow. Mitigation: T009 visual verification includes layout check on a single-mission view and on the empty-state view.
- **JS string template edge cases**: A template literal that concatenates `Feature:` from parts (not a single string) would escape grep. Mitigation: the grep tests check for the negative case (`"Feature: ${feature.name}"` absent); if any such concatenation exists it must be refactored.

## Reviewer Guidance

Reviewer should:
- Open each of the three files and verify the exact 11 changes listed in T005–T007.
- Run `grep -n "Feature:\|>Feature<\|first feature\|Unknown feature\|no feature context" src/specify_cli/dashboard/` — expect zero hits.
- Run `grep -n "feature-selector\|feature-select\|lastFeature\|currentFeature\|switchFeature\|getFeatureDisplayName\|/api/kanban/\|active_mission" src/specify_cli/dashboard/` — expect non-zero hits (backend preserved).
- Run the test file and confirm 20+ assertions pass.
- Verify T009 evidence in the PR description.
