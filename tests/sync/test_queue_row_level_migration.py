"""Row-level legacy queues migrate through the WP10 project-store boundary.

The former suite copied and deleted rows between a machine-global queue and a
hash-scoped queue.  Both are retired.  These eleven nodes retain its partition,
unrelated-state, idempotence, counting, retry, atomicity, and durability intent
against the public immutable-source migration and PROJECT_ONLY cutover APIs.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

import pytest

from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.event_journal.models import Event
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.project_store_migration import (
    LegacyProjectStoreMigration,
    MigrationError,
    MigrationPhase,
    MigrationTestHooks,
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

PROJECT_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
PROJECT_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 -- immutable source evidence


def _create_legacy_source(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE queue (
            id INTEGER PRIMARY KEY,
            event_id TEXT UNIQUE NOT NULL,
            event_type TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            coalesce_key TEXT
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
        CREATE TABLE body_upload_failure_log (
            id INTEGER PRIMARY KEY,
            project_uuid TEXT,
            artifact_path TEXT,
            content_hash TEXT,
            failure_reason TEXT
        );
        """
    )
    return connection


def _insert_event(
    connection: sqlite3.Connection,
    row_id: int,
    event_id: str,
    project: str,
) -> None:
    event = Event(
        event_id=event_id,
        event_type="MissionChanged",
        payload=json.dumps({"ordinal": row_id}, sort_keys=True).encode("utf-8"),
        occurred_at="2026-08-01T00:00:00Z",
        created_at="2026-08-01T00:00:00Z",
        project_uuid=project,
    )
    legacy_envelope = asdict(event)
    legacy_envelope["payload"] = json.loads(event.payload)
    connection.execute(
        "INSERT INTO queue VALUES (?, ?, 'MissionChanged', ?, ?, 0, NULL)",
        (
            row_id,
            event_id,
            json.dumps(legacy_envelope, sort_keys=True),
            1_700_000_000 + row_id,
        ),
    )


def _insert_body(
    connection: sqlite3.Connection,
    row_id: int,
    project: str,
    artifact_path: str,
) -> None:
    connection.execute(
        "INSERT INTO body_upload_queue VALUES (?, ?, 'mission', 'main', 'software-dev', '1', ?, ?, 'sha256', '# body', 6, 0, 0.0, ?)",
        (row_id, project, artifact_path, f"hash-{row_id}", 1_700_000_000.0 + row_id),
    )


def _insert_failure(
    connection: sqlite3.Connection,
    row_id: int,
    project: str,
) -> None:
    connection.execute(
        "INSERT INTO body_upload_failure_log VALUES (?, ?, 'spec.md', 'hash', 'offline')",
        (row_id, project),
    )


def _seed_mixed_source(
    path: Path,
    *,
    project: str = PROJECT_A,
    include_second_project: bool = False,
) -> None:
    connection = _create_legacy_source(path)
    _insert_event(connection, 1, "event-a1", project)
    _insert_event(connection, 2, "event-a2", project)
    _insert_body(connection, 1, project, "spec.md")
    _insert_body(connection, 2, project, "plan.md")
    _insert_failure(connection, 1, project)
    if include_second_project:
        _insert_event(connection, 3, "event-b1", PROJECT_B)
        _insert_body(connection, 3, PROJECT_B, "tasks.md")
    connection.commit()
    connection.close()


def _project_counts(project: str) -> tuple[int, int]:
    with ProjectSyncStore(project).unit_of_work() as unit:
        events = int(unit.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0])
        bodies = int(unit.execute("SELECT COUNT(*) FROM body_upload_tasks").fetchone()[0])
    return events, bodies


def _raise_on_phase(target: MigrationPhase) -> Callable[[MigrationPhase], None]:
    def stop(phase: MigrationPhase) -> None:
        if phase is target:
            raise SystemExit(f"simulated stop after {phase.value}")

    return stop


def test_preview_partitions_queue_and_body_and_quarantines_retired_failure_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed_mixed_source(source)
    before = _sha256(source)

    preview = LegacyProjectStoreMigration(runtime, (source,)).preview("mixed-preview")

    assert preview.total_rows == 5
    assert [(row.table, row.row_id) for row in preview.partitions[PROJECT_A]] == [
        ("body_upload_queue", "1"),
        ("body_upload_queue", "2"),
        ("queue", "event-a1"),
        ("queue", "event-a2"),
    ]
    assert [(row.table, row.reason) for row in preview.quarantine] == [("body_upload_failure_log", QuarantineReason.INCOMPATIBLE_ROW)]
    assert _sha256(source) == before


def test_migration_preserves_unrelated_project_store_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed_mixed_source(source)
    with ProjectSyncStore(PROJECT_A).unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://app.spec-kitty.ai', 'account-a', 'team-a', 7, "
            "'admitted', '9', 'private-teamspace:team-a')",
            (PROJECT_A,),
        )

    LegacyProjectStoreMigration(runtime, (source,)).migrate("preserve-unrelated")

    with ProjectSyncStore(PROJECT_A).unit_of_work() as unit:
        admission = unit.execute(
            "SELECT target_identity, configuration_generation, admission_generation FROM project_target_admissions WHERE project_uuid = ?",
            (PROJECT_A,),
        ).fetchone()
    assert admission == ("https://app.spec-kitty.ai", 7, "9")
    assert _project_counts(PROJECT_A) == (2, 2)


def test_migration_is_idempotent_without_deleting_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed_mixed_source(source)
    before = _sha256(source)
    migration = LegacyProjectStoreMigration(runtime, (source,))

    first = migration.migrate("idempotent")
    second = migration.migrate("idempotent")

    assert first == second
    assert _project_counts(PROJECT_A) == (2, 2)
    assert _sha256(source) == before


def test_preview_reports_exact_partition_and_quarantine_subtotals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed_mixed_source(source, include_second_project=True)

    preview = LegacyProjectStoreMigration(runtime, (source,)).preview("subtotals")

    partition_counts = {
        project: {table: sum(row.table == table for row in rows) for table in ("queue", "body_upload_queue")} for project, rows in preview.partitions.items()
    }
    assert partition_counts == {
        PROJECT_A: {"queue": 2, "body_upload_queue": 2},
        PROJECT_B: {"queue": 1, "body_upload_queue": 1},
    }
    assert len(preview.quarantine) == 1
    assert sum(len(rows) for rows in preview.partitions.values()) + len(preview.quarantine) == preview.total_rows == 7


def test_missing_legacy_source_fails_closed_without_creating_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "absent.db"

    with pytest.raises(MigrationError, match="legacy source is absent"):
        LegacyProjectStoreMigration(runtime, (source,)).preview("missing")

    assert not source.exists()


def test_migratable_and_quarantined_table_census_comes_from_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed_mixed_source(source)

    preview = LegacyProjectStoreMigration(runtime, (source,)).preview("table-census")

    assert preview.sources[0].tables == (
        "body_upload_failure_log",
        "body_upload_queue",
        "queue",
    )
    assert set(preview.sources[0].table_columns) == set(preview.sources[0].tables)
    assert {row.table for row in preview.partitions[PROJECT_A]} == {"queue", "body_upload_queue"}
    assert {row.table for row in preview.quarantine} == {"body_upload_failure_log"}


def test_multi_project_rows_land_only_in_their_uuid_owned_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed_mixed_source(source, include_second_project=True)

    completed = LegacyProjectStoreMigration(runtime, (source,)).migrate("two-projects")

    assert completed.phase is MigrationPhase.COMPLETE
    assert _project_counts(PROJECT_A) == (2, 2)
    assert _project_counts(PROJECT_B) == (1, 1)
    with ProjectSyncStore(PROJECT_A).unit_of_work() as unit_a:
        assert unit_a.execute("SELECT COUNT(*) FROM journal_entries WHERE project_uuid = ?", (PROJECT_B,)).fetchone() == (0,)
    with ProjectSyncStore(PROJECT_B).unit_of_work() as unit_b:
        assert unit_b.execute("SELECT COUNT(*) FROM body_upload_tasks WHERE project_uuid = ?", (PROJECT_A,)).fetchone() == (0,)


def test_interrupted_after_copy_resumes_without_duplicate_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed_mixed_source(source)
    migration = LegacyProjectStoreMigration(runtime, (source,))

    with pytest.raises(SystemExit, match="copied"):
        migration.migrate(
            "resume-copy",
            hooks=MigrationTestHooks(after_phase=_raise_on_phase(MigrationPhase.COPIED)),
        )
    assert migration.status("resume-copy").phase is MigrationPhase.COPIED

    completed = migration.migrate("resume-copy")

    assert completed.phase is MigrationPhase.COMPLETE
    assert _project_counts(PROJECT_A) == (2, 2)


def test_manifest_exposes_exact_source_row_count_without_global_scope_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed_mixed_source(source, include_second_project=True)

    preview = LegacyProjectStoreMigration(runtime, (source,)).preview("row-count")

    assert preview.sources[0].row_count == 7
    assert preview.total_rows == 7
    assert len(preview.partitions[PROJECT_A]) == 4
    assert len(preview.partitions[PROJECT_B]) == 2
    assert len(preview.quarantine) == 1


def test_prepublication_failure_never_publishes_project_only_layout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed_mixed_source(source)
    migration = LegacyProjectStoreMigration(runtime, (source,))

    def fail_before_publish() -> None:
        raise RuntimeError("simulated publication failure")

    with pytest.raises(RuntimeError, match="publication failure"):
        migration.migrate(
            "atomic-publication",
            hooks=MigrationTestHooks(before_project_only_publish=fail_before_publish),
        )

    assert migration.status("atomic-publication").phase is MigrationPhase.FAILED
    assert ProjectSyncStore(PROJECT_A).layout_generation().read_state().mode is not LayoutMode.PROJECT_ONLY


def test_cutover_interrupt_resumes_to_complete_with_source_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed_mixed_source(source)
    before = _sha256(source)
    migration = LegacyProjectStoreMigration(runtime, (source,))

    with pytest.raises(SystemExit, match="cutover"):
        migration.migrate(
            "resume-cutover",
            hooks=MigrationTestHooks(after_phase=_raise_on_phase(MigrationPhase.CUTOVER)),
        )
    assert migration.status("resume-cutover").phase is MigrationPhase.CUTOVER
    assert ProjectSyncStore(PROJECT_A).layout_generation().read_state().mode is LayoutMode.PROJECT_ONLY

    completed = migration.migrate("resume-cutover")

    assert completed.phase is MigrationPhase.COMPLETE
    assert _project_counts(PROJECT_A) == (2, 2)
    assert _sha256(source) == before
