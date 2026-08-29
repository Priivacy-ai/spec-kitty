"""Legacy journal identity migration is lossless, exact, and fail-closed.

These regressions used to instantiate the retired path-owning ``EventJournal``.
They now exercise the public WP10 migration boundary: legacy SQLite is immutable
input, attributable rows copy into their UUID-owned ``ProjectSyncStore``, and
unattributable or conflicting rows remain named quarantine evidence.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from specify_cli.sync.project_identity import NIL_PROJECT_UUID, resolve_event_project_uuid
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.project_store_migration import (
    LegacyProjectStoreMigration,
    MigrationPhase,
    QuarantineReason,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "11111111-1111-4111-8111-111111111111"
UUID_B = "22222222-2222-4222-8222-222222222222"
SC007_ROWS = 10_000


@pytest.fixture(autouse=True)
def _runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))


def _create_source(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE event_journal ("
        "event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, payload BLOB NOT NULL, "
        "occurred_at TEXT NOT NULL, created_at TEXT NOT NULL, coalesce_key TEXT, "
        "archived_at TEXT, drain_blocked_reason TEXT, project_uuid TEXT, "
        "project_slug TEXT, repo_slug TEXT)"
    )
    return connection


def _insert(
    connection: sqlite3.Connection,
    event_id: str,
    envelope: dict[str, Any] | bytes,
    *,
    project_uuid: str | None = None,
    project_slug: str | None = None,
    repo_slug: str | None = None,
    event_type: str = "WPStatusChanged",
    coalesce_key: str | None = None,
    blocked: str | None = None,
) -> None:
    payload = envelope if isinstance(envelope, bytes) else json.dumps(envelope).encode()
    connection.execute(
        "INSERT INTO event_journal VALUES (?, ?, ?, '2026-07-01T00:00:00Z', '2026-07-02T03:04:05Z', ?, NULL, ?, ?, ?, ?)",
        (
            event_id,
            event_type,
            payload,
            coalesce_key,
            blocked,
            project_uuid,
            project_slug,
            repo_slug,
        ),
    )


def _migration(tmp_path: Path, source: Path) -> LegacyProjectStoreMigration:
    return LegacyProjectStoreMigration(tmp_path / "runtime", (source,))


def _source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 -- immutable migration evidence


def _live_rows(project_uuid: str) -> list[tuple[Any, ...]]:
    with ProjectSyncStore(project_uuid).unit_of_work() as unit:
        return unit.execute(
            "SELECT entry_id, payload_json, created_at FROM journal_entries WHERE project_uuid = ? ORDER BY entry_id",
            (project_uuid,),
        ).fetchall()


def test_event_round_trips_project_identity(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    _insert(connection, "evt-1", {"project_uuid": UUID_A}, project_uuid=UUID_A, project_slug="acme")
    connection.commit()
    connection.close()

    completed = _migration(tmp_path, source).migrate("round-trip")

    assert completed.phase is MigrationPhase.COMPLETE
    assert _live_rows(UUID_A)[0][0] == "evt-1"


def test_identity_defaults_to_none(tmp_path: Path) -> None:
    """Missing identity is quarantined and never admitted to a live store."""
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    _insert(connection, "evt-1", {})
    connection.commit()
    connection.close()

    manifest = _migration(tmp_path, source).preview("missing")

    assert manifest.partitions == {}
    assert [(row.row_id, row.reason) for row in manifest.quarantine] == [("evt-1", QuarantineReason.MISSING_PROJECT_UUID)]


def test_project_uuid_is_indexed(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    _insert(connection, "evt-1", {"project_uuid": UUID_A}, project_uuid=UUID_A)
    connection.commit()
    connection.close()
    _migration(tmp_path, source).migrate("indexed")

    store = ProjectSyncStore(UUID_A)
    connection = sqlite3.connect(store.database_path)
    try:
        indexed = {row[2] for row in connection.execute("PRAGMA index_info('sqlite_autoindex_journal_entries_2')")}
    finally:
        connection.close()
    assert indexed == {"project_uuid", "entry_id"}


@pytest.mark.parametrize(
    ("label", "envelope"),
    [
        ("namespace", {"namespace": {"project_uuid": UUID_A, "project_slug": "acme"}}),
        ("envelope", {"project_uuid": UUID_A, "project_slug": "acme"}),
        ("payload", {"payload": {"project_uuid": UUID_A, "project_slug": "acme"}}),
        ("subject", {"payload": {"subject": {"project_uuid": UUID_A, "project_slug": "acme"}}}),
    ],
)
def test_backfill_resolves_each_writer_site(tmp_path: Path, label: str, envelope: dict[str, Any]) -> None:
    """The historical resolver projection feeds the governed migration census."""
    source = tmp_path / f"legacy-{label}.db"
    connection = _create_source(source)
    derived = resolve_event_project_uuid(envelope)
    assert derived == UUID_A
    _insert(connection, "evt-1", envelope, project_uuid=derived)
    connection.commit()
    connection.close()

    manifest = _migration(tmp_path, source).preview(f"writer-{label}")

    assert [row.row_id for row in manifest.partitions[UUID_A]] == ["evt-1"]
    assert manifest.quarantine == ()


def test_backfill_leaves_unresolvable_rows_null_and_counts_them(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    _insert(connection, "evt-resolvable", {"project_uuid": UUID_A}, project_uuid=UUID_A)
    _insert(connection, "evt-bare", {})
    _insert(connection, "evt-nil", {"project_uuid": NIL_PROJECT_UUID}, project_uuid=NIL_PROJECT_UUID)
    _insert(connection, "evt-corrupt", b"not-json{{{")
    connection.commit()
    connection.close()

    manifest = _migration(tmp_path, source).migrate("quarantine-unresolved")

    assert [row[0] for row in _live_rows(UUID_A)] == ["evt-resolvable"]
    assert {row.row_id for row in manifest.quarantine} == {"evt-bare", "evt-nil", "evt-corrupt"}
    assert {row.reason for row in manifest.quarantine} == {
        QuarantineReason.MISSING_PROJECT_UUID,
        QuarantineReason.NIL_PROJECT_UUID,
    }


def test_sc007_backfill_twice_is_byte_identical(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    for index in range(SC007_ROWS):
        project = UUID_A if index % 2 == 0 else UUID_B
        _insert(connection, f"evt-{index:05d}", {"project_uuid": project}, project_uuid=project)
    connection.commit()
    connection.close()
    before = _source_hash(source)
    migration = _migration(tmp_path, source)

    first = migration.migrate("scale")
    rows_once = (len(_live_rows(UUID_A)), len(_live_rows(UUID_B)))
    second = migration.migrate("scale")

    assert first == second
    assert rows_once == (SC007_ROWS // 2, SC007_ROWS // 2)
    assert (len(_live_rows(UUID_A)), len(_live_rows(UUID_B))) == rows_once
    assert _source_hash(source) == before


def test_backfill_does_not_clear_an_already_stored_repo_slug(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    _insert(connection, "evt-1", {"project_uuid": UUID_A}, project_uuid=UUID_A, repo_slug="acme/widgets")
    connection.commit()
    connection.close()

    before = _source_hash(source)
    manifest = _migration(tmp_path, source).preview("repo-preserved")

    assert "repo_slug" in manifest.sources[0].table_columns["event_journal"]
    connection = sqlite3.connect(source)
    try:
        assert connection.execute("SELECT repo_slug FROM event_journal WHERE event_id='evt-1'").fetchone() == ("acme/widgets",)
    finally:
        connection.close()
    assert _source_hash(source) == before


def test_backfill_writes_repo_slug_when_the_payload_carries_one(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    envelope = {"project_uuid": UUID_A, "repo_slug": "acme/widgets"}
    _insert(connection, "evt-1", envelope, project_uuid=UUID_A)
    connection.commit()
    connection.close()

    _migration(tmp_path, source).migrate("repo-payload")

    assert json.loads(_live_rows(UUID_A)[0][1])["repo_slug"] == "acme/widgets"


def test_the_preserved_column_set_is_neither_empty_nor_everything(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(event_journal)")}
    connection.close()
    assert {"project_uuid", "project_slug", "repo_slug"} < columns
    assert columns - {"project_uuid", "project_slug", "repo_slug"}


def test_backfill_preserves_all_non_identity_columns(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    _insert(
        connection,
        "evt-1",
        {"project_uuid": UUID_A},
        project_uuid=UUID_A,
        event_type="ProofRecorded",
        coalesce_key="ck-1",
        blocked="missing_auth",
    )
    connection.commit()
    before = connection.execute(
        "SELECT event_id, event_type, payload, occurred_at, created_at, coalesce_key, archived_at, drain_blocked_reason FROM event_journal"
    ).fetchone()
    connection.close()

    before_hash = _source_hash(source)
    manifest = _migration(tmp_path, source).preview("preserved")
    connection = sqlite3.connect(source)
    try:
        after = connection.execute(
            "SELECT event_id, event_type, payload, occurred_at, created_at, coalesce_key, archived_at, drain_blocked_reason FROM event_journal"
        ).fetchone()
    finally:
        connection.close()

    assert after == before
    assert _source_hash(source) == before_hash
    assert manifest.partitions[UUID_A][0].values["columns"] == tuple(sorted(manifest.sources[0].table_columns["event_journal"]))


def test_backfill_does_not_overwrite_an_existing_stored_identity(tmp_path: Path) -> None:
    """Stored/payload identity disagreement is quarantined, never overwritten."""
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    _insert(connection, "evt-1", {"project_uuid": UUID_B}, project_uuid=UUID_A)
    connection.commit()
    connection.close()

    manifest = _migration(tmp_path, source).preview("conflict")

    assert manifest.partitions == {}
    assert manifest.quarantine[0].reason is QuarantineReason.CONFLICTING_PROJECT_UUID
    assert not ProjectSyncStore(UUID_A).database_path.exists()
    assert not ProjectSyncStore(UUID_B).database_path.exists()


def test_backfill_on_an_empty_journal_is_a_no_op(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    connection = _create_source(source)
    connection.close()

    manifest = _migration(tmp_path, source).preview("empty")

    assert manifest.phase is MigrationPhase.INVENTORIED
    assert manifest.partitions == {}
    assert manifest.quarantine == ()


def test_backfill_migrates_a_pre_migration_file(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE event_journal (event_id TEXT PRIMARY KEY, payload BLOB NOT NULL, created_at TEXT, project_uuid TEXT)")
    connection.execute(
        "INSERT INTO event_journal VALUES ('evt-old', ?, '2026-06-01T00:00:00Z', ?)",
        (json.dumps({"project_uuid": UUID_A}), UUID_A),
    )
    connection.commit()
    connection.close()

    completed = _migration(tmp_path, source).migrate("pre-migration")

    assert completed.phase is MigrationPhase.COMPLETE
    assert [row[0] for row in _live_rows(UUID_A)] == ["evt-old"]
