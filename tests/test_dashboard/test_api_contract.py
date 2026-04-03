"""Contract test: dashboard JS must reference the keys the Python API emits.

Validates that the vanilla-JS dashboard reads the same response keys that
the Python handlers emit. This is a pragmatic text-matching approach — it
parses the JS as a string and checks for key access patterns.

Limitations:
- Brittle if JS is minified or uses variable aliases (acceptable for vanilla JS)
- Only checks keys the JS actually destructures; unused keys are not validated
- Long-term: replace with TypedDict codegen (Priivacy-ai/spec-kitty#361)

This test would have caught the original data.features→data.missions bug
that prompted mission-run 062.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

DASHBOARD_JS = Path("src/specify_cli/dashboard/static/dashboard/dashboard.js")


def _js_references_key(js_content: str, key: str) -> bool:
    """Check if JS content references a response key in any common access pattern."""
    return f"data.{key}" in js_content or f'data["{key}"]' in js_content or f"data['{key}']" in js_content


# ============================================================================
# /api/features → handle_missions_list() contract
# ============================================================================

# Keys emitted by handle_missions_list() in handlers/missions.py
# that the JS actively references in fetchData() / updateFeatureList()
MISSIONS_LIST_CONSUMED_KEYS = {
    "missions",
    "active_mission_id",
    "project_path",
    "active_worktree",
    "active_mission",
}
# Note: "worktrees_root" is returned by the handler but never read by the JS.


def test_js_references_missions_list_response_keys():
    """Frontend must access the same keys the /api/features handler emits."""
    js_content = DASHBOARD_JS.read_text(encoding="utf-8")
    for key in MISSIONS_LIST_CONSUMED_KEYS:
        assert _js_references_key(js_content, key), (
            f"Dashboard JS does not reference API response key '{key}'. "
            f"If the backend renamed this key, update the JS to match. "
            f"Handler: handle_missions_list() in dashboard/handlers/missions.py"
        )


# ============================================================================
# /api/kanban/{id} → handle_kanban() contract
# ============================================================================

# Keys from handle_kanban() that JS reads in loadKanban() / renderKanban()
KANBAN_CONSUMED_KEYS = {
    "lanes",
}
# Note: "is_legacy" and "upgrade_needed" are returned but never read by the JS.


def test_js_references_kanban_response_keys():
    """Frontend must access the same keys the /api/kanban handler emits."""
    js_content = DASHBOARD_JS.read_text(encoding="utf-8")
    for key in KANBAN_CONSUMED_KEYS:
        assert _js_references_key(js_content, key), (
            f"Dashboard JS does not reference kanban API key '{key}'. "
            f"Handler: handle_kanban() in dashboard/handlers/missions.py"
        )
