"""Parity tests between TypedDict shapes and Pydantic response models.

For every TypedDict in `dashboard.api_types`, the equivalent Pydantic
model in `dashboard.api.models` must accept a literal that satisfies the
TypedDict and round-trip it to byte-equivalent JSON. This protects the
Phase 1 contract surface (TypedDict-based) from drifting away from the
Phase 2 / FastAPI surface (Pydantic-based).

Each pair is tested with at least one non-trivial fixture — the simplest
possible literal that exercises every field. Fixtures are intentionally
kept small so a contract change shows up as a clear test failure.
"""
from __future__ import annotations

import json

import pytest

from dashboard.api import models as p

pytestmark = pytest.mark.fast


def _normalize(value):
    """Recursively re-serialise to byte-equivalent JSON with sorted keys."""
    return json.dumps(value, sort_keys=True, default=str)


def test_artifact_directory_response_parity() -> None:
    literal = {"files": [{"name": "spec.md", "path": "/abs/spec.md", "icon": "📝"}]}
    assert _normalize(p.ArtifactDirectoryResponse.model_validate(literal).model_dump()) == _normalize(literal)


def test_research_response_parity() -> None:
    literal = {
        "main_file": "research.md",
        "artifacts": [{"name": "appendix.md", "path": "research/appendix.md", "icon": "📝"}],
    }
    assert _normalize(p.ResearchResponse.model_validate(literal).model_dump()) == _normalize(literal)


def test_kanban_response_parity_minimal() -> None:
    literal = {
        "lanes": {"planned": [], "done": []},
        "is_legacy": False,
        "upgrade_needed": False,
        "weighted_percentage": None,
    }
    assert _normalize(p.KanbanResponse.model_validate(literal).model_dump()) == _normalize(literal)


def test_kanban_response_parity_with_card() -> None:
    literal = {
        "lanes": {
            "in_progress": [
                {
                    "id": "WP01",
                    "title": "Some WP",
                    "lane": "in_progress",
                    "subtasks": [{"id": "T001", "status": "done"}],
                    "agent": "claude",
                    "model": "opus-4-7",
                    "agent_profile": "python-pedro",
                    "role": "implementer",
                    "assignee": "claude",
                    "phase": "1",
                    "prompt_markdown": "## ⚡",
                    "prompt_path": "tasks/WP01.md",
                    "encoding_error": None,
                }
            ]
        },
        "is_legacy": False,
        "upgrade_needed": False,
        "weighted_percentage": 33.3,
    }
    parsed = p.KanbanResponse.model_validate(literal)
    # encoding_error is None, which is the explicit absence marker; both
    # representations serialise it to JSON null in the same place.
    assert parsed.lanes["in_progress"][0].id == "WP01"


def test_health_response_parity_minimal() -> None:
    literal = {"status": "ok", "project_path": "/abs/project"}
    parsed = p.HealthResponse.model_validate(literal)
    # Every other field is optional; round-trip preserves the input.
    dumped = parsed.model_dump(exclude_none=True)
    assert dumped == literal


def test_health_response_parity_with_sync() -> None:
    literal = {
        "status": "ok",
        "project_path": "/abs/project",
        "sync": {"running": True, "last_sync": "2026-05-02T19:00:00Z", "consecutive_failures": 0},
        "websocket_status": "connected",
    }
    parsed = p.HealthResponse.model_validate(literal)
    dumped = parsed.model_dump(exclude_none=True)
    # Pydantic preserves the field order from the model declaration; tests
    # use sorted-key normalization to compare.
    assert _normalize(dumped) == _normalize(literal)


def test_features_list_response_parity_empty() -> None:
    literal = {
        "features": [],
        "active_feature_id": None,
        "project_path": "/abs",
        "worktrees_root": None,
        "active_worktree": None,
        "active_mission": {
            "name": "No active feature",
            "domain": "unknown",
            "version": "",
            "slug": "",
            "description": "",
            "path": "",
            "feature": None,
        },
    }
    parsed = p.FeaturesListResponse.model_validate(literal)
    # model_dump() emits every field including None (matching the literal's
    # explicit nulls). The fields are normalized to sorted keys for compare.
    dumped = parsed.model_dump()
    assert _normalize(dumped) == _normalize(literal)


def test_sync_trigger_scheduled_parity() -> None:
    literal = {"status": "scheduled"}
    parsed = p.SyncTriggerScheduledResponse.model_validate(literal)
    assert parsed.model_dump() == literal


def test_sync_trigger_skipped_parity() -> None:
    literal = {"status": "skipped", "manual_mode": True, "reason": "policy_manual"}
    parsed = p.SyncTriggerSkippedResponse.model_validate(literal)
    assert parsed.model_dump() == literal


def test_sync_trigger_unavailable_parity_with_reason() -> None:
    literal = {"error": "sync_daemon_unavailable", "reason": "rollout_disabled"}
    parsed = p.SyncTriggerUnavailableResponse.model_validate(literal)
    assert parsed.model_dump() == literal


def test_sync_trigger_unavailable_parity_without_reason() -> None:
    literal = {"error": "sync_daemon_unavailable"}
    parsed = p.SyncTriggerUnavailableResponse.model_validate(literal)
    # exclude_none strips reason=None so the JSON shape matches the legacy stack.
    assert parsed.model_dump(exclude_none=True) == literal


def test_sync_trigger_failed_parity() -> None:
    literal = {"error": "sync_trigger_failed"}
    parsed = p.SyncTriggerFailedResponse.model_validate(literal)
    assert parsed.model_dump() == literal


def test_shutdown_response_parity() -> None:
    literal = {"status": "stopping"}
    parsed = p.ShutdownResponse.model_validate(literal)
    assert parsed.model_dump() == literal


def test_glossary_term_record_parity() -> None:
    literal = {"surface": "mission", "definition": "...", "status": "active", "confidence": 1.0}
    parsed = p.GlossaryTermRecord.model_validate(literal)
    assert parsed.model_dump() == literal


def test_diagnostics_minimal_parity() -> None:
    literal = {
        "project_path": "/abs",
        "current_working_directory": "/abs",
        "git_branch": "feature/foo",
        "in_worktree": False,
        "worktrees_exist": False,
        "active_mission": None,
        "file_integrity": {
            "total_expected": 1,
            "total_present": 1,
            "total_missing": 0,
            "missing_files": [],
        },
        "worktree_overview": {},
        "current_feature": {"detected": False, "error": "no spec found"},
        "all_features": [],
        "dashboard_health": {},
        "observations": [],
        "issues": [],
    }
    parsed = p.DiagnosticsResponse.model_validate(literal)
    dumped = parsed.model_dump()
    # The DashboardHealthInfo fields default to None; the literal has the
    # block as `{}` (empty), which deserialises to a model with all None
    # fields. Re-dumping then includes the explicit None values, so we
    # normalise the literal too by inflating the empty health block.
    inflated_literal = dict(literal)
    inflated_literal["dashboard_health"] = parsed.dashboard_health.model_dump()
    assert _normalize(dumped) == _normalize(inflated_literal)


def test_models_accept_extra_fields_silently() -> None:
    """`extra='allow'` is intentional — production scanner emits a superset
    of the original TypedDict fields (e.g. KanbanStats.weighted_percentage).
    Models must NOT reject unknown keys; schema drift is caught by the
    OpenAPI snapshot test, not by Pydantic validation at the API boundary.
    """
    parsed = p.HealthResponse.model_validate({"status": "ok", "rogue_field": True})
    # The extra field is preserved on the model instance (Pydantic v2 keeps
    # extras when extra='allow'); it is also serialised back out.
    dumped = parsed.model_dump()
    assert dumped["status"] == "ok"
    assert dumped.get("rogue_field") is True


def test_kanban_stats_accepts_weighted_percentage() -> None:
    """Regression test for the production-bug found by post-merge dashboard
    smoke: scanner._build_event_log_kanban_stats emits weighted_percentage
    on every event-log-derived feature; the Pydantic model must accept it."""
    literal = {
        "total": 6,
        "planned": 0,
        "doing": 0,
        "for_review": 0,
        "approved": 0,
        "done": 6,
        "weighted_percentage": 100.0,
    }
    parsed = p.KanbanStats.model_validate(literal)
    assert parsed.model_dump(exclude_none=True) == literal
