"""Integration tests for _propagate_one + projection policy (T036, T037).

Verifies:
1. With no transport registered, nothing is sent and nothing is logged
   (across all modes × events).
2. Policy correctly gates projection per (mode, event).
3. Envelope fields respect include_request_text / include_evidence_ref.
4. NFR-007 / SC-008: propagation-errors.jsonl stays empty when nothing is sent.

The former egress-consent gate that used to run first in ``_propagate_one``
retired with the sync transport (issue #5), so these tests drive clients in
through the ``_get_saas_client`` seam alone; production wiring (no factory
registered) makes propagation a silent no-op.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.propagator import PROPAGATION_ERRORS_PATH, _propagate_one
from specify_cli.invocation.record import OpCompletedEvent, OpStartedEvent


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _make_started_record(mode: str | None, invocation_id: str = "01KPQRX2EVGMRVB4Q1JQBAZJV3") -> OpStartedEvent:
    # Schema v2: mode_of_work is required; ``None`` callers map to the
    # task_execution default (mirrors the executor / WP05 migration default).
    return OpStartedEvent(
        invocation_id=invocation_id,
        profile_id="implementer-fixture",
        action="implement",
        request_text="the request text",
        governance_context_hash="abc123",
        governance_context_available=True,
        actor="claude",
        started_at="2026-04-23T00:00:00+00:00",
        mode_of_work=mode or "task_execution",
    )


def _make_completed_record(
    mode: str | None,  # noqa: ARG001 — v2 completed events carry no mode_of_work
    invocation_id: str = "01KPQRX2EVGMRVB4Q1JQBAZJV3",
) -> OpCompletedEvent:
    # Schema v2: completed events carry NO started-only fields (incl. mode).
    # The propagator resolves their policy with mode=None (task_execution default).
    return OpCompletedEvent(
        invocation_id=invocation_id,
        completed_at="2026-04-23T00:01:00+00:00",
        outcome="done",
        closed_by="agent",
        evidence_ref="kitty-specs/001/evidence.md",
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
# T036 — No transport registered: nothing is ever sent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["advisory", "task_execution", "mission_step", "query"])
@pytest.mark.parametrize("event_name", ["started", "completed"])
def test_no_transport_registered_never_sends(tmp_path: Path, mode: str, event_name: str) -> None:
    """With no factory registered, propagation is a silent no-op for every (mode, event).

    Nothing reaches a transport and no error is logged — the production state since
    issue #5 deleted the sync transport (the consent gate that used to stop this
    lookup retired with it).
    """
    if event_name == "started":
        record = _make_started_record(mode)
    else:
        record = _make_completed_record(mode)

    with patch(
        "specify_cli.invocation.propagator._get_saas_client",
        return_value=None,
    ) as mock_client_factory:
        _propagate_one(record, tmp_path)

    mock_client_factory.assert_called_once_with(tmp_path)
    assert not (tmp_path / PROPAGATION_ERRORS_PATH).exists(), (
        "no error may be logged when there is no transport to send through"
    )


# ---------------------------------------------------------------------------
# T036 — Policy gating for (mode, event) pairs
# ---------------------------------------------------------------------------


def test_task_execution_started_includes_request_text(tmp_path: Path) -> None:
    """TASK_EXECUTION/started sends envelope with request_text included."""
    record = _make_started_record("task_execution")
    mock_client = _make_mock_client()

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
    record = _make_started_record("advisory")
    mock_client = _make_mock_client()

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
    record = _make_started_record("query")
    mock_client = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator._get_saas_client",
        return_value=mock_client,
    ):
        _propagate_one(record, tmp_path)

    assert len(mock_client._captured) == 0, "QUERY/started should never call send_event"


def test_task_execution_completed_includes_evidence_ref(tmp_path: Path) -> None:
    """TASK_EXECUTION/completed envelope includes evidence_ref."""
    record = _make_completed_record("task_execution")
    mock_client = _make_mock_client()

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


def test_completed_event_resolves_policy_without_mode(tmp_path: Path) -> None:
    """v2 completed events carry no mode; policy resolves as task_execution default.

    The advisory/query evidence gate moved to write time (executor raises
    InvalidModeForEvidenceError before any completed event exists), so
    advisory completed events can never carry an evidence_ref in v2.
    """
    record = _make_completed_record(None)
    mock_client = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator._get_saas_client",
        return_value=mock_client,
    ):
        _propagate_one(record, tmp_path)

    assert len(mock_client._captured) == 1
    envelope = mock_client._captured[0]
    assert envelope["event_type"] == "ProfileInvocationCompleted"
    assert envelope["evidence_ref"] == "kitty-specs/001/evidence.md"


def test_mission_step_started_includes_request_text(tmp_path: Path) -> None:
    """MISSION_STEP/started behaves same as TASK_EXECUTION/started."""
    record = _make_started_record("mission_step")
    mock_client = _make_mock_client()

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
    record_null = _make_started_record(None)
    mock_client_null = _make_mock_client()

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
def test_no_propagation_errors_without_a_transport(tmp_path: Path, mode: str) -> None:
    """NFR-007 / SC-008 — propagation-errors.jsonl stays empty when nothing is sent.

    Runs a full started + completed pair with the transport seam answering ``None``
    (production reality: nothing registers a factory since issue #5 deleted the
    sync transport). Verifies that no propagation-errors file is created (or is
    empty if pre-existing).
    """
    started = _make_started_record(mode)
    completed = _make_completed_record(mode)

    with patch(
        "specify_cli.invocation.propagator._get_saas_client",
        return_value=None,
    ):
        _propagate_one(started, tmp_path)
        _propagate_one(completed, tmp_path)

    prop_errors_path = tmp_path / PROPAGATION_ERRORS_PATH
    if prop_errors_path.exists():
        content = prop_errors_path.read_text(encoding="utf-8").strip()
        assert not content, (
            f"Expected empty propagation-errors.jsonl when there is no transport, "
            f"but got: {content!r}"
        )


# ---------------------------------------------------------------------------
# #3030 FR-025 census — an unclassifiable record has no policy row, so it is
# not projected. Both coercions used to resolve "unintelligible" to the most
# permissive rule in the table (project=True, include_request_text=True).
# ---------------------------------------------------------------------------


def test_unrecognised_event_kind_is_not_projected(tmp_path: Path) -> None:
    """An ``event`` value with no policy row is dropped, not projected as STARTED.

    Built with ``model_construct`` because the models validate ``event`` against a
    Literal today — the point is what happens the day a schema change adds a kind
    before the policy table learns about it, which is precisely when the old
    fallback (``EventKind.STARTED`` → the permissive default rule) would have
    shipped a body nobody classified.
    """
    record = OpStartedEvent.model_construct(
        event="resumed",  # type: ignore[arg-type]
        invocation_id="01KPQRX2EVGMRVB4Q1JQBAZJV3",
        profile_id="implementer-fixture",
        action="implement",
        request_text="the request text",
        governance_context_hash="abc123",
        governance_context_available=True,
        actor="claude",
        started_at="2026-04-23T00:00:00+00:00",
        mode_of_work="task_execution",
    )
    client = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator._get_saas_client",
        return_value=client,
    ):
        _propagate_one(record, tmp_path)

    assert client._captured == [], f"LEAK: {client._captured}"


def test_unrecognised_mode_of_work_is_not_projected(tmp_path: Path) -> None:
    """A ``mode_of_work`` the policy table does not know refuses, body included.

    Distinct from a mode that is ABSENT (every completed event, and every pre-v2
    record), which keeps its documented task_execution default — pinned by
    ``test_completed_event_resolves_policy_without_mode`` and
    ``test_null_mode_projects_like_task_execution``. Collapsing the two is the
    defect; the fix must not close absence along with malformation.
    """
    record = OpStartedEvent.model_construct(
        event="started",
        invocation_id="01KPQRX2EVGMRVB4Q1JQBAZJV3",
        profile_id="implementer-fixture",
        action="implement",
        request_text="the request text",
        governance_context_hash="abc123",
        governance_context_available=True,
        actor="claude",
        started_at="2026-04-23T00:00:00+00:00",
        mode_of_work="TASK-EXECUTION",  # type: ignore[arg-type]
    )
    client = _make_mock_client()

    with patch(
        "specify_cli.invocation.propagator._get_saas_client",
        return_value=client,
    ):
        _propagate_one(record, tmp_path)

    assert client._captured == [], f"LEAK: {client._captured}"
