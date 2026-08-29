"""Public acceptance contract for one UUID-owned project sync store."""

from __future__ import annotations

import inspect
import sqlite3
from pathlib import Path

import pytest

from specify_cli.paths import windows_paths
from specify_cli.state.contract import STATE_SURFACES
from specify_cli.sync import project_store as project_store_module
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import (
    ProjectStoreCorruptError,
    ProjectStoreOwnerMismatchError,
    ProjectSyncStore,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


PROJECT_A = "AAAAAAAA000000000000000000000001"
PROJECT_B = "aaaaaaaa-0000-0000-0000-000000000002"
CANONICAL_A = "aaaaaaaa-0000-0000-0000-000000000001"


EXPECTED_AGGREGATE_COLUMNS = {
    "project_store_metadata": (
        "singleton",
        "project_uuid",
        "schema_version",
        "layout_version",
        "created_at",
    ),
    "project_consent_decisions": (
        "project_uuid",
        "state",
        "generation",
        "action",
        "actor",
        "decided_at",
        "decision_schema_version",
    ),
    "capture_sequences": ("project_uuid", "next_sequence"),
    "consent_epochs": (
        "epoch_id",
        "project_uuid",
        "opened_at_tail",
        "state",
        "consent_generation",
        "sealed_at_tail",
        "sealed_at",
        "reason",
    ),
    "journal_entries": (
        "entry_id",
        "project_uuid",
        "epoch_id",
        "capture_sequence",
        "payload_json",
        "created_at",
    ),
    "outbox_tasks": (
        "task_id",
        "project_uuid",
        "epoch_id",
        "journal_entry_id",
        "task_kind",
        "state",
        "idempotency_identity",
        "created_at",
    ),
    "body_upload_tasks": (
        "body_task_id",
        "project_uuid",
        "epoch_id",
        "capture_sequence",
        "content_hash",
        "body_reference",
        "state",
        "created_at",
    ),
    "project_target_admissions": (
        "project_uuid",
        "target_identity",
        "account_identity",
        "private_teamspace_id",
        "configuration_generation",
        "admission_state",
        "admission_generation",
        "binding_audience",
        "last_error_category",
    ),
    "admission_operations": (
        "operation_key",
        "project_uuid",
        "action",
        "expected_generation",
        "target_identity",
        "account_identity",
        "private_teamspace_id",
        "configuration_generation",
        "request_payload_hash",
        "request_payload_version",
        "state",
        "result_state",
        "result_generation",
        "binding_audience",
        "original_error_category",
        "attempts",
        "created_at",
        "updated_at",
    ),
    "history_disclosure_actions": (
        "action_id",
        "project_uuid",
        "idempotency_key",
        "source_epoch_ids_json",
        "row_ids_json",
        "preview_count",
        "preview_hash",
        "confirmed_by",
        "confirmed_at",
        "consent_generation",
        "target_generation",
        "admission_generation",
        "binding_audience",
        "state",
        "result_ids_json",
    ),
    "delivery_attempts": (
        "attempt_id",
        "project_uuid",
        "epoch_id",
        "outbox_task_id",
        "consent_generation",
        "target_generation",
        "admission_generation",
        "binding_audience",
        "payload_hash",
        "payload_reference",
        "state",
        "deadline_at",
        "reconciliation_policy",
        "created_at",
    ),
    "delivery_results": (
        "result_id",
        "project_uuid",
        "epoch_id",
        "attempt_id",
        "target_generation",
        "admission_generation",
        "outcome",
        "terminal_refusal_category",
        "recorded_at",
    ),
    "migration_manifests": (
        "migration_id",
        "project_uuid",
        "protocol_version",
        "source_paths",
        "source_fingerprints_json",
        "partition_json",
        "quarantine_json",
        "phase",
        "cutover_version",
        "started_at",
        "completed_at",
    ),
    "migration_cutover_state": (
        "singleton",
        "project_uuid",
        "migration_id",
        "phase",
        "cutover_version",
        "updated_at",
    ),
}


EXPECTED_AGGREGATE_FOREIGN_KEYS = {
    "project_store_metadata": set(),
    "project_consent_decisions": {
        ("project_store_metadata", "project_uuid", "project_uuid"),
    },
    "capture_sequences": {
        ("project_store_metadata", "project_uuid", "project_uuid"),
    },
    "consent_epochs": {
        ("project_store_metadata", "project_uuid", "project_uuid"),
    },
    "journal_entries": {
        ("consent_epochs", "project_uuid", "project_uuid"),
        ("consent_epochs", "epoch_id", "epoch_id"),
    },
    "outbox_tasks": {
        ("consent_epochs", "project_uuid", "project_uuid"),
        ("consent_epochs", "epoch_id", "epoch_id"),
        ("journal_entries", "project_uuid", "project_uuid"),
        ("journal_entries", "journal_entry_id", "entry_id"),
    },
    "body_upload_tasks": {
        ("consent_epochs", "project_uuid", "project_uuid"),
        ("consent_epochs", "epoch_id", "epoch_id"),
    },
    "project_target_admissions": {
        ("project_store_metadata", "project_uuid", "project_uuid"),
    },
    "admission_operations": {
        ("project_store_metadata", "project_uuid", "project_uuid"),
    },
    "history_disclosure_actions": {
        ("project_store_metadata", "project_uuid", "project_uuid"),
    },
    "delivery_attempts": {
        ("consent_epochs", "project_uuid", "project_uuid"),
        ("consent_epochs", "epoch_id", "epoch_id"),
        ("outbox_tasks", "project_uuid", "project_uuid"),
        ("outbox_tasks", "outbox_task_id", "task_id"),
    },
    "delivery_results": {
        ("consent_epochs", "project_uuid", "project_uuid"),
        ("consent_epochs", "epoch_id", "epoch_id"),
        ("delivery_attempts", "project_uuid", "project_uuid"),
        ("delivery_attempts", "attempt_id", "attempt_id"),
    },
    "migration_manifests": {
        ("project_store_metadata", "project_uuid", "project_uuid"),
    },
    "migration_cutover_state": {
        ("project_store_metadata", "project_uuid", "project_uuid"),
        ("migration_manifests", "project_uuid", "project_uuid"),
        ("migration_manifests", "migration_id", "migration_id"),
    },
}


def test_project_uuid_is_canonicalized_once_before_any_path_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))

    variants = (
        PROJECT_A,
        "AAAAAAAA-0000-0000-0000-000000000001",
        "{aaaaaaaa-0000-0000-0000-000000000001}",
    )
    stores = [ProjectSyncStore(project_uuid) for project_uuid in variants]

    assert {str(store.project_uuid) for store in stores} == {CANONICAL_A}
    assert stores[0].database_path == runtime / "projects" / CANONICAL_A / "sync" / "sync.db"
    assert stores[0].egress_lock_path == stores[0].database_path.with_name("egress.lock")
    assert stores[0].migration_report_dir == stores[0].database_path.parent / "migration" / "reports"
    assert stores[0].project_uuid.storage_token.isascii()
    assert not runtime.exists(), "path resolution is pure and must not create state"

    for invalid in (
        None,
        "",
        " ",
        "00000000-0000-0000-0000-000000000000",
        "not-a-uuid",
        "urn:uuid:aaaaaaaa-0000-0000-0000-000000000001",
    ):
        with pytest.raises((TypeError, ValueError)):
            ProjectSyncStore(invalid)  # type: ignore[arg-type]
    assert not runtime.exists(), "invalid identities must fail before filesystem creation"


@pytest.mark.parametrize("display_name", ["Café", "東京-プロジェクト"])
def test_display_text_and_checkout_location_cannot_select_storage(
    display_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    checkout_one = tmp_path / display_name / "one"
    checkout_two = tmp_path / display_name / "two"

    store_one = ProjectSyncStore(PROJECT_A)
    store_two = ProjectSyncStore(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B)

    assert checkout_one != checkout_two  # Worktree paths are deliberately irrelevant.
    assert store_one.database_path == store_two.database_path
    assert store_one.database_path != store_b.database_path
    assert display_name not in str(store_one.database_path)
    assert store_one.project_uuid.storage_token.isascii()
    assert tuple(inspect.signature(ProjectSyncStore).parameters) == ("project_uuid",)


def test_opening_project_a_never_opens_or_creates_project_b(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store_a = ProjectSyncStore(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B)
    opened: list[Path] = []
    real_connect = project_store_module.sqlite3.connect

    def tracked_connect(database: str | Path, **kwargs: object) -> sqlite3.Connection:
        opened.append(Path(database))
        return real_connect(database, **kwargs)

    monkeypatch.setattr(project_store_module.sqlite3, "connect", tracked_connect)

    with store_a.unit_of_work() as unit:
        row = unit.execute("SELECT project_uuid, schema_version, layout_version FROM project_store_metadata").fetchone()

    assert tuple(row) == (CANONICAL_A, store_a.schema_version, store_a.layout_version)
    assert store_a.database_path.is_file()
    assert opened == [store_a.database_path]
    assert not store_b.database_path.exists()
    assert not store_b.database_path.parent.exists()


def test_store_schema_contains_the_whole_transactional_aggregate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)

    with store.unit_of_work() as unit:
        tables = {str(row[0]) for row in unit.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}

    assert set(EXPECTED_AGGREGATE_COLUMNS) <= tables

    with store.unit_of_work() as unit:
        for table, expected_columns in EXPECTED_AGGREGATE_COLUMNS.items():
            columns = tuple(str(row[1]) for row in unit.execute(f'PRAGMA table_info("{table}")').fetchall())
            assert columns == expected_columns, table
            foreign_keys = {(str(row[2]), str(row[3]), str(row[4])) for row in unit.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()}
            assert foreign_keys == EXPECTED_AGGREGATE_FOREIGN_KEYS[table], table

    surfaces = {surface.name: surface for surface in STATE_SURFACES}
    assert surfaces["project_sync_store"].owner_module == "sync/project_store"
    assert surfaces["project_sync_egress_lock"].owner_module == "sync/project_store"
    assert surfaces["project_sync_layout_generation"].owner_module == ("sync/layout_generation")
    assert surfaces["project_sync_layout_generation_lock"].owner_module == ("sync/layout_generation")
    assert surfaces["project_sync_layout_generation_marker"].owner_module == ("sync/layout_generation")


def test_admission_operation_schema_pins_t024_states_and_payload_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)

    with store.unit_of_work() as unit:
        row = unit.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'admission_operations'").fetchone()

    assert row is not None
    schema = str(row[0])
    for state in ("prepared", "sent", "acknowledged", "refused", "unknown"):
        assert f"'{state}'" in schema
    for superseded in ("'pending'", "'in_flight'", "'succeeded'", "'conflict'"):
        assert superseded not in schema
    assert "request_payload_hash TEXT NOT NULL" in schema
    assert "request_payload_version INTEGER NOT NULL" in schema
    assert "configuration_generation INTEGER NOT NULL" in schema
    assert "original_error_category TEXT" in schema


def test_owner_tamper_fails_closed_without_rewriting_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)
    with store.unit_of_work():
        pass

    with sqlite3.connect(store.database_path) as connection:
        connection.execute(
            "UPDATE project_store_metadata SET project_uuid = ?",
            (PROJECT_B,),
        )
    before = store.database_path.read_bytes()

    with pytest.raises(ProjectStoreOwnerMismatchError), store.unit_of_work():
        pytest.fail("owner-mismatched stores must never expose a unit of work")

    assert store.database_path.read_bytes() == before


def test_corrupt_store_is_preserved_and_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)
    store.database_path.parent.mkdir(parents=True)
    evidence = b"not a sqlite database\x00incident-evidence"
    store.database_path.write_bytes(evidence)

    with pytest.raises(ProjectStoreCorruptError), store.unit_of_work():
        pytest.fail("corrupt stores must never expose a unit of work")

    assert store.database_path.read_bytes() == evidence


def test_canonical_uuid_value_rejects_loose_identity_objects() -> None:
    assert CanonicalProjectUUID.parse(PROJECT_A).storage_token == CANONICAL_A
    with pytest.raises(TypeError):
        CanonicalProjectUUID.parse(object())


@pytest.mark.parametrize("platform", ["linux", "darwin", "win32"])
def test_runtime_override_is_identical_on_every_supported_platform(
    platform: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "Café-東京" / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    monkeypatch.setattr(windows_paths, "_current_platform", lambda: platform)

    store = ProjectSyncStore(PROJECT_A)

    assert store.database_path == (runtime / "projects" / CANONICAL_A / "sync" / "sync.db")
    assert store.project_uuid.storage_token.isascii()
