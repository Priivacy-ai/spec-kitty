"""#3030 legacy journal identity is an immutable WP10 migration input.

The live journal constructor no longer upgrades shared databases.  Historical
eight-column files are inventoried read-only: rows whose payload proves a valid
project are copied into that project's sealed migration epoch; rows without
identity are quarantined and can never reach a sender.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.project_store_migration import (
    LegacyProjectStoreMigration,
    MigrationPhase,
    QuarantineReason,
)


pytestmark = [pytest.mark.fast]
PROJECT = "81818181-8181-4181-8181-818181818181"

_PRE_MIGRATION_COLUMNS = (
    "event_id",
    "event_type",
    "payload",
    "occurred_at",
    "created_at",
    "coalesce_key",
    "archived_at",
    "drain_blocked_reason",
)

_PRE_MIGRATION_DDL = """
CREATE TABLE event_journal (
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 -- source-evidence integrity


def _write_historical_journal(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute(_PRE_MIGRATION_DDL)
    connection.executemany(
        "INSERT INTO event_journal "
        "(event_id, event_type, payload, occurred_at, created_at) "
        "VALUES (?, 'WPStatusChanged', ?, '2026-07-01T00:00:00Z', "
        "'2026-07-01T00:00:00Z')",
        (
            (
                "evt-attributed",
                json.dumps({"event_id": "evt-attributed", "project_uuid": PROJECT}),
            ),
            ("evt-unattributed", json.dumps({"event_id": "evt-unattributed"})),
        ),
    )
    connection.commit()
    connection.close()


def _raw_rows(path: Path) -> list[tuple[object, ...]]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return list(
            connection.execute(
                "SELECT event_id, event_type, payload, occurred_at, created_at, "
                "coalesce_key, archived_at, drain_blocked_reason "
                "FROM event_journal ORDER BY event_id"
            )
        )
    finally:
        connection.close()


def test_historical_shape_is_inventoried_without_alter_or_source_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy-journal.db"
    _write_historical_journal(source)
    before_hash = _sha256(source)
    before_rows = _raw_rows(source)

    manifest = LegacyProjectStoreMigration(runtime, (source,)).preview("journal-preview")

    assert manifest.phase is MigrationPhase.INVENTORIED
    assert manifest.sources[0].tables == ("event_journal",)
    assert manifest.sources[0].row_count == 2
    assert set(manifest.partitions) == {PROJECT}
    assert [(row.row_id, row.reason) for row in manifest.quarantine] == [("evt-unattributed", QuarantineReason.MISSING_PROJECT_UUID)]
    assert _sha256(source) == before_hash
    assert _raw_rows(source) == before_rows

    connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    try:
        columns = tuple(row[1] for row in connection.execute("PRAGMA table_info(event_journal)"))
    finally:
        connection.close()
    assert columns == _PRE_MIGRATION_COLUMNS


def test_copy_preserves_attributed_identity_and_quarantines_unknown_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy-journal.db"
    _write_historical_journal(source)
    before_hash = _sha256(source)

    migration = LegacyProjectStoreMigration(runtime, (source,))
    completed = migration.migrate("journal-copy")

    assert completed.phase is MigrationPhase.COMPLETE
    with ProjectSyncStore(PROJECT).unit_of_work() as unit:
        assert unit.execute("SELECT entry_id, payload_json FROM journal_entries").fetchall() == [
            (
                "evt-attributed",
                json.dumps({"event_id": "evt-attributed", "project_uuid": PROJECT}),
            )
        ]
        assert unit.execute("SELECT state, reason FROM consent_epochs").fetchall() == [("sealed", "legacy_migration:journal-copy")]
        assert unit.execute("SELECT COUNT(*) FROM outbox_tasks").fetchone() == (0,)
    assert migration.quarantine("journal-copy")[0].row_id == "evt-unattributed"
    assert _sha256(source) == before_hash
    assert len(_raw_rows(source)) == 2


def test_rerun_is_idempotent_without_a_live_legacy_constructor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy-journal.db"
    _write_historical_journal(source)
    migration = LegacyProjectStoreMigration(runtime, (source,))

    first = migration.migrate("journal-idempotent")
    second = migration.migrate("journal-idempotent")

    assert second == first
    with ProjectSyncStore(PROJECT).unit_of_work() as unit:
        assert unit.execute("SELECT COUNT(*) FROM journal_entries").fetchone() == (1,)
