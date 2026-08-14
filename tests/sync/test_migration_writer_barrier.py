"""WP10 cutover/barrier and crash-resume acceptance tests."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path
from typing import cast

import pytest

from specify_cli.sync.layout_generation import LayoutDestination, LayoutMode
from specify_cli.sync.daemon_protocol import (
    DaemonCutoverProtocol,
    QuiesceAcknowledgement,
    RestartAcknowledgement,
)
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.project_store_migration import (
    LegacyProjectStoreMigration,
    MigrationError,
    MigrationPhase,
    MigrationTestHooks,
)


pytestmark = [pytest.mark.fast]
PROJECT = "33333333-3333-4333-8333-333333333333"


def _source(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE event_journal (event_id TEXT PRIMARY KEY, event_type TEXT, payload BLOB, occurred_at TEXT, created_at TEXT, project_uuid TEXT)"
    )
    connection.execute(
        "INSERT INTO event_journal VALUES ('event-1','mission.changed',?, '2026-08-01T00:00:00Z','2026-08-01T00:00:00Z',?)",
        (json.dumps({"event_id": "event-1", "project_uuid": PROJECT}), PROJECT),
    )
    connection.commit()
    connection.close()


def test_exact_verification_is_required_before_project_only_cutover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "legacy.db"
    _source(source)
    migration = LegacyProjectStoreMigration(tmp_path / "runtime", (source,))
    preview = migration.preview("migration-verify")

    def stop_after_quiesce(phase: MigrationPhase) -> None:
        if phase is MigrationPhase.QUIESCED:
            raise SystemExit(73)

    with pytest.raises(SystemExit):
        migration.migrate(
            "migration-verify",
            hooks=MigrationTestHooks(after_phase=stop_after_quiesce),
        )
    connection = sqlite3.connect(source)
    connection.execute(
        "INSERT INTO event_journal VALUES ('event-late','mission.changed',?, '2026-08-01T00:00:01Z','2026-08-01T00:00:01Z',?)",
        (json.dumps({"event_id": "event-late", "project_uuid": PROJECT}), PROJECT),
    )
    connection.commit()
    connection.close()

    with pytest.raises(Exception, match="changed|verification"):
        migration.migrate("migration-verify")

    state = ProjectSyncStore(PROJECT).layout_generation().read_state()
    assert state.mode is not LayoutMode.PROJECT_ONLY
    assert migration.status("migration-verify").phase is MigrationPhase.FAILED
    failed = migration.status("migration-verify")
    assert failed.source_digest == preview.source_digest
    assert failed.observed_source_digest != preview.source_digest


def test_writer_commit_before_quiesce_is_captured_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _source(source)

    class WriterDuringQuiesce:
        def quiesce(self, migration_id: str) -> QuiesceAcknowledgement:
            connection = sqlite3.connect(source)
            connection.execute(
                "INSERT INTO event_journal VALUES ('event-writer-won','mission.changed',?, '2026-08-01T00:00:01Z','2026-08-01T00:00:01Z',?)",
                (
                    json.dumps({"event_id": "event-writer-won", "project_uuid": PROJECT}),
                    PROJECT,
                ),
            )
            connection.commit()
            connection.close()
            return QuiesceAcknowledgement(migration_id, 1, 1, "test")

        def restart(self, migration_id: str) -> RestartAcknowledgement:
            return RestartAcknowledgement(migration_id, 1, "test")

    migration = LegacyProjectStoreMigration(
        runtime,
        (source,),
        daemon_protocol=cast(DaemonCutoverProtocol, WriterDuringQuiesce()),
    )
    assert migration.preview("migration-writer-wins").total_rows == 1

    completed = migration.migrate("migration-writer-wins")

    assert completed.total_rows == 2
    with ProjectSyncStore(PROJECT).unit_of_work() as unit:
        assert unit.execute("SELECT entry_id FROM journal_entries ORDER BY entry_id").fetchall() == [("event-1",), ("event-writer-won",)]


def test_post_cutover_old_binary_write_is_residue_not_live_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "legacy.db"
    _source(source)
    migration = LegacyProjectStoreMigration(tmp_path / "runtime", (source,))
    migration.migrate("migration-residue")

    connection = sqlite3.connect(source)
    connection.execute(
        "INSERT INTO event_journal VALUES ('event-residue','mission.changed',?, '2026-08-01T00:00:02Z','2026-08-01T00:00:02Z',?)",
        (
            json.dumps({"event_id": "event-residue", "project_uuid": PROJECT}),
            PROJECT,
        ),
    )
    connection.commit()
    connection.close()

    residue = migration.diagnose_residue("migration-residue")

    assert [(row.row_id, row.reason, row.evidence["residue_change"]) for row in residue] == [("event-residue", "post_cutover_residue", "added")]
    assert migration.status("migration-residue").residue == residue
    with ProjectSyncStore(PROJECT).unit_of_work() as unit:
        assert unit.execute("SELECT entry_id FROM journal_entries ORDER BY entry_id").fetchall() == [("event-1",)]
        assert unit.execute("SELECT COUNT(*) FROM outbox_tasks").fetchone() == (0,)


def test_hard_kill_after_each_phase_resumes_to_one_exact_copy(
    tmp_path: Path,
) -> None:
    package_root = Path(__file__).resolve().parents[2] / "src"
    script = (
        "import os,sys\n"
        "from pathlib import Path\n"
        "from specify_cli.sync.project_store_migration import LegacyProjectStoreMigration,MigrationPhase,MigrationTestHooks\n"
        "runtime,source,phase,migration_id=sys.argv[1:]\n"
        "os.environ['SPEC_KITTY_HOME']=runtime\n"
        "def after(value):\n"
        "  if value.value==phase: os._exit(73)\n"
        "LegacyProjectStoreMigration(Path(runtime),(Path(source),)).migrate(migration_id,hooks=MigrationTestHooks(after_phase=after))\n"
    )
    for phase in (
        MigrationPhase.INVENTORIED,
        MigrationPhase.QUIESCED,
        MigrationPhase.COPIED,
        MigrationPhase.VERIFIED,
        MigrationPhase.CUTOVER,
        MigrationPhase.RESTARTED,
    ):
        phase_root = tmp_path / phase.value
        phase_root.mkdir()
        runtime = phase_root / "runtime"
        source = phase_root / "legacy.db"
        _source(source)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(package_root)
        migration_id = f"migration-kill-{phase.value}"
        killed = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(runtime),
                str(source),
                phase.value,
                migration_id,
            ],
            env=env,
            check=False,
        )
        assert killed.returncode == 73
        os.environ["SPEC_KITTY_HOME"] = str(runtime)
        completed = LegacyProjectStoreMigration(runtime, (source,)).migrate(migration_id)
        assert completed.phase is MigrationPhase.COMPLETE
        with ProjectSyncStore(PROJECT).unit_of_work() as unit:
            assert unit.execute("SELECT COUNT(*) FROM journal_entries").fetchone() == (1,)


def test_writer_redirects_once_when_cutover_wins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    authority = store.layout_generation()
    permit = authority.issue_write_permit()
    assert permit.destination is LayoutDestination.LEGACY
    authority.begin_cutover("migration-writer")
    authority.publish_project_only("migration-writer", verify_exact=lambda: True)
    observed: list[LayoutDestination] = []

    final = authority.execute_write(permit, lambda current: observed.append(current.destination))

    assert observed == [LayoutDestination.PROJECT_STORE]
    assert final.redirect_count == 1


def test_commit_immediately_before_cutover_is_in_winning_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "legacy.db"
    _source(source)
    migration = LegacyProjectStoreMigration(tmp_path / "runtime", (source,))
    original = migration._cutover

    def commit_then_cutover(manifest: object, *, hooks: MigrationTestHooks | None) -> object:
        connection = sqlite3.connect(source)
        connection.execute(
            "INSERT INTO event_journal VALUES ('event-late','mission.changed',?, '2026-08-01T00:00:01Z','2026-08-01T00:00:01Z',?)",
            (json.dumps({"event_id": "event-late", "project_uuid": PROJECT}), PROJECT),
        )
        connection.commit()
        connection.close()
        return original(cast("object", manifest), hooks=hooks)  # type: ignore[arg-type]

    monkeypatch.setattr(migration, "_cutover", commit_then_cutover)
    completed = migration.migrate("migration-late-before-cutover")

    assert completed.total_rows == 2
    with ProjectSyncStore(PROJECT).unit_of_work() as unit:
        assert unit.execute("SELECT entry_id FROM journal_entries ORDER BY entry_id").fetchall() == [
            ("event-1",),
            ("event-late",),
        ]


def test_writer_waiting_post_verify_redirects_once_after_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "legacy.db"
    _source(source)
    store = ProjectSyncStore(PROJECT)
    authority = store.layout_generation()
    permit = authority.issue_write_permit()
    entered = threading.Event()
    finished = threading.Event()
    observed: list[LayoutDestination] = []

    def writer(current: object) -> None:
        destination = cast("object", current).destination  # type: ignore[attr-defined]
        observed.append(destination)
        if destination is not LayoutDestination.PROJECT_STORE:
            raise AssertionError("post-verify writer was not redirected")
        connection = sqlite3.connect(store.database_path)
        epoch_id = int(connection.execute("SELECT MAX(epoch_id) FROM consent_epochs").fetchone()[0])
        sequence = int(connection.execute("SELECT COALESCE(MAX(capture_sequence), 0) + 1 FROM journal_entries").fetchone()[0])
        connection.execute(
            "INSERT INTO journal_entries "
            "(entry_id, project_uuid, epoch_id, capture_sequence, payload_json, created_at) "
            "VALUES ('event-redirected', ?, ?, ?, ?, '2026-08-01T00:00:02Z')",
            (PROJECT, epoch_id, sequence, json.dumps({"event_id": "event-redirected", "project_uuid": PROJECT})),
        )
        connection.execute(
            "INSERT INTO capture_sequences (project_uuid, next_sequence) VALUES (?, ?) "
            "ON CONFLICT(project_uuid) DO UPDATE SET next_sequence = excluded.next_sequence",
            (PROJECT, sequence),
        )
        connection.commit()
        connection.close()

    def run_writer() -> None:
        entered.set()
        authority.execute_write(permit, writer)
        finished.set()

    thread: threading.Thread | None = None

    def start_waiting_writer() -> None:
        nonlocal thread
        thread = threading.Thread(target=run_writer)
        thread.start()
        assert entered.wait(timeout=2)
        assert not finished.is_set(), "writer crossed the machine lock before publication"

    LegacyProjectStoreMigration(tmp_path / "runtime", (source,)).migrate(
        "migration-continuous-lock",
        hooks=MigrationTestHooks(before_project_only_publish=start_waiting_writer),
    )
    assert thread is not None
    thread.join(timeout=5)
    assert finished.is_set()
    assert observed == [LayoutDestination.PROJECT_STORE]
    with ProjectSyncStore(PROJECT).unit_of_work() as unit:
        assert unit.execute("SELECT entry_id FROM journal_entries ORDER BY entry_id").fetchall() == [
            ("event-1",),
            ("event-redirected",),
        ]
    connection = sqlite3.connect(source)
    assert connection.execute("SELECT event_id FROM event_journal ORDER BY event_id").fetchall() == [("event-1",)]
    connection.close()


def test_new_migration_identity_cannot_rematerialize_post_cutover_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    source = tmp_path / "legacy.db"
    _source(source)
    LegacyProjectStoreMigration(tmp_path / "runtime", (source,)).migrate("migration-first")
    connection = sqlite3.connect(source)
    connection.execute(
        "INSERT INTO event_journal VALUES ('event-residue','mission.changed',?, '2026-08-01T00:00:03Z','2026-08-01T00:00:03Z',?)",
        (json.dumps({"event_id": "event-residue", "project_uuid": PROJECT}), PROJECT),
    )
    connection.commit()
    connection.close()

    with pytest.raises(MigrationError, match="project-only.*residue"):
        LegacyProjectStoreMigration(tmp_path / "runtime", (source,)).migrate("migration-second")

    with ProjectSyncStore(PROJECT).unit_of_work() as unit:
        assert unit.execute("SELECT entry_id FROM journal_entries ORDER BY entry_id").fetchall() == [("event-1",)]


def test_verification_failure_reports_only_safe_hashes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _source(source)
    marker = "RAW-TOKEN-MUST-NOT-LEAK"

    def corrupt_after_copy(phase: MigrationPhase) -> None:
        if phase is not MigrationPhase.COPIED:
            return
        with ProjectSyncStore(PROJECT).unit_of_work() as unit:
            unit.execute(
                "UPDATE journal_entries SET payload_json = ? WHERE entry_id = 'event-1'",
                (marker,),
            )

    migration = LegacyProjectStoreMigration(runtime, (source,))
    with pytest.raises(MigrationError) as captured:
        migration.migrate(
            "migration-safe-failure",
            hooks=MigrationTestHooks(after_phase=corrupt_after_copy),
        )

    manifest_text = (runtime / "projects" / ".migration" / "migration-safe-failure" / "manifest.json").read_text(encoding="utf-8")
    assert marker not in str(captured.value)
    assert marker not in manifest_text
    assert "actual_sha256" in str(captured.value)
    assert "diagnostic_sha256" in manifest_text


def test_cutover_resume_does_not_rehash_sanitized_manifest_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _source(source)
    migration = LegacyProjectStoreMigration(runtime, (source,))

    def stop_after_cutover(phase: MigrationPhase) -> None:
        if phase is MigrationPhase.CUTOVER:
            raise SystemExit(73)

    with pytest.raises(SystemExit):
        migration.migrate(
            "migration-stable-evidence",
            hooks=MigrationTestHooks(after_phase=stop_after_cutover),
        )
    path = runtime / "projects" / ".migration" / "migration-stable-evidence" / "manifest.json"
    before = json.loads(path.read_text(encoding="utf-8"))

    migration.migrate("migration-stable-evidence")
    after = json.loads(path.read_text(encoding="utf-8"))

    for field in ("sources", "partitions", "quarantine", "source_digest", "total_rows"):
        assert after[field] == before[field]
