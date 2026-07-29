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
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event

pytestmark = [pytest.mark.fast]

CONSENTED_UUID = "aaaaaaaa-1111-1111-1111-111111111111"
NONCONSENTED_UUID = "bbbbbbbb-2222-2222-2222-222222222222"

BACKLOG = 2_000
CONSENTED = 10


@pytest.fixture(autouse=True)
def _consent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(CONSENTED_UUID, True)
    set_project_consent(NONCONSENTED_UUID, False)


def _event(event_id: str, uuid: str, created_at: str) -> Event:
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=json.dumps({"event_id": event_id, "project_uuid": uuid}).encode(),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=uuid,
    )


def test_sc002_ten_consented_events_ship_behind_a_2000_row_backlog(
    tmp_path: Path,
) -> None:
    """All 10 consented events deliver in ONE drain, oldest-first ordering intact."""
    journal = EventJournal(tmp_path / "journal.db")

    # 2,000 non-consented rows, all strictly OLDER than the consented ones so FIFO
    # ordering puts them first.
    for i in range(BACKLOG):
        journal.append(
            _event(f"evt-blocked-{i:05d}", NONCONSENTED_UUID, f"2026-06-01T00:00:{i % 60:02d}.{i:05d}Z")
        )
    consented_ids = []
    for i in range(CONSENTED):
        event_id = f"evt-consented-{i:02d}"
        consented_ids.append(event_id)
        journal.append(_event(event_id, CONSENTED_UUID, f"2026-07-01T00:00:{i:02d}Z"))

    ledger = SqliteDeliveryLedger(":memory:")
    registry = SqliteDeliveryTargetRegistry(":memory:")
    target = registry.register(
        url="https://hosted.example.com",
        team_slug="team",
        user_email="operator@example.com",
    )
    receiver = StubReceiver()

    summary = dispatch(journal=journal, ledger=ledger, receiver=receiver, target=target)

    delivered = set(receiver.received_event_ids())
    assert set(consented_ids) <= delivered, (
        "every consented event must ship in a single drain; a predicate applied "
        "after the row limit lets the 2,000-row backlog fill the window and starves "
        "the drain permanently (NFR-002)"
    )
    assert summary.selected == CONSENTED, (
        "selection must contain only the consented project's rows — the backlog is "
        f"filtered out of the universe, not merely skipped: selected={summary.selected}"
    )
    assert not any(eid.startswith("evt-blocked-") for eid in delivered), (
        "no non-consented event may ship"
    )


def test_the_backlog_is_left_in_the_journal_undeleted(tmp_path: Path) -> None:
    """C-002: filtering is not deletion. The rows stay for the operator to purge."""
    journal = EventJournal(tmp_path / "journal.db")
    for i in range(50):
        journal.append(
            _event(f"evt-blocked-{i:05d}", NONCONSENTED_UUID, f"2026-06-01T00:00:{i:02d}Z")
        )
    journal.append(_event("evt-consented-0", CONSENTED_UUID, "2026-07-01T00:00:00Z"))

    ledger = SqliteDeliveryLedger(":memory:")
    registry = SqliteDeliveryTargetRegistry(":memory:")
    target = registry.register(
        url="https://hosted.example.com",
        team_slug="team",
        user_email="operator@example.com",
    )
    dispatch(journal=journal, ledger=ledger, receiver=StubReceiver(), target=target)

    assert journal.count() == 51, "non-consented rows must remain in the journal"
