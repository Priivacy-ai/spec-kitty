"""Ordering + drain-completeness proofs for the poison-batch bisection (#2736).

Two non-fakeable properties the merged anchor (:mod:`test_poison_batch_2736`) does
not pin on its own:

* **Straddle ordering (US2 / SC-003).** A ``wp_id`` whose *create* and *status*
  events fall in opposite halves of the naive midpoint cannot be kept together by any
  single midpoint — the create-before-status guarantee is produced *only* by the
  sequential left-before-right recursion. The fixture here has teeth: the culprit sits
  in the create/left half, and the straddling pair is non-adjacent and on opposite
  sides of the cut, so the assertion RE​DS under a parallel / right-before-left bisect
  (not merely under the unfixed single-POST path).

* **Drain completeness + boundedness (FR-004 / NFR-002 / NFR-003).** A full drain over
  a poison-containing backlog must leave *exactly* the culprit residual and re-select
  nothing innocent on a re-drain, within a bounded number of POSTs and with no
  event accepted twice.

The poster is REUSED from :mod:`test_poison_batch_2736` on purpose: its
``accepted_receipts`` records **server-acceptance (200-branch) POST order, never input
order** — input order is always create-before-status by FIFO, which would make the
ordering assertion a tautology and the fixture teeth decorative.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import pytest

from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    ExternalReceiver,
    OutboundEvent,
)

from ._poison_batch_poster import _AllOrNothingBatchPoster

pytestmark = pytest.mark.fast

_ENDPOINT = "https://ops.example/ingest/"
_TARGET_ID = "teamspace-1"
_BATCH_ERROR = "whole-batch rollback: one event failed validation, all rejected"


def _event(event_id: str, *, wp: str, event_type: str) -> OutboundEvent:
    """A realistically-shaped outbound event carrying its ``wp_id`` and role."""
    return OutboundEvent(
        event_id=event_id,
        payload={
            "event_id": event_id,
            "event_type": event_type,
            "payload": {"wp_id": wp, "kind": event_type},
        },
    )


def _create(event_id: str, *, wp: str) -> OutboundEvent:
    return _event(event_id, wp=wp, event_type="WPCreated")


def _status(event_id: str, *, wp: str) -> OutboundEvent:
    return _event(event_id, wp=wp, event_type="WPStatusChanged")


def _receiver(poster: _AllOrNothingBatchPoster) -> ExternalReceiver:
    return ExternalReceiver(endpoint_url=_ENDPOINT, poster=poster)


# -- T006: straddle ordering with teeth ----------------------------------------

# Layout (naive midpoint = 4 -> left [0..3] | right [4..7]):
#   0 A-create   1 S-create   2 CULPRIT   3 B-create
#   4 C-create   5 S-status   6 D-create  7 E-status
# WP-S's create (idx1, left) and status (idx5, right) are non-adjacent and on
# opposite sides of the cut; the culprit sits in the create/left half.
_A_CREATE = "01JMBY000000000000000A0001"
_S_CREATE = "01JMBY000000000000000S0001"
_CULPRIT = "01JMBY0000000000000CULPRIT"
_B_CREATE = "01JMBY000000000000000B0001"
_C_CREATE = "01JMBY000000000000000C0001"
_S_STATUS = "01JMBY000000000000000S0002"
_D_CREATE = "01JMBY000000000000000D0001"
_E_STATUS = "01JMBY000000000000000E0002"


def _straddle_batch() -> list[OutboundEvent]:
    return [
        _create(_A_CREATE, wp="WP-A"),
        _create(_S_CREATE, wp="WP-S"),
        _create(_CULPRIT, wp="WP-X"),
        _create(_B_CREATE, wp="WP-B"),
        _create(_C_CREATE, wp="WP-C"),
        _status(_S_STATUS, wp="WP-S"),
        _create(_D_CREATE, wp="WP-D"),
        _status(_E_STATUS, wp="WP-E"),
    ]


def test_straddling_create_receipts_before_its_status() -> None:
    """A batch-spanning create/status pair keeps create-before-status receipt order.

    Guaranteed only by the sequential left-before-right recursion: the create sits in
    the left half (delivered first), the status in the right half (delivered second).
    A parallel or right-before-left bisect would receipt the status first, inverting
    the index — exactly the SC-003 failure this pins.
    """
    poster = _AllOrNothingBatchPoster(
        invalid_event_ids=[_CULPRIT], batch_error=_BATCH_ERROR
    )
    results = {r.event_id: r for r in _receiver(poster).deliver(_straddle_batch())}

    # Every innocent delivered; only the culprit rejected.
    assert results[_CULPRIT].outcome is DeliveryOutcome.REJECTED
    innocents = [_A_CREATE, _S_CREATE, _B_CREATE, _C_CREATE, _S_STATUS, _D_CREATE, _E_STATUS]
    for eid in innocents:
        assert results[eid].outcome is DeliveryOutcome.SUCCESS

    # The teeth: create receipts strictly before its cross-half status.
    accepted = poster.accepted_receipts
    assert _S_CREATE in accepted and _S_STATUS in accepted
    assert accepted.index(_S_CREATE) < accepted.index(_S_STATUS), (
        "straddling create/status pair lost create-before-status order — "
        f"accepted receipt order was {accepted}"
    )
    # Culprit isolated to its own size-1 POST.
    assert {_CULPRIT} in poster.singleton_posts()


# -- T007: drain-harness residual set + NFR-002 / NFR-003 ----------------------

_INN_1 = "01JMBY00000000000000INN001"
_INN_2 = "01JMBY00000000000000INN002"
_INN_3 = "01JMBY00000000000000INN003"
_DRAIN_CULPRIT = "01JMBY0000000000000DRAINBAD"


def _drain_backlog() -> list[OutboundEvent]:
    # >=2 innocents so the residual-set equality is non-trivial; culprit interleaved.
    return [
        _create(_INN_1, wp="WP-1"),
        _create(_INN_2, wp="WP-2"),
        _create(_DRAIN_CULPRIT, wp="WP-X"),
        _create(_INN_3, wp="WP-3"),
    ]


def _record_all(ledger: SqliteDeliveryLedger, results: Any) -> None:
    for r in results:
        # Pass the DeliveryOutcome enum (r.outcome), NEVER the DeliveryResult object:
        # record_result raises ValueError on the object's unknown token (ledger.py).
        ledger.record_result(event_id=r.event_id, target_id=_TARGET_ID, result=r.outcome)


def test_drain_leaves_exactly_the_culprit_and_re_drain_does_not_re_poison() -> None:
    backlog = _drain_backlog()
    universe = [e.event_id for e in backlog]
    poster = _AllOrNothingBatchPoster(
        invalid_event_ids=[_DRAIN_CULPRIT], batch_error=_BATCH_ERROR
    )
    external = _receiver(poster)
    ledger = SqliteDeliveryLedger()

    _record_all(ledger, external.deliver(backlog))

    # FR-004: residual == just the culprit (innocents are terminal-success, excluded).
    residual = set(ledger.select_undelivered(target_id=_TARGET_ID, event_universe=universe))
    assert residual == {_DRAIN_CULPRIT}

    # Re-drain only the residual; innocents must NOT be re-selected (no re-poison).
    redrain = [e for e in backlog if e.event_id in residual]
    _record_all(ledger, external.deliver(redrain))
    still = set(ledger.select_undelivered(target_id=_TARGET_ID, event_universe=universe))
    assert still == {_DRAIN_CULPRIT}

    # NFR-002 (single culprit): bounded POST count + singleton termination.
    n = len(backlog)
    bound = 2 * math.ceil(math.log2(n)) + 1
    single_culprit_posts = poster.receipt_log[: _first_redrain_index(poster, redrain)]
    assert len(single_culprit_posts) <= bound
    _assert_no_singleton_reposted(poster)

    # NFR-003: no event accepted (delivered) twice.
    assert len(poster.accepted_receipts) == len(set(poster.accepted_receipts))

    ledger.close()


def _first_redrain_index(poster: _AllOrNothingBatchPoster, redrain: list[OutboundEvent]) -> int:
    """Index of the first POST belonging to the re-drain pass (the lone culprit POST)."""
    redrain_ids = {e.event_id for e in redrain}
    for index in range(len(poster.receipt_log) - 1, -1, -1):
        if set(poster.receipt_log[index]) != redrain_ids:
            return index + 1
    return 0


def _assert_no_singleton_reposted(poster: _AllOrNothingBatchPoster) -> None:
    singletons = poster.singleton_post_tuples()
    # The lone culprit is re-POSTed once on the re-drain; drop that intentional repeat
    # before asserting termination of the *first* drain's bisection.
    culprit_singleton = (_DRAIN_CULPRIT,)
    first_pass = [s for s in singletons if s != culprit_singleton]
    assert len(first_pass) == len(set(first_pass))


def test_all_invalid_batch_is_bounded_and_every_event_isolated() -> None:
    """All-invalid batch: every event ends rejected, within the 2*N-1 POST bound."""
    events = [_create(f"01JMBY0000000000000ALLBAD{i:02d}", wp=f"WP-{i}") for i in range(4)]
    poster = _AllOrNothingBatchPoster(
        invalid_event_ids=[e.event_id for e in events], batch_error=_BATCH_ERROR
    )
    results = _receiver(poster).deliver(events)

    assert all(r.outcome is DeliveryOutcome.REJECTED for r in results)
    n = len(events)
    assert len(poster.receipt_log) <= 2 * n - 1
    for event in events:
        assert {event.event_id} in poster.singleton_posts()
    singletons = poster.singleton_post_tuples()
    assert len(singletons) == len(set(singletons))  # termination: none repeated


def test_reposting_an_already_accepted_event_returns_duplicate() -> None:
    """A cross-pass re-POST of an already-accepted event maps to ``duplicate`` (spec §).

    Pins the idempotency edge: after a first accept the server's memory returns
    ``duplicate``, and the receiver maps it through the shared mapper — so a crash /
    re-drain never double-delivers an innocent.
    """
    backlog = _drain_backlog()
    poster = _AllOrNothingBatchPoster(
        invalid_event_ids=[_DRAIN_CULPRIT], batch_error=_BATCH_ERROR
    )
    external = _receiver(poster)

    external.deliver(backlog)  # first pass: innocents accepted
    repost = list(external.deliver([_create(_INN_1, wp="WP-1")]))

    assert repost[0].outcome is DeliveryOutcome.DUPLICATE


# -- R1: degenerate same-wp_id split must terminate (post-merge HIGH defect) ----
#
# ``create_aware_midpoint`` returns an EDGE index (0 or len) for a degenerate batch
# whose straddling events share a ``wp_id`` — e.g. a 2-element same-``wp_id``
# create/status pair (naive midpoint 1, keys equal, nudge-right would empty the
# right slice, so it snaps to 0). Feeding that raw index back as the split point
# means ``events[:0] == []`` and ``events[0:] == events`` — the right recursion
# never shrinks and ``_bisect_send`` recurses forever (RecursionError), violating
# NFR-002 termination. ``_bisect_send`` must clamp the split so both halves are
# strictly non-empty and smaller; splitting a same-key pair is correct because the
# sequential left-before-right recursion still delivers create before status.

_PAIR_CULPRIT = "01JMBY0000000000000PAIRBAD"
_PAIR_STATUS = "01JMBY0000000000000PAIRSTA"


def _same_wp_poison_pair() -> list[OutboundEvent]:
    # The mission's CENTRAL shape: a 2-element batch whose create + status share one
    # ``wp_id``, so the create-aware midpoint snaps to a degenerate edge index.
    return [
        _create(_PAIR_CULPRIT, wp="WP-X"),
        _status(_PAIR_STATUS, wp="WP-X"),
    ]


def test_same_wp_poison_pair_terminates_and_preserves_create_before_status() -> None:
    """A 2-event same-``wp_id`` poison pair terminates, isolates, and keeps ordering.

    RED before the clamp fix: the degenerate edge midpoint drives ``_bisect_send``
    into unbounded recursion (RecursionError) instead of splitting the pair. GREEN
    after: the forced split isolates the culprit to a singleton, the innocent status
    delivers, and the left-before-right recursion still receipts the (left) create
    POST before the (right) status POST — ordering preserved through the split.
    """
    poster = _AllOrNothingBatchPoster(
        invalid_event_ids=[_PAIR_CULPRIT], batch_error=_BATCH_ERROR
    )
    results = {r.event_id: r for r in _receiver(poster).deliver(_same_wp_poison_pair())}

    # Termination (reaching here means no RecursionError) + isolation.
    assert results[_PAIR_CULPRIT].outcome is DeliveryOutcome.REJECTED
    assert results[_PAIR_STATUS].outcome is DeliveryOutcome.SUCCESS
    assert {_PAIR_CULPRIT} in poster.singleton_posts()

    # Ordering: the same-key pair is split (not kept whole), and the left half
    # (create) is POSTed before the right half (status) — receipt_index(create) <
    # receipt_index(status).
    posts = poster.receipt_log
    assert [_PAIR_CULPRIT] in posts and [_PAIR_STATUS] in posts
    assert posts.index([_PAIR_CULPRIT]) < posts.index([_PAIR_STATUS]), (
        "forced split of the same-wp_id pair lost create-before-status POST order — "
        f"receipt_log was {posts}"
    )


# -- R1: 6-event FIFO funnelling toward the adjacent degenerate pair ------------
#
# Layout (naive midpoint 3 -> left [0..2] | right [3..5]); the culprit's create and
# its own status are ADJACENT and share ``wp_id`` (WP-X). The create-aware snap
# funnels the recursion down onto that degenerate 2-element same-wp_id pair, which
# is exactly where the unclamped split loops forever.
_SIX_A_CREATE = "01JMBY000000000000006A0001"
_SIX_B_CREATE = "01JMBY000000000000006B0001"
_SIX_CULPRIT = "01JMBY00000000000006CULPRT"
_SIX_X_STATUS = "01JMBY000000000000006X0002"
_SIX_C_CREATE = "01JMBY000000000000006C0001"
_SIX_D_STATUS = "01JMBY000000000000006D0002"

_SIX_INNOCENTS = (_SIX_A_CREATE, _SIX_B_CREATE, _SIX_X_STATUS, _SIX_C_CREATE, _SIX_D_STATUS)


def _adjacent_degenerate_backlog() -> list[OutboundEvent]:
    return [
        _create(_SIX_A_CREATE, wp="WP-A"),
        _create(_SIX_B_CREATE, wp="WP-B"),
        _create(_SIX_CULPRIT, wp="WP-X"),
        _status(_SIX_X_STATUS, wp="WP-X"),
        _create(_SIX_C_CREATE, wp="WP-C"),
        _status(_SIX_D_STATUS, wp="WP-D"),
    ]


def test_adjacent_same_wp_pair_funnel_terminates_and_isolates_culprit() -> None:
    """A 6-event FIFO whose culprit create+status are an adjacent same-``wp_id`` pair.

    The create-aware snap funnels the recursion onto the degenerate 2-element pair.
    RED before the clamp: RecursionError once the recursion reaches that pair. GREEN
    after: the drain terminates, isolates the culprit to a singleton, and delivers
    every innocent.
    """
    poster = _AllOrNothingBatchPoster(
        invalid_event_ids=[_SIX_CULPRIT], batch_error=_BATCH_ERROR
    )
    results = {r.event_id: r for r in _receiver(poster).deliver(_adjacent_degenerate_backlog())}

    assert results[_SIX_CULPRIT].outcome is DeliveryOutcome.REJECTED
    assert {_SIX_CULPRIT} in poster.singleton_posts()
    for eid in _SIX_INNOCENTS:
        assert results[eid].outcome is DeliveryOutcome.SUCCESS, f"innocent {eid} not delivered"


def test_transport_failure_is_not_bisected() -> None:
    """A transport failure (status None) maps the whole batch transient, never splits."""

    def _boom(url: str, *, data: bytes, headers: Mapping[str, str], timeout: float) -> Any:
        import requests

        raise requests.ConnectionError("connection reset")

    external = ExternalReceiver(endpoint_url=_ENDPOINT, poster=_boom)
    results = list(external.deliver(_drain_backlog()))

    assert [r.outcome for r in results] == [DeliveryOutcome.TRANSIENT] * len(results)
    assert all(r.http_status is None for r in results)
