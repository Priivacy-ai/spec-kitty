"""#3030 shared body queues are immutable migration/quarantine inputs.

There is intentionally no live global purge API.  WP10 must account for every
row in a shared queue, copy valid project rows into only their project stores,
and quarantine blank/whitespace identities without deleting source evidence.
"""

from __future__ import annotations

import hashlib
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
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]
PROJECT_X = "91919191-9191-4191-8191-919191919191"
PROJECT_Y = "92929292-9292-4292-8292-929292929292"

@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))



def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 -- source-evidence integrity


def _seed_shared_queue(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE queue (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp REAL NOT NULL,
            retry_count INTEGER NOT NULL
        );
        CREATE TABLE body_upload_queue (
            id INTEGER PRIMARY KEY,
            project_uuid TEXT NOT NULL,
            mission_slug TEXT NOT NULL,
            target_branch TEXT NOT NULL,
            mission_type TEXT NOT NULL,
            manifest_version TEXT NOT NULL,
            artifact_path TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            hash_algorithm TEXT NOT NULL,
            content_body TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            retry_count INTEGER NOT NULL,
            next_attempt_at REAL NOT NULL,
            created_at REAL NOT NULL
        );
        INSERT INTO queue VALUES ('legacy-event', 'mission.updated', '{}', 0, 0);
        """
    )
    rows = (
        (PROJECT_X, "spec.md"),
        (PROJECT_X, "plan.md"),
        (PROJECT_Y, "spec.md"),
        ("", "tasks/WP01.md"),
        ("   ", "tasks/WP02.md"),
    )
    connection.executemany(
        "INSERT INTO body_upload_queue "
        "(project_uuid, mission_slug, target_branch, mission_type, "
        "manifest_version, artifact_path, content_hash, hash_algorithm, "
        "content_body, size_bytes, retry_count, next_attempt_at, created_at) "
        "VALUES (?, '047-payroll', 'main', 'software-dev', '1', ?, "
        "? || ':' || ?, 'sha256', '# Client engagement detail', 26, 0, 0, 0)",
        ((project, artifact, project, artifact) for project, artifact in rows),
    )
    connection.commit()
    connection.close()


def _body_rows(path: Path) -> list[tuple[object, ...]]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return list(connection.execute("SELECT id, project_uuid, artifact_path, content_hash FROM body_upload_queue ORDER BY id"))
    finally:
        connection.close()


def test_preview_accounts_for_whole_store_without_purging_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "home"
    source = tmp_path / "queue.db"
    _seed_shared_queue(source)
    before_hash = _sha256(source)
    before_rows = _body_rows(source)

    manifest = LegacyProjectStoreMigration(runtime, (source,)).preview("body-preview")

    assert manifest.phase is MigrationPhase.INVENTORIED
    assert manifest.total_rows == 6
    assert {project: len(rows) for project, rows in manifest.partitions.items()} == {
        PROJECT_X: 2,
        PROJECT_Y: 1,
    }
    assert [(row.table, row.reason) for row in manifest.quarantine] == [
        ("body_upload_queue", QuarantineReason.MISSING_PROJECT_UUID),
        ("body_upload_queue", QuarantineReason.MISSING_PROJECT_UUID),
        ("queue", QuarantineReason.MISSING_PROJECT_UUID),
    ]
    assert sum(len(rows) for rows in manifest.partitions.values()) + len(manifest.quarantine) == manifest.total_rows
    assert _sha256(source) == before_hash
    assert _body_rows(source) == before_rows


def test_migrate_partitions_bodies_and_leaves_unknown_rows_as_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "home"
    source = tmp_path / "queue.db"
    _seed_shared_queue(source)
    before_hash = _sha256(source)
    migration = LegacyProjectStoreMigration(runtime, (source,))

    completed = migration.migrate("body-copy")

    assert completed.phase is MigrationPhase.COMPLETE
    with ProjectSyncStore(PROJECT_X).unit_of_work() as unit:
        assert unit.execute("SELECT body_task_id, state FROM body_upload_tasks ORDER BY body_task_id").fetchall() == [("1", "pending"), ("2", "pending")]
        assert unit.execute("SELECT COUNT(*) FROM outbox_tasks").fetchone() == (0,)
    with ProjectSyncStore(PROJECT_Y).unit_of_work() as unit:
        assert unit.execute("SELECT body_task_id FROM body_upload_tasks").fetchall() == [("3",)]
        assert unit.execute(
            "SELECT COUNT(*) FROM body_upload_tasks WHERE project_uuid = ?",
            (PROJECT_X,),
        ).fetchone() == (0,)
    assert len(migration.quarantine("body-copy")) == 3
    assert _sha256(source) == before_hash
    assert len(_body_rows(source)) == 5


def test_rerun_has_complete_disposition_without_duplicate_or_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "home"
    source = tmp_path / "queue.db"
    _seed_shared_queue(source)
    migration = LegacyProjectStoreMigration(runtime, (source,))

    first = migration.migrate("body-idempotent")
    second = migration.migrate("body-idempotent")

    assert second == first
    with ProjectSyncStore(PROJECT_X).unit_of_work() as unit:
        assert unit.execute("SELECT COUNT(*) FROM body_upload_tasks").fetchone() == (2,)
    assert len(_body_rows(source)) == 5
