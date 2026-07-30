"""T012/T013: identity columns, indexed, with an idempotent lossless backfill.

FR-006 stores project identity as a derived projection so consent is evaluable in
SQL instead of by decoding every payload (NFR-003). FR-009 backfills the existing
history using T011's chain. NFR-004/SC-007 require the backfill to be idempotent
and lossless; C-002 forbids deleting anything, including rows whose identity stays
unresolvable. T013 counts those so FR-011's denial is observable rather than
silent data loss.

Assertions are on the public seam — append/read/backfill — not on SQL, per WP04's
definition of done. The two exceptions are the index check (an index is not
observable through the API but NFR-003 depends on it) and the raw before/after
snapshot proving C-002.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event, TABLE_NAME
from specify_cli.sync.project_identity import (
    NIL_PROJECT_UUID,
    backfill_journal_identity,
    count_unresolved_identity,
)

pytestmark = [pytest.mark.fast]

UUID_A = "11111111-1111-1111-1111-111111111111"
UUID_B = "22222222-2222-2222-2222-222222222222"


def _event(event_id: str, envelope: dict, *, created: str = "2026-07-01T00:00:00Z") -> Event:
    return Event(
        event_id=event_id,
        event_type="WPStatusChanged",
        payload=json.dumps(envelope).encode(),
        occurred_at=created,
        created_at=created,
    )


def _stored_identity(db_path: Path) -> dict[str, tuple]:
    conn = sqlite3.connect(str(db_path))
    try:
        return {
            row[0]: (row[1], row[2])
            for row in conn.execute(
                f"SELECT event_id, project_uuid, project_slug FROM {TABLE_NAME}"
            )
        }
    finally:
        conn.close()


# --- T012: the columns are written and read through the seam ---------------


def test_event_round_trips_project_identity(tmp_path: Path) -> None:
    journal = EventJournal(tmp_path / "j.db")
    journal.append(
        Event(
            event_id="evt-1",
            event_type="WPStatusChanged",
            payload=b"{}",
            occurred_at="2026-07-01T00:00:00Z",
            created_at="2026-07-01T00:00:00Z",
            project_uuid=UUID_A,
            project_slug="acme",
        )
    )

    (stored,) = journal.read_all()
    assert stored.project_uuid == UUID_A
    assert stored.project_slug == "acme"


def test_identity_defaults_to_none(tmp_path: Path) -> None:
    """Additive and nullable — an event may carry no identity (C-001)."""
    journal = EventJournal(tmp_path / "j.db")
    journal.append(_event("evt-1", {}))

    (stored,) = journal.read_all()
    assert stored.project_uuid is None
    assert stored.project_slug is None


def test_project_uuid_is_indexed(tmp_path: Path) -> None:
    """NFR-003: the predicate must be an indexed lookup, not a scan."""
    db_path = tmp_path / "j.db"
    EventJournal(db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        indexed = {
            row[0]
            for row in conn.execute(
                f"SELECT name FROM sqlite_master WHERE type='index' "
                f"AND tbl_name='{TABLE_NAME}'"  # noqa: S608 - constant
            )
        }
    finally:
        conn.close()

    assert any("project" in name for name in indexed), (
        f"no project-identity index found among {sorted(indexed)}"
    )


# --- T012: backfill over the real writer sites ----------------------------


@pytest.mark.parametrize(
    ("label", "envelope"),
    [
        ("namespace", {"namespace": {"project_uuid": UUID_A, "project_slug": "acme"}}),
        ("envelope", {"project_uuid": UUID_A, "project_slug": "acme"}),
        ("payload", {"payload": {"project_uuid": UUID_A, "project_slug": "acme"}}),
        (
            "subject",
            {"payload": {"subject": {"project_uuid": UUID_A, "project_slug": "acme"}}},
        ),
    ],
)
def test_backfill_resolves_each_writer_site(
    tmp_path: Path, label: str, envelope: dict
) -> None:
    """All four sites, including the one the pre-#3030 chain missed."""
    db_path = tmp_path / f"j-{label}.db"
    journal = EventJournal(db_path)
    journal.append(_event("evt-1", envelope))

    result = backfill_journal_identity(journal)

    assert _stored_identity(db_path)["evt-1"] == (UUID_A, "acme")
    assert result.updated == 1


def test_backfill_leaves_unresolvable_rows_null_and_counts_them(
    tmp_path: Path,
) -> None:
    """C-002 + T013: never deleted, never guessed, always counted."""
    db_path = tmp_path / "j.db"
    journal = EventJournal(db_path)
    journal.append(_event("evt-resolvable", {"project_uuid": UUID_A}))
    journal.append(_event("evt-bare", {}))
    journal.append(_event("evt-nil", {"project_uuid": NIL_PROJECT_UUID}))
    journal.append(
        Event(
            event_id="evt-corrupt",
            event_type="WPStatusChanged",
            payload=b"not-json{{{",
            occurred_at="2026-07-01T00:00:00Z",
            created_at="2026-07-01T00:00:00Z",
        )
    )

    result = backfill_journal_identity(journal)

    identity = _stored_identity(db_path)
    assert identity["evt-resolvable"][0] == UUID_A
    assert identity["evt-bare"][0] is None
    assert identity["evt-nil"][0] is None, "the nil sentinel must not be stored"
    assert identity["evt-corrupt"][0] is None
    assert {e.event_id for e in journal.read_all()} == {
        "evt-resolvable",
        "evt-bare",
        "evt-nil",
        "evt-corrupt",
    }, "backfill must not delete rows (C-002)"

    assert result.unresolved == 3
    assert count_unresolved_identity(journal) == 3


#: SC-007's stated scale. Was 60 — 1/166th of it, which is not a scale test at all.
#: 10k rows cost ~0.5s here because the fixture seeds through the journal's own
#: batch-append transaction (0.19s); the per-row ``append`` this file used opens a
#: fresh SQLite connection per row and costs 4.7s for the same 10k, which is
#: presumably why the number was 60. No marker is needed at this cost.
SC007_ROWS = 10_000


def test_sc007_backfill_twice_is_byte_identical(tmp_path: Path) -> None:
    """SC-007/NFR-004 at its stated 10k-row multi-project scale.

    Seeded through ``EventJournal.transaction`` — the journal's own commit-once
    batch-append seam, not a test-only shortcut — because 10k per-row ``append``
    calls are 10k connection open/closes.
    """
    db_path = tmp_path / "j.db"
    journal = EventJournal(db_path)
    with journal.transaction() as txn:
        for i in range(SC007_ROWS):
            envelope = (
                {"project_uuid": UUID_A, "project_slug": "acme"}
                if i % 3 == 0
                else {"payload": {"subject": {"project_uuid": UUID_B}}}
                if i % 3 == 1
                else {}
            )
            txn.append(_event(f"evt-{i:05d}", envelope))
        txn.commit()

    first = backfill_journal_identity(journal)
    snapshot_1 = _raw_snapshot(db_path)

    second = backfill_journal_identity(journal)
    snapshot_2 = _raw_snapshot(db_path)

    assert snapshot_1 == snapshot_2, "second backfill mutated stored values"
    assert len(snapshot_1) == SC007_ROWS, (
        f"the fixture must actually hold {SC007_ROWS} rows, got {len(snapshot_1)}"
    )
    assert {e.event_id for e in journal.read_all()} == {
        f"evt-{i:05d}" for i in range(SC007_ROWS)
    }, "backfill must neither drop nor invent rows"
    assert second.updated == 0, "an idempotent re-run has nothing left to update"
    assert first.unresolved == second.unresolved
    assert first.updated + first.unresolved == SC007_ROWS, (
        "every row must be either identified or counted as unresolved — a row that "
        "is neither is silently unaccounted for (FR-011)"
    )


def _raw_snapshot(db_path: Path) -> list[tuple]:
    """Every column, ``repo_slug`` included.

    ``repo_slug`` was missing from this projection, and that omission was not
    cosmetic: it is a column the backfill *writes*, so SC-007's byte-identical claim
    simply did not cover it. The proof of that is
    ``test_backfill_does_not_clear_an_already_stored_repo_slug`` below, which found a
    real destructive write that this snapshot could not see.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        return list(
            conn.execute(
                f"SELECT event_id, event_type, payload, occurred_at, created_at, "
                f"coalesce_key, archived_at, drain_blocked_reason, project_uuid, "
                f"project_slug, repo_slug FROM {TABLE_NAME} ORDER BY event_id"  # noqa: S608 - constant
            )
        )
    finally:
        conn.close()


def test_backfill_does_not_clear_an_already_stored_repo_slug(tmp_path: Path) -> None:
    """NFR-004 is lossless, and ``repo_slug`` is a column the backfill writes.

    A row can carry ``repo_slug`` while ``project_uuid`` is still NULL: capture
    stamps the two from different sources (``event.get("repo_slug")`` versus T011's
    resolution chain), and ``sync/migrate_journal.py`` moves legacy rows in. When the
    payload carries no ``repo_slug``, ``SET_IDENTITY_SQL`` wrote NULL over the stored
    value — destroying the only record of which repo the row came from, which is the
    column's entire purpose (the WP07 per-project report).

    Not a leak: ``repo_slug`` is explicitly never an authorization key (FR-019). It
    is data loss, and it was invisible because ``_raw_snapshot`` did not select the
    column.
    """
    db_path = tmp_path / "j.db"
    journal = EventJournal(db_path)
    journal.append(
        Event(
            event_id="evt-migrated",
            event_type="WPStatusChanged",
            # Resolvable uuid, and NO repo_slug in the envelope.
            payload=json.dumps({"project_uuid": UUID_A, "project_slug": "acme"}).encode(),
            occurred_at="2026-07-01T00:00:00Z",
            created_at="2026-07-01T00:00:00Z",
            repo_slug="acme/widgets",
        )
    )

    backfill_journal_identity(journal)

    (stored,) = journal.read_all()
    assert stored.project_uuid == UUID_A, "the backfill must still fill the uuid"
    assert stored.repo_slug == "acme/widgets", (
        "the backfill must not overwrite a stored repo_slug with the payload's "
        "absent one; an absent derived value is not a correction"
    )


def test_backfill_writes_repo_slug_when_the_payload_carries_one(tmp_path: Path) -> None:
    """The converse, so the guard above cannot be satisfied by never writing at all."""
    db_path = tmp_path / "j.db"
    journal = EventJournal(db_path)
    journal.append(
        _event("evt-1", {"project_uuid": UUID_A, "repo_slug": "acme/widgets"})
    )

    backfill_journal_identity(journal)

    (stored,) = journal.read_all()
    assert stored.repo_slug == "acme/widgets"


def test_backfill_preserves_all_non_identity_columns(tmp_path: Path) -> None:
    """NFR-004: no row mutated outside the new identity columns.

    Three of them, not two: ``repo_slug`` joined ``project_uuid`` and
    ``project_slug`` after NFR-004's wording was written. The invariant is unchanged
    — nothing outside the columns this mission added is touched — and the slice
    below is what enforces it.
    """
    db_path = tmp_path / "j.db"
    journal = EventJournal(db_path)
    journal.append(
        Event(
            event_id="evt-1",
            event_type="ProofRecorded",
            payload=json.dumps({"project_uuid": UUID_A}).encode(),
            occurred_at="2026-07-01T00:00:00Z",
            created_at="2026-07-02T03:04:05Z",
            coalesce_key="ck-1",
            drain_blocked_reason="missing_auth",
        )
    )
    before = {r[0]: r[1:8] for r in _raw_snapshot(db_path)}

    backfill_journal_identity(journal)

    after = {r[0]: r[1:8] for r in _raw_snapshot(db_path)}
    assert after == before


def test_backfill_does_not_overwrite_an_existing_stored_identity(
    tmp_path: Path,
) -> None:
    """Resumability: a row already carrying identity is left alone.

    'Backfill interrupted' is a named edge case — a resumed run must not
    re-derive and possibly change a value the predicate already trusts.
    """
    db_path = tmp_path / "j.db"
    journal = EventJournal(db_path)
    journal.append(
        Event(
            event_id="evt-1",
            event_type="WPStatusChanged",
            payload=json.dumps({"project_uuid": UUID_B}).encode(),
            occurred_at="2026-07-01T00:00:00Z",
            created_at="2026-07-01T00:00:00Z",
            project_uuid=UUID_A,
        )
    )

    result = backfill_journal_identity(journal)

    assert _stored_identity(db_path)["evt-1"][0] == UUID_A
    assert result.updated == 0


def test_backfill_on_an_empty_journal_is_a_no_op(tmp_path: Path) -> None:
    journal = EventJournal(tmp_path / "j.db")
    result = backfill_journal_identity(journal)
    assert (result.updated, result.unresolved) == (0, 0)


def test_backfill_migrates_a_pre_migration_file(tmp_path: Path) -> None:
    """The two halves compose: T010's ALTER then T012's backfill."""
    db_path = tmp_path / "j-legacy.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            f"CREATE TABLE {TABLE_NAME} ("
            "event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, "
            "payload BLOB NOT NULL, occurred_at TEXT NOT NULL, "
            "created_at TEXT NOT NULL, coalesce_key TEXT, archived_at TEXT, "
            "drain_blocked_reason TEXT)"
        )
        conn.execute(
            f"INSERT INTO {TABLE_NAME} "  # noqa: S608 - constant
            "(event_id, event_type, payload, occurred_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                "evt-old",
                "WPStatusChanged",
                json.dumps({"project_uuid": UUID_A}).encode(),
                "2026-06-01T00:00:00Z",
                "2026-06-01T00:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    journal = EventJournal(db_path)
    backfill_journal_identity(journal)

    assert _stored_identity(db_path)["evt-old"][0] == UUID_A
