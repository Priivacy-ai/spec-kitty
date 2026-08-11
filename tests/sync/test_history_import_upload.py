"""Tests for the UPLOAD stage of ``sync import-history`` — WP-Y5 (#2262).

Provenance hashing, server preflight, and chunked delivery, all exercised with
zero network: a fake ``HttpPoster`` stands in for the preflight endpoint and a
``StubReceiver`` (records + dedups) stands in for the batch endpoint.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests

from specify_cli.core.contract_gate import ContractViolationError
from specify_cli.delivery.interfaces import DeliveryTarget, TargetIdentity
from specify_cli.delivery.receivers import DeliveryOutcome, DeliveryResult, StubReceiver
from specify_cli.delivery.targets import compute_target_id
from specify_cli.sync.consent import allocate_capture_sequence, record_project_opt_in
from specify_cli.sync.history_disclosure import (
    confirm_history_disclosure,
    preview_sealed_history,
)
from specify_cli.sync.history_import.upload import (
    _IMPORT_CHUNK_SIZE,
    _SERVER_MAX_BATCH_SIZE,
    PreflightRejected,
    _chunked,
    build_provenance_manifest,
    envelope_sha256,
    run_import_upload,
    run_server_preflight,
    upload_envelopes,
    validate_import_envelopes,
)
from specify_cli.sync.project_context import AdmissionState
from specify_cli.sync.project_store import ProjectSyncStore

pytestmark = pytest.mark.fast


def _env(
    event_id: str, event_type: str = "WPStatusChanged"
) -> dict[
    str, Any
]:  # canonical-event-exempt(exception-flow): the TeamSpace wire envelope is not a *Payload model; a raw fixture is the transport's unit-under-test input
    # canonical-event-exempt(exception-flow): minimal wire envelope fed into the upload transport under test
    return {
        "event_id": event_id,
        "event_type": event_type,
        "project_uuid": _FIXTURE_PROJECT_UUID,
        "payload": {"wp_id": "WP01"},
    }


#: The project every fixture envelope belongs to. Stamped because the upload
#: stage now refuses an envelope whose project cannot be identified (#3030
#: FR-028, NFR-001): unresolvable identity can never be shown to consent.
_FIXTURE_PROJECT_UUID = "00000000-0000-4000-8000-0000000021ce"
_SERVER = "https://app.spec-kitty.ai"


@pytest.fixture(autouse=True)
def _fixture_project_consents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Grant hosted-sync consent for the fixture project, at the one resolver.

    This file pins chunking, preflight ordering and outcome tallying — not the
    consent decision, which ``tests/sync/test_history_import_consent_3030.py``
    drives through the real chain against a real checkout. Stubbing
    ``consented_project_uuids`` (rather than passing a predicate at 15 call
    sites) keeps that separation while leaving the gate itself live: an envelope
    carrying a *different* project is still refused here.
    """
    import specify_cli.sync.consent as consent_module

    def _grant_the_fixture_project(candidates, *, checkout_roots=None):
        return frozenset(c for c in candidates if c == _FIXTURE_PROJECT_UUID)

    monkeypatch.setattr(consent_module, "consented_project_uuids", _grant_the_fixture_project)


@pytest.fixture
def authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Mint the exact persisted preview/confirmation authority for one cohort."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))

    def _make(envelopes: list[dict[str, Any]]) -> dict[str, object]:
        store = ProjectSyncStore(_FIXTURE_PROJECT_UUID)
        with store.unit_of_work() as unit:
            for envelope in envelopes:
                assignment = allocate_capture_sequence(unit)
                unit.execute(
                    "INSERT INTO journal_entries (entry_id, project_uuid, epoch_id, capture_sequence, payload_json) VALUES (?, ?, ?, ?, ?)",
                    (
                        envelope["event_id"],
                        _FIXTURE_PROJECT_UUID,
                        assignment.epoch_id,
                        assignment.capture_sequence,
                        json.dumps(envelope, sort_keys=True, separators=(",", ":")),
                    ),
                )
        record_project_opt_in(_FIXTURE_PROJECT_UUID, actor="test:history-upload")
        with store.unit_of_work() as unit:
            unit.execute(
                "INSERT INTO project_target_admissions "
                "(project_uuid, target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, admission_state, admission_generation, binding_audience) "
                "VALUES (?, ?, 'account-1', 'teamspace-1', 1, 'admitted', '1', "
                "'private-teamspace:teamspace-1')",
                (_FIXTURE_PROJECT_UUID, _SERVER),
            )
        context = store.create_context()
        capability = confirm_history_disclosure(
            store,
            preview_sealed_history(store),
            actor="test:history-upload",
            idempotency_key="legacy-suite-cohort",
            context=context,
        )
        audience = context.target_audience
        assert audience is not None
        identity = TargetIdentity(
            target_identity=audience.target_identity,
            account_identity=audience.account_identity,
            private_teamspace_id=audience.private_teamspace_id,
            project_uuid=audience.project_uuid,
            configuration_generation=audience.configuration_generation,
        )
        target = DeliveryTarget(
            target_id=compute_target_id(
                target_identity=identity.target_identity,
                account_identity=identity.account_identity,
                private_teamspace_id=identity.private_teamspace_id,
                project_uuid=identity.project_uuid,
                configuration_generation=identity.configuration_generation,
            ),
            identity=identity,
            admission_state=AdmissionState.ADMITTED,
            admission_generation=1,
            binding_audience="private-teamspace:teamspace-1",
            last_error_category=None,
        )
        return {
            "project_context": context,
            "target": target,
            "history_capability": capability,
        }

    return _make


# ── fake poster (preflight transport) ─────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any, *, json_raises: bool = False) -> None:
        self.status_code = status_code
        self._payload = payload
        self._json_raises = json_raises

    def json(self) -> Any:
        if self._json_raises:
            raise ValueError("not JSON")
        return self._payload


def _fake_poster(payload: Any, *, status: int = 200, json_raises: bool = False):
    captured: dict[str, Any] = {}

    def _poster(url: str, *, data: bytes, headers: dict[str, str], timeout: float) -> _FakeResponse:
        captured.update(url=url, data=data, headers=headers, timeout=timeout)
        return _FakeResponse(status, payload, json_raises=json_raises)

    _poster.captured = captured  # type: ignore[attr-defined]
    return _poster


def _accepting_preflight_poster(
    url: str,
    *,
    data: bytes,
    headers: dict[str, str],
    timeout: float,
) -> _FakeResponse:
    del url, headers, timeout
    events = json.loads(data)["events"]
    return _FakeResponse(
        200,
        {"results": [{"event_id": event["event_id"], "status": "success"} for event in events]},
    )


# ── provenance (stage 6) ──────────────────────────────────────────────────────


def test_envelope_sha256_is_canonical_and_deterministic():
    # Key order does not matter (canonical sort_keys), value changes do.
    assert envelope_sha256({"event_id": "a", "b": 1}) == envelope_sha256({"b": 1, "event_id": "a"})
    assert envelope_sha256({"x": 1}) != envelope_sha256({"x": 2})


def test_build_provenance_manifest():
    envelopes = [_env("e1", "MissionCreated"), _env("e2", "WPCreated")]
    manifest = build_provenance_manifest(envelopes)
    assert [p.event_id for p in manifest] == ["e1", "e2"]
    assert [p.event_type for p in manifest] == ["MissionCreated", "WPCreated"]
    assert all(p.row_sha256 is None for p in manifest)
    assert manifest[0].envelope_sha256 == envelope_sha256(envelopes[0])


# ── preflight (stage 7) ───────────────────────────────────────────────────────


def test_preflight_posts_exact_admission_bound_contract_request(authority):
    envelopes = [_env("e0")]
    transport_authority = authority(envelopes)
    capability = transport_authority["history_capability"]
    poster = _fake_poster({"results": [{"event_id": "e0", "status": "success"}]})
    run_server_preflight(
        envelopes,
        server_url=_SERVER,
        auth_token="tok",
        poster=poster,
        **transport_authority,
    )

    captured = poster.captured  # type: ignore[attr-defined]
    assert captured["url"] == f"{_SERVER}/api/v1/events/preflight/"
    assert "Content-Encoding" not in captured["headers"]
    assert captured["headers"]["Authorization"] == "Bearer tok"
    assert captured["headers"]["X-Spec-Kitty-Sync-Protocol"] == "2.0"
    assert json.loads(captured["data"]) == {
        "history_action_id": capability.action_id,
        "preview_hash": capability.preview_hash,
        "events": [
            {
                **_env("e0"),
                "admission_generation": 1,
                "binding_audience": "private-teamspace:teamspace-1",
            }
        ],
    }


def test_preflight_rejection_raises(authority):
    poster = _fake_poster({"error": "bad shape", "results": []}, status=400)
    envelopes = [_env("e0")]
    with pytest.raises(PreflightRejected, match="bad shape"):
        run_server_preflight(
            envelopes,
            server_url=_SERVER,
            auth_token="t",
            poster=poster,
            **authority(envelopes),
        )


def test_preflight_non_json_response_fails_closed(authority):
    poster = _fake_poster(None, status=502, json_raises=True)
    envelopes = [_env("e0")]
    with pytest.raises(PreflightRejected, match="not JSON"):
        run_server_preflight(
            envelopes,
            server_url=_SERVER,
            auth_token="t",
            poster=poster,
            **authority(envelopes),
        )


def test_preflight_transport_error_fails_closed_not_traceback(authority):
    """A transport failure (unreachable host / timeout / TLS reset) during
    preflight maps to a graceful PreflightRejected, not an escaping traceback
    (#2884). The delivery path already catches this; preflight now matches."""

    def _raising_poster(url: str, *, data: bytes, headers: dict[str, str], timeout: float):
        raise requests.ConnectionError("host unreachable")

    envelopes = [_env("e0")]
    with pytest.raises(PreflightRejected, match="transport failed"):
        run_server_preflight(
            envelopes,
            server_url=_SERVER,
            auth_token="t",
            poster=_raising_poster,
            **authority(envelopes),
        )


# ── upload (stage 8) ──────────────────────────────────────────────────────────


def test_upload_delivers_all_then_projects_terminal_attempt_rerun(authority):
    stub = StubReceiver(endpoint_url=_SERVER)
    envelopes = [_env(f"e{i}") for i in range(3)]
    transport_authority = authority(envelopes)

    first = upload_envelopes(envelopes, receiver=stub, **transport_authority)
    assert first.success == 3
    assert first.rejected == 0 and first.ok
    assert set(stub.received_event_ids()) == {"e0", "e1", "e2"}

    # The canonical typed terminal projection returns the exact prior outcome
    # without manufacturing a fresh request, nonce, or server call.
    second = upload_envelopes(envelopes, receiver=stub, **transport_authority)
    assert second.success == 3
    assert second.ok
    assert set(stub.received_event_ids()) == {"e0", "e1", "e2"}


def test_upload_chunks_by_chunk_size(authority):
    class _SpyStub(StubReceiver):
        def __init__(self, *, endpoint_url: str) -> None:
            super().__init__(endpoint_url=endpoint_url)
            self.sizes: list[int] = []

        def deliver(self, batch):
            self.sizes.append(len(list(batch)))
            return super().deliver(batch)

    envelopes = [_env(f"e{i}") for i in range(5)]
    stub = _SpyStub(endpoint_url=_SERVER)
    upload_envelopes(
        envelopes,
        receiver=stub,
        chunk_size=2,
        **authority(envelopes),
    )
    assert stub.sizes == [2, 2, 1]


def test_rejected_outcomes_are_tallied(authority):
    class _RejectingReceiver:
        endpoint_url = _SERVER

        def deliver(self, batch):
            return [DeliveryResult(event_id=e.event_id, outcome=DeliveryOutcome.REJECTED, error="nope") for e in batch]

    envelopes = [_env("e0")]
    report = upload_envelopes(
        envelopes,
        receiver=_RejectingReceiver(),
        **authority(envelopes),
    )
    assert report.rejected == 1
    assert not report.ok
    assert report.rejected_samples == ["e0: nope"]


# ── mission-atomic chunking (B2, #2884) ───────────────────────────────────────


def _mission_stream(mission: str, size: int) -> list[dict[str, Any]]:
    """A contiguous mission unit: MissionCreated + (size-1) trailing events."""
    # canonical-event-exempt(exception-flow): minimal wire envelopes fed into the chunker under test
    envs: list[dict[str, Any]] = [
        {
            "event_id": f"{mission}-mc",
            "event_type": "MissionCreated",
            "project_uuid": _FIXTURE_PROJECT_UUID,
            "payload": {},
        }
    ]
    # canonical-event-exempt(exception-flow): minimal wire envelopes fed into the chunker under test
    envs += [
        {
            "event_id": f"{mission}-e{i}",
            "event_type": "WPStatusChanged",
            "project_uuid": _FIXTURE_PROJECT_UUID,
            "payload": {},
        }
        for i in range(size - 1)
    ]
    return envs


def test_chunking_never_splits_a_mission():
    """A mission bigger than the budget becomes ONE oversized chunk (never
    split), and every chunk of a prefixed stream starts at a MissionCreated."""
    stream = _mission_stream("a", 4) + _mission_stream("b", 2)
    chunks = list(_chunked(stream, 3))
    assert [len(chunk) for chunk in chunks] == [4, 2]
    assert all(chunk[0]["event_type"] == "MissionCreated" for chunk in chunks)


def test_chunking_packs_whole_missions_at_the_real_budget():
    """At the real _IMPORT_CHUNK_SIZE: missions of 300+200 fill one chunk to
    exactly 500 and the next mission starts the next chunk (501st event never
    bleeds into the full chunk)."""
    stream = _mission_stream("a", 300) + _mission_stream("b", 200) + _mission_stream("c", 1)
    chunks = list(_chunked(stream, _IMPORT_CHUNK_SIZE))
    assert [len(chunk) for chunk in chunks] == [_IMPORT_CHUNK_SIZE, 1]
    assert chunks[1][0]["event_id"] == "c-mc"


def test_single_mission_over_the_budget_is_one_oversized_chunk():
    stream = _mission_stream("big", _IMPORT_CHUNK_SIZE + 1)
    chunks = list(_chunked(stream, _IMPORT_CHUNK_SIZE))
    assert [len(chunk) for chunk in chunks] == [_IMPORT_CHUNK_SIZE + 1]


def test_single_mission_over_the_server_cap_fails_closed_before_delivery(authority):
    """A mission bigger than the server's per-batch cap can't be split
    (mission-atomic) and would be rejected server-side. Catch it locally,
    before any delivery, with an actionable message (#2884, Paula n1)."""
    stub = StubReceiver(endpoint_url=_SERVER)
    stream = _mission_stream("huge", _SERVER_MAX_BATCH_SIZE + 1)
    with pytest.raises(PreflightRejected, match=f"{_SERVER_MAX_BATCH_SIZE}-event batch cap"):
        upload_envelopes(stream, receiver=stub, **authority(stream))
    assert not stub.received_event_ids()  # nothing delivered — fail-closed


# ── transport-transient partial delivery (B1, #2884) ──────────────────────────


class _TransientReceiver:
    """Succeeds every event except ids in *bad*, which map to TRANSIENT (a
    network error with no http_status), recording delivery order."""

    def __init__(self, bad: set[str]) -> None:
        self.bad = bad
        self.seen: list[str] = []

    endpoint_url = _SERVER

    def deliver(self, batch):
        results = []
        for event in batch:
            self.seen.append(event.event_id)
            outcome = DeliveryOutcome.TRANSIENT if event.event_id in self.bad else DeliveryOutcome.SUCCESS
            error = "network error" if event.event_id in self.bad else None
            results.append(DeliveryResult(event_id=event.event_id, outcome=outcome, error=error))
        return results


def test_transport_transient_mid_stream_stops_and_reports_partial(authority):
    """A transport TRANSIENT (network error, not a server rejection) on chunk 2
    of 3 halts delivery and reports partial — the same stop-on-failure contract
    as REJECTED, pinned for the transient path the transport actually raises."""
    receiver = _TransientReceiver(bad={"e1"})
    envelopes = [_env(f"e{i}") for i in range(3)]
    report = upload_envelopes(
        envelopes,
        receiver=receiver,
        chunk_size=1,
        **authority(envelopes),
    )

    assert receiver.seen == ["e0", "e1"]  # e2's chunk never attempted
    assert report.success == 1 and report.rejected == 1
    assert report.partial
    assert report.delivered_through_chunk == 1
    assert report.undelivered_event_count == 1
    assert not report.ok


# ── offline envelope contract gate (M2, #2884) ────────────────────────────────


def _valid_envelope(event_type: str = "MissionCreated") -> dict[str, Any]:
    # canonical-event-exempt(exception-flow): a minimal contract-valid wire envelope for the gate under test
    return {
        "event_id": "e0",
        "event_type": event_type,
        "aggregate_type": "Mission",
        "build_id": "import-history",
        "schema_version": "3.0.0",
        "payload": {},
    }


def test_validate_import_envelopes_passes_a_contract_valid_stream():
    validate_import_envelopes([_valid_envelope("MissionCreated"), _valid_envelope("WPCreated")])


def test_validate_import_envelopes_rejects_a_forbidden_top_level_field():
    """The offline gate refuses a leaked forbidden top-level field before any
    network round-trip — the drift a future edit to the hand-built envelope
    could introduce (#2884)."""
    leaked = _valid_envelope()
    leaked["from_lane"] = "planned"  # a retired status field that belongs in payload
    with pytest.raises(ContractViolationError):
        validate_import_envelopes([leaked])


# ── stop-on-first-failure delivery (B1, #2884) ────────────────────────────────


class _SelectiveReceiver:
    """Succeeds every event except the ids in *bad* (rejected); records order."""

    def __init__(self, bad: set[str]) -> None:
        self.bad = bad
        self.seen: list[str] = []

    endpoint_url = _SERVER

    def deliver(self, batch):
        results = []
        for event in batch:
            self.seen.append(event.event_id)
            if event.event_id in self.bad:
                results.append(DeliveryResult(event_id=event.event_id, outcome=DeliveryOutcome.REJECTED, error="nope"))
            else:
                results.append(DeliveryResult(event_id=event.event_id, outcome=DeliveryOutcome.SUCCESS))
        return results


def test_upload_stops_at_the_first_failed_chunk_and_reports_partial(authority):
    receiver = _SelectiveReceiver(bad={"e1"})
    envelopes = [_env(f"e{i}") for i in range(3)]
    report = upload_envelopes(
        envelopes,
        receiver=receiver,
        chunk_size=1,
        **authority(envelopes),
    )

    # e2's chunk was never attempted after e1's chunk failed.
    assert receiver.seen == ["e0", "e1"]
    assert report.success == 1 and report.rejected == 1
    assert report.partial
    assert report.delivered_through_chunk == 1  # only e0's chunk delivered cleanly
    assert report.undelivered_event_count == 1  # e2
    assert not report.ok


def test_run_import_upload_stops_delivering_after_a_failed_chunk(authority):
    """The --apply path (preflight passes, delivery fails mid-run) stops at the
    failed chunk: the remaining chunks are never handed to the receiver."""
    receiver = _SelectiveReceiver(bad={"e1"})
    poster = _accepting_preflight_poster
    envelopes = [_env(f"e{i}") for i in range(4)]
    report = run_import_upload(
        envelopes,
        receiver=receiver,
        server_url=_SERVER,
        auth_token="t",
        poster=poster,
        chunk_size=1,
        **authority(envelopes),
    )

    assert receiver.seen == ["e0", "e1"]
    assert report.partial and report.undelivered_event_count == 2  # e2, e3 not attempted
    assert report.success == 1 and report.rejected == 1


def test_a_failure_in_the_final_chunk_is_not_partial(authority):
    """Total-attempt-with-failures is a distinct state from partial: nothing
    was left unattempted, so partial stays False (rejected still counts)."""
    receiver = _SelectiveReceiver(bad={"e2"})
    envelopes = [_env(f"e{i}") for i in range(3)]
    report = upload_envelopes(
        envelopes,
        receiver=receiver,
        chunk_size=1,
        **authority(envelopes),
    )

    assert receiver.seen == ["e0", "e1", "e2"]
    assert report.rejected == 1 and not report.partial
    assert report.undelivered_event_count == 0
    assert not report.ok


# ── run_import_upload: preflight-all-then-upload (fail-closed) ─────────────────


def test_run_import_upload_preflights_then_uploads(authority):
    stub = StubReceiver(endpoint_url=_SERVER)
    poster = _accepting_preflight_poster
    envelopes = [_env(f"e{i}") for i in range(3)]
    report = run_import_upload(
        envelopes,
        receiver=stub,
        server_url=_SERVER,
        auth_token="t",
        poster=poster,
        **authority(envelopes),
    )
    assert report.success == 3
    assert set(stub.received_event_ids()) == {"e0", "e1", "e2"}


def test_run_import_upload_uploads_nothing_when_preflight_rejects(authority):
    stub = StubReceiver(endpoint_url=_SERVER)
    poster = _fake_poster({"error": "batch validation failed", "results": []}, status=400)
    envelopes = [_env("e0")]
    with pytest.raises(PreflightRejected):
        run_import_upload(
            envelopes,
            receiver=stub,
            server_url=_SERVER,
            auth_token="t",
            poster=poster,
            **authority(envelopes),
        )
    # Fail-closed: preflight ran before any delivery, so nothing was uploaded.
    assert not stub.received_event_ids()


def test_run_import_upload_rejects_on_a_later_chunk_uploads_nothing(authority):
    """A rejection on the SECOND chunk still uploads nothing — every chunk is
    preflighted before any chunk is delivered (not interleaved)."""
    stub = StubReceiver(endpoint_url=_SERVER)
    calls = {"n": 0}

    def _poster(url, *, data, headers, timeout):
        del url, headers, timeout
        calls["n"] += 1
        accepted = calls["n"] == 1  # chunk 1 accepts, chunk 2 rejects
        event_id = json.loads(data)["events"][0]["event_id"]
        if accepted:
            return _FakeResponse(
                200,
                {"results": [{"event_id": event_id, "status": "success"}]},
            )
        return _FakeResponse(
            400,
            {
                "error": "rejected",
                "details": [
                    {
                        "event_id": event_id,
                        "error_category": "preflight_rejected",
                    }
                ],
            },
        )

    envelopes = [_env("e0"), _env("e1")]
    with pytest.raises(PreflightRejected):
        run_import_upload(
            envelopes,
            receiver=stub,
            server_url=_SERVER,
            auth_token="t",
            poster=_poster,
            chunk_size=1,
            **authority(envelopes),
        )
    assert calls["n"] == 2  # both chunks preflighted...
    assert not stub.received_event_ids()  # ...before any was delivered
