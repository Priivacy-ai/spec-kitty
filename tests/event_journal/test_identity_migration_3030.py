"""T010: additive journal migration for project identity (#3030 WP04).

The journal has no schema-migration mechanism: ``_ensure_schema`` runs
``CREATE TABLE IF NOT EXISTS`` plus two index creates, and ``CREATE TABLE IF NOT
EXISTS`` is a no-op on an existing table. Meanwhile ``INSERT_SQL``,
``SELECT_ALL_SQL``, ``SELECT_BY_ID_SQL`` and ``SELECT_BLOCKED_SQL`` are all
derived from ``_COLUMN_LIST``. So adding ``project_uuid``/``project_slug`` to
``ORDERED_COLUMNS`` (T012) without an ALTER step raises ``no such column`` on
**every existing journal file** — bricking ``sync status``, ``sync now`` and the
backfill itself.

These tests pin the migration against a **genuine pre-migration database file**
built with the historical 8-column DDL, not a fixture that merely omits the
values. A migration tested only against freshly-created DBs would pass while
every real user's journal broke, because `CREATE TABLE` on a new file already
includes the new columns.

Assertions are on the public seam (construct a journal, read it) plus the
physical schema, per C-001/C-002: additive, nullable, nothing dropped.

C-001's pins iterate :data:`IDENTITY_COLUMNS` rather than naming columns. They used
to name two of the three, so dropping ``repo_slug`` from the migration's ALTER loop
was caught only *indirectly* — by ``SELECT_ALL_SQL`` raising ``no such column``
inside a different test — and never by the assertions whose job it is. A pin that
depends on an unrelated test failing is not a pin.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import (
    IDENTITY_COLUMNS,
    ORDERED_COLUMNS,
    TABLE_NAME,
)

pytestmark = [pytest.mark.fast]

#: The journal's column list exactly as it shipped before #3030 — 8 columns, no
#: identity. Frozen on purpose: regenerating it from today's constants would make
#: every test below vacuous the moment the constants change, since a "migration"
#: from today's schema to today's schema proves nothing.
#:
#: ``test_the_frozen_pre_migration_shape_still_describes_todays_non_identity_columns``
#: keeps the freeze honest. Frozen must not mean unexamined: if a column is added to
#: ``ORDERED_COLUMNS`` without being classified as identity, this literal silently
#: starts claiming the historical schema had a column that did not exist, and the
#: migration tests quietly stop covering it.
_PRE_MIGRATION_COLUMNS: tuple[str, ...] = (
    "event_id",
    "event_type",
    "payload",
    "occurred_at",
    "created_at",
    "coalesce_key",
    "archived_at",
    "drain_blocked_reason",
)

# The historical DDL, with types, kept verbatim rather than generated.
_PRE_MIGRATION_DDL = f"""
CREATE TABLE {TABLE_NAME} (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload BLOB NOT NULL,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    coalesce_key TEXT,
    archived_at TEXT,
    drain_blocked_reason TEXT
)
"""


def test_the_frozen_pre_migration_shape_still_describes_todays_non_identity_columns() -> None:
    """Tie the frozen literal to today's constants so drift fails loudly.

    The literal must stay frozen — that is what makes the migration tests test a
    migration. But a frozen literal nobody compares is how a test goes stale in
    silence, so the relationship is asserted instead of the value being derived:
    everything in today's schema that is not an identity column must be exactly what
    the pre-#3030 schema had.

    If this fails because a genuinely new non-identity column was added, the fix is a
    deliberate decision about the historical DDL — not a mechanical update of the
    literal.
    """
    assert set(_PRE_MIGRATION_COLUMNS) == set(ORDERED_COLUMNS) - set(IDENTITY_COLUMNS), (
        "the frozen pre-migration column list no longer matches today's schema minus "
        "its identity columns; a column was added without being classified, so the "
        "migration tests below have stopped covering it"
    )
    # The DDL and the column list are two spellings of one thing; keep them agreeing.
    for column in _PRE_MIGRATION_COLUMNS:
        assert column in _PRE_MIGRATION_DDL, f"{column} missing from the frozen DDL"


def _write_pre_migration_journal(db_path: Path, *, rows: int = 3) -> None:
    """Create a real pre-#3030 journal file carrying *rows* events."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(_PRE_MIGRATION_DDL)
        for i in range(rows):
            conn.execute(
                f"INSERT INTO {TABLE_NAME} "
                "(event_id, event_type, payload, occurred_at, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    f"evt-legacy-{i:03d}",
                    "WPStatusChanged",
                    b'{"wp_id": "WP01"}',
                    "2026-07-01T00:00:00Z",
                    "2026-07-01T00:00:00Z",
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _columns(db_path: Path) -> set[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})")}
    finally:
        conn.close()


def test_pre_migration_journal_gains_the_identity_columns(tmp_path: Path) -> None:
    """Opening a pre-migration file adds the columns (the T012 prerequisite)."""
    db_path = tmp_path / "journal-legacy.db"
    _write_pre_migration_journal(db_path)
    assert not (set(IDENTITY_COLUMNS) & _columns(db_path)), (
        "the fixture must start genuinely pre-migration"
    )

    EventJournal(db_path)

    assert set(IDENTITY_COLUMNS) <= _columns(db_path), (
        f"migration added only {sorted(set(IDENTITY_COLUMNS) & _columns(db_path))} "
        f"of {sorted(IDENTITY_COLUMNS)}"
    )


def test_pre_migration_journal_is_readable_through_the_public_seam(
    tmp_path: Path,
) -> None:
    """The real failure mode: reading an existing journal after the columns land.

    This is what would raise ``no such column: project_uuid`` without T010.
    """
    db_path = tmp_path / "journal-legacy.db"
    _write_pre_migration_journal(db_path, rows=3)

    journal = EventJournal(db_path)
    events = journal.read_all()

    assert [e.event_id for e in events] == [
        "evt-legacy-000",
        "evt-legacy-001",
        "evt-legacy-002",
    ]


def test_migration_preserves_every_existing_row_and_value(tmp_path: Path) -> None:
    """C-002: the migration adds columns and touches nothing else."""
    db_path = tmp_path / "journal-legacy.db"
    _write_pre_migration_journal(db_path, rows=5)

    before = _read_raw(db_path)
    EventJournal(db_path)
    after = _read_raw(db_path)

    assert after == before, "migration must not alter any pre-existing value"


def _read_raw(db_path: Path) -> list[tuple]:
    """Read the pre-migration columns only.

    Projected from the *frozen* :data:`_PRE_MIGRATION_COLUMNS`, deliberately not from
    ``ORDERED_COLUMNS``: this asserts that migrating did not disturb the values that
    existed **before** it ran, so it must keep asking about the historical eight even
    as the schema grows. Deriving it from today's constants would make it select
    columns the migration itself just added and compare them against themselves.
    """
    projection = ", ".join(_PRE_MIGRATION_COLUMNS)
    conn = sqlite3.connect(str(db_path))
    try:
        return list(
            conn.execute(
                f"SELECT {projection} FROM {TABLE_NAME} ORDER BY event_id"  # noqa: S608 - frozen literal
            )
        )
    finally:
        conn.close()


def test_identity_columns_are_nullable(tmp_path: Path) -> None:
    """C-001: additive and nullable, so an older CLI keeps writing this DB."""
    db_path = tmp_path / "journal-legacy.db"
    _write_pre_migration_journal(db_path, rows=1)
    EventJournal(db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        notnull = {
            row[1]: row[3]
            for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})")
        }
        missing = [c for c in IDENTITY_COLUMNS if c not in notnull]
        assert not missing, f"migration never added {missing}"
        not_nullable = [c for c in IDENTITY_COLUMNS if notnull[c] != 0]
        assert not not_nullable, (
            f"{not_nullable} are NOT NULL, so an older CLI can no longer write this "
            "database (C-001)"
        )
    finally:
        conn.close()


def test_migration_is_idempotent(tmp_path: Path) -> None:
    """Re-opening the same journal must not raise 'duplicate column name'."""
    db_path = tmp_path / "journal-legacy.db"
    _write_pre_migration_journal(db_path)

    EventJournal(db_path)
    EventJournal(db_path)
    EventJournal(db_path)

    assert set(IDENTITY_COLUMNS) <= _columns(db_path)


def test_a_fresh_journal_also_has_the_columns(tmp_path: Path) -> None:
    """New databases get identity from CREATE TABLE, not only from the ALTER."""
    db_path = tmp_path / "journal-fresh.db"

    EventJournal(db_path)

    assert set(IDENTITY_COLUMNS) <= _columns(db_path), (
        "CREATE TABLE and the ALTER loop must agree on the identity columns; a "
        "column present in only one of them breaks either new or existing journals"
    )
