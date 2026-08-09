"""Public acceptance contract for one UUID-owned project sync store."""

from __future__ import annotations

import inspect
import sqlite3
from pathlib import Path

import pytest

from specify_cli.state.contract import STATE_SURFACES
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import (
    ProjectStoreCorruptError,
    ProjectStoreOwnerMismatchError,
    ProjectSyncStore,
)


PROJECT_A = "AAAAAAAA000000000000000000000001"
PROJECT_B = "aaaaaaaa-0000-0000-0000-000000000002"
CANONICAL_A = "aaaaaaaa-0000-0000-0000-000000000001"


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

    for invalid in (None, "", " ", "00000000-0000-0000-0000-000000000000", "not-a-uuid"):
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

    with store_a.unit_of_work() as unit:
        row = unit.execute(
            "SELECT project_uuid, schema_version, layout_version FROM project_store_metadata"
        ).fetchone()

    assert tuple(row) == (CANONICAL_A, store_a.schema_version, store_a.layout_version)
    assert store_a.database_path.is_file()
    assert not store_b.database_path.exists()
    assert not store_b.database_path.parent.exists()


def test_store_schema_contains_the_whole_transactional_aggregate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)

    with store.unit_of_work() as unit:
        tables = {
            str(row[0])
            for row in unit.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {
        "project_store_metadata",
        "project_consent_decisions",
        "consent_epochs",
        "capture_sequences",
        "journal_entries",
        "delivery_attempts",
        "delivery_results",
        "outbox_tasks",
        "body_upload_tasks",
        "project_target_admissions",
        "admission_operations",
        "history_disclosure_actions",
        "migration_manifests",
        "migration_cutover_state",
    } <= tables

    surfaces = {surface.name: surface for surface in STATE_SURFACES}
    assert surfaces["project_sync_store"].owner_module == "sync/project_store"
    assert surfaces["project_sync_egress_lock"].owner_module == "sync/project_store"


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

    with pytest.raises(ProjectStoreOwnerMismatchError):
        with store.unit_of_work():
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

    with pytest.raises(ProjectStoreCorruptError):
        with store.unit_of_work():
            pytest.fail("corrupt stores must never expose a unit of work")

    assert store.database_path.read_bytes() == evidence


def test_canonical_uuid_value_rejects_loose_identity_objects() -> None:
    assert CanonicalProjectUUID.parse(PROJECT_A).storage_token == CANONICAL_A
    with pytest.raises(TypeError):
        CanonicalProjectUUID.parse(object())

