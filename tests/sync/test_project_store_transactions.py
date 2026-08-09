"""Atomicity and connection-ownership acceptance tests for ProjectSyncStore."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from specify_cli.sync.project_store import (
    ProjectStoreLockedError,
    ProjectStoreVersionError,
    ProjectSyncStore,
    ProjectUnitOfWork,
)


PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


def _aggregate_mutations(unit: ProjectUnitOfWork, fail_after: int) -> None:
    statements: tuple[tuple[str, tuple[object, ...]], ...] = (
        (
            "INSERT INTO project_consent_decisions "
            "(project_uuid, state, generation, action, actor, decided_at, decision_schema_version) "
            "VALUES (?, 'granted', 1, 'explicit_opt_in', 'test-actor', '2026-08-10T00:00:00Z', 1)",
            (PROJECT_UUID,),
        ),
        (
            "INSERT INTO consent_epochs "
            "(epoch_id, project_uuid, opened_at_tail, state, consent_generation, reason) "
            "VALUES (1, ?, 0, 'eligible', 1, 'opt_in')",
            (PROJECT_UUID,),
        ),
        (
            "INSERT INTO journal_entries "
            "(entry_id, project_uuid, epoch_id, capture_sequence, payload_json) "
            "VALUES ('event-1', ?, 1, 1, '{}')",
            (PROJECT_UUID,),
        ),
        (
            "INSERT INTO outbox_tasks "
            "(task_id, project_uuid, epoch_id, journal_entry_id, task_kind, state) "
            "VALUES ('task-1', ?, 1, 'event-1', 'event', 'pending')",
            (PROJECT_UUID,),
        ),
        (
            "INSERT INTO delivery_attempts "
            "(attempt_id, project_uuid, epoch_id, outbox_task_id, state) "
            "VALUES ('attempt-1', ?, 1, 'task-1', 'pending')",
            (PROJECT_UUID,),
        ),
    )
    for index, (statement, parameters) in enumerate(statements, start=1):
        unit.execute(statement, parameters)
        if index == fail_after:
            raise RuntimeError(f"fault after mutation {index}")


def _counts(store: ProjectSyncStore) -> tuple[int, ...]:
    with store.unit_of_work() as unit:
        return tuple(
            int(unit.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (
                "project_consent_decisions",
                "consent_epochs",
                "journal_entries",
                "outbox_tasks",
                "delivery_attempts",
            )
        )


@pytest.mark.parametrize("fail_after", range(1, 6))
def test_fault_between_any_bundle_mutation_rolls_back_the_outer_transaction(
    fail_after: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / f"runtime-{fail_after}"))
    store = ProjectSyncStore(PROJECT_UUID)

    with (
        pytest.raises(RuntimeError, match="fault after mutation"),
        store.unit_of_work() as unit,
    ):
        _aggregate_mutations(unit, fail_after)

    assert _counts(store) == (0, 0, 0, 0, 0)


def test_nested_business_operations_reuse_one_connection_and_cannot_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_UUID)

    with store.unit_of_work() as outer, store.unit_of_work() as inner:
        assert inner is outer
        assert inner.connection_identity == outer.connection_identity
        assert not hasattr(inner, "commit")
        assert not hasattr(inner, "rollback")
        with inner.savepoint("intentional_probe"):
            inner.execute(
                "INSERT INTO capture_sequences (project_uuid, next_sequence) VALUES (?, 1)",
                (PROJECT_UUID,),
            )

    assert _counts_for_query(
        store,
        "SELECT COUNT(*) FROM capture_sequences",
    ) == 1


def _counts_for_query(store: ProjectSyncStore, statement: str) -> int:
    with store.unit_of_work() as unit:
        return int(unit.execute(statement).fetchone()[0])


def test_foreign_project_rows_are_rejected_by_schema_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_UUID)

    with pytest.raises(sqlite3.IntegrityError), store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO capture_sequences (project_uuid, next_sequence) VALUES (?, 1)",
            ("bbbbbbbb-0000-0000-0000-000000000002",),
        )

    assert _counts_for_query(store, "SELECT COUNT(*) FROM capture_sequences") == 0


def test_incompatible_schema_is_preserved_and_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_UUID)
    with store.unit_of_work():
        pass
    with sqlite3.connect(store.database_path) as connection:
        connection.execute(
            "UPDATE project_store_metadata SET schema_version = 999"
        )
    before = store.database_path.read_bytes()

    with pytest.raises(ProjectStoreVersionError), store.unit_of_work():
        pytest.fail("incompatible stores must never expose a unit of work")

    assert store.database_path.read_bytes() == before


def test_locked_store_fails_closed_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_UUID)
    with store.unit_of_work():
        pass

    blocker = sqlite3.connect(store.database_path)
    before = store.database_path.read_bytes()
    blocker.execute("BEGIN EXCLUSIVE")
    try:
        with (
            pytest.raises(ProjectStoreLockedError),
            store.unit_of_work(lock_timeout_seconds=0.01),
        ):
            pytest.fail("locked stores must never expose a unit of work")
    finally:
        blocker.rollback()
        blocker.close()
    assert store.database_path.read_bytes() == before


def test_two_store_instances_serialize_shared_uuid_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    first = ProjectSyncStore(PROJECT_UUID)
    second = ProjectSyncStore(PROJECT_UUID)
    assert first.database_path == second.database_path

    first_entered = threading.Event()
    release_first = threading.Event()
    second_attempting = threading.Event()
    second_entered = threading.Event()
    failures: list[BaseException] = []

    def first_writer() -> None:
        try:
            with first.unit_of_work() as unit:
                unit.execute(
                    "INSERT INTO capture_sequences "
                    "(project_uuid, next_sequence) VALUES (?, 1)",
                    (PROJECT_UUID,),
                )
                first_entered.set()
                assert release_first.wait(timeout=5)
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    def second_writer() -> None:
        try:
            assert first_entered.wait(timeout=5)
            second_attempting.set()
            with second.unit_of_work() as unit:
                second_entered.set()
                unit.execute(
                    "UPDATE capture_sequences SET next_sequence = next_sequence + 1 "
                    "WHERE project_uuid = ?",
                    (PROJECT_UUID,),
                )
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    first_thread = threading.Thread(target=first_writer)
    second_thread = threading.Thread(target=second_writer)
    first_thread.start()
    assert first_entered.wait(timeout=5)
    second_thread.start()
    assert second_attempting.wait(timeout=5)

    probe = sqlite3.connect(first.database_path, timeout=0)
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            probe.execute("BEGIN IMMEDIATE")
    finally:
        probe.close()
    assert not second_entered.is_set()

    release_first.set()
    first_thread.join(timeout=5)
    second_thread.join(timeout=5)
    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert failures == []

    assert _counts_for_query(
        first,
        "SELECT next_sequence FROM capture_sequences",
    ) == 2


def test_unit_of_work_accepts_only_store_derived_connection_lifecycle() -> None:
    annotations = ProjectSyncStore.unit_of_work.__annotations__
    assert "database_path" not in annotations
    assert "connection" not in annotations
