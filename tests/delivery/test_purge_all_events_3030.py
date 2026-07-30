"""FR-017: ``purge all`` must actually be total, and must be hard to reach (#3030).

WP08 already ships two selectors over the journal + delivery ledger:
``purge_project_events`` (one project) and ``purge_identity_less_events``
(``project_uuid IS NULL``). ``--all`` looks like their union, so the first thing
this module does is **measure** whether it is. It is not: three populations belong
to neither selector, one of them created on purpose by a sibling function in the
same module. That measurement is why FR-017 gets its own read of both tables
rather than a loop over the per-project purges — recorded in
``test_the_union_of_the_existing_selectors_is_not_total``.

Totality is asserted by **independent counts** — fresh SQLite connections onto both
files, ``SELECT COUNT(*)`` — never by summing what the purge reported deleting. A
purge that substantiates "everything is gone" from its own arithmetic is the
tautology class a reviewer already rejected on this mission, where both operands
derived from the same read. Here the operands come from different readers: the
purge's own census, and a raw count this module takes itself.

**C-002** — deletion is only ever the operator's explicit act — is what the
confirmation pins are about. Dry run is the default, and the destructive branch
demands a literal phrase no unattended code path produces by accident.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.delivery.ledger import LEDGER_TABLE, SqliteDeliveryLedger
from specify_cli.delivery.retention import (
    PURGE_ALL_CONFIRMATION,
    PurgeNotConfirmedError,
    purge_all_events,
    purge_identity_less_events,
    purge_project_events,
)
from specify_cli.event_journal import Event, EventJournal
from specify_cli.event_journal.models import TABLE_NAME

pytestmark = [pytest.mark.fast]

AT = "2026-07-30T00:00:00+00:00"
UUID_CONSENTED = "aaaaaaaa-0000-0000-0000-00000000000a"
UUID_NEVER = "bbbbbbbb-0000-0000-0000-00000000000b"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)


def _event(event_id: str, project_uuid: str | None, *, archived: str | None = None) -> Event:
    return Event(
        event_id=event_id,
        event_type="WPStatusChanged",
        payload=b'{"payload": "confidential"}',
        occurred_at=AT,
        created_at=AT,
        project_uuid=project_uuid,
        archived_at=archived,
    )


@pytest.fixture
def stores(tmp_path: Path) -> Iterator[tuple[EventJournal, SqliteDeliveryLedger, Path, Path]]:
    """A journal + on-disk ledger seeded with every population FR-017 must reach.

    On disk, not ``:memory:``, precisely so totality can be counted by a *second*
    connection that shares nothing with the purge's own reads.
    """
    journal_path = tmp_path / "journal.db"
    ledger_path = tmp_path / "ledger.db"
    journal = EventJournal(journal_path)
    ledger = SqliteDeliveryLedger(str(ledger_path))

    # 1. a consented project, one row already delivered
    journal.append(_event("E-consented", UUID_CONSENTED))
    ledger.record_success("E-consented", "target-a")
    # 2. a never-consented project, never attempted (no ledger row at all)
    journal.append(_event("E-never", UUID_NEVER))
    # 3. identity-less: project_uuid IS NULL
    journal.append(_event("E-null", None))
    # 4. blank identity: non-NULL empty string — neither selector reaches it
    journal.append(_event("E-blank", ""))
    # 5. whitespace identity: the projection can see it, the purge cannot select it
    journal.append(_event("E-whitespace", "   "))
    # 6. archived: must not be treated as already-gone
    journal.append(_event("E-archived", UUID_CONSENTED, archived=AT))
    # 7. a ledger row whose event has no journal row — see the union test for why
    #    this is not a contrived state
    ledger.record_rejected("E-ghost", "target-a", error="gone")

    try:
        yield journal, ledger, journal_path, ledger_path
    finally:
        ledger.close()


def _raw_counts(journal_path: Path, ledger_path: Path) -> tuple[int, int]:
    """Count both stores over connections this module opens itself.

    The whole point: an independent reader. ``ProjectPurgeResult``'s censuses are
    the purge's own view, and "both stores are empty" must not be a restatement of
    them.
    """
    counts: list[int] = []
    for path, table in ((journal_path, TABLE_NAME), (ledger_path, LEDGER_TABLE)):
        connection = sqlite3.connect(str(path))
        try:
            row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608 — static module-constant identifiers
            counts.append(int(row[0]) if row else 0)
        finally:
            connection.close()
    return counts[0], counts[1]


# --------------------------------------------------------------------------- #
# Q1, measured: the union of the existing selectors is not total               #
# --------------------------------------------------------------------------- #


def test_the_union_of_the_existing_selectors_is_not_total(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
) -> None:
    """Why ``--all`` is its own read and not a loop over the per-project purges.

    Runs the strongest available union — every uuid the journal admits to holding,
    plus the identity-less selector — and shows what survives it. Three populations
    do:

    * ``project_uuid = ''``. ``distinct_project_uuids()`` returns it (it is not
      NULL), but ``read_identity_projection`` drops falsy uuids and
      ``purge_project_events`` blanks a falsy selector to "select nothing", while
      ``iter_rows_missing_identity`` matches ``IS NULL`` only. Neither selector owns
      it.
    * ``project_uuid = '   '``. The projection *can* see it, but
      ``purge_project_events`` strips the selector to ``''`` and then selects
      nothing — so it is visible in the census and unreachable by the purge.
    * a ledger row whose ``event_id`` is absent from the journal. The union only
      ever collects event ids *from the journal*, so nothing in it can reach one.
      Not contrived: ``gc_payloads`` in this same module deletes journal payload
      rows and **deliberately preserves ledger history** (FR-010), so any machine
      that has run ``sync gc`` is in exactly this state.

    If a later change makes the union total, this test fails — and that is the
    signal to reconsider whether ``purge_all_events`` should compose after all.
    """
    journal, ledger, journal_path, ledger_path = stores

    for uuid in list(journal.distinct_project_uuids()):
        purge_project_events(uuid, journal=journal, ledger=ledger, dry_run=False)
    purge_identity_less_events(journal=journal, ledger=ledger, dry_run=False)

    surviving_journal = {event.event_id for event in journal.read_all()}
    surviving_ledger = {
        str(row[0])
        for row in ledger.connection.execute(f"SELECT {'event_id'} FROM {LEDGER_TABLE}")  # noqa: S608 — static identifiers
    }

    assert surviving_journal == {"E-blank", "E-whitespace"}, (
        "the union of the per-project and identity-less selectors left journal rows "
        f"behind: {sorted(surviving_journal)}"
    )
    assert surviving_ledger == {"E-ghost"}, (
        "the union cannot reach a ledger row whose event has no journal row: "
        f"{sorted(surviving_ledger)}"
    )


# --------------------------------------------------------------------------- #
# Q2: totality, by an independent count                                        #
# --------------------------------------------------------------------------- #


def test_purge_all_empties_both_stores(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
) -> None:
    """FR-017: "everything" means both tables hold zero rows afterwards.

    Asserted by ``_raw_counts``, not by the result object, so a purge that
    miscounted its own work cannot report success.
    """
    journal, ledger, journal_path, ledger_path = stores
    assert _raw_counts(journal_path, ledger_path) == (6, 2), "fixture premise"

    purge_all_events(
        journal=journal,
        ledger=ledger,
        dry_run=False,
        confirmation=PURGE_ALL_CONFIRMATION,
    )

    assert _raw_counts(journal_path, ledger_path) == (0, 0), (
        "purge all left rows behind in one of the two stores"
    )


def test_purge_all_reaches_the_populations_the_union_misses(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
) -> None:
    """The three survivors of the union test, named individually.

    A bare "both stores are empty" assertion would still pass if a future refactor
    reintroduced the union *and* the fixture stopped seeding the awkward rows. This
    pins the populations themselves.
    """
    journal, ledger, journal_path, ledger_path = stores

    result = purge_all_events(
        journal=journal,
        ledger=ledger,
        dry_run=False,
        confirmation=PURGE_ALL_CONFIRMATION,
    )

    assert {"E-blank", "E-whitespace", "E-ghost"} <= set(result.purged_event_ids)
    assert "E-archived" in result.purged_event_ids, (
        "an archived row is retained-not-deleted, not already-deleted"
    )


def test_purge_all_reports_totality_consistently_with_the_independent_count(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
) -> None:
    """The result's own arithmetic must agree with the outside count, both ways.

    This is the anti-tautology pin: the two numbers come from different readers, so
    agreement is evidence. ``is_exact`` is the claim; ``_raw_counts`` is the check.
    """
    journal, ledger, journal_path, ledger_path = stores
    journal_before, ledger_before = _raw_counts(journal_path, ledger_path)

    result = purge_all_events(
        journal=journal,
        ledger=ledger,
        dry_run=False,
        confirmation=PURGE_ALL_CONFIRMATION,
    )

    assert result.purged_count == journal_before + 1, (
        "every journal row plus the ledger-only event id should have been selected"
    )
    assert result.ledger_rows_removed == ledger_before
    assert result.target_after == 0
    assert result.other_project_journal_differential == 0
    assert result.other_ledger_differential == 0
    assert result.is_exact


def test_the_journal_census_accounts_for_every_stored_row(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
) -> None:
    """NFR-006's differential is only sound if the census it subtracts is complete.

    ``_journal_census`` builds itself from ``distinct_project_uuids()`` plus the
    project-filtered projection, and the projection drops falsy uuids — so a
    ``project_uuid = ''`` row is counted nowhere and the census silently sums to
    less than the store holds. A population absent from both censuses has a
    differential of zero by construction, which is exactly how a purge could move
    it and still report NFR-006 satisfied.
    """
    from specify_cli.delivery.retention import _journal_census

    journal, _ledger, journal_path, _ledger_path = stores
    census = _journal_census(journal)

    assert sum(census.values()) == journal.count(), (
        f"census {census} sums to {sum(census.values())} but the journal holds "
        f"{journal.count()} rows; the shortfall is invisible to every differential"
    )


# --------------------------------------------------------------------------- #
# Q3: the dry run is the default, and it predicts what the real run does       #
# --------------------------------------------------------------------------- #


def test_dry_run_is_the_default_and_deletes_nothing(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
) -> None:
    """A destructive total wipe must never be what an omitted argument does."""
    journal, ledger, journal_path, ledger_path = stores
    before = _raw_counts(journal_path, ledger_path)

    result = purge_all_events(journal=journal, ledger=ledger)

    assert result.dry_run is True
    assert _raw_counts(journal_path, ledger_path) == before
    assert result.purged_count > 0, "a preview that previews nothing is not a preview"


def test_the_dry_run_predicts_exactly_what_the_real_run_deletes(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
) -> None:
    """A dry run whose numbers differ from the execution is worse than none.

    Both halves are checked: the event-id selection *and* the ledger row count,
    since ``ledger_rows_removed`` is necessarily 0 on a dry run and the preview has
    to carry ``ledger_rows_selected`` instead.
    """
    journal, ledger, journal_path, ledger_path = stores

    preview = purge_all_events(journal=journal, ledger=ledger, dry_run=True)
    executed = purge_all_events(
        journal=journal,
        ledger=ledger,
        dry_run=False,
        confirmation=PURGE_ALL_CONFIRMATION,
    )

    assert set(preview.purged_event_ids) == set(executed.purged_event_ids)
    assert preview.purged_count == executed.purged_count
    assert preview.ledger_rows_selected == executed.ledger_rows_removed, (
        f"the dry run promised {preview.ledger_rows_selected} ledger rows and the "
        f"real run removed {executed.ledger_rows_removed}"
    )


def test_a_confirmed_dry_run_still_deletes_nothing(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
) -> None:
    """Confirmation authorises; it does not trigger. ``dry_run`` alone decides."""
    journal, ledger, journal_path, ledger_path = stores
    before = _raw_counts(journal_path, ledger_path)

    purge_all_events(
        journal=journal,
        ledger=ledger,
        dry_run=True,
        confirmation=PURGE_ALL_CONFIRMATION,
    )

    assert _raw_counts(journal_path, ledger_path) == before


# --------------------------------------------------------------------------- #
# C-002: explicit confirmation, enforced at the store and not only at a CLI     #
# --------------------------------------------------------------------------- #


def test_an_unconfirmed_destructive_run_refuses_loudly(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
) -> None:
    """Raise, never return a zero result.

    A silent no-op is indistinguishable from "there was nothing to purge", which is
    the reporting failure this mission keeps finding. It must also leave both stores
    untouched — a refusal that had already deleted the ledger half would be worse
    than either outcome.
    """
    journal, ledger, journal_path, ledger_path = stores
    before = _raw_counts(journal_path, ledger_path)

    with pytest.raises(PurgeNotConfirmedError):
        purge_all_events(journal=journal, ledger=ledger, dry_run=False)

    assert _raw_counts(journal_path, ledger_path) == before


def test_a_wrong_confirmation_phrase_refuses(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
) -> None:
    """A near-miss is a refusal. ``True``-ish is not the contract; the phrase is.

    Requiring a literal sentence rather than a boolean is the C-002 property: an
    unattended code path can flip a default, but it does not spell a sentence by
    accident.
    """
    journal, ledger, journal_path, ledger_path = stores
    before = _raw_counts(journal_path, ledger_path)

    for attempt in ("yes", "PURGE", PURGE_ALL_CONFIRMATION.upper(), PURGE_ALL_CONFIRMATION + "!"):
        with pytest.raises(PurgeNotConfirmedError):
            purge_all_events(
                journal=journal, ledger=ledger, dry_run=False, confirmation=attempt
            )

    assert _raw_counts(journal_path, ledger_path) == before


# --------------------------------------------------------------------------- #
# Measured, not reasoned: what a failure between the two stores leaves behind   #
# --------------------------------------------------------------------------- #


def test_a_failure_between_the_two_stores_is_not_atomic_and_leaves_the_journal(
    stores: tuple[EventJournal, SqliteDeliveryLedger, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Characterises the crash window. The purge is **two** transactions, not one.

    ``_purge_ledger_rows`` commits inside ``ledger.transaction()`` and
    ``_purge_journal_rows`` then opens its own connection and commits separately, so
    a failure between them cannot roll the first back. Measured rather than argued:
    the ledger delete lands, the journal is untouched.

    That is the *recoverable* direction and it is deliberate (see ``_purge``): a
    journal row without its ledger rows is merely undelivered, whereas a ledger row
    without its journal row is an unresolvable orphan. Re-running the purge converges.
    This test exists so the property is a pinned observation rather than a comment,
    and so that anyone who reorders the two deletes has to confront it.
    """
    journal, ledger, journal_path, ledger_path = stores
    from specify_cli.delivery import retention

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk went away between the two stores")

    monkeypatch.setattr(retention, "_purge_journal_rows", _boom)

    with pytest.raises(OSError, match="disk went away"):
        purge_all_events(
            journal=journal,
            ledger=ledger,
            dry_run=False,
            confirmation=PURGE_ALL_CONFIRMATION,
        )

    journal_rows, ledger_rows = _raw_counts(journal_path, ledger_path)
    assert ledger_rows == 0, "the ledger delete committed before the failure"
    assert journal_rows == 6, "the journal is untouched, so a re-run converges"
