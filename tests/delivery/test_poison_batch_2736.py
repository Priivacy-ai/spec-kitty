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

import pytest

from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    ExternalReceiver,
    OutboundEvent,
)

from ._poison_batch_poster import _AllOrNothingBatchPoster, _FakeResponse

__all__ = ["_AllOrNothingBatchPoster", "_FakeResponse"]

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


def test_one_invalid_event_does_not_poison_innocent_events() -> None:
    """One invalid event must not reject the innocent events sharing its batch.

    Formerly the RED-FIRST P0 reproduction of #2736 (ADR 2026-07-17-1). The receiver
    now bisects a whole-batch 400 down to the singleton culprit, so the innocents
    deliver and only the invalid event is rejected — the marker is removed and this
    guards the fix as a normal regression test.
    """
    innocent = [_event(eid) for eid in _INNOCENT_EVENT_IDS]
    invalid = _event(_INVALID_EVENT_ID)
    # Interleave the invalid event so it genuinely shares a batch with innocents.
    batch = [innocent[0], innocent[1], invalid, innocent[2]]

    poster = _AllOrNothingBatchPoster(
        invalid_event_ids=[_INVALID_EVENT_ID], batch_error=_MISLEADING_BATCH_ERROR
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

    # 4) Isolation is *structural*: the culprit is driven down to a size-1 POST, so
    #    the server only ever saw it alone. Membership in the singleton POSTs (NOT
    #    receipt_log[-1]): the culprit is in the create/left half here, so the
    #    right-half innocents POST after it and its singleton is not chronologically
    #    last. A single-POST (unfixed) path produces no size-1 POST at all.
    assert {_INVALID_EVENT_ID} in poster.singleton_posts(), (
        "culprit was not isolated to its own size-1 POST; "
        f"receipt_log={poster.receipt_log}"
    )
