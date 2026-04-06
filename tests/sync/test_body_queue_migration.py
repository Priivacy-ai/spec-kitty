"""Tests for body_upload_queue column rename migration (T032).

Verifies that the SQLite column rename migration:
- Preserves all data in populated queues (FR-020)
- Is idempotent (safe to run multiple times)
- Handles empty tables
- Handles fresh installs (no pre-existing table)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from specify_cli.sync.queue import (
    _migrate_body_queue_column_rename,
    ensure_body_queue_schema,
)

pytestmark = pytest.mark.fast

# Old schema with legacy column names
_OLD_SCHEMA = """
CREATE TABLE body_upload_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid TEXT NOT NULL,
    mission_slug TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    mission_type TEXT NOT NULL,
    manifest_version TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    hash_algorithm TEXT NOT NULL DEFAULT 'sha256',
    content_body TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL NOT NULL DEFAULT 0.0,
    created_at REAL NOT NULL,
    last_error TEXT,
    UNIQUE(project_uuid, mission_slug, target_branch, mission_type, manifest_version, artifact_path, content_hash)
);
"""


def _get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return set of column names for a table."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor}


def _insert_old_row(
    conn: sqlite3.Connection,
    project_uuid: str = "uuid-1",
    mission_slug: str = "047-feat",
    target_branch: str = "main",
    mission_type: str = "software-dev",
    manifest_version: str = "1",
    artifact_path: str = "spec.md",
    content_hash: str = "abc123",
    content_body: str = "# Spec",
    size_bytes: int = 6,
) -> None:
    """Insert a row using the old column names."""
    conn.execute(
        """INSERT INTO body_upload_queue
           (project_uuid, mission_slug, target_branch, mission_type,
            manifest_version, artifact_path, content_hash, hash_algorithm,
            content_body, size_bytes, retry_count, next_attempt_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'sha256', ?, ?, 0, 0.0, 1000.0)""",
        (
            project_uuid,
            mission_slug,
            target_branch,
            mission_type,
            manifest_version,
            artifact_path,
            content_hash,
            content_body,
            size_bytes,
        ),
    )
    conn.commit()


class TestBodyQueueColumnMigration:
    """Test the column rename migration for body_upload_queue."""

    def test_populated_queue_preserves_data(self, tmp_path: Path) -> None:
        """Old-schema table with rows: migration renames columns, preserves data."""
        db = tmp_path / "test.db"
        conn = sqlite3.connect(db)
        conn.executescript(_OLD_SCHEMA)

        # Insert 3 rows with different data
        _insert_old_row(conn, mission_slug="feat-a", mission_type="sw-dev", artifact_path="spec.md", content_hash="h1")
        _insert_old_row(conn, mission_slug="feat-b", mission_type="research", artifact_path="plan.md", content_hash="h2")
        _insert_old_row(conn, mission_slug="feat-c", mission_type="doc", artifact_path="tasks.md", content_hash="h3")

        # Verify old columns exist
        columns_before = _get_columns(conn, "body_upload_queue")
        assert "mission_slug" in columns_before
        assert "mission_type" in columns_before

        # Run migration
        _migrate_body_queue_column_rename(conn)

        # Verify new columns exist, old ones gone
        columns_after = _get_columns(conn, "body_upload_queue")
        assert "mission_slug" in columns_after
        assert "mission_type" in columns_after
        assert "feature_slug" not in columns_after
        assert "mission_key" not in columns_after

        # Verify all 3 rows preserved with data intact
        rows = conn.execute(
            "SELECT mission_slug, mission_type, artifact_path FROM body_upload_queue ORDER BY id"
        ).fetchall()
        assert len(rows) == 3
        assert rows[0] == ("feat-a", "sw-dev", "spec.md")
        assert rows[1] == ("feat-b", "research", "plan.md")
        assert rows[2] == ("feat-c", "doc", "tasks.md")

        conn.close()

    def test_idempotent_migration(self, tmp_path: Path) -> None:
        """Running migration twice does not error."""
        db = tmp_path / "test.db"
        conn = sqlite3.connect(db)
        conn.executescript(_OLD_SCHEMA)
        _insert_old_row(conn)

        # Run migration twice
        _migrate_body_queue_column_rename(conn)
        _migrate_body_queue_column_rename(conn)  # Should not raise

        # Verify columns are correct
        columns = _get_columns(conn, "body_upload_queue")
        assert "mission_slug" in columns
        assert "mission_type" in columns

        # Verify data still intact
        row = conn.execute("SELECT mission_slug, mission_type FROM body_upload_queue").fetchone()
        assert row == ("047-feat", "software-dev")

        conn.close()

    def test_empty_table_migration(self, tmp_path: Path) -> None:
        """Migration succeeds on empty table."""
        db = tmp_path / "test.db"
        conn = sqlite3.connect(db)
        conn.executescript(_OLD_SCHEMA)

        _migrate_body_queue_column_rename(conn)

        columns = _get_columns(conn, "body_upload_queue")
        assert "mission_slug" in columns
        assert "mission_type" in columns
        assert "feature_slug" not in columns
        assert "mission_key" not in columns

        conn.close()

    def test_no_table_skips_migration(self, tmp_path: Path) -> None:
        """Migration is a no-op when the table does not exist."""
        db = tmp_path / "test.db"
        conn = sqlite3.connect(db)

        # Should not raise when table doesn't exist
        _migrate_body_queue_column_rename(conn)

        conn.close()


class TestFreshInstallSchema:
    """Test that fresh installs create the table with canonical column names."""

    def test_fresh_install_uses_new_columns(self, tmp_path: Path) -> None:
        """ensure_body_queue_schema on empty DB creates table with mission_slug/mission_type."""
        db = tmp_path / "test.db"
        conn = sqlite3.connect(db)

        ensure_body_queue_schema(conn)

        columns = _get_columns(conn, "body_upload_queue")
        assert "mission_slug" in columns
        assert "mission_type" in columns
        assert "feature_slug" not in columns
        assert "mission_key" not in columns

        conn.close()

    def test_fresh_install_unique_constraint(self, tmp_path: Path) -> None:
        """Unique constraint uses new column names."""
        db = tmp_path / "test.db"
        conn = sqlite3.connect(db)
        ensure_body_queue_schema(conn)

        # Insert a row
        conn.execute(
            """INSERT INTO body_upload_queue
               (project_uuid, mission_slug, target_branch, mission_type,
                manifest_version, artifact_path, content_hash, content_body,
                size_bytes, created_at)
               VALUES ('uuid', 'slug', 'main', 'sw', '1', 'spec.md', 'h1', 'body', 4, 1000.0)"""
        )
        conn.commit()

        # Duplicate should be rejected by unique constraint
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO body_upload_queue
                   (project_uuid, mission_slug, target_branch, mission_type,
                    manifest_version, artifact_path, content_hash, content_body,
                    size_bytes, created_at)
                   VALUES ('uuid', 'slug', 'main', 'sw', '1', 'spec.md', 'h1', 'body2', 5, 2000.0)"""
            )

        conn.close()


class TestEnsureBodyQueueSchemaWithLegacyDB:
    """Test that ensure_body_queue_schema handles existing DBs with old columns."""

    def test_legacy_db_migrated_on_schema_ensure(self, tmp_path: Path) -> None:
        """Old DB with mission_slug/mission_type gets migrated when schema is ensured."""
        db = tmp_path / "test.db"
        conn = sqlite3.connect(db)
        conn.executescript(_OLD_SCHEMA)
        _insert_old_row(conn, mission_slug="my-feat", mission_type="my-type")

        # This is the real entrypoint called during queue init
        ensure_body_queue_schema(conn)

        columns = _get_columns(conn, "body_upload_queue")
        assert "mission_slug" in columns
        assert "mission_type" in columns

        row = conn.execute("SELECT mission_slug, mission_type FROM body_upload_queue").fetchone()
        assert row == ("my-feat", "my-type")

        conn.close()
