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

import pathlib
import sqlite3
from pathlib import Path

import pytest

from specify_cli.sync.queue import (
    _MIGRATION_TABLES,
    LegacyRowCounts,
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
    """NFR-001 + C-008: redirect HOME cross-platform.

    Patch ``pathlib.Path.home`` directly so the same fixture works on
    POSIX (``HOME``), Windows (``USERPROFILE``), and macOS (where
    ``pwd.getpwuid`` can shadow the env var). The env-var patches are
    kept as belt-and-braces for any code that reads them directly.
    """
    monkeypatch.setattr(
        pathlib.Path, "home", classmethod(lambda cls: tmp_path)
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
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


# ----------------------------------------------------------------------
# Scenario 5 (WP02 / T009): body-upload migration when scoped is non-empty.
#
# Spec: FR-006 (non-empty scoped DB merge) + FR-007 (body_upload coverage).
# Anchor: extends the WP01 anchor at line :231.
# ----------------------------------------------------------------------


def test_body_upload_migration_with_non_empty_scoped_db(
    _isolate_home: Path, tmp_path: Path
) -> None:
    """Body-upload rows in the legacy DB land in a populated scoped DB.

    Scoped DB starts with unrelated rows. Legacy DB carries two body-upload
    rows for the current scope (artifact paths /current/a and /current/b)
    plus one for a different scope (artifact path /other/x). After
    migration the scoped DB holds its prior rows plus the two
    current-scope rows; the legacy DB is drained because today there is
    no per-scope partitioning in legacy (every legacy row counts toward
    the active scope, per the helper's docstring).

    The "other scope" row in this fixture is modeled as a *different
    artifact-path key* so the schema-canonical unique constraint can tell
    it apart from the current-scope rows. Because the legacy DB cannot
    distinguish scopes, the migration drains all three rows — the
    coverage we are pinning is that body-upload rows survive a
    non-empty scoped DB, not legacy-side scope filtering.
    """
    legacy = _make_legacy_db(_isolate_home)
    scoped = _make_scoped_db(tmp_path)

    # Pre-seed scoped DB with unrelated rows that must not be touched.
    conn = sqlite3.connect(scoped)
    try:
        _insert_queue_row(conn, "scoped-evt-pre")
        _insert_body_upload_row(
            conn, project_uuid="pre-proj", artifact_path="/pre/x"
        )
        conn.commit()
    finally:
        conn.close()

    # Seed legacy with two current-scope body uploads and one we tag
    # "other-scope" to show that artifact-path keying preserves row
    # identity end-to-end.
    conn = sqlite3.connect(legacy)
    try:
        _insert_body_upload_row(conn, artifact_path="/current/a")
        _insert_body_upload_row(conn, artifact_path="/current/b")
        _insert_body_upload_row(
            conn, project_uuid="other-scope", artifact_path="/other/x"
        )
        conn.commit()
    finally:
        conn.close()

    migrated = _migrate_legacy_queue_to_scope(scoped)

    # 3 legacy body-upload rows merged into scoped.
    assert migrated == 3
    # Scoped now has 1 pre-existing + 3 migrated = 4 body uploads.
    assert _row_count(scoped, "body_upload_queue") == 4
    # Pre-existing scoped queue row is still there.
    assert _row_count(scoped, "queue") == 1

    # Verify the specific current-scope artifact paths survived as-is.
    conn = sqlite3.connect(scoped)
    try:
        scoped_paths = {
            row[0]
            for row in conn.execute("SELECT artifact_path FROM body_upload_queue")
        }
    finally:
        conn.close()
    assert {"/pre/x", "/current/a", "/current/b", "/other/x"} == scoped_paths


# ----------------------------------------------------------------------
# Scenario 6 (WP02 / T009): retries are safe — second pass is a no-op.
#
# Spec: R2 idempotence (research.md). Re-running migration on the same
# (legacy, scoped) pair must not duplicate rows or grow row counts.
# ----------------------------------------------------------------------


def test_migration_is_idempotent_on_retry(
    _isolate_home: Path, tmp_path: Path
) -> None:
    """Second migration pass leaves both DBs unchanged from the first."""
    legacy = _make_legacy_db(_isolate_home)
    scoped = _make_scoped_db(tmp_path)

    # Seed legacy with rows across all three migration tables.
    conn = sqlite3.connect(legacy)
    try:
        _insert_queue_row(conn, "evt-a")
        _insert_queue_row(conn, "evt-b")
        _insert_body_upload_row(conn, artifact_path="/retry/a")
        _insert_body_upload_row(conn, artifact_path="/retry/b")
        _insert_failure_log_row(conn, failure_reason="retry-1")
        conn.commit()
    finally:
        conn.close()

    first_migrated = _migrate_legacy_queue_to_scope(scoped)

    scoped_counts_after_first = {
        table: _row_count(scoped, table)
        for table, _ in _MIGRATION_TABLES
    }
    legacy_counts_after_first = {
        table: _row_count(legacy, table)
        for table, _ in _MIGRATION_TABLES
    }

    # Second pass: nothing left to migrate, counts must stay put.
    second_migrated = _migrate_legacy_queue_to_scope(scoped)

    assert first_migrated == 5
    assert second_migrated == 0

    for table, _ in _MIGRATION_TABLES:
        assert _row_count(scoped, table) == scoped_counts_after_first[table], (
            f"scoped {table} row count drifted on retry"
        )
        assert _row_count(legacy, table) == legacy_counts_after_first[table], (
            f"legacy {table} row count drifted on retry"
        )


# ----------------------------------------------------------------------
# Scenario 7 (WP02 / T009): detect_legacy_rows_for_scope returns subtotals.
#
# Spec: contracts/sync-boundary-preflight.md names `event_rows`,
# `body_upload_rows`, and a `total_rows` convenience field.
# ----------------------------------------------------------------------


def test_detect_legacy_rows_for_scope_returns_subtotals(
    _isolate_home: Path,
) -> None:
    """Structured return splits event vs body-upload subtotals."""
    legacy = _make_legacy_db(_isolate_home)

    conn = sqlite3.connect(legacy)
    try:
        _insert_queue_row(conn, "evt-1")
        _insert_queue_row(conn, "evt-2")
        _insert_queue_row(conn, "evt-3")
        _insert_body_upload_row(conn, artifact_path="/sub/a")
        _insert_body_upload_row(conn, artifact_path="/sub/b")
        conn.commit()
    finally:
        conn.close()

    counts = detect_legacy_rows_for_scope("https://test|alice|team-x")

    assert isinstance(counts, LegacyRowCounts)
    assert counts.event_rows == 3
    assert counts.body_upload_rows == 2
    assert counts.failure_log_rows == 0
    assert counts.total_rows == 5

    # Backwards-compat: the value still behaves like a per-table mapping
    # for callers that pre-date the structured return shape.
    assert counts.get("queue") == 3
    assert counts.get("body_upload_queue") == 2
    assert counts == {"queue": 3, "body_upload_queue": 2}


# ----------------------------------------------------------------------
# Scenario 8 (WP02 / T009): atomic rollback — failure halfway leaves
# neither row class in scoped.
#
# Spec: FR-006/FR-007 imply both row classes commit/rollback together.
# We inject a controlled failure by patching ``_migrate_one_table`` to
# raise on the second invocation (after ``queue`` rows have been
# inserted but before ``body_upload_queue`` rows commit). The wrapper
# must roll the dst connection back so the scoped DB ends up with zero
# migrated rows, and the legacy DB must still own everything.
# ----------------------------------------------------------------------


def test_migration_atomic_failure_rolls_back_body_uploads_too(
    _isolate_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mid-migration failure leaves neither row class in scoped."""
    from specify_cli.sync import queue as queue_mod

    legacy = _make_legacy_db(_isolate_home)
    scoped = _make_scoped_db(tmp_path)

    # Seed legacy with both row classes.
    conn = sqlite3.connect(legacy)
    try:
        _insert_queue_row(conn, "atomic-evt-1")
        _insert_queue_row(conn, "atomic-evt-2")
        _insert_body_upload_row(conn, artifact_path="/atomic/a")
        _insert_body_upload_row(conn, artifact_path="/atomic/b")
        conn.commit()
    finally:
        conn.close()

    real = queue_mod._migrate_one_table
    call_count = {"n": 0}

    def fail_on_body_uploads(*args: object, **kwargs: object) -> int:
        call_count["n"] += 1
        # First call processes ``queue`` rows; let it through.
        if call_count["n"] == 1:
            return real(*args, **kwargs)  # type: ignore[arg-type]
        # Second call would process ``body_upload_queue`` — simulate a
        # mid-migration crash. The wrapper must roll the dst connection
        # back, leaving the scoped DB pristine.
        raise RuntimeError("simulated body-upload migration failure")

    monkeypatch.setattr(queue_mod, "_migrate_one_table", fail_on_body_uploads)

    with pytest.raises(RuntimeError, match="simulated body-upload migration failure"):
        _migrate_legacy_queue_to_scope(scoped)

    # FR-006/FR-007 atomicity: scoped DB must be untouched by the failed
    # migration. Pre-existing rows (none here) must survive, and no
    # legacy row may have landed.
    assert _row_count(scoped, "queue") == 0
    assert _row_count(scoped, "body_upload_queue") == 0
    assert _row_count(scoped, "body_upload_failure_log") == 0

    # Legacy DB must still own every row — the partial DELETEs against
    # src that ran during the queue-table loop are also rolled back
    # because the wrapper never reaches ``src.commit()``.
    assert _row_count(legacy, "queue") == 2
    assert _row_count(legacy, "body_upload_queue") == 2


# ----------------------------------------------------------------------
# Scenario 9 (WP02 cycle 2): durability — dst.commit() must persist
# BEFORE src.commit() drops the legacy rows.
#
# Reviewer finding (cycle 1): the previous order
#     src.commit()
#     dst.commit()
# stranded rows if dst.commit() failed after src.commit() succeeded —
# the legacy rows were already gone but never persisted in scoped.
#
# Fix: reverse the order. dst.commit() runs first. If src.commit() fails
# after dst.commit() succeeds, the legacy DELETEs roll back, the legacy
# rows survive, and the migration can be replayed. The replay is safe
# because per-row INSERT OR IGNORE deduplicates on the schema-canonical
# unique key (event_id for queue, artifact-key for body uploads).
# ----------------------------------------------------------------------


def test_migration_durability_dst_commit_first(
    _isolate_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If src.commit() fails AFTER dst.commit() succeeds, the migration
    must leave the scoped rows persisted AND keep the legacy rows so a
    retry can complete cleanly without dropping data.
    """
    import sqlite3 as _sqlite3

    from specify_cli.sync import queue as queue_mod

    legacy = _make_legacy_db(_isolate_home)
    scoped = _make_scoped_db(tmp_path)

    # Seed legacy with rows across all three migration tables so we can
    # observe both row classes survive the durability window.
    conn = sqlite3.connect(legacy)
    try:
        _insert_queue_row(conn, "dur-evt-1")
        _insert_queue_row(conn, "dur-evt-2")
        _insert_body_upload_row(conn, artifact_path="/dur/a")
        _insert_body_upload_row(conn, artifact_path="/dur/b")
        _insert_failure_log_row(conn, failure_reason="dur-reason")
        conn.commit()
    finally:
        conn.close()

    original_connect = _sqlite3.connect
    dst_committed = {"flag": False}

    class _TrackingConnection:
        """Forwarding wrapper that lets the test observe commit ordering.

        - Records when the destination (scoped) connection commits.
        - Forces the source (legacy) connection's first commit to raise
          AFTER the destination has already committed. Subsequent
          commits (e.g. during the second retry pass) pass through.
        """

        def __init__(self, real: _sqlite3.Connection, role: str) -> None:
            self._real = real
            self._role = role
            self._fail_next_commit = role == "src"

        def commit(self) -> None:
            if self._role == "dst":
                self._real.commit()
                dst_committed["flag"] = True
                return
            # role == "src"
            if self._fail_next_commit:
                # Critical invariant under test: dst must have committed
                # before src tries to. If this ever flips, the order
                # regressed.
                assert dst_committed["flag"], (
                    "ordering regression: src.commit() ran before dst.commit()"
                )
                self._fail_next_commit = False
                raise _sqlite3.OperationalError(
                    "simulated src.commit failure after dst.commit succeeded"
                )
            self._real.commit()

        def __getattr__(self, name: str) -> object:
            return getattr(self._real, name)

    call_seq: list[str] = []

    def tracking_connect(target: object, *args: object, **kwargs: object) -> object:
        real_conn = original_connect(target, *args, **kwargs)  # type: ignore[arg-type]
        # Discriminate roles by path: the migration opens legacy first
        # (src), then scoped (dst). We compare against the known paths.
        target_path = Path(str(target))
        if target_path == legacy:
            role = "src"
        elif target_path == scoped:
            role = "dst"
        else:  # pragma: no cover — defensive
            return real_conn
        call_seq.append(role)
        return _TrackingConnection(real_conn, role)

    monkeypatch.setattr(queue_mod.sqlite3, "connect", tracking_connect)

    # First pass: dst commits, then src.commit() raises. The migration
    # call propagates the OperationalError.
    with pytest.raises(_sqlite3.OperationalError, match="simulated src.commit"):
        _migrate_legacy_queue_to_scope(scoped)

    # The destination must have committed before we tried to commit src.
    assert dst_committed["flag"], (
        "dst.commit() never ran — ordering invariant broken"
    )

    # Restore real sqlite3.connect so the post-failure assertions and
    # the retry pass see real connections.
    monkeypatch.setattr(queue_mod.sqlite3, "connect", original_connect)

    # Durability invariant 1: scoped DB has the migrated rows persisted
    # despite the src.commit() failure.
    assert _row_count(scoped, "queue") == 2
    assert _row_count(scoped, "body_upload_queue") == 2
    assert _row_count(scoped, "body_upload_failure_log") == 1

    # Durability invariant 2: legacy DB still owns every row because the
    # DELETEs against src were never committed (rolled back when
    # src.commit() raised, then the except branch ran src.rollback()).
    assert _row_count(legacy, "queue") == 2
    assert _row_count(legacy, "body_upload_queue") == 2
    assert _row_count(legacy, "body_upload_failure_log") == 1

    # Retry the migration without the patch in place. INSERT OR IGNORE
    # deduplicates against the rows already in scoped, and the legacy
    # rows are now safe to drain.
    migrated_retry = _migrate_legacy_queue_to_scope(scoped)

    # Every legacy row counts as "migrated" on the retry pass because
    # the helper treats already-landed rows as a successful merge before
    # deleting them from src.
    assert migrated_retry == 5

    # Final scoped row counts unchanged — INSERT OR IGNORE kicked in.
    assert _row_count(scoped, "queue") == 2
    assert _row_count(scoped, "body_upload_queue") == 2
    assert _row_count(scoped, "body_upload_failure_log") == 1

    # Legacy DB is now drained.
    assert _row_count(legacy, "queue") == 0
    assert _row_count(legacy, "body_upload_queue") == 0
    assert _row_count(legacy, "body_upload_failure_log") == 0
