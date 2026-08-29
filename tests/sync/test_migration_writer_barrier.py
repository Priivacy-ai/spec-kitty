"""WP10 cutover/barrier and crash-resume acceptance tests."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from specify_cli.sync.layout_generation import (
    LayoutDestination,
    LayoutMode,
    LayoutTestHooks,
    LayoutWritePermit,
)
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


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]
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
    # Post cutover-flip (WP03/IC-02) ``issue_write_permit`` no longer hands back a
    # raw LEGACY permit — it resolves greenfield roots straight to project_only.
    # Bind a permit to the legacy generation directly to model a writer that
    # obtained it before cutover advanced, which is what this barrier exercises.
    state = authority.read_state()
    assert state.mode is LayoutMode.LEGACY
    permit = LayoutWritePermit(
        project_uuid=store.project_uuid,
        generation=state.generation,
        destination=LayoutDestination.LEGACY,
    )
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
        return original(manifest, hooks=hooks)

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
    """A live capture that waits out a cutover window redirects exactly once to the
    project store after publication — it is never silently dropped to legacy (INV-5).

    WP03/IC-02 replaced the old lock-blocking writer barrier with a *bounded*
    block-and-retry whose deterministic sync point is the ``before_revalidate`` hook
    (the migration publishes mid-wait). This reconciles the pin to that model: hold
    the machine CUTOVER_PENDING under a foreign (operator-owned) migration id so the
    capture resolves to a LEGACY (pending) permit, publish project_only during the
    wait, and assert the event lands in the project store — a capture only succeeds
    against a project_store permit — with no legacy db left behind.
    """
    from specify_cli.event_journal.journal import EventJournal
    from specify_cli.event_journal.models import Event

    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    store = ProjectSyncStore(PROJECT)
    authority = store.layout_generation()
    authority.begin_cutover("held-by-operator-migration")

    observed: list[LayoutDestination] = []

    def publish_mid_wait(permit: LayoutWritePermit) -> None:
        if observed:
            return
        observed.append(permit.destination)
        authority.publish_project_only("held-by-operator-migration", verify_exact=lambda: True)

    event = Event(
        event_id="event-redirected",
        event_type="WPStatusChanged",
        payload=json.dumps({"event_id": "event-redirected", "project_uuid": PROJECT}).encode(),
        occurred_at="2026-08-01T00:00:02+00:00",
        created_at="2026-08-01T00:00:02+00:00",
        project_uuid=PROJECT,
        project_slug="continuous-lock",
        repo_slug="continuous-lock",
    )

    with store.unit_of_work() as unit:
        receipt = EventJournal(unit, authority).append(
            event,
            test_hooks=LayoutTestHooks(before_revalidate=publish_mid_wait),
        )
        assert EventJournal(unit, authority).count() == 1

    # The permit the capture waited on was LEGACY (pending); after publication the
    # write redirected once and landed against a project_store permit.
    assert observed == [LayoutDestination.LEGACY]
    assert receipt.inserted is True
    with ProjectSyncStore(PROJECT).unit_of_work() as unit:
        assert unit.execute(
            "SELECT entry_id FROM journal_entries ORDER BY entry_id"
        ).fetchall() == [("event-redirected",)]
    # Only the project store db exists — nothing was dropped to a legacy queue.
    assert list(runtime.rglob("*.db")) == [store.database_path]


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
