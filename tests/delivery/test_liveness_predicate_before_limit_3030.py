"""T019/SC-002: the predicate runs before the row limit, at real scale (#3030 WP06).

NFR-002's failure mode is starvation, not a leak, and it is easy to ship by
accident: filter *after* the limit and 2,000 non-consented rows ahead of 10
consented ones fill every window forever. ``_should_stop_sync_loop`` breaks on an
empty selection, so the drain would report "nothing to deliver" while the
operator's own events sat behind the backlog indefinitely.

The sibling #3031 pin covers the same ordering with a 10-row backlog. This one uses
SC-002's stated shape — 2,000 older non-consented rows — because the cheap fix for
a small backlog is "loop a few more times", and at 2,000 rows against a 1,000-row
batch limit that stops working. Scale is the assertion.

**The limit has to actually be in play, and for a while it was not (H5-1).** Every
``dispatch`` call here omitted ``limit``, whose default is ``None``, and
``ledger.select_undelivered`` returns the universe unsliced when it is ``None``. So
there was no row limit anywhere in the exercise, and a predicate applied *after* the
limit could not be detected: moving consent filtering to after the ledger call left
this file at 2 passed. The docstring above claimed the opposite, and H5's commit body
cited that greenness as the NFR-002 evidence for keeping no LIMIT in the journal
read — so the recorded argument was weaker than stated. The calls now pass
production's own ``_EVENT_SYNC_DISPATCH_BATCH_LIMIT``, imported rather than copied so
the test follows the real drain if that window ever changes.

Two distinct starvation mechanisms are pinned, because they fail past different
guards:

1. **Excluded rows fill the window** — consent applied after the limit. Caught by
   :func:`test_sc002_ten_consented_events_ship_behind_a_2000_row_backlog`.
2. **Already-delivered rows fill the window** — a ``LIMIT`` (or an equivalent
   Python-side ``rows[:n]`` slice) inside the journal's universe read. The existing
   guard for this is a *text* assertion on the generated SQL
   (``test_nfr003_predicate_cost_3030.py``), which a Python slice would walk
   straight past. Caught behaviourally by
   :func:`test_a_delivered_prefix_must_not_starve_the_undelivered_tail`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.sync import _EVENT_SYNC_DISPATCH_BATCH_LIMIT
from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.interfaces import DeliveryTarget
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
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

CONSENTED_UUID = "aaaaaaaa-1111-1111-1111-111111111111"
NONCONSENTED_UUID = "bbbbbbbb-2222-2222-2222-222222222222"

BACKLOG = 2_000
CONSENTED = 10

#: The window production actually drains through (``_run_dispatch_batches``).
#: Imported, not copied: a test that hard-codes 1000 keeps passing after the real
#: window changes, which is how this file came to exercise no limit at all.
BATCH_LIMIT = _EVENT_SYNC_DISPATCH_BATCH_LIMIT


@pytest.fixture(autouse=True)
def _consent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    consenting = ProjectSyncStore(CONSENTED_UUID)
    blocked = ProjectSyncStore(NONCONSENTED_UUID)
    for store in (consenting, blocked):
        authority = store.layout_generation()
        if authority.read_state().mode is LayoutMode.LEGACY:
            authority.begin_cutover("wp07-liveness-fixture")
            authority.publish_project_only("wp07-liveness-fixture", verify_exact=lambda: True)
    record_project_opt_in(CONSENTED_UUID, actor="wp07-liveness-test")
    record_project_opt_out(NONCONSENTED_UUID, actor="wp07-liveness-test")
    with consenting.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://hosted.example.com', 'operator@example.com', 'team', 1, "
            "'admitted', '1', 'private-teamspace:team')",
            (CONSENTED_UUID,),
        )


def _event(event_id: str, uuid: str, created_at: str) -> Event:
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=json.dumps({"event_id": event_id, "project_uuid": uuid}).encode(),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=uuid,
    )


def _store(uuid: str) -> ProjectSyncStore:
    return ProjectSyncStore(uuid)


def _append(store: ProjectSyncStore, event: Event) -> None:
    with store.unit_of_work() as unit:
        EventJournal(unit, store.layout_generation()).append(event)


def _append_many(store: ProjectSyncStore, events: list[Event]) -> None:
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        for event in events:
            journal.append(event)


def _target(store: ProjectSyncStore) -> DeliveryTarget:
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None
    return target


def test_sc002_ten_consented_events_ship_behind_a_2000_row_backlog(
    tmp_path: Path,
) -> None:
    """All 10 consented events deliver in ONE drain, oldest-first ordering intact.

    The backlog (2,000) deliberately exceeds the batch limit (1,000), which is what
    makes the ordering observable: filter *after* the limit and the window is 1,000
    non-consented rows, all stripped afterwards, leaving an empty selection with the
    operator's 10 events behind it. ``_should_stop_sync_loop`` then breaks on that
    empty selection and reports "nothing to deliver" — permanently.
    """
    consenting_store = _store(CONSENTED_UUID)
    blocked_store = _store(NONCONSENTED_UUID)

    # The retired shared journal put this older backlog in front of the operator's
    # rows.  Project-owned storage now isolates it physically, so the same scale
    # assertion proves it cannot fill the consenting project's dispatch window.
    _append_many(
        blocked_store,
        [_event(f"evt-blocked-{i:05d}", NONCONSENTED_UUID, f"2026-06-01T00:00:{i % 60:02d}.{i:05d}Z") for i in range(BACKLOG)],
    )
    consented_ids = []
    for i in range(CONSENTED):
        event_id = f"evt-consented-{i:02d}"
        consented_ids.append(event_id)
        _append(
            consenting_store,
            _event(event_id, CONSENTED_UUID, f"2026-07-01T00:00:{i:02d}Z"),
        )

    target = _target(consenting_store)
    receiver = StubReceiver()

    assert BACKLOG > BATCH_LIMIT, (
        "precondition: the backlog must exceed the batch window, or the window cannot be filled with excluded rows and this test proves nothing"
    )
    summary = dispatch(
        store=consenting_store,
        receiver=receiver,
        target=target,
        context=consenting_store.create_context(),
        limit=BATCH_LIMIT,
    )

    delivered = set(receiver.received_event_ids())
    assert set(consented_ids) <= delivered, (
        "every consented event must ship in a single drain; a predicate applied "
        "after the row limit lets the 2,000-row backlog fill the window and starves "
        "the drain permanently (NFR-002)"
    )
    assert summary.selected == CONSENTED, (
        f"selection must contain only the consented project's rows — the backlog is filtered out of the universe, not merely skipped: selected={summary.selected}"
    )
    assert not any(eid.startswith("evt-blocked-") for eid in delivered), "no non-consented event may ship"


def test_the_backlog_is_left_in_the_journal_undeleted(tmp_path: Path) -> None:
    """C-002: filtering is not deletion. The rows stay for the operator to purge."""
    consenting_store = _store(CONSENTED_UUID)
    blocked_store = _store(NONCONSENTED_UUID)
    _append_many(
        blocked_store,
        [_event(f"evt-blocked-{i:05d}", NONCONSENTED_UUID, f"2026-06-01T00:00:{i:02d}Z") for i in range(50)],
    )
    _append(
        consenting_store,
        _event("evt-consented-0", CONSENTED_UUID, "2026-07-01T00:00:00Z"),
    )
    dispatch(
        store=consenting_store,
        receiver=StubReceiver(),
        target=_target(consenting_store),
        context=consenting_store.create_context(),
    )

    with blocked_store.unit_of_work() as blocked_unit, consenting_store.unit_of_work() as consenting_unit:
        remaining = EventJournal(blocked_unit, blocked_store.layout_generation()).count()
        remaining += EventJournal(consenting_unit, consenting_store.layout_generation()).count()
    assert remaining == 51, "non-consented rows must remain in the journal"


def test_a_delivered_prefix_must_not_starve_the_undelivered_tail(
    tmp_path: Path,
) -> None:
    """Starvation mechanism 2, pinned behaviourally rather than by reading SQL.

    ``test_nfr003_predicate_cost_3030.py`` asserts the string ``"LIMIT"`` does not
    appear in the generated projection SQL. That catches a pushed-down SQL limit and
    nothing else: an "efficient" rewrite that slices in Python —
    ``rows[:n]`` inside ``read_identity_projection`` — reintroduces exactly the same
    starvation and is invisible to a text assertion.

    The population makes the defect observable without needing to inject it. Every
    row belongs to ONE consenting project, so consent cannot be what excludes
    anything; the first ``limit + 10`` rows are already delivered to this target, and
    the undelivered tail sits behind them.

    * Correct (no limit in the universe read): the ledger receives all rows, strips
      the delivered prefix, and the tail fills the window. The tail ships.
    * Truncated read (SQL LIMIT or a Python slice): the universe is the delivered
      prefix only, the ledger strips every row in it, and the selection is empty —
      the tail never ships, and no amount of looping helps because each pass
      re-reads the same prefix.

    The limit here is small and explicit because the property is *relational* — the
    delivered prefix must exceed the window — not a matter of scale. Using
    production's 1,000 would need 1,010 rows to prove the identical thing.
    """
    limit = 20
    prefix = limit + 10
    tail = 5

    store = _store(CONSENTED_UUID)
    target = _target(store)

    # Oldest rows first, so FIFO ordering puts the delivered prefix at the head of
    # the universe — the position from which it can crowd out the tail.
    for i in range(prefix):
        _append(store, _event(f"evt-old-{i:04d}", CONSENTED_UUID, f"2026-06-01T00:00:{i % 60:02d}.{i:04d}Z"))

    # Drain them for real, so "already delivered" is genuine ledger state rather
    # than hand-written rows.
    first = dispatch(
        store=store,
        receiver=StubReceiver(),
        target=target,
        context=store.create_context(),
        limit=prefix,
    )
    assert first.delivered == prefix, f"precondition: the prefix must actually be delivered, got {first.delivered}"

    tail_ids = [f"evt-new-{i:04d}" for i in range(tail)]
    for i, event_id in enumerate(tail_ids):
        _append(
            store,
            _event(event_id, CONSENTED_UUID, f"2026-07-01T00:00:{i:02d}Z"),
        )

    assert prefix > limit, (
        "precondition: the delivered prefix must exceed the window, or a truncated read would still reach the tail and the test would prove nothing"
    )

    receiver = StubReceiver()
    summary = dispatch(
        store=store,
        receiver=receiver,
        target=target,
        context=store.create_context(),
        limit=limit,
    )

    assert set(receiver.received_event_ids()) == set(tail_ids), (
        "the undelivered tail must ship: the universe read must hand the ledger "
        "every consented row so the delivered prefix is stripped BEFORE the window "
        "is filled. A LIMIT — in SQL or as a Python slice — fills the window with "
        "the delivered prefix instead, and the tail starves forever (NFR-002)"
    )
    assert summary.selected == tail
    assert summary.delivered == tail
