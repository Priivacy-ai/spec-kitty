"""Historical body queues are immutable WP10 migration inputs.

The retired shared queue used to rename columns in place.  PROJECT_ONLY layout
never opens that database as a live queue: the public migration service takes a
read-only snapshot, partitions attributable rows into UUID-owned stores, and
leaves the source bytes unchanged.  These seven nodes preserve the old suite's
data, idempotence, empty/fresh-schema, uniqueness, and legacy-column intents at
that current boundary.
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
)


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT_A = "11111111-1111-4111-8111-111111111111"
PROJECT_B = "22222222-2222-4222-8222-222222222222"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 -- immutable source evidence


def _create_historical_body_source(
    path: Path,
    rows: tuple[tuple[int, str, str, str, str, str, str], ...],
    *,
    include_body_task_id: bool = False,
) -> None:
    connection = sqlite3.connect(path)
    identity_column = ", body_task_id TEXT" if include_body_task_id else ""
    connection.execute(
        "CREATE TABLE body_upload_queue ("
        "id INTEGER PRIMARY KEY"
        f"{identity_column}, "
        "project_uuid TEXT NOT NULL, mission_slug TEXT NOT NULL, "
        "target_branch TEXT NOT NULL, mission_type TEXT NOT NULL, "
        "manifest_version TEXT NOT NULL, artifact_path TEXT NOT NULL, "
        "content_hash TEXT NOT NULL, hash_algorithm TEXT NOT NULL, "
        "content_body TEXT NOT NULL, size_bytes INTEGER NOT NULL, "
        "retry_count INTEGER NOT NULL, next_attempt_at REAL NOT NULL, "
        "created_at REAL NOT NULL, last_error TEXT)"
    )
    for row_id, project, mission, mission_type, artifact, digest, body in rows:
        columns = "id, project_uuid"
        values: tuple[object, ...] = (row_id, project)
        if include_body_task_id:
            columns = "id, body_task_id, project_uuid"
            values = (row_id, "shared-body-task", project)
        connection.execute(
            f"INSERT INTO body_upload_queue ({columns}, mission_slug, target_branch, "  # noqa: S608 -- closed test schema
            "mission_type, manifest_version, artifact_path, content_hash, "
            "hash_algorithm, content_body, size_bytes, retry_count, "
            "next_attempt_at, created_at, last_error) "
            "VALUES (" + ", ".join("?" for _ in range(len(values) + 13)) + ")",
            (
                *values,
                mission,
                "main",
                mission_type,
                "1",
                artifact,
                digest,
                "sha256",
                body,
                len(body.encode("utf-8")),
                0,
                0.0,
                1000.0 + row_id,
                None,
            ),
        )
    connection.commit()
    connection.close()


def _body_rows(project: str) -> list[tuple[str, str, str, str]]:
    with ProjectSyncStore(project).unit_of_work() as unit:
        rows = unit.execute("SELECT body_task_id, content_hash, body_reference, state FROM body_upload_tasks ORDER BY body_task_id").fetchall()
    return [(str(row[0]), str(row[1]), str(row[2]), str(row[3])) for row in rows]


def test_historical_body_rows_copy_to_project_store_without_source_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy-body.db"
    _create_historical_body_source(
        source,
        (
            (1, PROJECT_A, "feat-a", "software-dev", "spec.md", "h1", "# Spec"),
            (2, PROJECT_A, "feat-b", "research", "plan.md", "h2", "# Plan"),
            (3, PROJECT_A, "feat-c", "documentation", "tasks.md", "h3", "# Tasks"),
        ),
    )
    before = _sha256(source)

    completed = LegacyProjectStoreMigration(runtime, (source,)).migrate("body-copy")

    assert completed.phase is MigrationPhase.COMPLETE
    rows = _body_rows(PROJECT_A)
    assert [(row[0], row[1]) for row in rows] == [("1", "h1"), ("2", "h2"), ("3", "h3")]
    references = [json.loads(row[2]) for row in rows]
    assert [(item["mission_slug"], item["mission_type"], item["artifact_path"]) for item in references] == [
        ("feat-a", "software-dev", "spec.md"),
        ("feat-b", "research", "plan.md"),
        ("feat-c", "documentation", "tasks.md"),
    ]
    assert _sha256(source) == before


def test_body_migration_rerun_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy-body.db"
    _create_historical_body_source(
        source,
        ((1, PROJECT_A, "feat", "software-dev", "spec.md", "hash", "body"),),
    )
    migration = LegacyProjectStoreMigration(runtime, (source,))

    first = migration.migrate("body-idempotent")
    second = migration.migrate("body-idempotent")

    assert second == first
    assert len(_body_rows(PROJECT_A)) == 1


def test_empty_body_table_previews_without_cutover_or_source_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "empty-body.db"
    _create_historical_body_source(source, ())
    before = _sha256(source)

    preview = LegacyProjectStoreMigration(runtime, (source,)).preview("empty-body")

    assert preview.phase is MigrationPhase.INVENTORIED
    assert preview.total_rows == 0
    assert preview.partitions == {}
    assert preview.sources[0].tables == ("body_upload_queue",)
    assert _sha256(source) == before


def test_source_without_tables_previews_as_empty_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "empty.db"
    sqlite3.connect(source).close()

    preview = LegacyProjectStoreMigration(runtime, (source,)).preview("no-tables")

    assert preview.total_rows == 0
    assert preview.sources[0].tables == ()
    assert preview.partitions == {}
    assert preview.quarantine == ()


def test_fresh_project_store_uses_canonical_body_task_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))

    with ProjectSyncStore(PROJECT_A).unit_of_work() as unit:
        columns = {str(row[1]) for row in unit.execute("PRAGMA table_info(body_upload_tasks)")}

    assert columns == {
        "body_task_id",
        "project_uuid",
        "epoch_id",
        "capture_sequence",
        "content_hash",
        "body_reference",
        "state",
        "created_at",
    }
    assert {"mission_slug", "mission_type", "feature_slug", "mission_key"}.isdisjoint(columns)


def test_same_historical_body_identity_is_isolated_by_project_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source_a = tmp_path / "project-a.db"
    source_b = tmp_path / "project-b.db"
    _create_historical_body_source(
        source_a,
        ((1, PROJECT_A, "a", "software-dev", "spec.md", "hash-a", "body-a"),),
        include_body_task_id=True,
    )
    _create_historical_body_source(
        source_b,
        ((1, PROJECT_B, "b", "software-dev", "spec.md", "hash-b", "body-b"),),
        include_body_task_id=True,
    )

    completed = LegacyProjectStoreMigration(runtime, (source_a, source_b)).migrate("body-isolation")

    assert set(completed.partitions) == {PROJECT_A, PROJECT_B}
    assert [(row[0], row[1]) for row in _body_rows(PROJECT_A)] == [("shared-body-task", "hash-a")]
    assert [(row[0], row[1]) for row in _body_rows(PROJECT_B)] == [("shared-body-task", "hash-b")]


def test_historical_column_names_are_inventory_only_and_preserved_as_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy-columns.db"
    _create_historical_body_source(
        source,
        ((1, PROJECT_A, "mission-047", "software-dev", "tasks.md", "hash", "payload"),),
    )
    before = _sha256(source)
    migration = LegacyProjectStoreMigration(runtime, (source,))

    preview = migration.preview("legacy-columns")
    columns = preview.sources[0].table_columns["body_upload_queue"]
    completed = migration.migrate("legacy-columns")

    assert {"mission_slug", "mission_type"}.issubset(columns)
    assert completed.phase is MigrationPhase.COMPLETE
    reference = json.loads(_body_rows(PROJECT_A)[0][2])
    assert (reference["mission_slug"], reference["mission_type"]) == ("mission-047", "software-dev")
    assert _sha256(source) == before
