"""Legacy hash-scoped journals are immutable WP10 migration inputs.

This suite used to instantiate the retired path-backed ``OfflineQueue`` and
``EventJournal`` APIs, then delete source rows after copying them into another
shared live store.  Project-only layout makes that behavior invalid.  These
tests retain the historical hash-scoped database evidence while pinning the
current partition/quarantine boundary and unchanged source bytes.
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


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]
PROJECT_A = "a1a1a1a1-a1a1-41a1-81a1-a1a1a1a1a1a1"
PROJECT_B = "b2b2b2b2-b2b2-42b2-82b2-b2b2b2b2b2b2"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 -- source-evidence integrity


def _historical_queue(
    path: Path,
    rows: tuple[tuple[str, str | None], ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE queue (id INTEGER PRIMARY KEY, event_id TEXT UNIQUE, event_type TEXT, data TEXT, timestamp INTEGER, retry_count INTEGER)")
    for index, (event_id, project_uuid) in enumerate(rows, start=1):
        payload: dict[str, object] = {
            "event_id": event_id,
            "event_type": "MissionCreated",
            "payload": {},
        }
        if project_uuid is not None:
            payload["project_uuid"] = project_uuid
        connection.execute(
            "INSERT INTO queue VALUES (?, ?, 'MissionCreated', ?, ?, 0)",
            (index, event_id, json.dumps(payload, sort_keys=True), index),
        )
    connection.commit()
    connection.close()


def test_multiple_hash_scoped_sources_partition_in_one_immutable_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source_a = tmp_path / "queues" / "queue-1111111111111111.db"
    source_b = tmp_path / "queues" / "queue-2222222222222222.db"
    _historical_queue(source_a, (("event-a1", PROJECT_A), ("event-a2", PROJECT_A)))
    _historical_queue(source_b, (("event-b1", PROJECT_B),))
    before = {source_a: _sha256(source_a), source_b: _sha256(source_b)}

    completed = LegacyProjectStoreMigration(
        runtime,
        (source_a, source_b),
    ).migrate("hash-scoped-copy")

    assert completed.phase is MigrationPhase.COMPLETE
    assert set(completed.partitions) == {PROJECT_A, PROJECT_B}
    with ProjectSyncStore(PROJECT_A).unit_of_work() as unit:
        assert unit.execute("SELECT entry_id FROM journal_entries ORDER BY entry_id").fetchall() == [("event-a1",), ("event-a2",)]
    with ProjectSyncStore(PROJECT_B).unit_of_work() as unit:
        assert unit.execute("SELECT entry_id FROM journal_entries ORDER BY entry_id").fetchall() == [("event-b1",)]
    assert {source: _sha256(source) for source in before} == before


def test_hash_only_source_identity_is_never_reverse_engineered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "queues" / "queue-deadbeefdeadbeef.db"
    _historical_queue(source, (("event-unknown", None),))
    before = _sha256(source)

    preview = LegacyProjectStoreMigration(runtime, (source,)).preview("hash-only-preview")

    assert preview.partitions == {}
    assert [(row.row_id, row.reason) for row in preview.quarantine] == [("event-unknown", QuarantineReason.MISSING_PROJECT_UUID)]
    assert _sha256(source) == before


def test_body_only_shared_source_is_quarantined_not_opened_as_live_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "queue.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE body_upload_queue (id INTEGER PRIMARY KEY, project_uuid TEXT, artifact_path TEXT, content_hash TEXT, content_body TEXT)")
    connection.execute("INSERT INTO body_upload_queue VALUES (1, ' ', 'spec.md', 'hash', '# body')")
    connection.commit()
    connection.close()
    before = _sha256(source)

    preview = LegacyProjectStoreMigration(runtime, (source,)).preview("body-only-preview")

    assert preview.total_rows == 1
    assert preview.quarantine[0].reason is QuarantineReason.MISSING_PROJECT_UUID
    assert _sha256(source) == before
