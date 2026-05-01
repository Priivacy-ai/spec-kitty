"""Integration tests for _propagate_one + projection policy (T036, T037).

Verifies:
1. Sync-disabled checkouts never call send_event (across all modes × events).
2. Policy correctly gates projection per (mode, event).
3. Envelope fields respect include_request_text / include_evidence_ref.
4. NFR-007 / SC-008: propagation-errors.jsonl stays empty under sync-disabled.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from specify_cli.invocation.propagator import _propagate_one
from specify_cli.invocation.record import InvocationRecord
from specify_cli.sync.routing import CheckoutSyncRouting


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_routing(*, effective_sync_enabled: bool, repo_root: Path) -> CheckoutSyncRouting:
    return CheckoutSyncRouting(
        repo_root=repo_root,
        project_uuid="test-uuid",
        project_slug="test-slug",
        build_id=None,
        repo_slug="test-repo",
        local_sync_enabled=effective_sync_enabled,
        repo_default_sync_enabled=None,
        effective_sync_enabled=effective_sync_enabled,
    )


def _make_started_record(mode: str | None, invocation_id: str = "01KPQRX2EVGMRVB4Q1JQBAZJV3") -> InvocationRecord:
    return InvocationRecord(
        event="started",
        invocation_id=invocation_id,
        profile_id="implementer-fixture",
        action="implement",
        request_text="the request text",
        governance_context_hash="abc123",
        actor="claude",
        started_at="2026-04-23T00:00:00+00:00",
        mode_of_work=mode,
    )


def _make_completed_record(mode: str | None, invocation_id: str = "01KPQRX2EVGMRVB4Q1JQBAZJV3") -> InvocationRecord:
    return InvocationRecord(
        event="completed",
        invocation_id=invocation_id,
        profile_id="implementer-fixture",
        action="implement",
        started_at="2026-04-23T00:00:00+00:00",
        completed_at="2026-04-23T00:01:00+00:00",
        outcome="done",
        evidence_ref="kitty-specs/001/evidence.md",
        mode_of_work=mode,
    )


def _make_mock_client() -> MagicMock:
    """Return a mock SaaS client with an async send_event."""
    client = MagicMock()
    captured: list[dict[str, object]] = []

    async def async_send(event_dict: dict[str, object]) -> None:
        captured.append(event_dict)

    client.send_event = async_send
    client._captured = captured
    return client


# ---------------------------------------------------------------------------
# T036 — Sync-disabled never calls send_event
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["advisory", "task_execution", "mission_step", "query"])
@pytest.mark.parametrize("event_name", ["started", "completed"])
def test_sync_disabled_never_calls_send(tmp_path: Path, mode: str, event_name: str) -> None:
    """Sync-disabled checkout never calls send_event regardless of (mode, event)."""
    routing = _make_routing(effective_sync_enabled=False, repo_root=tmp_path)

    if event_name == "started":
        record = _make_started_record(mode)
    else:
        record = _make_completed_record(mode)

    with patch(
        "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
        return_value=routing,
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
        ) as mock_client_factory:
            _propagate_one(record, tmp_path)
            mock_client_factory.assert_not_called()


# ---------------------------------------------------------------------------
# T036 — Policy gating for (mode, event) pairs
# ---------------------------------------------------------------------------


def test_task_execution_started_includes_request_text(tmp_path: Path) -> None:
    """TASK_EXECUTION/started sends envelope with request_text included."""
    routing = _make_routing(effective_sync_enabled=True, repo_root=tmp_path)
    record = _make_started_record("task_execution")
    mock_client = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
        return_value=routing,
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=mock_client,
        ):
            _propagate_one(record, tmp_path)

    assert len(mock_client._captured) == 1
    envelope = mock_client._captured[0]
    assert envelope["event_type"] == "ProfileInvocationStarted"
    assert "request_text" in envelope, "TASK_EXECUTION/started envelope must include request_text"
    assert envelope["request_text"] == "the request text"
    assert envelope["mode_of_work"] == "task_execution"


def test_advisory_started_omits_request_text(tmp_path: Path) -> None:
    """ADVISORY/started projects but without request_text key in envelope."""
    routing = _make_routing(effective_sync_enabled=True, repo_root=tmp_path)
    record = _make_started_record("advisory")
    mock_client = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
        return_value=routing,
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=mock_client,
        ):
            _propagate_one(record, tmp_path)

    assert len(mock_client._captured) == 1, "ADVISORY/started should produce one send_event call"
    envelope = mock_client._captured[0]
    assert envelope["event_type"] == "ProfileInvocationStarted"
    assert "request_text" not in envelope, (
        "ADVISORY/started must omit request_text key entirely (not empty string)"
    )


def test_query_started_does_not_project(tmp_path: Path) -> None:
    """QUERY/started produces no send_event call (policy.project=False)."""
    routing = _make_routing(effective_sync_enabled=True, repo_root=tmp_path)
    record = _make_started_record("query")
    mock_client = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
        return_value=routing,
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=mock_client,
        ):
            _propagate_one(record, tmp_path)

    assert len(mock_client._captured) == 0, "QUERY/started should never call send_event"


def test_task_execution_completed_includes_evidence_ref(tmp_path: Path) -> None:
    """TASK_EXECUTION/completed envelope includes evidence_ref."""
    routing = _make_routing(effective_sync_enabled=True, repo_root=tmp_path)
    record = _make_completed_record("task_execution")
    mock_client = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
        return_value=routing,
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=mock_client,
        ):
            _propagate_one(record, tmp_path)

    assert len(mock_client._captured) == 1
    envelope = mock_client._captured[0]
    assert envelope["event_type"] == "ProfileInvocationCompleted"
    assert "evidence_ref" in envelope, "TASK_EXECUTION/completed must include evidence_ref"
    assert envelope["evidence_ref"] == "kitty-specs/001/evidence.md"


def test_advisory_completed_omits_evidence_ref(tmp_path: Path) -> None:
    """ADVISORY/completed projects but without evidence_ref key in envelope."""
    routing = _make_routing(effective_sync_enabled=True, repo_root=tmp_path)
    record = _make_completed_record("advisory")
    mock_client = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
        return_value=routing,
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=mock_client,
        ):
            _propagate_one(record, tmp_path)

    assert len(mock_client._captured) == 1, "ADVISORY/completed should project (advisory projects)"
    envelope = mock_client._captured[0]
    assert envelope["event_type"] == "ProfileInvocationCompleted"
    assert "evidence_ref" not in envelope, (
        "ADVISORY/completed must omit evidence_ref key (policy.include_evidence_ref=False)"
    )


def test_mission_step_started_includes_request_text(tmp_path: Path) -> None:
    """MISSION_STEP/started behaves same as TASK_EXECUTION/started."""
    routing = _make_routing(effective_sync_enabled=True, repo_root=tmp_path)
    record = _make_started_record("mission_step")
    mock_client = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
        return_value=routing,
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=mock_client,
        ):
            _propagate_one(record, tmp_path)

    assert len(mock_client._captured) == 1
    envelope = mock_client._captured[0]
    assert "request_text" in envelope
    assert envelope["mode_of_work"] == "mission_step"


def test_null_mode_projects_like_task_execution(tmp_path: Path) -> None:
    """Pre-WP06 records (mode_of_work=None) project as TASK_EXECUTION (backward compat)."""
    routing = _make_routing(effective_sync_enabled=True, repo_root=tmp_path)
    record_null = _make_started_record(None)
    mock_client_null = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
        return_value=routing,
    ):
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
            return_value=mock_client_null,
        ):
            _propagate_one(record_null, tmp_path)

    # Should have exactly one send_event call (like task_execution)
    assert len(mock_client_null._captured) == 1
    envelope = mock_client_null._captured[0]
    assert "request_text" in envelope, "Null mode should include request_text (TASK_EXECUTION fallback)"


# ---------------------------------------------------------------------------
# T037 — NFR-007 / SC-008: propagation-errors.jsonl stays empty under sync-disabled
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["advisory", "task_execution", "mission_step", "query"])
def test_no_propagation_errors_under_sync_disabled(tmp_path: Path, mode: str) -> None:
    """NFR-007 / SC-008 — propagation-errors.jsonl stays empty with sync disabled.

    Runs a full started + completed pair with sync disabled. Verifies that no
    propagation-errors file is created (or is empty if pre-existing).
    """
    routing = _make_routing(effective_sync_enabled=False, repo_root=tmp_path)
    started = _make_started_record(mode)
    completed = _make_completed_record(mode)

    with patch(
        "specify_cli.invocation.propagator.resolve_checkout_sync_routing",
        return_value=routing,
    ):
        # _get_saas_client must never be called; but even if it were, no errors should result.
        with patch(
            "specify_cli.invocation.propagator._get_saas_client",
        ):
            _propagate_one(started, tmp_path)
            _propagate_one(completed, tmp_path)

    prop_errors_path = tmp_path / ".kittify" / "events" / "propagation-errors.jsonl"
    if prop_errors_path.exists():
        content = prop_errors_path.read_text(encoding="utf-8").strip()
        assert not content, (
            f"Expected empty propagation-errors.jsonl under sync-disabled, "
            f"but got: {content!r}"
        )
