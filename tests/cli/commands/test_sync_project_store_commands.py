"""WP10 operator CLI for preview, migrate, status, and quarantine."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.sync import app
import specify_cli.cli.commands.sync as sync_command
from specify_cli.migration.envelope_seam import build_teamspace_envelope
from specify_cli.sync.project_context import ProjectSyncContext
from specify_cli.sync.project_store import ProjectSyncStore


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]
PROJECT = "44444444-4444-4444-8444-444444444444"


def _stored_history_event(event_id: str) -> dict[str, object]:
    """Serialize the legacy four-field row from the canonical envelope owner."""
    canonical = build_teamspace_envelope(
        event_id=event_id,
        event_type="MissionCreated",
        aggregate_id=event_id,
        aggregate_type="Mission",
        payload={},
        timestamp="2026-08-01T00:00:00+00:00",
        build_id="project-store-command-test",
        node_id="project-store-command-test",
        lamport_clock=1,
        project_uuid=PROJECT,
        project_slug="project-store-command-test",
        repo_slug=None,
        correlation_id=event_id,
    ).model_dump()
    return {key: canonical[key] for key in ("event_id", "event_type", "payload", "project_uuid")}


def _seed(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE event_journal (event_id TEXT PRIMARY KEY, event_type TEXT, payload BLOB, occurred_at TEXT, created_at TEXT, project_uuid TEXT)"
    )
    connection.execute(
        "INSERT INTO event_journal VALUES ('event-cli','mission.changed',?, '2026-08-01T00:00:00Z','2026-08-01T00:00:00Z',?)",
        (
            json.dumps(
                _stored_history_event("event-cli"),
                sort_keys=True,
                separators=(",", ":"),
            ),
            PROJECT,
        ),
    )
    connection.execute("INSERT INTO event_journal VALUES ('event-unknown','mission.changed','{}', '2026-08-01T00:00:00Z','2026-08-01T00:00:00Z',NULL)")
    connection.commit()
    connection.close()


def test_operator_flow_is_previewable_explicit_and_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    source = tmp_path / "legacy.db"
    _seed(source)
    runner = CliRunner()

    preview = runner.invoke(
        app,
        ["project-store-preview", "--source", str(source), "--migration-id", "cli-migration", "--json"],
    )
    assert preview.exit_code == 0, preview.output
    assert json.loads(preview.stdout)["phase"] == "inventoried"

    migrated = runner.invoke(
        app,
        ["project-store-migrate", "--source", str(source), "--migration-id", "cli-migration", "--json"],
    )
    assert migrated.exit_code == 0, migrated.output
    assert json.loads(migrated.stdout)["phase"] == "complete"

    status = runner.invoke(app, ["project-store-status", "--migration-id", "cli-migration", "--json"])
    assert status.exit_code == 0, status.output
    assert json.loads(status.stdout)["phase"] == "complete"

    connection = sqlite3.connect(source)
    connection.execute(
        "INSERT INTO event_journal VALUES ('event-residue','mission.changed',?, '2026-08-01T00:00:01Z','2026-08-01T00:00:01Z',?)",
        (
            json.dumps({"event_id": "event-residue", "project_uuid": PROJECT}),
            PROJECT,
        ),
    )
    connection.commit()
    connection.close()
    diagnosed = runner.invoke(
        app,
        [
            "project-store-status",
            "--migration-id",
            "cli-migration",
            "--diagnose-residue",
            "--json",
        ],
    )
    assert diagnosed.exit_code == 0, diagnosed.output
    assert json.loads(diagnosed.stdout)["residue"][0]["row_id"] == "event-residue"

    quarantine = runner.invoke(
        app,
        ["project-store-quarantine", "--migration-id", "cli-migration", "--json"],
    )
    assert quarantine.exit_code == 0, quarantine.output
    payload = json.loads(quarantine.stdout)
    assert payload[0]["row_id"] == "event-unknown"
    assert payload[0]["reason"] == "missing_project_uuid"
    assert payload[1]["row_id"] == "event-residue"
    assert payload[1]["reason"] == "post_cutover_residue"


def test_retired_shared_migrate_fails_before_runtime_or_consent_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sync_command,
        "_open_event_sync_runtime",
        lambda: pytest.fail("retired migration opened the live runtime"),
    )
    monkeypatch.setattr(
        sync_command,
        "_run_consent_index_backfill",
        lambda: pytest.fail("retired migration promoted legacy consent"),
    )

    result = CliRunner().invoke(app, ["migrate", "--backfill-consent-index"])

    assert result.exit_code == 1
    assert "shared-store `sync migrate` path is retired" in result.output
    assert "project-store-preview" in result.output


def test_retired_auto_convergence_is_guidance_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sync_command,
        "_open_event_sync_runtime",
        lambda: pytest.fail("automatic convergence opened a legacy source"),
    )

    sync_command._auto_converge_legacy_on_enable()

    assert "Automatic legacy convergence is retired" in capsys.readouterr().out


def _route_local_store(
    monkeypatch: pytest.MonkeyPatch,
    store: ProjectSyncStore,
) -> None:
    import specify_cli.sync.routing as routing

    monkeypatch.setattr(
        routing,
        "resolve_checkout_sync_routing_readonly",
        lambda: SimpleNamespace(
            project_uuid=store.project_uuid,
            project_slug="project-store-test",
            repo_slug=None,
            build_id=None,
        ),
    )
    monkeypatch.setattr(
        sync_command,
        "_current_event_sync_scope",
        lambda: SimpleNamespace(user_id=None, team_slug=None),
    )


@pytest.mark.parametrize("command", ["gc", "archive"])
def test_local_retention_refuses_legacy_layout_without_materializing_store(
    command: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_root))
    store = ProjectSyncStore(PROJECT)
    authority = store.layout_generation()
    _route_local_store(monkeypatch, store)

    result = CliRunner().invoke(app, [command])

    assert result.exit_code == 1
    assert "project store migration required" in result.output
    assert "project-store-migrate" in result.output
    assert not store.database_path.exists()
    assert not authority.record_path.exists()
    assert not authority.marker_path.exists()
    assert not authority.lock_path.exists()


def test_project_only_status_and_archive_are_offline_and_project_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from specify_cli.event_journal import Event
    from specify_cli.event_journal.journal import EventJournal
    from specify_cli.sync.migrate_journal import (
        AUDIT_DB_NAME,
        MigrationAudit,
        MigrationConflict,
    )

    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_root))
    store = ProjectSyncStore(PROJECT)
    authority = store.layout_generation()
    authority.begin_cutover("offline-status")
    authority.publish_project_only("offline-status", verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, authority)
        journal.append(
            Event(
                event_id="offline-status-event",
                event_type="mission.changed",
                payload=b"{}",
                occurred_at="2026-08-01T00:00:00Z",
                created_at="2026-08-01T00:00:00Z",
                project_uuid=PROJECT,
            )
        )
    _route_local_store(monkeypatch, store)
    from specify_cli.sync import queue as queue_module

    real_get_max_queue_size = queue_module.get_max_queue_size
    max_queue_reads = 0

    def max_queue_size_with_lock_probe() -> int:
        nonlocal max_queue_reads
        max_queue_reads += 1
        with store.unit_of_work(lock_timeout_seconds=0):
            pass
        return cast(int, cast(Any, real_get_max_queue_size)())

    monkeypatch.setattr(queue_module, "get_max_queue_size", max_queue_size_with_lock_probe)
    monkeypatch.setattr(
        sync_command,
        "_assert_event_sync_runtime_authority",
        lambda **_: pytest.fail("local status consulted authenticated transport authority"),
    )

    audit_path = runtime_root / AUDIT_DB_NAME
    audit = MigrationAudit(audit_path)
    audit.record_conflict(
        MigrationConflict(
            event_id="offline-conflict",
            source_digest="legacy",
            existing_sha="aaa",
            incoming_sha="bbb",
        )
    )
    audit.commit()
    audit.close()
    audit_bytes = audit_path.read_bytes()

    runtime = sync_command._open_event_sync_runtime()
    report = sync_command._event_sync_report({}, runtime)
    archived = CliRunner().invoke(app, ["archive"])

    assert report["event_journal"]["retained_event_count"] == 1
    assert max_queue_reads == 1
    assert report["migration_conflicts"]["conflicts"][0]["event_id"] == "offline-conflict"
    assert audit_path.read_bytes() == audit_bytes
    assert not Path(f"{audit_path}-wal").exists()
    assert not Path(f"{audit_path}-shm").exists()
    assert archived.exit_code == 0, archived.output
    with store.unit_of_work() as unit:
        stored = EventJournal(unit, authority).read_by_id("offline-status-event")
        assert stored is not None
        assert stored.archived_at is not None


def _migrated_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[SimpleNamespace, ProjectSyncStore]:
    from specify_cli.sync.project_store_migration import LegacyProjectStoreMigration

    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_root))
    source = tmp_path / "history-legacy.db"
    _seed(source)
    LegacyProjectStoreMigration(runtime_root, (source,)).migrate("history-migration")
    store = ProjectSyncStore(PROJECT)
    runtime = SimpleNamespace(
        store=store,
        context=store.create_context(),
        delivery_target=None,
        close=lambda: None,
    )
    monkeypatch.setattr(
        sync_command,
        "_open_project_dispatch_runtime",
        lambda: runtime,
    )
    return runtime, store


def test_history_preview_never_confirms_or_manufactures_legacy_grant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store = _migrated_runtime(tmp_path, monkeypatch)
    runner = CliRunner()

    preview = runner.invoke(app, ["project-store-history", "--json"])

    assert preview.exit_code == 0, preview.output
    payload = json.loads(preview.stdout)
    assert payload["state"] == "preview"
    assert payload["row_ids"] == ["event-cli"]
    assert payload["preview_count"] == 1
    with store.unit_of_work() as unit:
        assert unit.execute("SELECT COUNT(*) FROM history_disclosure_actions").fetchone() == (0,)
        assert unit.execute("SELECT COUNT(*) FROM project_consent_decisions").fetchone() == (0,)

    refused = runner.invoke(
        app,
        [
            "project-store-history",
            "--confirm-by",
            "operator:test",
            "--idempotency-key",
            "migration-history",
            "--json",
        ],
    )
    assert refused.exit_code == 1
    assert "requires current consent" in refused.output
    assert runtime.context.consent_generation is None


def _grant_history_authority(store: ProjectSyncStore) -> ProjectSyncContext:
    from specify_cli.sync.consent import record_project_opt_in

    record_project_opt_in(PROJECT, actor="operator:test")
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, "
            "binding_audience) VALUES (?, 'https://app.spec-kitty.ai', 'account-1', "
            "'teamspace-1', 1, 'admitted', '7', 'private-teamspace:teamspace-1')",
            (PROJECT,),
        )
    return store.create_context()


def test_history_confirmation_then_apply_uses_exact_wp07_capability_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from specify_cli.delivery.interfaces import DeliveryTarget, TargetIdentity
    from specify_cli.delivery.targets import compute_target_id
    from specify_cli.sync.history_import.upload import UploadReport
    from specify_cli.sync.project_context import AdmissionState
    from specify_cli.sync.project_identity import CanonicalProjectUUID

    runtime, store = _migrated_runtime(tmp_path, monkeypatch)
    context = _grant_history_authority(store)
    identity = TargetIdentity(
        target_identity="https://app.spec-kitty.ai",
        account_identity="account-1",
        private_teamspace_id="teamspace-1",
        project_uuid=CanonicalProjectUUID.parse(PROJECT),
        configuration_generation=1,
    )
    target = DeliveryTarget(
        target_id=compute_target_id(
            target_identity=identity.target_identity,
            account_identity=identity.account_identity,
            private_teamspace_id=identity.private_teamspace_id,
            project_uuid=identity.project_uuid,
            configuration_generation=identity.configuration_generation,
        ),
        identity=identity,
        admission_state=AdmissionState.ADMITTED,
        admission_generation=7,
        binding_audience="private-teamspace:teamspace-1",
        last_error_category=None,
    )
    runtime.context = context
    runtime.delivery_target = target
    runner = CliRunner()

    confirmation = runner.invoke(
        app,
        [
            "project-store-history",
            "--confirm-by",
            "operator:test",
            "--idempotency-key",
            "migration-history",
            "--json",
        ],
    )
    assert confirmation.exit_code == 0, confirmation.output
    action_id = json.loads(confirmation.stdout)["action_id"]

    monkeypatch.setattr(sync_command, "_event_sync_access_token", lambda: "token")
    receiver = SimpleNamespace(endpoint_url="https://app.spec-kitty.ai/batch")
    monkeypatch.setattr(
        sync_command,
        "_resolve_history_import_receiver",
        lambda current, *, token: (
            receiver,
            "https://app.spec-kitty.ai",
        ),
    )
    seen: dict[str, object] = {}

    def run_import_upload(envelopes: object, **kwargs: object) -> UploadReport:
        seen["envelopes"] = envelopes
        seen.update(kwargs)
        return UploadReport(success=1)

    import specify_cli.sync.history_import.upload as history_upload

    monkeypatch.setattr(history_upload, "run_import_upload", run_import_upload)

    applied = runner.invoke(
        app,
        [
            "project-store-history",
            "--apply",
            "--history-action-id",
            action_id,
            "--json",
        ],
    )

    assert applied.exit_code == 0, applied.output
    assert json.loads(applied.stdout)["ok"] is True
    assert seen["envelopes"] == [_stored_history_event("event-cli")]
    assert set(cast(list[dict[str, object]], seen["envelopes"])[0]) == {
        "event_id",
        "event_type",
        "payload",
        "project_uuid",
    }
    assert seen["project_context"] is context
    assert seen["target"] is target
    assert cast(Any, seen["history_capability"]).action_id == action_id


def test_strict_sync_refuses_zero_selection_when_retained_state_is_unknown() -> None:
    """A gate-blocked zero summary cannot erase the conservative retained signal."""
    from specify_cli.cli.commands.sync import _enforce_sync_now_exit_from_dispatch
    from specify_cli.delivery.dispatcher import DispatchSummary

    summary = DispatchSummary(
        target_id=None,
        selected=0,
        delivered=0,
        duplicate=0,
        pending=0,
        rejected=0,
        transient=0,
        terminal_failed=0,
    )
    with pytest.raises(typer.Exit) as excinfo:
        _enforce_sync_now_exit_from_dispatch(
            True,
            0,
            summary,
            retained_work_present=True,
        )
    assert excinfo.value.exit_code == 1
