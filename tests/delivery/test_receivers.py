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
    BATCH_ENDPOINT_PATH,
    DeliveryEffectCertainty,
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
from tests._support.consented_batches import deliverable

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

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

    def __call__(self, url: str, *, data: bytes, headers: Mapping[str, str], timeout: float) -> _FakeResponse:
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
    results = stub.deliver(deliverable(batch))

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
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=poster)
    stub = StubReceiver()

    ts_results = list(teamspace.deliver(deliverable(batch)))
    stub_results = list(stub.deliver(deliverable(batch)))

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
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=poster)
    stub = StubReceiver()

    teamspace.deliver(deliverable(batch))
    stub.deliver(deliverable(batch))
    ts_second = list(teamspace.deliver(deliverable(batch)))
    stub_second = list(stub.deliver(deliverable(batch)))

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
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=poster)
    teamspace.deliver(deliverable(batch))
    call = poster.calls[0]
    assert call["url"] == EXPECTED_BATCH_ENDPOINT
    assert call["headers"]["Authorization"] == f"Bearer {_TOKEN}"
    assert call["headers"]["Content-Encoding"] == "gzip"
    assert call["headers"]["X-Spec-Kitty-Sync-Protocol"] == "2.0"


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
    results = list(external.deliver(deliverable(batch)))
    assert results[0].outcome is DeliveryOutcome.SUCCESS


def test_external_non_batch_shape_maps_transient_not_silent_success() -> None:
    batch = [_event("01JMBY0000000000000000000F")]
    poster = _FakePoster(_FakeResponse(200, {"ok": True}))  # not the batch shape
    external = ExternalReceiver(endpoint_url="https://ops.example/ingest/", poster=poster)
    results = list(external.deliver(deliverable(batch)))
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


def test_event_absent_from_results_maps_transient_not_pending_or_success() -> None:
    batch = [_event("01JMBY0000000000000000000I"), _event("01JMBY0000000000000000000J")]
    body = _ok_body(("01JMBY0000000000000000000I", "success"))  # second event missing
    results = map_batch_response(batch, http_status=200, body=body)
    assert results[0].outcome is DeliveryOutcome.SUCCESS
    assert results[1].outcome is DeliveryOutcome.TRANSIENT
    assert results[1].effect_certainty is DeliveryEffectCertainty.POSSIBLY_EFFECTIVE


def test_explicit_pending_status_maps_pending() -> None:
    batch = [_event("01JMBY0000000000000000000K")]
    body = _ok_body(("01JMBY0000000000000000000K", "pending"))
    results = map_batch_response(batch, http_status=200, body=body)
    assert results[0].outcome is DeliveryOutcome.PENDING


@pytest.mark.parametrize("category_field", ["error_category", "category", "code"])
def test_project_not_admitted_rejection_maps_terminal_refusal(category_field: str) -> None:
    batch = [_event("01JMBY00000000000000000PNA")]
    body = {
        "results": [
            {
                "event_id": "01JMBY00000000000000000PNA",
                "status": "rejected",
                category_field: "project_not_admitted",
                "error": "admission revoked",
            }
        ]
    }
    results = map_batch_response(batch, http_status=200, body=body)
    assert results[0].outcome is DeliveryOutcome.TERMINAL_FAILED
    assert results[0].effect_certainty is DeliveryEffectCertainty.TERMINAL


@pytest.mark.parametrize("status_code", [401, 403, 500, 503])
def test_batch_level_failure_maps_transient_for_every_event(status_code: int) -> None:
    batch = [_event("01JMBY0000000000000000000L"), _event("01JMBY0000000000000000000M")]
    results = map_batch_response(batch, http_status=status_code, body={"error": "boom"})
    assert all(r.outcome is DeliveryOutcome.TRANSIENT for r in results)
    # Transient carries the batch http status but is NOT a per-event content reject.
    assert all(r.http_status == status_code for r in results)


# -- HTTP 412: protocol-version skew (#1553) ------------------------------------
#
# The server's compatibility handshake (spec-kitty-saas ``apps/sync/compatibility.py``)
# answers 412 when the CLI's advertised protocol version is outside the supported
# range. That is ENVIRONMENT skew, not a per-event fault: parking the events would
# strand them in the ledger forever (``TERMINAL_STATUSES`` are never re-selected
# and ``target_id`` does not change on upgrade). The mapper therefore keeps them
# selectable and the dispatch loop halts the pass (tested in test_dispatcher /
# test_sync_routes / test_sync_dispatch_exec).


def test_protocol_mismatch_412_keeps_events_selectable_not_parked() -> None:
    batch = [_event("01JMBY0000000000000000000Q"), _event("01JMBY0000000000000000000R")]
    results = map_batch_response(batch, http_status=412, body={"error": "protocol version mismatch"})
    assert all(r.outcome is DeliveryOutcome.TRANSIENT for r in results)
    assert all(r.effect_certainty is DeliveryEffectCertainty.KNOWN_NO_EFFECT for r in results)
    assert all(r.http_status == 412 for r in results)
    # No server error code -> the CLI's own distinct category, never None.
    assert all(r.error_category == "protocol_mismatch" for r in results)
    # Neutral fallback: the mapper must not assume "upgrade" (a too-NEW client
    # must pin, not upgrade) nor invent a pip command the server never sent.
    assert all(r.error and "412" in r.error for r in results)
    assert not any("pip install" in (r.error or "") for r in results)


def test_protocol_mismatch_412_prefers_server_upgrade_guidance_and_error_code() -> None:
    batch = [_event("01JMBY0000000000000000000S")]
    body = {
        "ok": False,
        "error_code": "client-too-new",
        "error_description": "Client protocol version is above the supported maximum.",
        "sync_protocol": {
            "contract_version": "sync-protocol-handshake.v1",
            "upgrade_guidance": "Pin spec-kitty to a supported release or wait for the SaaS rollout.",
        },
    }
    (result,) = map_batch_response(batch, http_status=412, body=body)
    assert result.outcome is DeliveryOutcome.TRANSIENT
    assert result.error == "Pin spec-kitty to a supported release or wait for the SaaS rollout."
    assert result.error_category == "client-too-new"


def test_protocol_mismatch_412_falls_back_to_error_description() -> None:
    batch = [_event("01JMBY0000000000000000000T")]
    body = {
        "error_code": "client-too-old",
        "error_description": "Client protocol version is below the supported minimum. Run `spec-kitty upgrade` to update.",
        "sync_protocol": {"upgrade_guidance": ""},
    }
    (result,) = map_batch_response(batch, http_status=412, body=body)
    assert result.error == body["error_description"]
    assert result.error_category == "client-too-old"


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
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=poster)
    results = list(teamspace.deliver(deliverable(batch)))
    assert results[0].outcome is DeliveryOutcome.TRANSIENT
    assert results[0].http_status is None


def test_transport_failure_error_carries_underlying_exception_text() -> None:
    """The TRANSIENT result surfaces WHY the transport failed, not a bare constant.

    A connection-refused vs timeout vs DNS failure must be distinguishable on the
    ledger: the mapped ``transient`` error threads the underlying exception text
    through (``transport failure: <exc>``) so operators can diagnose the transport
    without losing the classification.
    """
    batch = [_event("01JMBY0000000000000000000Q")]
    poster = _FakePoster(raise_exc=requests.ConnectionError("boom"))
    external = ExternalReceiver(endpoint_url="https://ops.example/ingest/", poster=poster)
    results = list(external.deliver(deliverable(batch)))
    assert results[0].outcome is DeliveryOutcome.TRANSIENT
    assert results[0].http_status is None
    error = results[0].error or ""
    assert "transport failure" in error
    assert "boom" in error


def test_empty_batch_returns_empty_results() -> None:
    teamspace = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN)
    stub = StubReceiver()
    assert list(teamspace.deliver(deliverable([]))) == []
    assert list(stub.deliver(deliverable([]))) == []


def test_bisect_send_is_self_defending_on_empty_batch() -> None:
    """``_bisect_send([])`` returns ``[]`` directly — never recurses.

    ``deliver()`` already guards the empty case, but the recursive leaf must be
    self-defending. A poison-400 response (whole-batch 400, no details) drives
    the split arm, where the midpoint clamp ``max(1, min(mid, len - 1))`` yields
    ``1`` for ``len == 0`` — splitting ``[]`` into ``[][:1] + [][1:]`` == two more
    empty batches, i.e. an infinite recursion (``RecursionError``) if a future
    caller reached ``_bisect_send([])`` directly. The first-line empty guard
    short-circuits before any POST, so no ``RecursionError`` can occur.
    """
    # A poster that would classify even an empty POST as the #2736 poison
    # signature — the exact response that would otherwise trigger the split arm.
    poison_poster = _FakePoster(_FakeResponse(400, {"error": "batch validation failed"}))
    external = ExternalReceiver(endpoint_url="https://ops.example/ingest/", poster=poison_poster)
    assert external._bisect_send([]) == []
    # The guard returns BEFORE posting: a self-defending leaf never hits the wire.
    assert poison_poster.calls == []


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
    assert results[0].outcome is DeliveryOutcome.TRANSIENT
    assert results[0].effect_certainty is DeliveryEffectCertainty.POSSIBLY_EFFECTIVE
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
    results = list(external.deliver(deliverable(batch)))
    assert results[0].outcome is DeliveryOutcome.TRANSIENT


def test_stub_received_events_read_surface() -> None:
    stub = StubReceiver()
    batch = [_event("01JMBY0000000000000000000V")]
    stub.deliver(deliverable(batch))
    received = stub.received_events()
    assert frozenset(e.event_id for e in received) == frozenset({"01JMBY0000000000000000000V"})


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


# --- WP01 / spec-kitty#3030: cross-project refusal + terminal rejection -------


def _evt(event_id: str, project_uuid: str | None) -> OutboundEvent:
    payload: dict[str, Any] = {"event_id": event_id, "event_type": "WPStatusChanged"}
    if project_uuid is not None:
        payload["project_uuid"] = project_uuid
    return OutboundEvent(event_id=event_id, payload=payload)


def test_batch_spanning_two_projects_is_refused_before_any_post() -> None:
    """FR-004: a multi-project batch must refuse pre-POST and make NO request.

    This is the incident's shape. The drain selected 13,384 events spanning six
    projects and shipped them; nothing between selection and POST looked at
    project identity.
    """
    calls: list[str] = []

    def _never_called(url, *, data, headers, timeout):  # pragma: no cover - must not run
        calls.append(url)
        raise AssertionError("a cross-project batch must never be POSTed")

    receiver = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=_never_called)

    results = receiver.deliver(deliverable([_evt("e1", "aaaaaaaa-0000-0000-0000-000000000001"), _evt("e2", "bbbbbbbb-0000-0000-0000-000000000002")]))

    assert calls == [], "no HTTP request may be made for a cross-project batch"
    # NOT terminal_failed: that status leaves select_undelivered forever, so the
    # net destroyed the consented project's events along with the refusal (#3030
    # H1). The round-trip is pinned in test_cross_project_refusal_state_3030.py.
    assert {r.outcome for r in results} == {DeliveryOutcome.TRANSIENT}
    assert all("more than one project" in (r.error or "") for r in results)
    # The refusal must name the projects so the operator can act on it.
    assert any("aaaaaaaa" in (r.error or "") for r in results)


def test_single_project_batch_still_delivers() -> None:
    """The refusal must not fire on a homogeneous batch (no false positives)."""
    seen: list[str] = []

    def _ok(url, *, data, headers, timeout):
        seen.append(url)
        return _FakeResponse(200, {"results": [{"event_id": "e1", "status": "success"}]})

    receiver = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=_ok)
    results = receiver.deliver(deliverable([_evt("e1", "aaaaaaaa-0000-0000-0000-000000000001")]))

    assert seen == [SERVER_URL + BATCH_ENDPOINT_PATH], "a single-project batch must POST exactly once, to the batch endpoint"
    assert [r.outcome for r in results] == [DeliveryOutcome.SUCCESS]


def test_identity_less_events_do_not_count_as_a_project_at_this_seam() -> None:
    """Identity-less events must not fabricate a second project here.

    An event with no ``project_uuid`` resolves to ``None``. Counting ``None`` as
    a project would refuse ordinary single-project batches that happen to
    contain a legacy identity-less row. Denying unresolvable identity is
    WP06's job at the *selection* seam, where the stored column is the sole
    authority — not the receiver's.

    The ``{None}`` cardinality trap this could invite is handled by NFR-001
    being stated as a subset invariant, not a count.

    The batch is minted with **explicit** attribution (#3030 FR-028) because that
    is the real shape: the legacy row's identity lives in the journal's stored
    ``project_uuid`` column, which C-003 makes the sole selection authority, while
    its envelope carries none. So consent is answered for the project the row
    belongs to, and the refusal — which reads the envelope — still sees one
    project. Attributing ``e2`` from its envelope instead would deny it, which is
    the *mint's* documented behaviour and a different seam from the one under test.
    """
    project = "aaaaaaaa-0000-0000-0000-000000000001"
    seen: list[str] = []

    def _ok(url, *, data, headers, timeout):
        seen.append(url)
        return _FakeResponse(
            200,
            {"results": [{"event_id": "e1", "status": "success"}, {"event_id": "e2", "status": "success"}]},
        )

    receiver = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=_ok)
    results = receiver.deliver(
        deliverable(
            [_evt("e1", project), _evt("e2", None)],
            event_projects={"e1": project, "e2": project},
        )
    )

    assert seen == [SERVER_URL + BATCH_ENDPOINT_PATH], "a single-project batch with a legacy row still delivers, once, to the batch endpoint"
    assert {r.outcome for r in results} == {DeliveryOutcome.SUCCESS}


def test_server_refusal_category_maps_to_terminal_failed() -> None:
    """FR-014 / #3005: a refused project must be TERMINAL, not endlessly retried.

    Today TERMINAL_FAILED is reachable from exactly one predicate (oversized
    single event), so every server refusal became REJECTED -> retried forever
    with no ceiling. That is the '4,141 rejected / 0 terminal failures' signal.
    """

    def _refuse(url, *, data, headers, timeout):
        return _FakeResponse(
            200,
            {
                "results": [
                    {"event_id": "e1", "status": "rejected", "error_category": "project_not_consented", "error": "project has not been admitted to this teamspace"}
                ]
            },
        )

    receiver = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=_refuse)
    results = receiver.deliver(deliverable([_evt("e1", "aaaaaaaa-0000-0000-0000-000000000001")]))

    assert [r.outcome for r in results] == [DeliveryOutcome.TERMINAL_FAILED]


def test_ordinary_rejection_stays_retryable() -> None:
    """A rejection WITHOUT a terminal category must stay REJECTED (retryable)."""

    def _reject(url, *, data, headers, timeout):
        return _FakeResponse(200, {"results": [{"event_id": "e1", "status": "rejected", "error": "schema drift"}]})

    receiver = TeamspaceReceiver(resolved_server_url=SERVER_URL, auth_token=_TOKEN, poster=_reject)
    results = receiver.deliver(deliverable([_evt("e1", "aaaaaaaa-0000-0000-0000-000000000001")]))

    assert [r.outcome for r in results] == [DeliveryOutcome.REJECTED]


@pytest.mark.parametrize("category_field", ["error_category", "category", "code"])
def test_structured_400_project_not_admitted_maps_terminal_refusal(category_field: str) -> None:
    batch = [_event("01JMBY00000000000000000400")]
    results = map_batch_response(
        batch,
        http_status=400,
        body={
            "error": "batch validation failed",
            "details": [
                {
                    "event_id": "01JMBY00000000000000000400",
                    "reason": "project is not admitted",
                    category_field: "project_not_admitted",
                }
            ],
        },
    )

    assert results[0].outcome is DeliveryOutcome.TERMINAL_FAILED
    assert results[0].error_category == "project_not_admitted"
    assert results[0].effect_certainty is DeliveryEffectCertainty.TERMINAL
