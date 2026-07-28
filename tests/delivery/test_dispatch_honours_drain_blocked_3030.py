"""RED pins: the drain must honour the capture-time consent classification (#3030).

Background (see ``docs/development/read-side-seam-classification.md`` sibling
investigation and issue #3030). ``event_journal/models.py:113-129`` — the
``Event`` dataclass has no project field. ``SELECT_ALL_SQL``
(``event_journal/models.py:78``) has no WHERE clause; ``EventJournal.read_all()``
(``event_journal/journal.py:258``) takes no predicate; ``_select_undelivered``
(``delivery/dispatcher.py:192-223``) sets ``universe = journal.read_all()`` and
never inspects ``Event.drain_blocked_reason`` at all. The column exists — it is
populated at capture time by ``capture_teamspace_bound`` via
``classify_drain_blocked_reason`` — but nothing on the drain side reads it back.
``sync/batch.py:357`` (``_prepare_events_for_ingress``) actively *strips*
``drain_blocked_reason`` from the legacy queue payload before POSTing, which
confirms the field is understood elsewhere as "must not leave the machine
un-vetted" — the WP07 journal/dispatcher path (the one under test here) has no
equivalent guard at all.

Two tests:

* :func:`test_dispatch_excludes_events_with_recorded_drain_blocked_reason` —
  the direct pin: one blocked event, one unblocked event, single dispatch call.
  Also closes the #3031 "Defect 5, per-event drain filtering" gap (the sibling
  ``tests/sync/test_sync_consent_default_deny.py`` docstring flags this as
  uncovered): both events are drained in the SAME call (one process tick), so
  a fix that filters per-*process* rather than per-*event* cannot pass this.

* :func:`test_consent_predicate_must_apply_before_limit_not_after` — a guard
  against the shallow fix: filtering blocked rows out of the *already
  limit-truncated* selection. With a 10-event blocked backlog older than the
  one consenting event and ``limit=5``, a post-selection filter starves the
  queue (the whole window is blocked, so the batch goes to zero and the drain
  loop looks "done" while the consenting event never gets a turn). The
  predicate must live inside the filtered read, before ``LIMIT`` truncates —
  mirrors the legacy ``OfflineQueue.drain_queue`` shape
  (``sync/queue.py:1570-1593``: ``SELECT event_id, data FROM queue ORDER BY
  timestamp ASC, id ASC LIMIT ?`` — no predicate at all), which is the sibling
  code path this journal/dispatcher pair is meant to replace.

Both tests are additive: they do not alter any assertion in
``tests/delivery/test_dispatcher.py``, whose own fixtures never populate
``drain_blocked_reason`` (its ``_make_event`` helper leaves the default
``None`` on every row), so this file's premise cannot collide with any
existing green there.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import DRAIN_BLOCKED_SAAS_DISABLED, Event

if TYPE_CHECKING:
    from specify_cli.delivery.interfaces import DeliveryTarget

pytestmark = pytest.mark.fast

_TARGET_URL = "https://hosted.example.com"
_TARGET_TEAM_SLUG = "team"
_TARGET_USER_EMAIL = "operator@example.com"


def _make_event(
    event_id: str,
    *,
    project_slug: str,
    drain_blocked_reason: str | None,
    created_at: str,
) -> Event:
    """Build a realistic, production-shaped journal event.

    The payload mirrors the wire envelope's project correlation field
    (``project_slug`` — see ``sync/emitter.py:2038``), even though today's
    dispatcher never looks inside the payload to make a delivery decision;
    that is the point of the wider #3030 defect.
    """
    payload = json.dumps(
        {
            "event_id": event_id,
            "event_type": "WorkPackageApproved",
            "project_slug": project_slug,
            "drain_blocked_reason": drain_blocked_reason,
        }
    ).encode("utf-8")
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=payload,
        occurred_at=created_at,
        created_at=created_at,
        drain_blocked_reason=drain_blocked_reason,
    )


def _register_target(registry: SqliteDeliveryTargetRegistry) -> DeliveryTarget:
    return registry.register(
        url=_TARGET_URL, team_slug=_TARGET_TEAM_SLUG, user_email=_TARGET_USER_EMAIL
    )


def test_dispatch_excludes_events_with_recorded_drain_blocked_reason(
    tmp_path: Path,
) -> None:
    """A journal row captured as ``drain_blocked_reason=saas_disabled`` must not ship.

    Reds today: the dispatcher delivers BOTH events. ``_select_undelivered``
    only excludes rows with a terminal-success or terminal-failed *ledger*
    row for the target (``ledger.select_undelivered``); it applies no
    predicate over ``Event.drain_blocked_reason`` at all, so a row the capture
    layer explicitly classified as not-ready-to-ship is drained exactly like
    any other row.
    """
    journal = EventJournal(tmp_path / "journal.db")
    unblocked = _make_event(
        "evt-engagement-assistant-0",
        project_slug="engagement-assistant",
        drain_blocked_reason=None,
        created_at="2026-06-29T00:00:00+00:00",
    )
    blocked = _make_event(
        "evt-client-confidential-0",
        project_slug="client-confidential",
        drain_blocked_reason=DRAIN_BLOCKED_SAAS_DISABLED,
        created_at="2026-06-29T00:00:01+00:00",
    )
    journal.append(unblocked)
    journal.append(blocked)

    ledger = SqliteDeliveryLedger(":memory:")
    registry = SqliteDeliveryTargetRegistry(":memory:")
    target = _register_target(registry)
    receiver = StubReceiver()

    dispatch(journal=journal, ledger=ledger, receiver=receiver, target=target)

    received_ids = set(receiver.received_event_ids())
    assert unblocked.event_id in received_ids, (
        "the unblocked event must still ship — this test is not about "
        "breaking healthy drains"
    )
    assert blocked.event_id not in received_ids, (
        f"a journal row captured with drain_blocked_reason={DRAIN_BLOCKED_SAAS_DISABLED!r} "
        "must never reach the receiver; the drain has no predicate over "
        "Event.drain_blocked_reason at all (dispatcher.py:_select_undelivered), "
        "so capture-time consent classification is silently discarded at drain time"
    )

    blocked_row = ledger.get(blocked.event_id, target.target_id)
    assert blocked_row is None, (
        "a blocked event must not be recorded delivered to the ledger either — "
        "today it is, because dispatch() posted it and _record() wrote a "
        "terminal-success row for it"
    )


def test_consent_predicate_must_apply_before_limit_not_after(tmp_path: Path) -> None:
    """A large blocked backlog must not starve a newer consenting event.

    Seeds 10 non-consenting (blocked) events older than 1 consenting
    (unblocked) event, then drains with ``limit=5``. ``ledger.select_undelivered``
    preserves ``event_universe`` order (created_at ASC, from
    ``journal.read_all()``) and slices ``[:limit]`` — so today's unfiltered
    selection returns the 5 OLDEST rows, which are all blocked, and the
    consenting event (created last) is never even selected, let alone
    delivered. This reds for the same root cause as the test above (no
    predicate at all) but demonstrates why the eventual fix must apply the
    consent predicate *inside* the filtered read, before ``LIMIT`` truncates —
    a fix that instead filters the alreadyselected 5-row batch would leave an
    empty batch and make the drain loop look "done" while the consenting event
    is permanently stranded behind the backlog.
    """
    journal = EventJournal(tmp_path / "journal.db")
    for index in range(10):
        journal.append(
            _make_event(
                f"evt-client-confidential-{index}",
                project_slug="client-confidential",
                drain_blocked_reason=DRAIN_BLOCKED_SAAS_DISABLED,
                created_at=f"2026-06-29T00:00:{index:02d}+00:00",
            )
        )
    consenting = _make_event(
        "evt-engagement-assistant-0",
        project_slug="engagement-assistant",
        drain_blocked_reason=None,
        created_at="2026-06-29T00:01:00+00:00",
    )
    journal.append(consenting)

    ledger = SqliteDeliveryLedger(":memory:")
    registry = SqliteDeliveryTargetRegistry(":memory:")
    target = _register_target(registry)
    receiver = StubReceiver()

    dispatch(journal=journal, ledger=ledger, receiver=receiver, target=target, limit=5)

    received_ids = set(receiver.received_event_ids())
    assert consenting.event_id in received_ids, (
        "the one consenting event must be delivered even behind a 10-event "
        "blocked backlog; today the drain has no consent predicate at all, "
        "so it ships the 5 OLDEST rows (all blocked) and never reaches the "
        "consenting event within the requested limit"
    )
