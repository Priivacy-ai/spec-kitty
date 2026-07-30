"""FR-016/FR-017 purge across the journal and the delivery ledger (#3030 T022).

The incident left 1,322 rows of six projects' payloads on disk with no remediation
path: ``sync gc`` only reclaims payloads delivered to *every* known target, so it
cannot clear retained rejected or never-delivered rows. This is the primitive the
operator's purge stands on.

What these tests hold to:

* **Dry-run is the default**, at the primitive — not only in a future CLI. A
  destructive operation over confidential text has to be inspectable first, and
  the dry run must earn its "nothing changed" claim by re-reading the stores.
* **NFR-006 is a differential, not a "target is gone" check.** Every assertion
  below measures the *other* projects' rows too, in both stores. "100% of X, 0% of
  anything else" is unfalsifiable if you only count X.
* **Identity-less rows are their own population.** ``project_uuid IS NULL`` rows
  cannot be matched by uuid, are permanently undeliverable, and are what FR-011's
  counter surfaces. A uuid purge must not touch them, and they must not be
  unpurgeable in silence.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from specify_cli.delivery.ledger import (
    STATUS_REJECTED,
    STATUS_SUCCESS,
    SqliteDeliveryLedger,
)
from specify_cli.delivery.retention import (
    purge_identity_less_events,
    purge_project_events,
)
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event

pytestmark = pytest.mark.fast

_TARGET_A = "aaaaaaaa-0000-0000-0000-00000000000a"
_OTHER_B = "bbbbbbbb-0000-0000-0000-00000000000b"
_TARGET_ID = "tgt_teamspace"


def _event(event_id: str, project_uuid: str | None, index: int) -> Event:
    payload = {"event_id": event_id, "event_type": "mission.updated"}
    if project_uuid is not None:
        payload["project_uuid"] = project_uuid
    return Event(
        event_id=event_id,
        event_type="mission.updated",
        payload=json.dumps(payload).encode("utf-8"),
        occurred_at="2026-07-29T00:00:00+00:00",
        created_at=f"2026-07-29T00:00:{index:02d}+00:00",
        project_uuid=project_uuid,
    )


@pytest.fixture
def journal(tmp_path: Any) -> EventJournal:
    """Three projects' worth of rows: the target, another project, identity-less.

    Mirrors the incident's real shape — a machine-global store where the operator's
    remediation has to be surgical.
    """
    jrnl = EventJournal(tmp_path / "journal.db")
    jrnl.append(_event("a-1", _TARGET_A, 1))
    jrnl.append(_event("a-2", _TARGET_A, 2))
    jrnl.append(_event("a-3", _TARGET_A, 3))
    jrnl.append(_event("b-1", _OTHER_B, 4))
    jrnl.append(_event("b-2", _OTHER_B, 5))
    jrnl.append(_event("none-1", None, 6))
    return jrnl


@pytest.fixture
def ledger() -> SqliteDeliveryLedger:
    """Delivery history spanning the same three populations."""
    led = SqliteDeliveryLedger(":memory:")
    led.record_success("a-1", _TARGET_ID)          # delivered
    led.record_rejected("a-2", _TARGET_ID, error="nope")  # retained rejection
    # a-3 has no ledger row at all: never attempted.
    led.record_success("b-1", _TARGET_ID)
    led.record_rejected("b-2", _TARGET_ID, error="nope")
    led.record_rejected("none-1", _TARGET_ID, error="nope")
    return led


def _journal_ids(journal: EventJournal) -> set[str]:
    return {event.event_id for event in journal.read_all()}


def _ledger_ids(ledger: SqliteDeliveryLedger) -> set[str]:
    rows = ledger.connection.execute("SELECT event_id FROM delivery_ledger").fetchall()
    return {str(row["event_id"]) for row in rows}


class TestDryRunIsTheDefault:
    def test_purge_without_dry_run_argument_changes_nothing(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        """Omitting the flag must be the safe direction, not the destructive one."""
        result = purge_project_events(_TARGET_A, journal=journal, ledger=ledger)

        assert result.dry_run is True
        assert _journal_ids(journal) == {"a-1", "a-2", "a-3", "b-1", "b-2", "none-1"}
        assert _ledger_ids(ledger) == {"a-1", "a-2", "b-1", "b-2", "none-1"}

    def test_dry_run_reports_exactly_what_a_real_run_would_remove(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        preview = purge_project_events(_TARGET_A, journal=journal, ledger=ledger)

        assert set(preview.purged_event_ids) == {"a-1", "a-2", "a-3"}
        assert preview.target_before == 3
        assert preview.target_after == 3, "a dry run must not shrink the target"
        assert preview.is_exact is True

        # The preview must state the ledger half as a would-remove count.
        # ``ledger_rows_removed`` is 0 on a dry run by construction, so a preview
        # that only carried that number would say nothing about the ledger.
        assert preview.ledger_rows_removed == 0
        assert preview.ledger_rows_selected == 2

        real = purge_project_events(
            _TARGET_A, journal=journal, ledger=ledger, dry_run=False
        )
        assert set(real.purged_event_ids) == set(preview.purged_event_ids)
        assert real.ledger_rows_removed == preview.ledger_rows_selected

    def test_dry_run_reports_the_forensic_state_breakdown_before_deletion(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        """Ledger rows are removed, so the record has to be produced *first*.

        Per-state counts are the forensic answer to "what happened to this
        project's events" — 1 delivered, 1 rejected, 1 never attempted here. The
        dry run is where the operator captures it.
        """
        preview = purge_project_events(_TARGET_A, journal=journal, ledger=ledger)

        assert preview.ledger_status_before.get(STATUS_SUCCESS) == 1
        assert preview.ledger_status_before.get(STATUS_REJECTED) == 1
        assert preview.never_attempted == 1, "a-3 has no ledger row"


class TestExactness:
    def test_purge_removes_all_of_the_target_and_nothing_else(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        result = purge_project_events(
            _TARGET_A, journal=journal, ledger=ledger, dry_run=False
        )

        assert _journal_ids(journal) == {"b-1", "b-2", "none-1"}
        assert result.target_after == 0
        assert result.other_project_journal_differential == 0, (
            "NFR-006: no other project's journal rows may change"
        )
        assert result.other_ledger_differential == 0, (
            "NFR-006: no other project's ledger rows may change"
        )
        assert result.is_exact is True

    def test_the_other_projects_ledger_history_survives(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        purge_project_events(_TARGET_A, journal=journal, ledger=ledger, dry_run=False)

        assert _ledger_ids(ledger) == {"b-1", "b-2", "none-1"}

    def test_the_target_projects_ledger_history_is_removed(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        """WP08's open research decision 2, answered: removed, not retained.

        A ledger row outliving its journal row is an orphan keyed to an event that
        no longer exists — permanently unresolvable, and still carrying
        ``last_error`` / ``last_response_json`` text that can name the very project
        the operator just purged. Reporting "100% of X removed" while keeping that
        would be the same false attestation the body-queue store was omitted from.
        """
        result = purge_project_events(
            _TARGET_A, journal=journal, ledger=ledger, dry_run=False
        )

        assert result.ledger_rows_removed == 2  # a-1 delivered, a-2 rejected
        assert {"a-1", "a-2"} & _ledger_ids(ledger) == set()

    def test_purging_an_absent_project_is_a_no_op_not_an_error(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        result = purge_project_events(
            "cccccccc-0000-0000-0000-00000000000c",
            journal=journal,
            ledger=ledger,
            dry_run=False,
        )

        assert result.purged_event_ids == ()
        assert result.other_project_journal_differential == 0
        assert len(_journal_ids(journal)) == 6

    def test_a_blank_selector_removes_nothing(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        """A blank uuid must never degrade into "match everything"."""
        result = purge_project_events("", journal=journal, ledger=ledger, dry_run=False)

        assert result.purged_event_ids == ()
        assert len(_journal_ids(journal)) == 6
        assert len(_ledger_ids(ledger)) == 5


class TestIdentityLessRows:
    def test_a_project_purge_never_touches_identity_less_rows(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        """They cannot be attributed to a project, so no project may delete them."""
        purge_project_events(_TARGET_A, journal=journal, ledger=ledger, dry_run=False)

        assert "none-1" in _journal_ids(journal)
        assert "none-1" in _ledger_ids(ledger)

    def test_identity_less_rows_are_visible_in_the_census(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        """Counted, so "unpurgeable by uuid" is never "invisible"."""
        result = purge_project_events(_TARGET_A, journal=journal, ledger=ledger)

        assert result.journal_before.get("") == 1

    def test_identity_less_rows_have_their_own_selector(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        """FR-011's counter surfaces them; this is the operator's only remedy."""
        preview = purge_identity_less_events(journal=journal, ledger=ledger)
        assert preview.dry_run is True
        assert set(preview.purged_event_ids) == {"none-1"}
        assert len(_journal_ids(journal)) == 6

        result = purge_identity_less_events(
            journal=journal, ledger=ledger, dry_run=False
        )

        assert set(result.purged_event_ids) == {"none-1"}
        assert _journal_ids(journal) == {"a-1", "a-2", "a-3", "b-1", "b-2"}
        assert _ledger_ids(ledger) == {"a-1", "a-2", "b-1", "b-2"}
        assert result.other_project_journal_differential == 0


class TestUndeliveredOnlyScope:
    """The scope `sync opt-out` uses — see C-002 and the routing re-point."""

    def test_undelivered_only_keeps_delivered_history(
        self, journal: EventJournal, ledger: SqliteDeliveryLedger
    ) -> None:
        """Opt-out claims to remove *queued* events, so it must remove only those.

        C-002 reserves wholesale deletion for FR-016/FR-017 as the operator's
        explicit act. A routing toggle must not destroy the record of what already
        left the machine — that record is the incident's own evidence.
        """
        result = purge_project_events(
            _TARGET_A,
            journal=journal,
            ledger=ledger,
            dry_run=False,
            undelivered_only=True,
        )

        # a-1 was delivered (terminal success) -> retained. a-2 (rejected) and a-3
        # (never attempted) were still queued -> removed.
        assert set(result.purged_event_ids) == {"a-2", "a-3"}
        assert "a-1" in _journal_ids(journal)
        assert "a-1" in _ledger_ids(ledger), "delivery history must survive"
        assert result.other_project_journal_differential == 0
        assert result.other_ledger_differential == 0
        assert result.is_exact is True
