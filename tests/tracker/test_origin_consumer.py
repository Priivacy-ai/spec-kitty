"""Tests for tracker/origin_consumer.py and observer wiring (T015, FR-005, FR-006).

Covers the remaining T015 projections (the former dossier-sync projection,
T015.1, was removed by issue #677 along with the dead
``fire_dossier_sync``/``register_dossier_sync_handler`` fan-out seam it
exercised — that registry had no production registrants):
  1. SaaS fan-out — fire_lifecycle_saas_fanout is called via emit_mission_created_local.
  2. Origin binding end-to-end — with consume_pending_origin_impl registered as the
     REAL consumer (as it is in production), a mission creation populates
     MissionCreationResult.origin_binding_* and clears the pending origin.

Tests call reset_origin_consumer() in teardown to prevent state bleed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

from specify_cli.core.adapters import (
    consume_pending_origin,
    register_pending_origin_consumer,
    reset_origin_consumer,
)
from specify_cli.tracker.origin_consumer import consume_pending_origin_impl


# This file carries `git_repo` (CI's -m git_repo gate selects it) alongside the
# integration category marker (marker-correctness Rule 1) for its origin-binding
# tests, which model `repo_root`/feature-dir paths under a mission's git checkout.
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_META: dict[str, Any] = {
    "mission_slug": "test-mission-01TSTULID12345678",
    "mission_id": "01TSTULID12345678901234AB",
}


def _write_pending_origin(repo_root: Path, *, provider: str = "linear") -> Path:
    """Write a well-formed pending-origin.yaml and return its path."""
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    pending = kittify / "pending-origin.yaml"
    pending.write_text(
        "\n".join(
            [
                f"provider: {provider}",
                "issue_key: ENG-99",
                "issue_id: issue-456",
                "title: Test dark mode",
                "url: https://linear.app/acme/ENG-99",
                "status: In Progress",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return pending


# ---------------------------------------------------------------------------
# Unit tests for consume_pending_origin_impl (no registry involved)
# ---------------------------------------------------------------------------


def test_no_pending_origin_returns_safe_default(tmp_path: Path) -> None:
    """Returns (False, False, None, meta) when no pending origin file exists."""
    meta = dict(_DUMMY_META)
    result = consume_pending_origin_impl(tmp_path, tmp_path / "feature", meta)
    assert result == (False, False, None, meta)


def test_missing_provider_returns_validation_error(tmp_path: Path) -> None:
    """Returns (True, False, error_msg, meta) when pending origin lacks provider."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "pending-origin.yaml").write_text("issue_key: ENG-1\nissue_id: id-1\n", encoding="utf-8")
    meta = dict(_DUMMY_META)
    attempted, succeeded, error_msg, returned_meta = consume_pending_origin_impl(tmp_path, tmp_path / "feature", meta)
    assert attempted is True
    assert succeeded is False
    assert error_msg is not None
    assert "provider" in error_msg.lower() or "identifier" in error_msg.lower()
    assert returned_meta is meta


def test_missing_issue_id_returns_validation_error(tmp_path: Path) -> None:
    """Returns (True, False, error_msg, meta) when pending origin lacks issue_id."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "pending-origin.yaml").write_text("provider: jira\nissue_key: PROJ-1\n", encoding="utf-8")
    meta = dict(_DUMMY_META)
    attempted, succeeded, error_msg, returned_meta = consume_pending_origin_impl(tmp_path, tmp_path / "feature", meta)
    assert attempted is True
    assert succeeded is False
    assert error_msg is not None


def test_bind_failure_returns_error_tuple(tmp_path: Path) -> None:
    """Returns (True, False, str(exc), meta) when bind_mission_origin raises OriginBindingError."""
    _write_pending_origin(tmp_path)
    meta = dict(_DUMMY_META)

    with patch(
        "specify_cli.tracker.origin.bind_mission_origin",
        side_effect=Exception("tracker unavailable"),
    ):
        attempted, succeeded, error_msg, returned_meta = consume_pending_origin_impl(tmp_path, tmp_path / "feature", meta)

    assert attempted is True
    assert succeeded is False
    assert error_msg is not None
    assert "tracker unavailable" in error_msg
    # meta unchanged on failure
    assert returned_meta is meta
    # pending-origin file still present on failure
    assert (tmp_path / ".kittify" / "pending-origin.yaml").exists()


def test_successful_bind_clears_pending_origin(tmp_path: Path) -> None:
    """On success, clears pending-origin.yaml and returns (True, True, None, updated_meta)."""
    pending_path = _write_pending_origin(tmp_path)
    meta = dict(_DUMMY_META)
    updated_meta = {**meta, "origin_ticket": {"provider": "linear"}}

    with patch(
        "specify_cli.tracker.origin.bind_mission_origin",
        return_value=(updated_meta, True),
    ):
        attempted, succeeded, error_msg, returned_meta = consume_pending_origin_impl(tmp_path, tmp_path / "feature", meta)

    assert attempted is True
    assert succeeded is True
    assert error_msg is None
    assert returned_meta == updated_meta
    # pending-origin file must be removed on success
    assert not pending_path.exists()


# ---------------------------------------------------------------------------
# T015.3 — End-to-end: real consumer registered, origin binding works
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_consumer():
    """Ensure the origin consumer registry is clean before/after every test."""
    reset_origin_consumer()
    yield
    reset_origin_consumer()


def test_real_consumer_registered_dispatches_correctly(tmp_path: Path) -> None:
    """With consume_pending_origin_impl registered, consume_pending_origin populates binding result.

    This is the key behavior-preservation test: proves that the WP01→WP02→WP03
    chain is end-to-end correct.  ``consume_pending_origin`` (called by
    ``core/mission_creation.py``) correctly dispatches to the tracker package
    and returns the populated 4-tuple.
    """
    pending_path = _write_pending_origin(tmp_path)
    meta = dict(_DUMMY_META)
    updated_meta = {**meta, "origin_ticket": {"provider": "linear"}}

    register_pending_origin_consumer(consume_pending_origin_impl)

    with patch(
        "specify_cli.tracker.origin.bind_mission_origin",
        return_value=(updated_meta, True),
    ):
        attempted, succeeded, error_msg, returned_meta = consume_pending_origin(tmp_path, tmp_path / "feature", meta)

    assert attempted is True
    assert succeeded is True
    assert error_msg is None
    assert returned_meta == updated_meta
    # pending-origin must be cleared
    assert not pending_path.exists()


def test_real_consumer_safe_degrade_when_no_pending_origin(tmp_path: Path) -> None:
    """With real consumer registered, consume_pending_origin returns safe default when no pending origin."""
    meta = dict(_DUMMY_META)
    register_pending_origin_consumer(consume_pending_origin_impl)

    result = consume_pending_origin(tmp_path, tmp_path / "feature", meta)

    assert result == (False, False, None, meta)


def test_real_consumer_propagates_bind_failure(tmp_path: Path) -> None:
    """With real consumer registered, bind failures surface as (True, False, error_msg, meta)."""
    from specify_cli.tracker.origin import OriginBindingError

    _write_pending_origin(tmp_path)
    meta = dict(_DUMMY_META)

    register_pending_origin_consumer(consume_pending_origin_impl)

    with patch(
        "specify_cli.tracker.origin.bind_mission_origin",
        side_effect=OriginBindingError("SaaS tracker call failed"),
    ):
        attempted, succeeded, error_msg, returned_meta = consume_pending_origin(tmp_path, tmp_path / "feature", meta)

    assert attempted is True
    assert succeeded is False
    assert error_msg is not None
    assert "SaaS tracker call failed" in error_msg
    assert returned_meta is meta


def test_consumer_qualified_name_is_stable() -> None:
    """consume_pending_origin_impl has a stable qualified name for idempotent registration."""
    module = getattr(consume_pending_origin_impl, "__module__", None)
    qualname = getattr(consume_pending_origin_impl, "__qualname__", None)
    assert isinstance(module, str), "consume_pending_origin_impl must have __module__"
    assert isinstance(qualname, str), "consume_pending_origin_impl must have __qualname__"
    key = f"{module}.{qualname}"
    assert "tracker" in key, f"Qualified name should contain 'tracker': {key}"
    assert "consume_pending_origin_impl" in key


# ---------------------------------------------------------------------------
# T015.2 — SaaS fan-out: fire_lifecycle_saas_fanout fires via emit_mission_created_local
# ---------------------------------------------------------------------------


def test_saas_fanout_fires_via_emit_mission_created_local(tmp_path: Path) -> None:
    """fire_lifecycle_saas_fanout is called when emit_mission_created_local runs.

    Verifies that the lifecycle event fan-out chain is intact after the
    WP02 removal of the direct emit_mission_created call from core/.
    """
    from specify_cli.status.lifecycle_events import emit_mission_created_local

    (tmp_path / ".git").mkdir()
    (tmp_path / "status.events.jsonl").parent.mkdir(parents=True, exist_ok=True)

    mock_fanout = MagicMock()

    with patch("specify_cli.status.adapters.fire_lifecycle_saas_fanout", mock_fanout):
        emit_mission_created_local(
            tmp_path,
            mission_slug="test-fanout-01TSTULID00000001",
            mission_id="01TSTULID000000000000001AB",
            mission_number=None,
            mission_type="software-dev",
            target_branch="main",
            wp_count=0,
        )

    mock_fanout.assert_called_once()
    call_kwargs = mock_fanout.call_args.kwargs
    assert "envelope" in call_kwargs
    envelope = call_kwargs["envelope"]
    assert envelope.get("event_type") == "MissionCreated"
