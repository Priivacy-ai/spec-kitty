"""Atomicity and connection-ownership acceptance tests for ProjectSyncStore."""

from __future__ import annotations

import multiprocessing
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from specify_cli.sync.project_store import (
    ProjectStoreError,
    ProjectStoreLockedError,
    ProjectStoreVersionError,
    ProjectSyncStore,
    ProjectUnitOfWork,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


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
            "INSERT INTO consent_epochs (epoch_id, project_uuid, opened_at_tail, state, consent_generation, reason) VALUES (1, ?, 0, 'eligible', 1, 'opt_in')",
            (PROJECT_UUID,),
        ),
        (
            "INSERT INTO journal_entries (entry_id, project_uuid, epoch_id, capture_sequence, payload_json) VALUES ('event-1', ?, 1, 1, '{}')",
            (PROJECT_UUID,),
        ),
        (
            "INSERT INTO outbox_tasks (task_id, project_uuid, epoch_id, journal_entry_id, task_kind, state) VALUES ('task-1', ?, 1, 'event-1', 'event', 'pending')",
            (PROJECT_UUID,),
        ),
        (
            "INSERT INTO delivery_attempts (attempt_id, project_uuid, epoch_id, outbox_task_id, state) VALUES ('attempt-1', ?, 1, 'task-1', 'pending')",
            (PROJECT_UUID,),
        ),
        (
            "INSERT INTO delivery_results "
            "(result_id, project_uuid, epoch_id, attempt_id, outcome, recorded_at) "
            "VALUES ('result-1', ?, 1, 'attempt-1', 'delivered', "
            "'2026-08-10T00:00:01Z')",
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
                "delivery_results",
            )
        )


@pytest.mark.parametrize("fail_after", range(1, 7))
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

    assert _counts(store) == (0, 0, 0, 0, 0, 0)


def test_query_results_cannot_reach_connection_transaction_controls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_UUID)

    with (
        pytest.raises(RuntimeError, match="business failure"),
        store.unit_of_work() as unit,
    ):
        result = unit.execute(
            "INSERT INTO capture_sequences (project_uuid, next_sequence) VALUES (?, 1)",
            (PROJECT_UUID,),
        )
        with pytest.raises(AttributeError):
            result.connection.commit()  # type: ignore[attr-defined]
        raise RuntimeError("business failure")

    assert _counts_for_query(store, "SELECT COUNT(*) FROM capture_sequences") == 0


@pytest.mark.parametrize(
    "transaction_statement",
    (
        "BEGIN",
        "COMMIT",
        "END",
        "ROLLBACK",
        "SAVEPOINT hidden",
        "RELEASE hidden",
        "/* disguised */ COMMIT",
        "-- disguised\nROLLBACK",
        "; COMMIT",
        ";;;ROLLBACK",
        "\ufeffCOMMIT",
    ),
)
def test_sql_transaction_control_escape_is_rejected_and_business_work_rolls_back(
    transaction_statement: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_UUID)

    with (
        pytest.raises(RuntimeError, match="business failure"),
        store.unit_of_work() as unit,
    ):
        unit.execute(
            "INSERT INTO capture_sequences (project_uuid, next_sequence) VALUES (?, 1)",
            (PROJECT_UUID,),
        )
        with pytest.raises(ProjectStoreError, match="transaction control"):
            unit.execute(transaction_statement)
        raise RuntimeError("business failure")

    assert _counts_for_query(store, "SELECT COUNT(*) FROM capture_sequences") == 0


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

    assert (
        _counts_for_query(
            store,
            "SELECT COUNT(*) FROM capture_sequences",
        )
        == 1
    )


def test_failing_savepoint_rolls_back_inner_work_without_ending_outer_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_UUID)

    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO admission_operations "
            "(operation_key, project_uuid, action, target_identity, account_identity, "
            "private_teamspace_id, configuration_generation, request_payload_hash, "
            "request_payload_version, state, created_at, updated_at) "
            "VALUES ('outer-before', ?, 'admit', 'target', 'account', 'teamspace', "
            "1, ?, 1, 'prepared', '2026-08-10T00:00:00Z', '2026-08-10T00:00:00Z')",
            (PROJECT_UUID, "a" * 64),
        )
        assert unit.execute("SELECT state FROM admission_operations WHERE operation_key = 'outer-before'").fetchone() == ("prepared",)
        with (
            pytest.raises(RuntimeError, match="inner failure"),
            unit.savepoint("expected_failure"),
        ):
            unit.execute(
                "INSERT INTO admission_operations "
                "(operation_key, project_uuid, action, target_identity, "
                "account_identity, private_teamspace_id, configuration_generation, "
                "request_payload_hash, request_payload_version, state, created_at, updated_at) "
                "VALUES ('inner', ?, 'admit', 'target', 'account', 'teamspace', "
                "1, ?, 1, 'prepared', '2026-08-10T00:00:01Z', '2026-08-10T00:00:01Z')",
                (PROJECT_UUID, "b" * 64),
            )
            assert unit.execute("SELECT state FROM admission_operations WHERE operation_key = 'inner'").fetchone() == ("prepared",)
            raise RuntimeError("inner failure")
        unit.execute(
            "INSERT INTO admission_operations "
            "(operation_key, project_uuid, action, target_identity, account_identity, "
            "private_teamspace_id, configuration_generation, request_payload_hash, "
            "request_payload_version, state, created_at, updated_at) "
            "VALUES ('outer-after', ?, 'admit', 'target', 'account', 'teamspace', "
            "1, ?, 1, 'prepared', '2026-08-10T00:00:02Z', '2026-08-10T00:00:02Z')",
            (PROJECT_UUID, "c" * 64),
        )

    with store.unit_of_work() as unit:
        keys = tuple(str(row[0]) for row in unit.execute("SELECT operation_key FROM admission_operations ORDER BY operation_key").fetchall())
    assert keys == ("outer-after", "outer-before")


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
        connection.execute("UPDATE project_store_metadata SET schema_version = 999")
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
                    "INSERT INTO capture_sequences (project_uuid, next_sequence) VALUES (?, 1)",
                    (PROJECT_UUID,),
                )
                first_entered.set()
                if not release_first.wait(timeout=5):
                    raise TimeoutError("release_first was not signaled within 5s")
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    def second_writer() -> None:
        try:
            if not first_entered.wait(timeout=5):
                raise TimeoutError("first_entered was not signaled within 5s")
            second_attempting.set()
            with second.unit_of_work() as unit:
                second_entered.set()
                unit.execute(
                    "UPDATE capture_sequences SET next_sequence = next_sequence + 1 WHERE project_uuid = ?",
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

    assert (
        _counts_for_query(
            first,
            "SELECT next_sequence FROM capture_sequences",
        )
        == 2
    )


def _first_process_writer(
    runtime_root: str,
    entered: Any,
    release: Any,
) -> None:
    os.environ["SPEC_KITTY_HOME"] = runtime_root
    store = ProjectSyncStore(PROJECT_UUID)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO capture_sequences (project_uuid, next_sequence) VALUES (?, 1)",
            (PROJECT_UUID,),
        )
        entered.set()
        if not release.wait(timeout=10):
            raise RuntimeError("first writer release timed out")


def _second_process_writer(
    runtime_root: str,
    attempting: Any,
    entered: Any,
) -> None:
    os.environ["SPEC_KITTY_HOME"] = runtime_root
    store = ProjectSyncStore(PROJECT_UUID)
    attempting.set()
    with store.unit_of_work() as unit:
        entered.set()
        unit.execute(
            "UPDATE capture_sequences SET next_sequence = next_sequence + 1 WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )


def test_independent_processes_serialize_shared_uuid_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    store = ProjectSyncStore(PROJECT_UUID)
    context = multiprocessing.get_context("spawn")
    first_entered = context.Event()
    release_first = context.Event()
    second_attempting = context.Event()
    second_entered = context.Event()

    first = context.Process(
        target=_first_process_writer,
        args=(str(runtime), first_entered, release_first),
    )
    second = context.Process(
        target=_second_process_writer,
        args=(str(runtime), second_attempting, second_entered),
    )
    first.start()
    assert first_entered.wait(timeout=10)
    second.start()
    assert second_attempting.wait(timeout=10)

    probe = sqlite3.connect(store.database_path, timeout=0)
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            probe.execute("BEGIN IMMEDIATE")
    finally:
        probe.close()
    assert not second_entered.is_set()

    release_first.set()
    assert second_entered.wait(timeout=10)
    first.join(timeout=10)
    second.join(timeout=10)
    assert first.exitcode == 0
    assert second.exitcode == 0
    assert (
        _counts_for_query(
            store,
            "SELECT next_sequence FROM capture_sequences",
        )
        == 2
    )


def test_busy_timeout_bounds_the_wait_under_contention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#3625: a competing writer waits up to the timeout, then fails — never hangs.

    ``busy_timeout`` (project_store.py) turns a contended ``BEGIN IMMEDIATE``
    into a *bounded* wait instead of an immediate ``ProjectStoreLockedError``.
    This pins that: while one unit_of_work holds the write lock, a second
    acquisition with a small timeout blocks for roughly the timeout and then
    raises — it must neither raise instantly (proving the pragma is in force)
    nor block forever (proving the wait is bounded).
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    holder_store = ProjectSyncStore(PROJECT_UUID)
    waiter_store = ProjectSyncStore(PROJECT_UUID)
    with holder_store.unit_of_work():
        pass  # establish the store (WAL + schema) before contending

    holder_entered = threading.Event()
    release_holder = threading.Event()
    failures: list[BaseException] = []

    def holder() -> None:
        try:
            with holder_store.unit_of_work() as unit:
                unit.execute(
                    "INSERT INTO capture_sequences (project_uuid, next_sequence) VALUES (?, 1)",
                    (PROJECT_UUID,),
                )
                holder_entered.set()
                if not release_holder.wait(timeout=10):
                    raise TimeoutError("release_holder was not signaled within 10s")
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    holder_thread = threading.Thread(target=holder)
    holder_thread.start()
    assert holder_entered.wait(timeout=5)

    wait_budget = 0.5
    started = time.monotonic()
    with (
        pytest.raises(ProjectStoreLockedError),
        waiter_store.unit_of_work(lock_timeout_seconds=wait_budget),
    ):
        pytest.fail("a held write lock must never expose a second unit of work")
    elapsed = time.monotonic() - started

    release_holder.set()
    holder_thread.join(timeout=5)
    assert not holder_thread.is_alive()
    assert failures == []

    # It WAITED (bounded by busy_timeout) rather than failing instantly...
    assert elapsed >= wait_budget * 0.5
    # ...and the wait was BOUNDED — no indefinite hang.
    assert elapsed < 5.0


class _RecordingConnection:
    """Delegates to a real sqlite3 connection, logging executed SQL text."""

    def __init__(self, real: sqlite3.Connection, log: list[str]) -> None:
        self._real = real
        self._log = log

    def execute(self, sql: str, *args: Any, **kwargs: Any) -> sqlite3.Cursor:
        self._log.append(sql)
        return self._real.execute(sql, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


def _first_index_containing(statements: list[str], needle: str) -> int:
    for index, statement in enumerate(statements):
        if needle in statement.lower():
            return index
    raise AssertionError(f"no executed statement contained {needle!r}: {statements}")


def test_busy_timeout_pragma_precedes_begin_immediate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#3625 ordering guard: ``PRAGMA busy_timeout`` must run before ``BEGIN IMMEDIATE``.

    The bounded-wait guarantee only holds if the timeout pragma is installed
    on the connection before the transaction attempts to acquire the write
    lock. This records the actual statement order on a live connection and
    fails if a refactor reorders the pragma after ``BEGIN IMMEDIATE``.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_UUID)
    with store.unit_of_work():
        pass  # initialize first, so the recording captures the steady-state path

    statements: list[str] = []
    real_connect = sqlite3.connect

    def recording_connect(*args: Any, **kwargs: Any) -> Any:
        return _RecordingConnection(real_connect(*args, **kwargs), statements)

    monkeypatch.setattr(
        "specify_cli.sync.project_store.sqlite3.connect",
        recording_connect,
    )
    with store.unit_of_work():
        pass

    busy_index = _first_index_containing(statements, "busy_timeout")
    begin_index = _first_index_containing(statements, "begin immediate")
    assert busy_index < begin_index


def test_unit_of_work_accepts_only_store_derived_connection_lifecycle() -> None:
    annotations = ProjectSyncStore.unit_of_work.__annotations__
    assert "database_path" not in annotations
    assert "connection" not in annotations
