"""RED-FIRST P0 reproduction of the poison-batch delivery defect (#2736).

The server validates an events batch all-or-nothing: one genuinely-invalid event
makes it reject the **whole** batch with HTTP 400 carrying a single top-level
``error`` string and no per-event ``details`` granularity. On the CLI side,
``receivers._map_400`` then fans that batch-level error out to **every** event in
the batch, so a batch of N events where only one is invalid comes back as N
``rejected`` results — the N-1 innocent events never deliver and each inherits a
misleading reason that has nothing to do with them.

This module reproduces that behaviour through the pre-existing receiver delivery
entry point (:meth:`ExternalReceiver.deliver`, the same batch-post path the
Teamspace receiver uses), with a content-aware fake poster standing in for the
all-or-nothing server. No network, deterministic.
"""
from __future__ import annotations

import gzip
import json
from collections.abc import Mapping
from typing import Any

import pytest

from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    ExternalReceiver,
    OutboundEvent,
)

pytestmark = pytest.mark.fast

# The exact misleading reason observed in the field drain (issue #2736): a
# backward lane-rollback error that has nothing to do with the innocent events it
# was fanned onto.
_MISLEADING_BATCH_ERROR = "review-rejection rollback in_progress -> planned requires force=True"

# One genuinely-invalid event; the rest are ordinary, valid events.
_INVALID_EVENT_ID = "01JMBY0000000000000000BAD1"
_INNOCENT_EVENT_IDS = (
    "01JMBY00000000000000000001",
    "01JMBY00000000000000000002",
    "01JMBY00000000000000000003",
)


def _event(event_id: str, *, wp: str = "WP01") -> OutboundEvent:
    """Build a realistically-shaped outbound event (mirrors the WP06 fixtures)."""
    return OutboundEvent(
        event_id=event_id,
        payload={
            "event_id": event_id,
            "event_type": "WPStatusChanged",
            "payload": {"wp_id": wp, "from_lane": "planned", "to_lane": "in_progress"},
        },
    )


class _FakeResponse:
    """Minimal ``requests.Response`` stand-in (same surface as WP06's fixture)."""

    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        return self._body


class _AllOrNothingBatchPoster:
    """Content-aware poster that models the server's whole-batch 400 (#2736).

    Decompresses the posted batch body and inspects which events it carries:

    * if the single invalid event is present, the **whole** batch is rejected with
      HTTP 400 carrying only a top-level ``error`` string (no per-event
      ``details`` granularity) — exactly the all-or-nothing server contract;
    * otherwise every event in the batch is accepted (HTTP 200, ``success``).

    This is what lets a correct (bisecting) delivery path isolate the culprit down
    to a singleton and still deliver every innocent event.
    """

    def __init__(self, *, invalid_event_id: str, batch_error: str) -> None:
        self._invalid_event_id = invalid_event_id
        self._batch_error = batch_error
        self.posted_batches: list[frozenset[str]] = []

    def __call__(
        self, url: str, *, data: bytes, headers: Mapping[str, str], timeout: float
    ) -> _FakeResponse:
        payload = json.loads(gzip.decompress(data).decode("utf-8"))
        ids = [str(event["event_id"]) for event in payload["events"]]
        self.posted_batches.append(frozenset(ids))
        if self._invalid_event_id in ids:
            # Whole-batch 400: top-level error only, no per-event `details`.
            return _FakeResponse(400, {"error": self._batch_error})
        return _FakeResponse(
            200, {"results": [{"event_id": eid, "status": "success"} for eid in ids]}
        )


@pytest.mark.regression
def test_one_invalid_event_does_not_poison_innocent_events() -> None:
    """One invalid event must not reject the innocent events sharing its batch.

    RED-FIRST P0 reproduction of #2736 per ADR 2026-07-17-1
    (docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md).
    Intentionally FAILS until the product bug is fixed — a red mainline is the honest
    signal of this release-blocking P0. Do NOT xfail/skip/quarantine to green; fix the
    product. Tracking issue: #2736.
    """
    innocent = [_event(eid) for eid in _INNOCENT_EVENT_IDS]
    invalid = _event(_INVALID_EVENT_ID)
    # Interleave the invalid event so it genuinely shares a batch with innocents.
    batch = [innocent[0], innocent[1], invalid, innocent[2]]

    poster = _AllOrNothingBatchPoster(
        invalid_event_id=_INVALID_EVENT_ID, batch_error=_MISLEADING_BATCH_ERROR
    )
    external = ExternalReceiver(endpoint_url="https://ops.example/ingest/", poster=poster)

    results = {result.event_id: result for result in external.deliver(batch)}

    # 1) Every innocent (valid) event must still deliver — it is not the culprit.
    for event in innocent:
        result = results[event.event_id]
        assert result.outcome is DeliveryOutcome.SUCCESS, (
            f"innocent event {event.event_id} was poisoned by the batch-level 400 "
            f"and marked {result.outcome.value!r}"
        )
        # 2) ...and it must not inherit the misleading batch-level reason.
        assert result.error != _MISLEADING_BATCH_ERROR, (
            f"innocent event {event.event_id} inherited the misleading batch error"
        )

    # 3) The one genuinely-invalid event is correctly rejected with its own reason.
    invalid_result = results[_INVALID_EVENT_ID]
    assert invalid_result.outcome is DeliveryOutcome.REJECTED
    assert invalid_result.error == _MISLEADING_BATCH_ERROR
