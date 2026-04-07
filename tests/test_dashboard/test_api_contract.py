"""Contract test: JS frontend <-> Python TypedDict key alignment.

Validates that the JavaScript dashboard frontend references the same
response keys that the Python TypedDict definitions declare.  This is a
Phase 1 "static regex" approach — it parses ``dashboard.js`` for property
accesses and compares them against the TypedDict annotations.

Known limitations (documented, not bugs):
- Dynamic property access (``obj[variable]``) is invisible to regex.
- Some TypedDict fields are only present conditionally (``NotRequired``);
  the JS may not reference every key.
- The test asserts JS-referenced keys are *present* in the TypedDict, not
  that every TypedDict key is referenced in JS.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import get_type_hints

import pytest

from specify_cli.dashboard.api_types import (
    ArtifactDirectoryResponse,
    ArtifactInfo,
    CurrentFeatureDetected,
    DiagnosticsFeatureStatus,
    DiagnosticsResponse,
    FeatureItem,
    FeaturesListResponse,
    FileIntegrity,
    HealthResponse,
    KanbanResponse,
    KanbanStats,
    KanbanTaskData,
    ResearchArtifact,
    ResearchResponse,
    WorkflowStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JS_PATH = Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "dashboard" / "static" / "dashboard" / "dashboard.js"


def _typed_dict_keys(td: type) -> set[str]:
    """Return the set of field names declared on a TypedDict class."""
    # get_type_hints resolves forward refs; __annotations__ is enough for
    # simple cases but get_type_hints is more robust with from __future__.
    try:
        return set(get_type_hints(td).keys())
    except Exception:
        return set(td.__annotations__.keys())


def _extract_all_js_identifiers(js_text: str) -> set[str]:
    """Extract all dot-accessed and bracket-accessed property names from JS."""
    dot = set(re.findall(r"\.(\w+)", js_text))
    bracket = set(re.findall(r'\["(\w+)"\]', js_text))
    return dot | bracket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def js_identifiers() -> set[str]:
    """All property identifiers referenced anywhere in dashboard.js."""
    assert _JS_PATH.exists(), f"dashboard.js not found at {_JS_PATH}"
    return _extract_all_js_identifiers(_JS_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Per-endpoint contract tests
# ---------------------------------------------------------------------------


class TestFeaturesListContract:
    """``GET /api/features`` response contract."""

    def test_top_level_keys_referenced_in_js(self, js_identifiers: set[str]) -> None:
        """JS accesses every required top-level key of FeaturesListResponse."""
        expected_in_js = {"features", "active_feature_id", "project_path"}
        missing = expected_in_js - js_identifiers
        assert not missing, f"FeaturesListResponse keys not found in JS: {missing}"

    def test_top_level_keys_declared_in_typeddict(self) -> None:
        keys = _typed_dict_keys(FeaturesListResponse)
        for k in ("features", "active_feature_id", "project_path", "worktrees_root", "active_worktree", "active_mission"):
            assert k in keys, f"FeaturesListResponse missing key: {k}"

    def test_feature_item_keys_referenced_in_js(self, js_identifiers: set[str]) -> None:
        """JS accesses the core FeatureItem keys."""
        expected = {"id", "name", "display_name", "artifacts", "workflow", "kanban_stats", "meta"}
        missing = expected - js_identifiers
        assert not missing, f"FeatureItem keys not found in JS: {missing}"

    def test_feature_item_keys_declared_in_typeddict(self) -> None:
        keys = _typed_dict_keys(FeatureItem)
        for k in ("id", "name", "display_name", "path", "artifacts", "workflow", "kanban_stats", "meta", "worktree", "is_legacy"):
            assert k in keys, f"FeatureItem missing key: {k}"

    def test_workflow_status_keys_in_js(self, js_identifiers: set[str]) -> None:
        """JS accesses workflow step keys."""
        expected = {"specify", "plan", "tasks", "implement"}
        missing = expected - js_identifiers
        assert not missing, f"WorkflowStatus keys not found in JS: {missing}"

    def test_workflow_status_keys_declared(self) -> None:
        assert _typed_dict_keys(WorkflowStatus) == {"specify", "plan", "tasks", "implement"}

    def test_kanban_stats_keys_in_js(self, js_identifiers: set[str]) -> None:
        expected = {"total", "done", "planned", "doing", "for_review", "approved"}
        missing = expected - js_identifiers
        assert not missing, f"KanbanStats keys not found in JS: {missing}"

    def test_kanban_stats_keys_declared(self) -> None:
        keys = _typed_dict_keys(KanbanStats)
        for k in ("total", "planned", "doing", "for_review", "approved", "done"):
            assert k in keys, f"KanbanStats missing key: {k}"

    def test_artifact_info_keys_declared(self) -> None:
        assert _typed_dict_keys(ArtifactInfo) == {"exists", "mtime", "size"}

    def test_artifact_exists_referenced_in_js(self, js_identifiers: set[str]) -> None:
        assert "exists" in js_identifiers


class TestKanbanContract:
    """``GET /api/kanban/{id}`` response contract."""

    def test_top_level_keys_in_js(self, js_identifiers: set[str]) -> None:
        assert "lanes" in js_identifiers

    def test_top_level_keys_declared(self) -> None:
        keys = _typed_dict_keys(KanbanResponse)
        assert keys == {"lanes", "is_legacy", "upgrade_needed"}

    def test_lane_names_in_js(self, js_identifiers: set[str]) -> None:
        """JS accesses the 6 kanban lane names."""
        expected = {"planned", "doing", "for_review", "in_review", "approved", "done"}
        missing = expected - js_identifiers
        assert not missing, f"Lane names not found in JS: {missing}"

    def test_task_data_keys_in_js(self, js_identifiers: set[str]) -> None:
        """JS accesses core KanbanTaskData properties."""
        expected = {"id", "title", "agent", "agent_profile", "role", "subtasks", "lane", "phase", "prompt_path", "model", "prompt_markdown"}
        missing = expected - js_identifiers
        assert not missing, f"KanbanTaskData keys not found in JS: {missing}"

    def test_task_data_keys_declared(self) -> None:
        keys = _typed_dict_keys(KanbanTaskData)
        for k in ("id", "title", "lane", "subtasks", "agent", "phase", "prompt_path", "model", "agent_profile", "role", "prompt_markdown", "assignee"):
            assert k in keys, f"KanbanTaskData missing key: {k}"


class TestResearchContract:
    """``GET /api/research/{id}`` response contract."""

    def test_top_level_keys_in_js(self, js_identifiers: set[str]) -> None:
        expected = {"main_file", "artifacts"}
        missing = expected - js_identifiers
        assert not missing, f"ResearchResponse keys not found in JS: {missing}"

    def test_top_level_keys_declared(self) -> None:
        assert _typed_dict_keys(ResearchResponse) == {"main_file", "artifacts"}

    def test_artifact_keys_in_js(self, js_identifiers: set[str]) -> None:
        expected = {"name", "path", "icon"}
        missing = expected - js_identifiers
        assert not missing, f"ResearchArtifact keys not found in JS: {missing}"

    def test_artifact_keys_declared(self) -> None:
        assert _typed_dict_keys(ResearchArtifact) == {"name", "path", "icon"}


class TestArtifactDirectoryContract:
    """``GET /api/contracts/{id}`` and ``GET /api/checklists/{id}``."""

    def test_files_key_in_js(self, js_identifiers: set[str]) -> None:
        assert "files" in js_identifiers

    def test_keys_declared(self) -> None:
        assert _typed_dict_keys(ArtifactDirectoryResponse) == {"files"}

    def test_file_item_keys_in_js(self, js_identifiers: set[str]) -> None:
        expected = {"name", "path", "icon"}
        missing = expected - js_identifiers
        assert not missing, f"ArtifactDirectoryFile keys not found in JS: {missing}"


class TestHealthContract:
    """``GET /api/health`` response contract.

    Note: ``/api/health`` is NOT consumed by ``dashboard.js`` (as of the
    current codebase).  We still validate the TypedDict is well-formed.
    """

    def test_keys_declared(self) -> None:
        keys = _typed_dict_keys(HealthResponse)
        for k in ("status", "project_path", "sync", "websocket_status", "token"):
            assert k in keys, f"HealthResponse missing key: {k}"


class TestDiagnosticsContract:
    """``GET /api/diagnostics`` response contract."""

    def test_top_level_keys_in_js(self, js_identifiers: set[str]) -> None:
        expected = {
            "project_path",
            "current_working_directory",
            "git_branch",
            "in_worktree",
            "active_mission",
            "file_integrity",
            "worktree_overview",
            "current_feature",
            "all_features",
            "observations",
        }
        missing = expected - js_identifiers
        assert not missing, f"DiagnosticsResponse keys not found in JS: {missing}"

    def test_top_level_keys_declared(self) -> None:
        keys = _typed_dict_keys(DiagnosticsResponse)
        for k in (
            "project_path",
            "current_working_directory",
            "git_branch",
            "in_worktree",
            "worktrees_exist",
            "active_mission",
            "file_integrity",
            "worktree_overview",
            "current_feature",
            "all_features",
            "dashboard_health",
            "observations",
            "issues",
        ):
            assert k in keys, f"DiagnosticsResponse missing key: {k}"

    def test_file_integrity_keys_in_js(self, js_identifiers: set[str]) -> None:
        expected = {"total_expected", "total_present", "total_missing", "missing_files"}
        missing = expected - js_identifiers
        assert not missing, f"FileIntegrity keys not found in JS: {missing}"

    def test_file_integrity_keys_declared(self) -> None:
        assert _typed_dict_keys(FileIntegrity) == {
            "total_expected",
            "total_present",
            "total_missing",
            "missing_files",
        }

    def test_current_feature_keys_in_js(self, js_identifiers: set[str]) -> None:
        expected = {"detected", "name", "state", "branch_exists", "worktree_exists", "worktree_path", "artifacts_in_main", "artifacts_in_worktree"}
        missing = expected - js_identifiers
        assert not missing, f"CurrentFeatureDetected keys not found in JS: {missing}"

    def test_current_feature_keys_declared(self) -> None:
        keys = _typed_dict_keys(CurrentFeatureDetected)
        for k in ("detected", "name", "state", "branch_exists", "branch_merged", "worktree_exists", "worktree_path", "artifacts_in_main", "artifacts_in_worktree"):
            assert k in keys, f"CurrentFeatureDetected missing key: {k}"

    def test_diagnostics_feature_status_keys_in_js(self, js_identifiers: set[str]) -> None:
        expected = {"name", "state", "branch_exists", "branch_merged", "worktree_exists", "artifacts_in_main", "artifacts_in_worktree"}
        missing = expected - js_identifiers
        assert not missing, f"DiagnosticsFeatureStatus keys not found in JS: {missing}"

    def test_diagnostics_feature_status_keys_declared(self) -> None:
        keys = _typed_dict_keys(DiagnosticsFeatureStatus)
        for k in ("name", "state", "branch_exists", "branch_merged", "worktree_exists", "worktree_path", "artifacts_in_main", "artifacts_in_worktree"):
            assert k in keys, f"DiagnosticsFeatureStatus missing key: {k}"


# ---------------------------------------------------------------------------
# Cross-cutting: every TypedDict should be importable
# ---------------------------------------------------------------------------


class TestTypeImports:
    """Verify all public TypedDict types are importable."""

    def test_all_exports_importable(self) -> None:
        from specify_cli.dashboard import api_types

        for name in api_types.__all__:
            obj = getattr(api_types, name, None)
            assert obj is not None, f"{name} listed in __all__ but not defined"
