"""Regression guard: the drain filters *per event*, not per process (#3031 Defect 5).

Rescoped from an earlier #3030 framing (see git history / PR #3050 landing
notes): this file's original docstring claimed a ``drain_blocked_reason``
predicate implemented per-project consent. It does not. ``drain_blocked_reason``
is a **capture-time snapshot of machine-global gates**
(``classify_drain_blocked_reason``, ``event_journal/journal.py:338-351`` —
SaaS-enabled flag, checkout-enabled flag, auth state, team resolution). Every
project on the machine that emits at the same moment gets the *same*
classification, because none of those gates are project-scoped. A predicate
that filters on this column therefore implements **no per-project consent
whatsoever** — it can only ever answer "was the whole process/checkout
blocked at capture time", never "did *this* project consent". Per-project
consent (repo-slug-keyed, resolvable per event) is a distinct defect, pinned
separately in ``tests/delivery/test_dispatch_project_consent_3030.py``
(#3030). Do not read a green here as #3030 coverage.

What #3031 Defect 5 actually is (see
``docs/development/read-side-seam-classification.md`` and the sibling
``tests/sync/test_sync_consent_default_deny.py`` docstring, which flags this
exact gap as uncovered): ``event_journal/models.py:113-129`` — the ``Event``
dataclass has no project field. ``SELECT_ALL_SQL`` (``event_journal/models.py:78``)
has no WHERE clause; ``EventJournal.read_all()`` (``event_journal/journal.py:258``)
takes no predicate; ``_select_undelivered`` (``delivery/dispatcher.py:192-223``)
sets ``universe = journal.read_all()`` and never inspects
``Event.drain_blocked_reason`` at all. The column exists — it is populated at
capture time by ``capture_teamspace_bound`` via ``classify_drain_blocked_reason``
— but nothing on the drain side reads it back, so even the coarse, machine-global
signal that DOES exist on the row is silently discarded at drain time.
``sync/batch.py:357`` (``_prepare_events_for_ingress``) actively *strips*
``drain_blocked_reason`` from the legacy queue payload before POSTing, which
confirms the field is understood elsewhere as "must not leave the machine
un-vetted" — the WP07 journal/dispatcher path (the one under test here) has no
equivalent guard at all.

Two tests:

* :func:`test_dispatch_excludes_events_with_recorded_drain_blocked_reason` —
  the direct pin: one blocked event, one unblocked event, single dispatch call.
  Both events are drained in the SAME call (one process tick), so a fix that
  filters per-*process* rather than per-*event* cannot pass this — the
  predicate must inspect ``Event.drain_blocked_reason`` on each row.

* :func:`test_consent_predicate_must_apply_before_limit_not_after` — a guard
  against the shallow fix: filtering blocked rows out of the *already
  limit-truncated* selection. This is expressed through
  ``specify_cli.cli.commands.sync._run_dispatch_batches`` — the actual
  multi-batch drain loop ``sync now`` runs (``sync.py:807-828``), not a single
  ``dispatch(..., limit=...)`` call — because a single call cannot
  distinguish "the predicate lives inside the filtered read" from "the
  predicate runs after ``LIMIT`` but a later loop iteration reaches the
  unblocked event anyway"; the multi-batch loop's own termination condition
  (``batch.selected == 0 or not advanced: break``, ``sync.py:857``) is what a
  post-selection filter actually breaks: a batch of all-blocked rows that get
  filtered out post-``LIMIT`` never posts (no ``delivered``), so
  ``terminal_progress`` is ``False``; since a transparently-filtered row is
  never added to ``retryable_event_ids`` either, ``skip`` never grows, so
  ``advanced`` is ``False`` and the loop exits on that very first batch,
  stranding the unblocked event exactly as the legacy
  ``OfflineQueue.drain_queue`` shape would (``sync/queue.py:1570-1593``:
  ``SELECT event_id, data FROM queue ORDER BY timestamp ASC, id ASC LIMIT ?``
  — no predicate at all), which is the sibling code path this
  journal/dispatcher pair is meant to replace. The per-batch limit
  (``sync.py:459``, normally 1000) is monkeypatched down to 5 purely so a
  10-event blocked backlog is enough to force truncation within one batch —
  the property under test is unchanged by the smaller number. This test also
  asserts the negative: none of the 10 blocked rows may ship either — a fix
  that merely reorders selection (e.g. newest-first) to surface the unblocked
  event while still shipping the blocked backlog must not pass.

Both tests are additive: they do not alter any assertion in
``tests/delivery/test_dispatcher.py``, whose own fixtures never populate
``drain_blocked_reason`` (its ``_make_event`` helper leaves the default
``None`` on every row), so this file's premise cannot collide with any
existing green there.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli.cli.commands import sync as sync_commands
from specify_cli.cli.commands.sync import _run_dispatch_batches
from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.interfaces import DeliveryTarget
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import DRAIN_BLOCKED_SAAS_DISABLED, Event
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

_TARGET_URL = "https://hosted.example.com"
_TARGET_TEAM_SLUG = "team"
_TARGET_USER_EMAIL = "operator@example.com"


_CONSENTED_UUID = "eeeeeeee-0000-0000-0000-00000000000e"


@pytest.fixture(autouse=True)
def _consent_to_the_single_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Consent to this file's one project so drain_blocked_reason is the variable."""
    home = tmp_path / "consent-home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    store = ProjectSyncStore(_CONSENTED_UUID)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover("drain-blocked-test")
        authority.publish_project_only("drain-blocked-test", verify_exact=lambda: True)
    record_project_opt_in(_CONSENTED_UUID, actor="drain-blocked-test")
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, ?, ?, ?, 1, 'admitted', '1', ?)",
            (
                _CONSENTED_UUID,
                _TARGET_URL,
                _TARGET_USER_EMAIL,
                _TARGET_TEAM_SLUG,
                f"private-teamspace:{_TARGET_TEAM_SLUG}",
            ),
        )


def _make_event(
    event_id: str,
    *,
    project_slug: str,
    drain_blocked_reason: str | None,
    created_at: str,
) -> Event:
    """Build a realistic, production-shaped journal event.

    Carries one consented ``project_uuid`` for every event in this file. #3030 WP06
    made the stored identity column the sole authority for selection, so an
    identity-less row is unselectable regardless of its drain_blocked_reason — which
    would make this file's subject unobservable. Holding identity constant and
    consented is what keeps ``drain_blocked_reason`` the only variable, exactly as
    this docstring's next paragraph requires.

    The payload carries the wire envelope's project correlation field
    (``project_slug`` — see ``sync/emitter.py:2038``) for payload-shape
    realism only; this file's pin is about ``Event.drain_blocked_reason``
    (a machine-global, capture-time column), never about ``project_slug`` or
    per-project consent — that's #3030, pinned in the sibling
    ``test_dispatch_project_consent_3030.py``.
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
        project_uuid=_CONSENTED_UUID,
        project_slug=project_slug,
    )


def _store_and_target() -> tuple[ProjectSyncStore, DeliveryTarget]:
    store = ProjectSyncStore(_CONSENTED_UUID)
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None
    return store, target


def test_dispatch_excludes_events_with_recorded_drain_blocked_reason(
    tmp_path: Path,
) -> None:
    """A journal row captured as ``drain_blocked_reason=saas_disabled`` must not ship.

    #3031 Defect 5 (per-event drain filtering) — NOT a #3030 consent pin.
    ``drain_blocked_reason`` is a machine-global gate snapshot (SaaS-enabled /
    checkout-enabled / auth / team resolution), not a per-project decision;
    a fix satisfying this test alone implements no project-scoped consent.

    Previously red because the dispatcher delivered BOTH events:
    ``_select_undelivered`` only excluded rows with a terminal-success or
    terminal-failed *ledger* row for the target (``ledger.select_undelivered``)
    and applied no predicate over ``Event.drain_blocked_reason`` at all, so a
    row the capture layer explicitly classified as not-ready-to-ship was
    drained exactly like any other row. The drain now inspects
    ``Event.drain_blocked_reason`` on each row, so this guard is green.
    """
    del tmp_path
    store, target = _store_and_target()
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
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        journal.append(unblocked)
        journal.append(blocked)
    receiver = StubReceiver()

    dispatch(
        store=store,
        receiver=receiver,
        target=target,
        context=store.create_context(),
    )

    received_ids = set(receiver.received_event_ids())
    assert unblocked.event_id in received_ids, "the unblocked event must still ship — this test is not about breaking healthy drains"
    assert blocked.event_id not in received_ids, (
        f"a journal row captured with drain_blocked_reason={DRAIN_BLOCKED_SAAS_DISABLED!r} "
        "must never reach the receiver; the drain has no predicate over "
        "Event.drain_blocked_reason at all (dispatcher.py:_select_undelivered), "
        "so capture-time consent classification is silently discarded at drain time"
    )

    with store.unit_of_work() as unit:
        blocked_row = SqliteDeliveryLedger(unit, store.layout_generation()).get(blocked.event_id, target.target_id)
    assert blocked_row is None, (
        "a blocked event must not be recorded delivered to the ledger either — "
        "today it is, because dispatch() posted it and _record() wrote a "
        "terminal-success row for it"
    )


def test_consent_predicate_must_apply_before_limit_not_after(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A large blocked backlog must not starve a newer unblocked event.

    #3031 Defect 5 (per-event drain filtering) — NOT a #3030 consent pin. The
    "consenting"/"non-consenting" naming below is legacy from this file's
    original #3030 framing; the only property under test is
    ``Event.drain_blocked_reason`` (machine-global), never per-project
    consent, so it is renamed to blocked/unblocked in this docstring.

    Driven through ``_run_dispatch_batches`` — the loop
    ``specify_cli.cli.commands.sync`` runs for every ``sync now`` invocation
    (``sync.py:807-828``), not a single ``dispatch(..., limit=...)`` call.
    A single call cannot separate "the predicate is missing" from "the
    predicate runs after ``LIMIT`` truncates, but a later loop iteration
    reaches the unblocked event anyway" — both look identical through one
    call. The multi-batch loop's own stop condition
    (``batch.selected == 0 or not advanced: break``, ``sync.py:857``) is what
    actually distinguishes them: a post-``LIMIT`` filter drops the batch to
    zero *delivered* without producing any *retryable* ids either (the rows
    were filtered transparently, not rejected), so neither ``terminal_progress``
    nor ``skip`` growth fires, ``advanced`` is ``False``, and the loop exits
    on the very first batch — stranding the unblocked event exactly like the
    legacy ``OfflineQueue.drain_queue`` shape this journal/dispatcher pair
    replaces (``sync/queue.py:1570-1593``: ``SELECT event_id, data FROM queue
    ORDER BY timestamp ASC, id ASC LIMIT ?`` — no predicate at all).

    Seeds 10 blocked events older than 1 unblocked event. The per-batch limit
    (``sync.py:459``, normally 1000) is monkeypatched down to 5 so the same
    10-event backlog forces truncation within a single batch instead of
    requiring a 1000+-event fixture — the property under test (predicate
    placement relative to ``LIMIT``) is unaffected by the constant's value.
    Previously red: with no predicate over ``drain_blocked_reason`` at all
    (inside or outside the filtered read), the loop simply kept calling
    ``dispatch`` with a growing limit until the whole backlog — blocked and
    unblocked alike — was delivered, so this test used to red on the negative
    assertion below (all 10 blocked ids shipped alongside the unblocked one).
    The drain now filters per event before the limit is applied.

    The negative assertion below (none of the 10 blocked ids ship) closes the
    cheap-green this test previously left open: reversing
    ``_select_undelivered``'s ordering to newest-first would deliver the
    unblocked event first and satisfy the old positive-only assertion while
    still shipping all 10 blocked rows once the batch/limit allowed it — that
    is not a correct fix and must not pass this test.
    """
    monkeypatch.setattr(sync_commands, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 5)

    del tmp_path
    store, target = _store_and_target()
    blocked_ids = [f"evt-client-confidential-{index}" for index in range(10)]
    for index, event_id in enumerate(blocked_ids):
        with store.unit_of_work() as unit:
            EventJournal(unit, store.layout_generation()).append(
                _make_event(
                    event_id,
                    project_slug="client-confidential",
                    drain_blocked_reason=DRAIN_BLOCKED_SAAS_DISABLED,
                    created_at=f"2026-06-29T00:00:{index:02d}+00:00",
                )
            )
    unblocked = _make_event(
        "evt-engagement-assistant-0",
        project_slug="engagement-assistant",
        drain_blocked_reason=None,
        created_at="2026-06-29T00:01:00+00:00",
    )
    with store.unit_of_work() as unit:
        EventJournal(unit, store.layout_generation()).append(unblocked)
    receiver = StubReceiver()
    runtime = SimpleNamespace(store=store, context=store.create_context())

    _run_dispatch_batches(runtime, receiver, target)

    received_ids = set(receiver.received_event_ids())
    assert unblocked.event_id in received_ids, (
        "the one unblocked event must be delivered even behind a 10-event "
        "blocked backlog; today the drain has no drain_blocked_reason "
        "predicate at all, so the batch loop ships the 5 OLDEST rows (all "
        "blocked) in its first pass and only reaches the unblocked event "
        "because it keeps looping — a correct fix must not depend on that "
        "looping behaviour to avoid starving it"
    )
    shipped_blocked_ids = received_ids.intersection(blocked_ids)
    assert not shipped_blocked_ids, (
        "none of the 10 blocked backlog rows may ship, regardless of how the "
        f"unblocked event is surfaced — got {sorted(shipped_blocked_ids)!r} "
        "shipped; a fix that reorders selection (e.g. newest-first) to reach "
        "the unblocked event while still shipping blocked rows once the "
        "batch/limit allows is not a correct per-event drain_blocked_reason "
        "filter and must not pass this test"
    )
