---
work_package_id: WP02
work_package_title: Dashboard Infrastructure
subtitle: Extract dashboard static assets and core functions
subtasks:
  - T010
  - T011
  - T012
  - T013
  - T014
  - T015
  - T016
  - T017
  - T018
  - T019
phases: foundational
priority: P2
lane: planned
tags:
  - dashboard
  - parallel
  - agent-a
history:
  - date: 2025-11-11
    status: created
    by: spec-kitty.tasks
---

# WP02: Dashboard Infrastructure

## Objective

Extract dashboard static assets (HTML/CSS/JS) from embedded Python strings and create core dashboard utility modules for feature scanning and diagnostics.

## Context

The `dashboard.py` file contains 1,782 lines of embedded HTML/CSS/JS as Python strings. This work package extracts these to proper static files and creates focused modules for dashboard operations.

**Agent Assignment**: Agent A (Days 2-3)

## Requirements from Specification

- Extract embedded templates to separate files
- Each Python module under 200 lines
- Maintain exact dashboard functionality
- Support subprocess import contexts

## Implementation Guidance

### T010-T012: Extract HTML/CSS/JS to static files [P]

These can be done in parallel as they're independent files.

**T010**: Extract HTML from `get_dashboard_html()` function (around line 501-2200+)
- Create `dashboard/templates/index.html`
- Remove <!DOCTYPE html> through </html> from Python string
- Save as proper HTML file with correct indentation

**T011**: Extract CSS to `dashboard/static/dashboard.css`
- Find the <style> section in the HTML
- Extract all CSS rules (approximately 1000 lines)
- Create separate CSS file
- Update HTML to link to external stylesheet

**T012**: Extract JavaScript to `dashboard/static/dashboard.js`
- Find <script> sections in HTML
- Extract all JavaScript code
- Create separate JS file
- Update HTML to link to external script

### T013-T016: Extract scanner and diagnostic functions

**T013**: Extract `scan_all_features()` to `dashboard/scanner.py`
- Lines 381-441 from dashboard.py
- Imports: Path, json, mission module
- Include helper: `resolve_feature_dir()`

**T014**: Extract `scan_feature_kanban()` to `dashboard/scanner.py`
- Lines 444-498 from dashboard.py
- Uses parse_frontmatter() - may need to import or include

**T015**: Extract artifact functions to `dashboard/scanner.py`
- `get_feature_artifacts()` (lines 131-144)
- `get_workflow_status()` (lines 147-190)
- `work_package_sort_key()` (lines 118-128)

**T016**: Extract `run_diagnostics()` to `dashboard/diagnostics.py`
- Lines 221-371 from dashboard.py
- Complex function with git operations
- Needs imports from manifest, acceptance modules

### T017: Create dashboard package __init__.py

```python
"""Dashboard package public API."""

# Note: Main API functions will be added by WP05
# For now, just document the package

__all__ = []  # Will be populated in WP05
```

### T018-T019: Write integration tests

Create `tests/test_dashboard/`:
- `test_scanner.py` - Test feature scanning with mock project
- `test_diagnostics.py` - Test diagnostics with mock git repo

## Testing Strategy

1. **File extraction verification**: Ensure HTML renders correctly
2. **Function extraction**: Compare output before/after extraction
3. **Import testing**: Verify scanner/diagnostics can be imported
4. **Integration**: Run dashboard and verify it still loads

## Definition of Done

- [ ] HTML/CSS/JS extracted to separate files
- [ ] Scanner functions in dashboard/scanner.py (<200 lines)
- [ ] Diagnostics in dashboard/diagnostics.py (<200 lines)
- [ ] Tests written and passing
- [ ] Dashboard still loads and displays correctly
- [ ] No embedded HTML/CSS/JS strings remain

## Risks and Mitigations

**Risk**: HTML/CSS/JS extraction breaks formatting
**Mitigation**: Test dashboard rendering after each extraction

**Risk**: Scanner functions have complex dependencies
**Mitigation**: Use try/except for optional imports

## Review Guidance

1. Verify extracted files are properly formatted
2. Check that dashboard loads without errors
3. Ensure scanner finds test features
4. Confirm diagnostics run successfully

## Dependencies

- WP01: Needs `core/config.py` and `core/utils.py`

## Dependents

- WP05: Dashboard handlers will use these modules