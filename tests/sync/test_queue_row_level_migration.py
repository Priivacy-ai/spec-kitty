"""Row-level legacy→scoped queue migration (WP01, FR-001/FR-002).

These tests pin the behavior described in
``kitty-specs/mvp-sync-boundary-cli-01KRVCQS/data-model.md``:

* ``_migrate_legacy_queue_to_scope`` performs row-level
  ``INSERT OR IGNORE`` merge across ``queue``, ``body_upload_queue``,
  and ``body_upload_failure_log``.
* Legacy rows are deleted only after verifying the row exists in the
  scoped DB.
* The migration is idempotent: re-running against an already-drained
  legacy DB returns ``0`` and produces no further mutations.
* ``detect_legacy_rows_for_scope(scope)`` returns per-table counts of
  legacy rows that still need to migrate (used by WP03 status check).

NFR-001: every test uses ``monkeypatch.setenv("HOME", str(tmp_path))``
so we never touch the operator's real ``~/.spec-kitty``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from specify_cli.sync.queue import (
    _MIGRATION_TABLES,
    _legacy_queue_db_path,
    _migrate_legacy_queue_to_scope,
    detect_legacy_rows_for_scope,
    ensure_body_queue_schema,
)


# ----------------------------------------------------------------------
# Test fixtures / helpers
# ----------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """NFR-001: redirect HOME so legacy queue.db lives under tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # On Linux ``Path.home()`` consults HOME first, but on macOS it can
    # fall back to ``pwd.getpwuid``. Patch the env var defensively.
    return tmp_path


def _init_queue_schema(conn: sqlite3.Connection) -> None:
    """Recreate the event-queue + body-queue schema on a fresh connection."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            event_type TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            retry_count INTEGER DEFAULT 0,
            coalesce_key TEXT
        )
        """
    )
    ensure_body_queue_schema(conn)
    conn.commit()


def _insert_queue_row(conn: sqlite3.Connection, event_id: str) -> None:
    conn.execute(
        "INSERT INTO queue (event_id, event_type, data, timestamp) "
        "VALUES (?, ?, ?, ?)",
        (event_id, "TestEvent", '{"event_id":"' + event_id + '"}', 1700000000),
    )


def _insert_body_upload_row(
    conn: sqlite3.Connection,
    *,
    project_uuid: str = "proj-1",
    mission_slug: str = "mission-1",
    artifact_path: str = "/path/to/artifact",
    content_hash: str = "deadbeef",
) -> None:
    conn.execute(
        """
        INSERT INTO body_upload_queue (
            project_uuid, mission_slug, target_branch, mission_type,
            manifest_version, artifact_path, content_hash, hash_algorithm,
            content_body, size_bytes, retry_count, next_attempt_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_uuid,
            mission_slug,
            "main",
            "software-dev",
            "v1",
            artifact_path,
            content_hash,
            "sha256",
            "{}",
            2,
            0,
            0.0,
            1700000000.0,
        ),
    )


def _insert_failure_log_row(
    conn: sqlite3.Connection,
    *,
    project_uuid: str = "proj-1",
    failure_reason: str = "oops",
) -> None:
    conn.execute(
        """
        INSERT INTO body_upload_failure_log (
            project_uuid, mission_slug, target_branch, mission_type,
            manifest_version, artifact_path, content_hash, hash_algorithm,
            size_bytes, failure_reason, failure_count, first_failed_at, last_failed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_uuid,
            "mission-1",
            "main",
            "software-dev",
            "v1",
            "/path/to/artifact",
            "deadbeef",
            "sha256",
            2,
            failure_reason,
            1,
            1700000000.0,
            1700000000.0,
        ),
    )


def _row_count(db_path: Path, table: str) -> int:
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table,),
        )
        if cursor.fetchone() is None:
            return 0
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table}"  # noqa: S608 — test-only static names
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def _make_legacy_db(_isolate_home: Path) -> Path:
    """Build the legacy queue.db under the isolated HOME."""
    legacy_db = _legacy_queue_db_path()
    legacy_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(legacy_db)
    try:
        _init_queue_schema(conn)
    finally:
        conn.close()
    return legacy_db


def _make_scoped_db(tmp_path: Path, name: str = "queue-scoped.db") -> Path:
    scoped = tmp_path / "queues" / name
    scoped.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(scoped)
    try:
        _init_queue_schema(conn)
    finally:
        conn.close()
    return scoped


# ----------------------------------------------------------------------
# Scenario 1: empty scoped + populated legacy → all rows migrate
# ----------------------------------------------------------------------


def test_migration_copies_all_legacy_body_rows_to_empty_scoped(
    _isolate_home: Path, tmp_path: Path
) -> None:
    legacy = _make_legacy_db(_isolate_home)
    scoped = _make_scoped_db(tmp_path)

    # Seed legacy with mixed rows across all three tables.
    conn = sqlite3.connect(legacy)
    try:
        _insert_queue_row(conn, "evt-1")
        _insert_queue_row(conn, "evt-2")
        for idx in range(3):
            _insert_body_upload_row(conn, artifact_path=f"/a/{idx}")
        _insert_failure_log_row(conn, failure_reason="reason-1")
        _insert_failure_log_row(conn, failure_reason="reason-2")
        conn.commit()
    finally:
        conn.close()

    migrated = _migrate_legacy_queue_to_scope(scoped)

    assert migrated == 2 + 3 + 2
    # Scoped DB gained every row.
    assert _row_count(scoped, "queue") == 2
    assert _row_count(scoped, "body_upload_queue") == 3
    assert _row_count(scoped, "body_upload_failure_log") == 2
    # Legacy DB is empty for the migrated tables.
    assert _row_count(legacy, "queue") == 0
    assert _row_count(legacy, "body_upload_queue") == 0
    assert _row_count(legacy, "body_upload_failure_log") == 0


# ----------------------------------------------------------------------
# Scenario 2: scoped already has unrelated rows → legacy still merges,
# pre-existing scoped rows are untouched.
# ----------------------------------------------------------------------


def test_migration_preserves_unrelated_scoped_rows(
    _isolate_home: Path, tmp_path: Path
) -> None:
    legacy = _make_legacy_db(_isolate_home)
    scoped = _make_scoped_db(tmp_path)

    # Pre-seed scoped with unrelated rows (different keys than legacy).
    conn = sqlite3.connect(scoped)
    try:
        _insert_queue_row(conn, "scoped-evt-A")
        _insert_body_upload_row(
            conn, project_uuid="other-proj", artifact_path="/other/a"
        )
        conn.commit()
    finally:
        conn.close()

    # Seed legacy with rows that DO NOT collide with scoped's keys.
    conn = sqlite3.connect(legacy)
    try:
        _insert_queue_row(conn, "legacy-evt-1")
        _insert_queue_row(conn, "legacy-evt-2")
        _insert_body_upload_row(conn, artifact_path="/legacy/x")
        conn.commit()
    finally:
        conn.close()

    migrated = _migrate_legacy_queue_to_scope(scoped)

    assert migrated == 2 + 1
    # Scoped now has its original rows PLUS the legacy ones.
    assert _row_count(scoped, "queue") == 3
    assert _row_count(scoped, "body_upload_queue") == 2
    # Legacy is empty.
    assert _row_count(legacy, "queue") == 0
    assert _row_count(legacy, "body_upload_queue") == 0

    # Pre-existing scoped rows survived (no overwrite).
    conn = sqlite3.connect(scoped)
    try:
        scoped_event_ids = {
            row[0] for row in conn.execute("SELECT event_id FROM queue")
        }
        scoped_artifact_paths = {
            row[0]
            for row in conn.execute("SELECT artifact_path FROM body_upload_queue")
        }
    finally:
        conn.close()

    assert "scoped-evt-A" in scoped_event_ids
    assert {"legacy-evt-1", "legacy-evt-2"}.issubset(scoped_event_ids)
    assert "/other/a" in scoped_artifact_paths
    assert "/legacy/x" in scoped_artifact_paths


# ----------------------------------------------------------------------
# Scenario 3: idempotent — second run is a no-op.
# ----------------------------------------------------------------------


def test_migration_is_idempotent(_isolate_home: Path, tmp_path: Path) -> None:
    legacy = _make_legacy_db(_isolate_home)
    scoped = _make_scoped_db(tmp_path)

    conn = sqlite3.connect(legacy)
    try:
        _insert_queue_row(conn, "evt-1")
        _insert_body_upload_row(conn, artifact_path="/idem/a")
        _insert_failure_log_row(conn)
        conn.commit()
    finally:
        conn.close()

    first = _migrate_legacy_queue_to_scope(scoped)
    second = _migrate_legacy_queue_to_scope(scoped)

    assert first == 3
    assert second == 0
    assert _row_count(legacy, "queue") == 0
    assert _row_count(legacy, "body_upload_queue") == 0
    assert _row_count(legacy, "body_upload_failure_log") == 0
    assert _row_count(scoped, "queue") == 1
    assert _row_count(scoped, "body_upload_queue") == 1
    assert _row_count(scoped, "body_upload_failure_log") == 1


# ----------------------------------------------------------------------
# Scenario 4: detect_legacy_rows_for_scope returns per-table counts.
# ----------------------------------------------------------------------


def test_detect_legacy_rows_for_scope_returns_counts(
    _isolate_home: Path,
) -> None:
    legacy = _make_legacy_db(_isolate_home)

    conn = sqlite3.connect(legacy)
    try:
        _insert_queue_row(conn, "evt-1")
        _insert_queue_row(conn, "evt-2")
        _insert_queue_row(conn, "evt-3")
        _insert_body_upload_row(conn, artifact_path="/q/a")
        conn.commit()
    finally:
        conn.close()

    counts = detect_legacy_rows_for_scope("https://test|alice|team-x")
    assert counts == {"queue": 3, "body_upload_queue": 1}

    # After migration drains legacy, the helper reports zero pending rows
    # by omitting empty tables from the result.
    scoped = _legacy_queue_db_path().parent / "queues" / "scoped.db"
    _migrate_legacy_queue_to_scope(scoped)
    assert detect_legacy_rows_for_scope("https://test|alice|team-x") == {}


def test_detect_legacy_rows_for_scope_missing_db_returns_empty(
    _isolate_home: Path,
) -> None:
    # No legacy DB on disk at all → empty dict, not an error.
    assert not _legacy_queue_db_path().exists()
    assert detect_legacy_rows_for_scope("any-scope") == {}


def test_migration_tables_constant_lists_expected_tables() -> None:
    """Pin the public contract of _MIGRATION_TABLES (used by WP03 too)."""
    table_names = [table for table, _ in _MIGRATION_TABLES]
    assert table_names == [
        "queue",
        "body_upload_queue",
        "body_upload_failure_log",
    ]
    queue_keys = dict(_MIGRATION_TABLES)["queue"]
    assert queue_keys == ("event_id",)
