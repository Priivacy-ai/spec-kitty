"""Tests for the UPLOAD stage of ``sync import-history`` — WP-Y5 (#2262).

Provenance hashing, server preflight, and chunked delivery, all exercised with
zero network: a fake ``HttpPoster`` stands in for the preflight endpoint and a
``StubReceiver`` (records + dedups) stands in for the batch endpoint.
"""

from __future__ import annotations

import gzip
import json
from typing import Any

import pytest

from specify_cli.delivery.receivers import DeliveryOutcome, DeliveryResult, StubReceiver
from specify_cli.sync.history_import.upload import (
    PreflightRejected,
    build_provenance_manifest,
    envelope_sha256,
    run_import_upload,
    run_server_preflight,
    upload_envelopes,
)

pytestmark = pytest.mark.fast


def _env(
    event_id: str, event_type: str = "WPStatusChanged"
) -> dict[
    str, Any
]:  # canonical-event-exempt(exception-flow): the TeamSpace wire envelope is not a *Payload model; a raw fixture is the transport's unit-under-test input
    # canonical-event-exempt(exception-flow): minimal wire envelope fed into the upload transport under test
    return {"event_id": event_id, "event_type": event_type, "payload": {"wp_id": "WP01"}}


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


def test_preflight_posts_gzipped_events_to_the_endpoint():
    poster = _fake_poster({"accepted": True, "event_count": 1, "reconciliation": {}})
    run_server_preflight([_env("e0")], server_url="http://host/", auth_token="tok", poster=poster)

    captured = poster.captured  # type: ignore[attr-defined]
    assert captured["url"] == "http://host/api/v1/events/preflight/"
    assert captured["headers"]["Content-Encoding"] == "gzip"
    assert captured["headers"]["Authorization"] == "Bearer tok"
    assert json.loads(gzip.decompress(captured["data"])) == {"events": [_env("e0")]}


def test_preflight_rejection_raises():
    poster = _fake_poster({"accepted": False, "reconciliation": {"reason": "bad shape"}}, status=400)
    with pytest.raises(PreflightRejected, match="bad shape"):
        run_server_preflight([_env("e0")], server_url="http://x", auth_token="t", poster=poster)


def test_preflight_non_json_response_fails_closed():
    poster = _fake_poster(None, status=502, json_raises=True)
    with pytest.raises(PreflightRejected, match="not JSON"):
        run_server_preflight([_env("e0")], server_url="http://x", auth_token="t", poster=poster)


# ── upload (stage 8) ──────────────────────────────────────────────────────────


def test_upload_delivers_all_then_dedups_on_rerun():
    stub = StubReceiver()
    envelopes = [_env(f"e{i}") for i in range(3)]

    first = upload_envelopes(envelopes, receiver=stub)
    assert first.success == 3
    assert first.rejected == 0 and first.ok
    assert set(stub.received_event_ids()) == {"e0", "e1", "e2"}

    # Re-delivering the same event_ids to the same stub maps them to duplicate.
    second = upload_envelopes(envelopes, receiver=stub)
    assert second.duplicate == 3
    assert second.ok


def test_upload_chunks_by_chunk_size():
    class _SpyStub(StubReceiver):
        def __init__(self) -> None:
            super().__init__()
            self.sizes: list[int] = []

        def deliver(self, batch):
            events = list(batch)
            self.sizes.append(len(events))
            return super().deliver(events)

    stub = _SpyStub()
    upload_envelopes([_env(f"e{i}") for i in range(5)], receiver=stub, chunk_size=2)
    assert stub.sizes == [2, 2, 1]


def test_rejected_outcomes_are_tallied():
    class _RejectingReceiver:
        def deliver(self, batch):
            return [DeliveryResult(event_id=e.event_id, outcome=DeliveryOutcome.REJECTED, error="nope") for e in batch]

    report = upload_envelopes([_env("e0")], receiver=_RejectingReceiver())
    assert report.rejected == 1
    assert not report.ok
    assert report.rejected_samples == ["e0: nope"]


# ── run_import_upload: preflight-all-then-upload (fail-closed) ─────────────────


def test_run_import_upload_preflights_then_uploads():
    stub = StubReceiver()
    poster = _fake_poster({"accepted": True, "event_count": 3, "reconciliation": {}})
    report = run_import_upload([_env(f"e{i}") for i in range(3)], receiver=stub, server_url="http://x", auth_token="t", poster=poster)
    assert report.success == 3
    assert set(stub.received_event_ids()) == {"e0", "e1", "e2"}


def test_run_import_upload_uploads_nothing_when_preflight_rejects():
    stub = StubReceiver()
    poster = _fake_poster({"accepted": False, "reconciliation": {}}, status=400)
    with pytest.raises(PreflightRejected):
        run_import_upload([_env("e0")], receiver=stub, server_url="http://x", auth_token="t", poster=poster)
    # Fail-closed: preflight ran before any delivery, so nothing was uploaded.
    assert not stub.received_event_ids()
