"""Acceptance tests for the ``DeliveryReceiver`` contract + receivers (WP06).

These tests pin **observable** result/sink state (NFR-001), never internal call
order. They lock the contract §4 behaviours:

* one :class:`DeliveryReceiver` protocol covers all five §4 aspects and every
  concrete receiver implements it (**FR-014**, §4 rule 1);
* :class:`StubReceiver` is a *real* receiver in the production module that records
  events with **no Teamspace credentials present** (**SC-005**, §4 required test 1);
* the Teamspace and stub receivers produce the **same** per-event outcome sequence
  for equivalent payloads (**SC-007**, §4 required test 2);
* the full §4 result vocabulary is exercised (success / duplicate / pending /
  rejected / transient / terminal-failed) — NFR-002 — and a batch-level transient
  failure never poisons per-event retry state;
* :class:`ExternalReceiver` applies **no** Teamspace gating (**FR-007**);
* gate evaluation is per-receiver data driven by a shared helper — no target-type
  ``if`` (FR-014).
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
import requests

from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    DeliveryReceiver,
    DeliveryResult,
    ExternalReceiver,
    GateContext,
    GateKind,
    OutboundEvent,
    ReceiverGate,
    StubReceiver,
    TeamspaceReceiver,
    evaluate_gates,
    map_batch_response,
)

pytestmark = pytest.mark.fast

# -- Fixtures / helpers --------------------------------------------------------

SERVER_URL = "https://spec-kitty-dev.fly.dev"
EXPECTED_BATCH_ENDPOINT = "https://spec-kitty-dev.fly.dev/api/v1/events/batch/"
_TOKEN = "jwt-access-token"

# Token-ish ambient env names a developer machine might carry. SC-005 clears them
# so a real local key cannot mask a regression in the no-credentials stub path.
_AMBIENT_TOKEN_ENV = (
    "SPEC_KITTY_SAAS_URL",
    "SPEC_KITTY_ENABLE_SAAS_SYNC",
    "SPEC_KITTY_SAAS_TOKEN",
    "SPEC_KITTY_TEAMSPACE_KEY",
    "SPEC_KITTY_ACCESS_TOKEN",
)


def _event(event_id: str, *, wp: str = "WP01") -> OutboundEvent:
    return OutboundEvent(
        event_id=event_id,
        payload={
            "event_id": event_id,
            "event_type": "WPStatusChanged",
            "payload": {"wp_id": wp, "from_lane": "planned", "to_lane": "in_progress"},
        },
    )


class _FakeResponse:
    """Minimal ``requests.Response`` stand-in for the faked transport."""

    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class _FakePoster:
    """A faked HTTP poster: never hits the network, records the last call."""

    def __init__(self, *responses: _FakeResponse, raise_exc: Exception | None = None) -> None:
        self._responses = list(responses)
        self._raise = raise_exc
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self, url: str, *, data: bytes, headers: Mapping[str, str], timeout: float
    ) -> _FakeResponse:
        self.calls.append({"url": url, "data": data, "headers": dict(headers), "timeout": timeout})
        if self._raise is not None:
            raise self._raise
        return self._responses.pop(0) if self._responses else _FakeResponse(200, {"results": []})


def _ok_body(*pairs: tuple[str, str]) -> dict[str, Any]:
    return {"results": [{"event_id": eid, "status": status} for eid, status in pairs]}


# -- Protocol / vocabulary -----------------------------------------------------


def test_delivery_outcome_has_exactly_the_six_section4_values() -> None:
    assert {o.value for o in DeliveryOutcome} == {
        "success",
        "duplicate",
        "pending",
        "rejected",
        "terminal_failed",
        "transient",
    }


def test_all_three_receivers_implement_the_one_protocol() -> None:
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN)
    external = ExternalReceiver(endpoint_url="https://ops.example/ingest/")
    stub = StubReceiver()
    for receiver in (teamspace, external, stub):
        assert isinstance(receiver, DeliveryReceiver)
        # Every aspect of §4 is present and callable.
        assert isinstance(receiver.endpoint_url, str)
        assert isinstance(receiver.auth_headers(), dict)
        assert isinstance(receiver.gates(), tuple)


# -- SC-005: stub with NO Teamspace credentials --------------------------------


def test_stub_records_events_with_no_teamspace_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in _AMBIENT_TOKEN_ENV:
        monkeypatch.delenv(name, raising=False)
    import os

    assert all(name not in os.environ for name in _AMBIENT_TOKEN_ENV)

    stub = StubReceiver()
    # A real stub requires no credentials and no gates.
    assert stub.auth_headers() == {}
    assert stub.gates() == ()

    batch = [_event("01JMBY00000000000000000001"), _event("01JMBY00000000000000000002")]
    results = stub.deliver(batch)

    assert [r.outcome for r in results] == [DeliveryOutcome.SUCCESS, DeliveryOutcome.SUCCESS]
    assert stub.received_event_ids() == (
        "01JMBY00000000000000000001",
        "01JMBY00000000000000000002",
    )


# -- SC-007: stub and Teamspace produce the SAME ledger state ------------------


def test_stub_and_teamspace_produce_identical_outcomes_for_equivalent_payloads() -> None:
    batch = [_event("01JMBY0000000000000000000A"), _event("01JMBY0000000000000000000B")]
    # Teamspace faked transport reports success for both events.
    poster = _FakePoster(
        _FakeResponse(
            200,
            _ok_body(
                ("01JMBY0000000000000000000A", "success"),
                ("01JMBY0000000000000000000B", "success"),
            ),
        )
    )
    teamspace = TeamspaceReceiver(
        resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=poster
    )
    stub = StubReceiver()

    ts_results = list(teamspace.deliver(batch))
    stub_results = list(stub.deliver(batch))

    ts_map = {r.event_id: r.outcome for r in ts_results}
    stub_map = {r.event_id: r.outcome for r in stub_results}
    assert ts_map == stub_map
    assert all(o is DeliveryOutcome.SUCCESS for o in ts_map.values())


def test_stub_and_teamspace_agree_on_duplicate_redelivery() -> None:
    batch = [_event("01JMBY0000000000000000000C")]
    # Re-delivery: server reports duplicate; stub remembers its own seen id.
    poster = _FakePoster(
        _FakeResponse(200, _ok_body(("01JMBY0000000000000000000C", "success"))),
        _FakeResponse(200, _ok_body(("01JMBY0000000000000000000C", "duplicate"))),
    )
    teamspace = TeamspaceReceiver(
        resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=poster
    )
    stub = StubReceiver()

    teamspace.deliver(batch)
    stub.deliver(batch)
    ts_second = list(teamspace.deliver(batch))
    stub_second = list(stub.deliver(batch))

    assert ts_second[0].outcome is DeliveryOutcome.DUPLICATE
    assert stub_second[0].outcome is DeliveryOutcome.DUPLICATE


# -- TeamspaceReceiver: endpoint, auth, gates ----------------------------------


def test_teamspace_endpoint_and_bearer_auth() -> None:
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL + "/", auth_token=_TOKEN)
    assert teamspace.endpoint_url == EXPECTED_BATCH_ENDPOINT
    assert teamspace.auth_headers() == {"Authorization": f"Bearer {_TOKEN}"}


def test_teamspace_gate_set_is_saas_private_teamspace_auth() -> None:
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN)
    kinds = {g.kind for g in teamspace.gates()}
    assert kinds == {GateKind.SAAS_ENABLED, GateKind.PRIVATE_TEAMSPACE, GateKind.AUTH}


def test_teamspace_posts_to_resolved_endpoint_with_bearer_header() -> None:
    batch = [_event("01JMBY0000000000000000000D")]
    poster = _FakePoster(_FakeResponse(200, _ok_body(("01JMBY0000000000000000000D", "success"))))
    teamspace = TeamspaceReceiver(
        resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=poster
    )
    teamspace.deliver(batch)
    call = poster.calls[0]
    assert call["url"] == EXPECTED_BATCH_ENDPOINT
    assert call["headers"]["Authorization"] == f"Bearer {_TOKEN}"
    assert call["headers"]["Content-Encoding"] == "gzip"


# -- ExternalReceiver: FR-007, no Teamspace gating -----------------------------


def test_external_applies_only_endpoint_configured_gate() -> None:
    external = ExternalReceiver(endpoint_url="https://ops.example/ingest/")
    kinds = {g.kind for g in external.gates()}
    assert kinds == {GateKind.ENDPOINT_CONFIGURED}
    assert GateKind.SAAS_ENABLED not in kinds
    assert GateKind.AUTH not in kinds


def test_external_delivers_with_no_credentials_when_endpoint_configured() -> None:
    external = ExternalReceiver(endpoint_url="https://ops.example/ingest/")
    # No Teamspace creds anywhere; only an endpoint-configured context is needed.
    decision = evaluate_gates(external, GateContext(endpoint_configured=True))
    assert decision.satisfied is True
    assert external.auth_headers() == {}


def test_external_endpoint_verbatim_and_optional_auth() -> None:
    url = "https://ops.example/custom/path/"
    no_auth = ExternalReceiver(endpoint_url=url)
    assert no_auth.endpoint_url == url
    assert no_auth.auth_headers() == {}

    with_auth = ExternalReceiver(endpoint_url=url, auth_headers={"X-Api-Key": "secret"})
    assert with_auth.auth_headers() == {"X-Api-Key": "secret"}


def test_external_reuses_the_shared_batch_mapper() -> None:
    batch = [_event("01JMBY0000000000000000000E")]
    poster = _FakePoster(_FakeResponse(200, _ok_body(("01JMBY0000000000000000000E", "success"))))
    external = ExternalReceiver(endpoint_url="https://ops.example/ingest/", poster=poster)
    results = list(external.deliver(batch))
    assert results[0].outcome is DeliveryOutcome.SUCCESS


def test_external_non_batch_shape_maps_transient_not_silent_success() -> None:
    batch = [_event("01JMBY0000000000000000000F")]
    poster = _FakePoster(_FakeResponse(200, {"ok": True}))  # not the batch shape
    external = ExternalReceiver(endpoint_url="https://ops.example/ingest/", poster=poster)
    results = list(external.deliver(batch))
    assert results[0].outcome is DeliveryOutcome.TRANSIENT


# -- Gate evaluation: per-receiver data, shared helper -------------------------


def test_evaluate_gates_no_gates_is_satisfied() -> None:
    stub = StubReceiver()
    decision = evaluate_gates(stub, GateContext())
    assert decision.satisfied is True
    assert decision.unsatisfied == ()


def test_evaluate_gates_teamspace_blocked_when_context_unsatisfied() -> None:
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN)
    decision = evaluate_gates(teamspace, GateContext())  # nothing enabled
    assert decision.satisfied is False
    assert {g.kind for g in decision.unsatisfied} == {
        GateKind.SAAS_ENABLED,
        GateKind.PRIVATE_TEAMSPACE,
        GateKind.AUTH,
    }


def test_evaluate_gates_teamspace_satisfied_when_all_present() -> None:
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN)
    ctx = GateContext(saas_enabled=True, private_teamspace=True, auth_present=True)
    assert evaluate_gates(teamspace, ctx).satisfied is True


def test_receiver_gate_is_pure_declarative_data() -> None:
    gate = ReceiverGate(kind=GateKind.SAAS_ENABLED)
    assert gate.name == "saas_enabled"
    assert gate.is_satisfied(GateContext(saas_enabled=True)) is True
    assert gate.is_satisfied(GateContext(saas_enabled=False)) is False


# -- Full §4 outcome vocabulary via the shared mapper --------------------------


def test_rejected_maps_with_error_message_or_error() -> None:
    batch = [_event("01JMBY0000000000000000000G"), _event("01JMBY0000000000000000000H")]
    body = {
        "results": [
            {
                "event_id": "01JMBY0000000000000000000G",
                "status": "rejected",
                "error": "Invalid payload: missing field 'wp_id'",
            },
            {
                "event_id": "01JMBY0000000000000000000H",
                "status": "rejected",
                "error_message": "alt field name accepted",
            },
        ]
    }
    results = map_batch_response(batch, http_status=200, body=body)
    assert results[0].outcome is DeliveryOutcome.REJECTED
    assert results[0].error == "Invalid payload: missing field 'wp_id'"
    assert results[1].outcome is DeliveryOutcome.REJECTED
    assert results[1].error == "alt field name accepted"


def test_event_absent_from_results_maps_pending_not_success() -> None:
    batch = [_event("01JMBY0000000000000000000I"), _event("01JMBY0000000000000000000J")]
    body = _ok_body(("01JMBY0000000000000000000I", "success"))  # second event missing
    results = map_batch_response(batch, http_status=200, body=body)
    assert results[0].outcome is DeliveryOutcome.SUCCESS
    assert results[1].outcome is DeliveryOutcome.PENDING


def test_explicit_pending_status_maps_pending() -> None:
    batch = [_event("01JMBY0000000000000000000K")]
    body = _ok_body(("01JMBY0000000000000000000K", "pending"))
    results = map_batch_response(batch, http_status=200, body=body)
    assert results[0].outcome is DeliveryOutcome.PENDING


@pytest.mark.parametrize("status_code", [401, 403, 500, 503])
def test_batch_level_failure_maps_transient_for_every_event(status_code: int) -> None:
    batch = [_event("01JMBY0000000000000000000L"), _event("01JMBY0000000000000000000M")]
    results = map_batch_response(batch, http_status=status_code, body={"error": "boom"})
    assert all(r.outcome is DeliveryOutcome.TRANSIENT for r in results)
    # Transient carries the batch http status but is NOT a per-event content reject.
    assert all(r.http_status == status_code for r in results)


def test_oversized_413_maps_terminal_failed() -> None:
    batch = [_event("01JMBY0000000000000000000N")]
    results = map_batch_response(batch, http_status=413, body={"error": "payload too large"})
    assert results[0].outcome is DeliveryOutcome.TERMINAL_FAILED


def test_multi_event_413_maps_transient_not_terminal_failed() -> None:
    batch = [
        _event("01JMBY0000000000000000000W"),
        _event("01JMBY0000000000000000000X"),
    ]
    results = map_batch_response(batch, http_status=413, body={"error": "payload too large"})
    assert [result.outcome for result in results] == [
        DeliveryOutcome.TRANSIENT,
        DeliveryOutcome.TRANSIENT,
    ]


def test_http_400_maps_per_event_rejected_with_details() -> None:
    batch = [_event("01JMBY0000000000000000000O")]
    body = {
        "error": "Batch validation failed",
        "details": [
            {"event_id": "01JMBY0000000000000000000O", "error": "missing field wp_id"},
        ],
    }
    results = map_batch_response(batch, http_status=400, body=body)
    assert results[0].outcome is DeliveryOutcome.REJECTED
    assert "missing field" in (results[0].error or "")


def test_transport_timeout_maps_transient_without_poisoning_retries() -> None:
    batch = [_event("01JMBY0000000000000000000P")]
    poster = _FakePoster(raise_exc=requests.Timeout("timed out"))
    teamspace = TeamspaceReceiver(
        resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=poster
    )
    results = list(teamspace.deliver(batch))
    assert results[0].outcome is DeliveryOutcome.TRANSIENT
    assert results[0].http_status is None


def test_empty_batch_returns_empty_results() -> None:
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN)
    stub = StubReceiver()
    assert list(teamspace.deliver([])) == []
    assert list(stub.deliver([])) == []


def test_gate_decision_blocked_is_inverse_of_satisfied() -> None:
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN)
    blocked = evaluate_gates(teamspace, GateContext())
    satisfied = evaluate_gates(StubReceiver(), GateContext())
    assert blocked.blocked is True
    assert satisfied.blocked is False


def test_unknown_per_event_status_maps_rejected() -> None:
    batch = [_event("01JMBY0000000000000000000R")]
    body = {"results": [{"event_id": "01JMBY0000000000000000000R", "status": "weird"}]}
    results = map_batch_response(batch, http_status=200, body=body)
    assert results[0].outcome is DeliveryOutcome.REJECTED
    assert "weird" in (results[0].error or "")


def test_http_400_details_as_json_string_is_parsed() -> None:
    batch = [_event("01JMBY0000000000000000000S")]
    body = {
        "error": "Batch validation failed",
        "details": '[{"event_id": "01JMBY0000000000000000000S", "reason": "bad type"}]',
    }
    results = map_batch_response(batch, http_status=400, body=body)
    assert results[0].outcome is DeliveryOutcome.REJECTED
    assert results[0].error == "bad type"


def test_http_400_unstructured_details_falls_back_to_top_error() -> None:
    batch = [_event("01JMBY0000000000000000000T")]
    # details is a plain string (not a structured list) -> top-level error applies.
    body = {"error": "whole batch rolled back", "details": "not json"}
    results = map_batch_response(batch, http_status=400, body=body)
    assert results[0].outcome is DeliveryOutcome.REJECTED
    assert results[0].error == "whole batch rolled back"


def test_non_json_response_body_maps_transient() -> None:
    batch = [_event("01JMBY0000000000000000000U")]
    poster = _FakePoster(_FakeResponse(200, ValueError("not json")))
    external = ExternalReceiver(endpoint_url="https://ops.example/ingest/", poster=poster)
    results = list(external.deliver(batch))
    assert results[0].outcome is DeliveryOutcome.TRANSIENT


def test_stub_received_events_read_surface() -> None:
    stub = StubReceiver()
    batch = [_event("01JMBY0000000000000000000V")]
    stub.deliver(batch)
    received = stub.received_events()
    assert len(received) == 1
    assert received[0].event_id == "01JMBY0000000000000000000V"


def test_delivery_result_is_transport_agnostic_value() -> None:
    result = DeliveryResult(
        event_id="01JMBY0000000000000000000Q",
        outcome=DeliveryOutcome.SUCCESS,
        http_status=200,
        error=None,
        raw={"event_id": "01JMBY0000000000000000000Q", "status": "success"},
    )
    # The outcome's wire value folds onto the WP05 ledger vocabulary.
    assert result.outcome.value == "success"
