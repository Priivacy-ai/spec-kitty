"""WP10 acceptance tests for WAL-aware project-store migration."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.project_store_migration import (
    LegacyProjectStoreMigration,
    MigrationError,
    MigrationPhase,
    QuarantineReason,
    migration_artifact_path,
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


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 -- source-evidence integrity


def _seed_wal_source(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA wal_autocheckpoint=0")
    connection.executescript(
        """
        CREATE TABLE event_journal (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            payload BLOB NOT NULL,
            occurred_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            project_uuid TEXT
        );
        CREATE TABLE body_upload_queue (
            id INTEGER PRIMARY KEY,
            project_uuid TEXT,
            artifact_path TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            content_body TEXT NOT NULL,
            created_at REAL NOT NULL,
            state TEXT NOT NULL
        );
        CREATE TABLE delivery_attempts (
            attempt_id TEXT PRIMARY KEY,
            project_uuid TEXT,
            epoch_id INTEGER,
            outbox_task_id TEXT,
            consent_generation INTEGER,
            target_generation INTEGER,
            admission_generation TEXT,
            binding_audience TEXT,
            payload_hash TEXT,
            payload_reference TEXT,
            state TEXT NOT NULL,
            deadline_at TEXT,
            reconciliation_policy TEXT,
            created_at TEXT
        );
        CREATE TABLE delivery_results (
            result_id TEXT PRIMARY KEY,
            project_uuid TEXT,
            epoch_id INTEGER,
            attempt_id TEXT,
            target_generation INTEGER,
            admission_generation TEXT,
            outcome TEXT NOT NULL,
            terminal_refusal_category TEXT,
            recorded_at TEXT NOT NULL
        );
        CREATE TABLE legacy_consent (
            project_uuid TEXT PRIMARY KEY,
            granted INTEGER NOT NULL,
            refused INTEGER NOT NULL
        );
        """
    )
    for project, event in ((PROJECT_A, "event-a"), (PROJECT_B, "event-b")):
        connection.execute(
            "INSERT INTO event_journal VALUES (?, 'mission.changed', ?, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z', ?)",
            (event, json.dumps({"event_id": event, "project_uuid": project}), project),
        )
        connection.execute(
            "INSERT INTO body_upload_queue "
            "(project_uuid, artifact_path, content_hash, content_body, created_at, state) "
            "VALUES (?, 'spec.md', ?, '# body', 1.0, 'retry')",
            (project, f"hash-{event}"),
        )
    connection.execute(
        "INSERT INTO body_upload_queue "
        "(project_uuid, artifact_path, content_hash, content_body, created_at, state) "
        "VALUES ('   ', 'tasks/WP01.md', 'unknown', '# secret', 2.0, 'pending')"
    )
    connection.execute(
        "INSERT INTO delivery_attempts VALUES "
        "('attempt-a', ?, 40, NULL, 3, 7, '9', 'private-teamspace:team-a', "
        "'sha256:attempt-a', 'event:event-a', 'refused', '2026-09-01T00:00:00Z', "
        "'native_identity_query', '2026-08-01T00:00:01Z')",
        (PROJECT_A,),
    )
    connection.execute("INSERT INTO delivery_results VALUES ('result-a', NULL, 40, 'attempt-a', 7, '9', 'refused', 'project_refused', '2026-08-01T00:00:02Z')")
    connection.execute(
        "INSERT INTO delivery_results VALUES ('ghost', ?, 41, 'missing-attempt', 8, '1', 'delivered', NULL, '2026-08-01T00:00:03Z')",
        (PROJECT_B,),
    )
    connection.execute("INSERT INTO legacy_consent VALUES (?, 1, 0)", (PROJECT_A,))
    connection.execute("INSERT INTO legacy_consent VALUES (?, 0, 1)", (PROJECT_B,))
    connection.commit()
    assert Path(f"{path}-wal").exists(), "fixture must retain committed WAL bytes"
    return connection


def test_preview_includes_committed_wal_and_never_mutates_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    connection = _seed_wal_source(source)
    physical = (("main", source), ("wal", Path(f"{source}-wal")), ("shm", Path(f"{source}-shm")))
    before = {name: _sha(path) for name, path in physical}

    migration = LegacyProjectStoreMigration(tmp_path / "runtime", (source,))
    manifest = migration.preview("migration-wal")

    assert manifest.phase is MigrationPhase.INVENTORIED
    assert manifest.total_rows == 10
    assert manifest.sources[0].wal.present is True
    assert manifest.sources[0].wal.included_in_logical_snapshot is True
    assert manifest.sources[0].table_columns["event_journal"] == (
        "event_id",
        "event_type",
        "payload",
        "occurred_at",
        "created_at",
        "project_uuid",
    )
    assert set(manifest.partitions) == {PROJECT_A, PROJECT_B}
    assert any(row.reason is QuarantineReason.MISSING_PROJECT_UUID for row in manifest.quarantine)
    assert any(row.reason is QuarantineReason.LEDGER_GHOST for row in manifest.quarantine)
    manifest_report = migration_artifact_path(
        runtime,
        "migration-wal",
        "manifest.json",
    ).read_text(encoding="utf-8")
    quarantine_report = migration_artifact_path(
        runtime,
        "migration-wal",
        "quarantine.json",
    ).read_text(encoding="utf-8")
    assert "# body" not in manifest_report
    assert "# secret" not in manifest_report
    assert "# secret" not in quarantine_report
    assert "values_sha256" in manifest_report
    assert "values_sha256" in quarantine_report
    snapshot = runtime / "projects" / ".migration" / "migration-wal" / "snapshots" / "source-0.db"
    assert snapshot.stat().st_mode & 0o777 == 0o600
    assert {name: _sha(path) for name, path in physical} == before
    connection.close()


def test_hard_kill_leaves_only_private_raw_staging_and_resume_cleans_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    connection = _seed_wal_source(source)
    package_root = Path(__file__).resolve().parents[2] / "src"
    script = (
        "import os,sys\n"
        "from pathlib import Path\n"
        "import specify_cli.sync.project_store_migration as module\n"
        "runtime,source=sys.argv[1:]\n"
        "os.environ['SPEC_KITTY_HOME']=runtime\n"
        "def kill(source_stream,destination_stream,*args,**kwargs):\n"
        " destination_stream.write(source_stream.read(128));destination_stream.flush();os.fsync(destination_stream.fileno());os._exit(73)\n"
        "module.shutil.copyfileobj=kill\n"
        "module.LegacyProjectStoreMigration(Path(runtime),(Path(source),)).preview('migration-private-staging')\n"
    )
    killed = subprocess.run(
        [sys.executable, "-c", script, str(runtime), str(source)],
        env={**os.environ, "PYTHONPATH": str(package_root)},
        check=False,
    )
    assert killed.returncode == 73
    snapshots = runtime / "projects" / ".migration" / "migration-private-staging" / "snapshots"
    staging = snapshots / ".raw-staging"
    assert stat.S_IMODE(snapshots.stat().st_mode) == 0o700
    assert stat.S_IMODE(staging.stat().st_mode) == 0o700
    residual = tuple(staging.iterdir())
    assert residual
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in residual)

    manifest = LegacyProjectStoreMigration(runtime, (source,)).preview("migration-private-staging")

    assert manifest.total_rows == 10
    assert not staging.exists()
    snapshot = snapshots / "source-0.db"
    assert stat.S_IMODE(snapshot.stat().st_mode) == 0o600
    connection.close()


def test_incompatible_known_schema_fails_closed_without_source_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "incompatible.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE event_journal (event_id TEXT PRIMARY KEY)")
    connection.execute("INSERT INTO event_journal VALUES ('event-no-payload')")
    connection.commit()
    connection.close()
    before = _sha(source)

    with pytest.raises(MigrationError, match="incompatible.*payload"):
        LegacyProjectStoreMigration(tmp_path / "runtime", (source,)).preview("migration-incompatible")

    assert _sha(source) == before


def test_unknown_attributable_table_is_quarantined_not_silently_dropped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "unknown-table.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE future_payloads (id TEXT PRIMARY KEY, project_uuid TEXT NOT NULL, payload TEXT NOT NULL)")
    connection.execute(
        "INSERT INTO future_payloads VALUES ('future-1', ?, 'secret')",
        (PROJECT_A,),
    )
    connection.commit()
    connection.close()
    before = _sha(source)

    manifest = LegacyProjectStoreMigration(tmp_path / "runtime", (source,)).preview("migration-unknown-table")

    assert manifest.partitions == {}
    assert [(row.table, row.row_id, row.reason) for row in manifest.quarantine] == [("future_payloads", "future-1", QuarantineReason.INCOMPATIBLE_ROW)]
    assert _sha(source) == before


def _seed_single_event(path: Path, payload: str) -> None:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE event_journal (event_id TEXT PRIMARY KEY, payload BLOB NOT NULL, created_at TEXT, project_uuid TEXT)")
    connection.execute(
        "INSERT INTO event_journal VALUES ('shared-event', ?, '2026-08-01T00:00:00Z', ?)",
        (payload, PROJECT_A),
    )
    connection.commit()
    connection.close()


def test_divergent_cross_source_identity_is_wholly_quarantined(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source_a = tmp_path / "source-a.db"
    source_b = tmp_path / "source-b.db"
    _seed_single_event(source_a, json.dumps({"project_uuid": PROJECT_A, "value": "a"}))
    _seed_single_event(source_b, json.dumps({"project_uuid": PROJECT_A, "value": "b"}))

    manifest = LegacyProjectStoreMigration(
        tmp_path / "runtime",
        (source_a, source_b),
    ).preview("migration-divergent")

    assert manifest.partitions == {}
    assert [row.reason for row in manifest.quarantine] == [
        QuarantineReason.DIVERGENT_DUPLICATE,
        QuarantineReason.DIVERGENT_DUPLICATE,
    ]


def test_identical_cross_source_identity_converges_once_with_both_evidence_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source_a = tmp_path / "source-a.db"
    source_b = tmp_path / "source-b.db"
    payload = json.dumps({"project_uuid": PROJECT_A, "value": "same"})
    _seed_single_event(source_a, payload)
    _seed_single_event(source_b, payload)
    migration = LegacyProjectStoreMigration(
        tmp_path / "runtime",
        (source_a, source_b),
    )

    manifest = migration.migrate("migration-identical")

    assert len(manifest.partitions[PROJECT_A]) == 2
    with ProjectSyncStore(PROJECT_A).unit_of_work() as unit:
        assert unit.execute("SELECT entry_id, payload_json FROM journal_entries").fetchall() == [("shared-event", payload)]
        assert unit.execute("SELECT opened_at_tail, sealed_at_tail FROM consent_epochs").fetchone() == (0, 1)
        assert unit.execute("SELECT next_sequence FROM capture_sequences").fetchone() == (1,)


def test_copy_preserves_project_partition_state_and_never_promotes_grant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "legacy.db"
    connection = _seed_wal_source(source)
    migration = LegacyProjectStoreMigration(tmp_path / "runtime", (source,))

    completed = migration.migrate("migration-copy")

    assert completed.phase is MigrationPhase.COMPLETE
    for project, expected_event in ((PROJECT_A, "event-a"), (PROJECT_B, "event-b")):
        with ProjectSyncStore(project).unit_of_work() as unit:
            rows = unit.execute(
                "SELECT entry_id, payload_json FROM journal_entries WHERE project_uuid = ?",
                (project,),
            ).fetchall()
            assert [row[0] for row in rows] == [expected_event]
            assert unit.execute(
                "SELECT state, reason FROM consent_epochs WHERE project_uuid = ? AND reason = ?",
                (project, "legacy_migration:migration-copy"),
            ).fetchone() == ("sealed", "legacy_migration:migration-copy")
            decision = unit.execute(
                "SELECT state, action FROM project_consent_decisions WHERE project_uuid = ?",
                (project,),
            ).fetchone()
            if project == PROJECT_B:
                assert decision == ("refused", "migrated_refusal")
            else:
                assert decision is None, "legacy grants are report-only"
    with ProjectSyncStore(PROJECT_A).unit_of_work() as unit:
        assert unit.execute(
            "SELECT epoch_id, consent_generation, target_generation, admission_generation, "
            "binding_audience, payload_hash, payload_reference, state, deadline_at, "
            "reconciliation_policy, created_at FROM delivery_attempts"
        ).fetchone() == (
            40,
            3,
            7,
            "9",
            "private-teamspace:team-a",
            "sha256:attempt-a",
            "event:event-a",
            "refused",
            "2026-09-01T00:00:00Z",
            "native_identity_query",
            "2026-08-01T00:00:01Z",
        )
        assert unit.execute("SELECT outcome, terminal_refusal_category FROM delivery_results").fetchone() == ("refused", "project_refused")
    assert migration.quarantine("migration-copy")
    connection.close()


def test_rerun_is_idempotent_and_cross_project_stores_are_disjoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "legacy.db"
    connection = _seed_wal_source(source)
    migration = LegacyProjectStoreMigration(tmp_path / "runtime", (source,))
    first = migration.migrate("migration-repeat")
    second = migration.migrate("migration-repeat")

    assert second == first
    with ProjectSyncStore(PROJECT_A).unit_of_work() as unit_a:
        assert unit_a.execute("SELECT COUNT(*) FROM journal_entries").fetchone() == (1,)
        assert unit_a.execute("SELECT COUNT(*) FROM journal_entries WHERE project_uuid = ?", (PROJECT_B,)).fetchone() == (0,)
    with ProjectSyncStore(PROJECT_B).unit_of_work() as unit_b:
        assert unit_b.execute("SELECT COUNT(*) FROM journal_entries").fetchone() == (1,)
        assert unit_b.execute("SELECT COUNT(*) FROM journal_entries WHERE project_uuid = ?", (PROJECT_A,)).fetchone() == (0,)
    connection.close()


def test_malformed_delivery_attempt_is_quarantined_without_type_coercion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "malformed-attempt.db"
    connection = sqlite3.connect(source)
    connection.execute(
        "CREATE TABLE delivery_attempts (attempt_id TEXT PRIMARY KEY, project_uuid TEXT, "
        "epoch_id INTEGER, outbox_task_id TEXT, consent_generation INTEGER, "
        "target_generation, admission_generation TEXT, binding_audience TEXT, "
        "payload_hash TEXT, payload_reference TEXT, state TEXT, deadline_at TEXT, "
        "reconciliation_policy TEXT, created_at TEXT)"
    )
    connection.execute(
        "INSERT INTO delivery_attempts VALUES "
        "('attempt-bad', ?, 1, NULL, 1, 'not-an-int', '1', 'private-teamspace:t', "
        "'sha256:x', 'event:x', 'in_flight', '2026-09-01T00:00:00Z', "
        "'native_identity_query', '2026-08-01T00:00:00Z')",
        (PROJECT_A,),
    )
    connection.commit()
    connection.close()

    manifest = LegacyProjectStoreMigration(
        tmp_path / "runtime",
        (source,),
    ).preview("migration-malformed-attempt")

    assert manifest.partitions == {}
    assert [(row.row_id, row.reason) for row in manifest.quarantine] == [("attempt-bad", QuarantineReason.INCOMPATIBLE_ROW)]


def _create_canonical_transport_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE delivery_attempts (
            attempt_id TEXT PRIMARY KEY, project_uuid TEXT, epoch_id INTEGER,
            outbox_task_id TEXT, consent_generation INTEGER, target_generation INTEGER,
            admission_generation TEXT, binding_audience TEXT, payload_hash TEXT,
            payload_reference TEXT, state TEXT, deadline_at TEXT,
            reconciliation_policy TEXT, created_at TEXT
        );
        CREATE TABLE delivery_results (
            result_id TEXT PRIMARY KEY, project_uuid TEXT, epoch_id INTEGER,
            attempt_id TEXT, target_generation INTEGER, admission_generation TEXT,
            outcome TEXT, terminal_refusal_category TEXT, recorded_at TEXT
        );
        """
    )


def _insert_attempt(
    connection: sqlite3.Connection,
    *,
    attempt_id: str,
    outbox_task_id: str | None = None,
) -> None:
    connection.execute(
        "INSERT INTO delivery_attempts VALUES (?, ?, 5, ?, 2, 3, '4', "
        "'private-teamspace:team-a', 'sha256:payload', 'event:event-a', "
        "'in_flight', '2026-09-01T00:00:00Z', 'native_identity_query', "
        "'2026-08-01T00:00:00Z')",
        (attempt_id, PROJECT_A, outbox_task_id),
    )


def test_malformed_delivery_results_are_quarantined_without_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "malformed-results.db"
    connection = sqlite3.connect(source)
    _create_canonical_transport_tables(connection)
    _insert_attempt(connection, attempt_id="attempt-a")
    connection.executemany(
        "INSERT INTO delivery_results VALUES (?, ?, 5, 'attempt-a', 3, '4', ?, ?, ?)",
        (
            ("result-blank-time", PROJECT_A, "delivered", None, ""),
            ("result-invalid-outcome", PROJECT_A, "invented", None, "2026-08-01T00:00:01Z"),
            ("result-refused-no-category", PROJECT_A, "refused", None, "2026-08-01T00:00:02Z"),
        ),
    )
    connection.commit()
    connection.close()

    manifest = LegacyProjectStoreMigration(
        tmp_path / "runtime",
        (source,),
    ).preview("migration-malformed-results")

    assert [row.row_id for row in manifest.partitions[PROJECT_A]] == ["attempt-a"]
    assert [(row.row_id, row.reason) for row in manifest.quarantine] == [
        ("result-blank-time", QuarantineReason.INCOMPATIBLE_ROW),
        ("result-invalid-outcome", QuarantineReason.INCOMPATIBLE_ROW),
        ("result-refused-no-category", QuarantineReason.INCOMPATIBLE_ROW),
    ]


def test_delivery_result_requires_exact_shape_and_strict_rfc3339(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    extra_source = tmp_path / "extra-result-field.db"
    connection = sqlite3.connect(extra_source)
    _create_canonical_transport_tables(connection)
    connection.execute("ALTER TABLE delivery_results ADD COLUMN future_field TEXT")
    _insert_attempt(connection, attempt_id="attempt-extra")
    connection.execute(
        "INSERT INTO delivery_results VALUES ('result-extra', ?, 5, 'attempt-extra', 3, '4', 'delivered', NULL, '2026-08-01T00:00:01Z', 'not-canonical')",
        (PROJECT_A,),
    )
    connection.commit()
    connection.close()

    time_source = tmp_path / "result-times.db"
    connection = sqlite3.connect(time_source)
    _create_canonical_transport_tables(connection)
    _insert_attempt(connection, attempt_id="attempt-bad-time")
    _insert_attempt(connection, attempt_id="attempt-valid-time")
    connection.executemany(
        "INSERT INTO delivery_results VALUES (?, ?, 5, ?, 3, '4', 'delivered', NULL, ?)",
        (
            ("result-bad-time", PROJECT_A, "attempt-bad-time", "not-a-time"),
            (
                "result-valid-time",
                PROJECT_A,
                "attempt-valid-time",
                "2026-08-01t00:00:01z",
            ),
        ),
    )
    connection.commit()
    connection.close()

    manifest = LegacyProjectStoreMigration(
        tmp_path / "runtime",
        (extra_source, time_source),
    ).preview("migration-strict-result-shape")

    assert {(row.table, row.row_id) for row in manifest.partitions[PROJECT_A]} == {
        ("delivery_attempts", "attempt-bad-time"),
        ("delivery_attempts", "attempt-extra"),
        ("delivery_attempts", "attempt-valid-time"),
        ("delivery_results", "result-valid-time"),
    }
    assert {(row.row_id, row.reason) for row in manifest.quarantine} == {
        ("result-bad-time", QuarantineReason.INCOMPATIBLE_ROW),
        ("result-extra", QuarantineReason.INCOMPATIBLE_ROW),
    }


def test_non_null_outbox_reference_parks_attempt_and_dependent_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "outbox-reference.db"
    connection = sqlite3.connect(source)
    _create_canonical_transport_tables(connection)
    _insert_attempt(
        connection,
        attempt_id="attempt-outbox",
        outbox_task_id="task-not-migrated",
    )
    connection.execute(
        "INSERT INTO delivery_results VALUES ('result-outbox', ?, 5, 'attempt-outbox', 3, '4', 'unknown', NULL, '2026-08-01T00:00:01Z')",
        (PROJECT_A,),
    )
    connection.commit()
    connection.close()

    manifest = LegacyProjectStoreMigration(
        tmp_path / "runtime",
        (source,),
    ).preview("migration-outbox-reference")

    assert manifest.partitions == {}
    assert [(row.row_id, row.reason) for row in manifest.quarantine] == [
        ("attempt-outbox", QuarantineReason.INCOMPATIBLE_ROW),
        ("result-outbox", QuarantineReason.LEDGER_GHOST),
    ]


def test_visible_attempt_extension_parks_attempt_and_dependent_result_before_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "extended-attempt.db"
    connection = sqlite3.connect(source)
    _create_canonical_transport_tables(connection)
    _insert_attempt(connection, attempt_id="attempt-extended")
    connection.execute("ALTER TABLE delivery_attempts ADD COLUMN future_authority TEXT")
    connection.execute("UPDATE delivery_attempts SET future_authority = 'must-not-drop' WHERE attempt_id = 'attempt-extended'")
    connection.execute(
        "INSERT INTO delivery_results VALUES ('result-extended', ?, 5, 'attempt-extended', 3, '4', 'unknown', NULL, '2026-08-01T00:00:01Z')",
        (PROJECT_A,),
    )
    connection.commit()
    connection.close()

    manifest = LegacyProjectStoreMigration(
        tmp_path / "runtime",
        (source,),
    ).preview("migration-extended-attempt")

    assert manifest.partitions == {}
    assert [(row.row_id, row.reason) for row in manifest.quarantine] == [
        ("attempt-extended", QuarantineReason.INCOMPATIBLE_ROW),
        ("result-extended", QuarantineReason.LEDGER_GHOST),
    ]


def test_divergent_attempt_duplicate_parks_its_dependent_result_before_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source_a = tmp_path / "source-a.db"
    source_b = tmp_path / "source-b.db"
    for source in (source_a, source_b):
        connection = sqlite3.connect(source)
        _create_canonical_transport_tables(connection)
        _insert_attempt(connection, attempt_id="attempt-divergent")
        connection.commit()
        connection.close()

    connection = sqlite3.connect(source_a)
    connection.execute(
        "INSERT INTO delivery_results VALUES ('result-a', ?, 5, 'attempt-divergent', 3, '4', 'unknown', NULL, '2026-08-01T00:00:01Z')",
        (PROJECT_A,),
    )
    connection.commit()
    connection.close()

    connection = sqlite3.connect(source_b)
    connection.execute("UPDATE delivery_attempts SET payload_hash = 'sha256:other' WHERE attempt_id = 'attempt-divergent'")
    connection.commit()
    connection.close()

    manifest = LegacyProjectStoreMigration(
        tmp_path / "runtime",
        (source_a, source_b),
    ).preview("migration-divergent-attempt")

    assert manifest.partitions == {}
    assert {(Path(row.source_path).name, row.table, row.row_id): row.reason for row in manifest.quarantine} == {
        ("source-a.db", "delivery_attempts", "attempt-divergent"): QuarantineReason.DIVERGENT_DUPLICATE,
        ("source-a.db", "delivery_results", "result-a"): QuarantineReason.LEDGER_GHOST,
        ("source-b.db", "delivery_attempts", "attempt-divergent"): QuarantineReason.DIVERGENT_DUPLICATE,
    }


def test_generated_legacy_column_is_rejected_from_xinfo_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "generated-extension.db"
    connection = sqlite3.connect(source)
    connection.execute(
        "CREATE TABLE event_journal ("
        "event_id TEXT PRIMARY KEY, payload TEXT, project_uuid TEXT, "
        "generated_identity TEXT GENERATED ALWAYS AS (project_uuid) VIRTUAL)"
    )
    connection.commit()
    connection.close()

    with pytest.raises(MigrationError, match="generated or hidden columns"):
        LegacyProjectStoreMigration(
            tmp_path / "runtime",
            (source,),
        ).preview("migration-generated-extension")


def test_malformed_divergent_attempt_duplicate_poisons_all_copies_and_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source_a = tmp_path / "source-valid.db"
    source_b = tmp_path / "source-malformed.db"
    for source in (source_a, source_b):
        connection = sqlite3.connect(source)
        _create_canonical_transport_tables(connection)
        _insert_attempt(connection, attempt_id="attempt-poisoned")
        connection.commit()
        connection.close()

    connection = sqlite3.connect(source_a)
    connection.execute(
        "INSERT INTO delivery_results VALUES ('result-poisoned', ?, 5, 'attempt-poisoned', 3, '4', 'unknown', NULL, '2026-08-01T00:00:01Z')",
        (PROJECT_A,),
    )
    connection.commit()
    connection.close()

    connection = sqlite3.connect(source_b)
    connection.execute("UPDATE delivery_attempts SET target_generation = 'not-an-int' WHERE attempt_id = 'attempt-poisoned'")
    connection.commit()
    connection.close()

    manifest = LegacyProjectStoreMigration(
        tmp_path / "runtime",
        (source_a, source_b),
    ).preview("migration-malformed-duplicate")

    assert manifest.partitions == {}
    assert {(Path(row.source_path).name, row.table, row.row_id): row.reason for row in manifest.quarantine} == {
        ("source-valid.db", "delivery_attempts", "attempt-poisoned"): QuarantineReason.DIVERGENT_DUPLICATE,
        ("source-valid.db", "delivery_results", "result-poisoned"): QuarantineReason.LEDGER_GHOST,
        ("source-malformed.db", "delivery_attempts", "attempt-poisoned"): QuarantineReason.DIVERGENT_DUPLICATE,
    }


def test_delivery_attempt_timestamps_require_strict_rfc3339_with_lowercase_parity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "attempt-times.db"
    connection = sqlite3.connect(source)
    _create_canonical_transport_tables(connection)
    for attempt_id, deadline_at, created_at in (
        ("attempt-naive", "2026-09-01T00:00:00", "2026-08-01T00:00:00Z"),
        ("attempt-space", "2026-09-01 00:00:00Z", "2026-08-01T00:00:00Z"),
        ("attempt-impossible", "2026-09-31T00:00:00Z", "2026-08-01T00:00:00Z"),
        ("attempt-bad-created", "2026-09-01T00:00:00Z", "2026-08-01T00:00:00"),
        ("attempt-lowercase", "2026-09-01t00:00:00z", "2026-08-01t00:00:00z"),
        ("attempt-offset", "2026-09-01T00:00:00+02:00", "2026-08-01T00:00:00-04:00"),
    ):
        connection.execute(
            "INSERT INTO delivery_attempts VALUES (?, ?, 5, NULL, 2, 3, '4', "
            "'private-teamspace:team-a', 'sha256:payload', ?, 'in_flight', ?, "
            "'native_identity_query', ?)",
            (attempt_id, PROJECT_A, f"event:{attempt_id}", deadline_at, created_at),
        )
    connection.commit()
    connection.close()

    manifest = LegacyProjectStoreMigration(
        tmp_path / "runtime",
        (source,),
    ).preview("migration-attempt-times")

    assert {row.row_id for row in manifest.partitions[PROJECT_A]} == {
        "attempt-lowercase",
        "attempt-offset",
    }
    assert {(row.row_id, row.reason) for row in manifest.quarantine} == {
        ("attempt-naive", QuarantineReason.INCOMPATIBLE_ROW),
        ("attempt-space", QuarantineReason.INCOMPATIBLE_ROW),
        ("attempt-impossible", QuarantineReason.INCOMPATIBLE_ROW),
        ("attempt-bad-created", QuarantineReason.INCOMPATIBLE_ROW),
    }
