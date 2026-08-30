"""WP09 hard-kill and compound late-recovery matrix for every sender family."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
from specify_cli.sync.routing import disable_checkout_sync
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptSpec,
    DeliveryAttemptState,
    DeliveryOutcome,
    RecoveryAction,
    mark_transport_started,
    plan_delivery_attempt_recovery,
    prepare_delivery_attempt,
    record_delivery_result,
)
from specify_cli.sync.transport_lease import acquire_project_transport_lease
from tests.support.sync_transport_barriers import (
    BarrierIdentity,
    BarrierPhase,
    HostedReferenceExpectation,
    ProcessTransportBarrier,
    ResultExpectation,
    TRANSPORT_FAMILIES,
    assert_exact_transport_evidence,
    evidence_from_barrier,
    invoke_production_adapter,
    recover_production_adapter,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"


def _admitted_store(project_uuid: str) -> ProjectSyncStore:
    record_project_opt_in(project_uuid, actor="wp09-crash")
    store = ProjectSyncStore(project_uuid)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://app.spec-kitty.ai', 'account-1', 'teamspace-1', 4, "
            "'admitted', '1', 'private-teamspace:teamspace-1')",
            (project_uuid,),
        )
    return store


def _identity(family: str, phase: BarrierPhase) -> BarrierIdentity:
    return BarrierIdentity(
        family=family,
        project_uuid=PROJECT_A,
        attempt_id=f"{family}:{phase.value}",
        native_identity=f"native:{family}:{phase.value}",
    )


def _spec(identity: BarrierIdentity) -> DeliveryAttemptSpec:
    return DeliveryAttemptSpec(
        attempt_id=identity.attempt_id,
        write_kind=identity.family,
        native_identity=identity.native_identity,
        payload_hash=f"sha256:{identity.family}:{identity.attempt_id}",
        payload_reference=f"payload:{identity.family}:{identity.attempt_id}",
        deadline_at="2999-01-01T00:00:00Z",
        reconciliation_policy="native_identity_retry_then_query",
    )


def _worker_script(
    root: Path,
    repo_root: Path,
    identity: BarrierIdentity,
    phase: BarrierPhase,
) -> str:
    return textwrap.dedent(
        f"""
        from pathlib import Path

        from tests.support.sync_transport_barriers import (
            BarrierIdentity,
            BarrierPhase,
            ProcessTransportBarrier,
            invoke_production_adapter,
        )

        identity = BarrierIdentity(
            family={identity.family!r},
            project_uuid={identity.project_uuid!r},
            attempt_id={identity.attempt_id!r},
            native_identity={identity.native_identity!r},
        )
        phase = BarrierPhase({phase.value!r})
        barrier = ProcessTransportBarrier(Path({str(root)!r}), identity, phase)
        invoke_production_adapter(
            Path({str(repo_root)!r}),
            identity,
            outcome="delivered",
            barrier=barrier,
        )
        """
    )


def _spawn_worker(
    root: Path,
    repo_root: Path,
    identity: BarrierIdentity,
    phase: BarrierPhase,
) -> tuple[subprocess.Popen[str], ProcessTransportBarrier]:
    barrier = ProcessTransportBarrier(root, identity, phase)
    process = subprocess.Popen(
        [sys.executable, "-c", _worker_script(root, repo_root, identity, phase)],
        cwd=Path.cwd(),
        env={**os.environ, "PYTHONPATH": str(Path.cwd())},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 45
    while not barrier.binding_path.exists():
        if process.poll() is not None:
            _stdout, stderr = process.communicate(timeout=5)
            raise AssertionError(f"{identity.family} worker exited before binding {phase.value}: {stderr}")
        if time.monotonic() >= deadline:
            process.kill()
            _stdout, stderr = process.communicate(timeout=5)
            raise TimeoutError(f"{identity.family} worker did not bind {phase.value}: {stderr}")
        time.sleep(0.01)
    barrier.controller_wait_for_binding(timeout=0.1)
    while not barrier.arrived_path.exists():
        if process.poll() is not None:
            _stdout, stderr = process.communicate(timeout=5)
            raise AssertionError(f"{identity.family} worker exited before {phase.value}: {stderr}")
        if time.monotonic() >= deadline:
            process.kill()
            _stdout, stderr = process.communicate(timeout=5)
            raise TimeoutError(f"{identity.family} worker did not reach {phase.value}: {stderr}")
        time.sleep(0.01)
    barrier.controller_wait_for_arrival(timeout=0.1)
    return process, barrier


def _kill(process: subprocess.Popen[str]) -> None:
    process.kill()
    _stdout, stderr = process.communicate(timeout=10)
    assert process.returncode is not None and process.returncode < 0, stderr


def _attempt_row(store: ProjectSyncStore, attempt_id: str) -> tuple[str, str, str | None] | None:
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT delivery_attempts.state, delivery_attempts.payload_reference, "
            "delivery_results.outcome FROM delivery_attempts LEFT JOIN delivery_results "
            "ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "WHERE delivery_attempts.project_uuid = ? AND delivery_attempts.attempt_id = ?",
            (store.project_uuid.storage_token, attempt_id),
        ).fetchone()
    if row is None:
        return None
    return str(row[0]), str(row[1]), str(row[2]) if row[2] is not None else None


def _transport_authority_snapshot(
    store: ProjectSyncStore,
) -> tuple[tuple[str, int], dict[int, str]]:
    with store.unit_of_work() as unit:
        decision = unit.execute(
            "SELECT state, generation FROM project_consent_decisions WHERE project_uuid = ?",
            (store.project_uuid.storage_token,),
        ).fetchone()
        epochs = unit.execute(
            "SELECT epoch_id, state FROM consent_epochs WHERE project_uuid = ?",
            (store.project_uuid.storage_token,),
        ).fetchall()
    assert decision is not None
    return (str(decision[0]), int(decision[1])), {int(epoch_id): str(state) for epoch_id, state in epochs}


def _restore_transport_authority(
    store: ProjectSyncStore,
    snapshot: tuple[tuple[str, int], dict[int, str]],
) -> None:
    decision, epochs = snapshot
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_consent_decisions SET state = ?, generation = ? WHERE project_uuid = ?",
            (*decision, store.project_uuid.storage_token),
        )
        for epoch_id, state in epochs.items():
            unit.execute(
                "UPDATE consent_epochs SET state = ? WHERE project_uuid = ? AND epoch_id = ?",
                (state, store.project_uuid.storage_token, epoch_id),
            )


@contextmanager
def _temporarily_restore_transport_authority(
    store: ProjectSyncStore,
    admitted: tuple[tuple[str, int], dict[int, str]],
) -> Iterator[None]:
    revoked = _transport_authority_snapshot(store)
    _restore_transport_authority(store, admitted)
    try:
        context = store.create_context()
        assert context.consent_generation is not None
        assert context.admission_generation is not None
        yield
    finally:
        _restore_transport_authority(store, revoked)


def _production_attempt_row(
    store: ProjectSyncStore,
) -> tuple[str, str, str, str | None, str] | None:
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT delivery_attempts.attempt_id, delivery_attempts.state, "
            "delivery_attempts.payload_reference, delivery_results.outcome, "
            "delivery_attempts.reconciliation_policy "
            "FROM delivery_attempts LEFT JOIN delivery_results "
            "ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "WHERE delivery_attempts.project_uuid = ? "
            "ORDER BY delivery_attempts.created_at DESC LIMIT 1",
            (store.project_uuid.storage_token,),
        ).fetchone()
    if row is None:
        return None
    return (
        str(row[0]),
        str(row[1]),
        str(row[2]),
        str(row[3]) if row[3] is not None else None,
        str(row[4]),
    )


def _attempt_ids(store: ProjectSyncStore) -> tuple[str, ...]:
    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT attempt_id FROM delivery_attempts WHERE project_uuid = ? ORDER BY attempt_id",
            (store.project_uuid.storage_token,),
        ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _persisted_native_identity(payload_reference: str) -> str:
    payload = json.loads(payload_reference)
    native = payload.get("native_identity")
    assert isinstance(native, str) and native
    return native


def _assert_exact_relay_delegation(barrier: ProcessTransportBarrier) -> None:
    raw = barrier.captured_delegation_bytes()
    assert raw is not None
    delegated = json.loads(raw)
    assert isinstance(delegated, dict) and frozenset(delegated) == {"event", "token"}
    event = delegated["event"]
    assert isinstance(event, dict)
    assert event["event_id"] == barrier.identity.native_identity
    assert event["project_uuid"] == barrier.identity.project_uuid


def _assert_exact_authority(
    store: ProjectSyncStore,
    attempt_id: str,
    *,
    has_result: bool,
) -> None:
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT delivery_attempts.epoch_id, delivery_attempts.consent_generation, "
            "delivery_attempts.target_generation, delivery_attempts.admission_generation, "
            "delivery_attempts.binding_audience, delivery_results.epoch_id, "
            "delivery_results.target_generation, delivery_results.admission_generation "
            "FROM delivery_attempts LEFT JOIN delivery_results "
            "ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "WHERE delivery_attempts.project_uuid = ? AND delivery_attempts.attempt_id = ?",
            (store.project_uuid.storage_token, attempt_id),
        ).fetchone()
    context = store.create_context()
    assert context.target_audience is not None
    expected = (
        context.epoch_id,
        context.consent_generation,
        context.target_audience.configuration_generation,
        context.admission_generation,
        context.binding_audience,
    )
    assert row is not None
    assert tuple(row[:5]) == expected
    assert tuple(row[5:]) == (
        (
            context.epoch_id,
            context.target_audience.configuration_generation,
            context.admission_generation,
        )
        if has_result
        else (None, None, None)
    )


def _assert_result_matches_attempt_authority(
    store: ProjectSyncStore,
    attempt_id: str,
) -> None:
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT delivery_attempts.epoch_id, delivery_attempts.target_generation, "
            "delivery_attempts.admission_generation, delivery_results.epoch_id, "
            "delivery_results.target_generation, delivery_results.admission_generation "
            "FROM delivery_attempts JOIN delivery_results "
            "ON delivery_results.project_uuid = delivery_attempts.project_uuid "
            "AND delivery_results.attempt_id = delivery_attempts.attempt_id "
            "WHERE delivery_attempts.project_uuid = ? AND delivery_attempts.attempt_id = ?",
            (store.project_uuid.storage_token, attempt_id),
        ).fetchone()
    assert row is not None
    assert tuple(row[:3]) == tuple(row[3:])


def _prove_project_b_progress(
    store: ProjectSyncStore,
    family: str,
    repo_root: Path,
) -> None:
    from unittest.mock import patch

    identity = BarrierIdentity(
        family=family,
        project_uuid=PROJECT_B,
        attempt_id=f"project-b:{family}",
        native_identity=f"project-b-native:{family}",
    )
    opened_projects: list[str] = []
    original_init = ProjectSyncStore.__init__

    def _record_open(active: ProjectSyncStore, project_uuid: object) -> None:
        opened_projects.append(str(project_uuid))
        original_init(active, project_uuid)

    with patch.object(ProjectSyncStore, "__init__", _record_open):
        evidence = invoke_production_adapter(repo_root, identity, outcome="delivered")
    assert opened_projects and set(opened_projects) == {PROJECT_B}
    assert evidence.succeeded is True
    assert evidence.request_bytes
    assert_exact_transport_evidence(evidence)
    row = _production_attempt_row(store)
    assert row is not None
    assert (row[1], row[3]) == (
        DeliveryAttemptState.SUCCEEDED.value,
        DeliveryOutcome.DELIVERED.value,
    )
    _assert_exact_authority(store, row[0], has_result=True)


@pytest.mark.parametrize("family", TRANSPORT_FAMILIES)
@pytest.mark.parametrize("phase", tuple(BarrierPhase))
def test_hard_kill_recovery_window_preserves_identity_and_project_b(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    phase: BarrierPhase,
) -> None:
    """T040/T042: hard-kill each exact window, never infer from timing."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / phase.value / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store_a = ProjectSyncStore(PROJECT_A) if family == "history_import" else _admitted_store(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B) if family == "history_import" else _admitted_store(PROJECT_B)
    identity = _identity(family, phase)
    process, barrier = _spawn_worker(
        tmp_path / "barriers",
        _repo(tmp_path),
        identity,
        phase,
    )

    _prove_project_b_progress(
        store_b,
        family,
        _repo(tmp_path / "project-b", PROJECT_B),
    )
    _kill(process)

    row = _production_attempt_row(store_a)
    if phase is BarrierPhase.BEFORE_ATTEMPT_COMMIT:
        assert row is None
        if family == "event_relay":
            _assert_exact_relay_delegation(barrier)
        else:
            assert barrier.captured_bytes() is None
        return
    assert row is not None
    actual_attempt_id = row[0]
    assert actual_attempt_id == barrier.identity.attempt_id
    _assert_exact_authority(
        store_a,
        actual_attempt_id,
        has_result=phase is BarrierPhase.RESULT_COMMITTED,
    )
    with store_a.unit_of_work() as unit:
        recovery = plan_delivery_attempt_recovery(unit, attempt_id=actual_attempt_id)
    assert recovery.native_identity == barrier.identity.native_identity == _persisted_native_identity(row[2])

    if phase is BarrierPhase.AFTER_ATTEMPT_COMMIT_BEFORE_SEND:
        assert row[1] == DeliveryAttemptState.PREPARED.value
        assert recovery.action is RecoveryAction.RETRY_NATIVE_IDENTITY
        assert recovery.may_resend is True
        if family == "event_relay":
            _assert_exact_relay_delegation(barrier)
        else:
            assert barrier.captured_bytes() is None
    else:
        evidence = evidence_from_barrier(
            barrier,
            result_expectation=(ResultExpectation.COMPLETED if phase is BarrierPhase.RESULT_COMMITTED else ResultExpectation.ABSENT),
            expected_result_outcome=(DeliveryOutcome.DELIVERED.value if phase is BarrierPhase.RESULT_COMMITTED else None),
            hosted_reference_expectation=(
                HostedReferenceExpectation.REQUIRED
                if phase is BarrierPhase.RESULT_COMMITTED and family in {"tracker_hosted", "generic_saas"}
                else HostedReferenceExpectation.ABSENT
            ),
        )
        assert_exact_transport_evidence(evidence)
        if phase is BarrierPhase.RESULT_COMMITTED:
            assert (row[1], row[3]) == (
                DeliveryAttemptState.SUCCEEDED.value,
                DeliveryOutcome.DELIVERED.value,
            )
            assert recovery.may_resend is False
        else:
            assert row[1] in {
                DeliveryAttemptState.IN_FLIGHT.value,
                DeliveryAttemptState.UNKNOWN.value,
            }
            expected_action = RecoveryAction.QUERY_NATIVE_IDENTITY if "query" in row[4] else RecoveryAction.OPERATOR_REVIEW
            assert recovery.action is expected_action
            assert recovery.may_resend is False


def test_queued_attempt_rejects_changed_target_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegated WP06 control: queued old-authority bytes cannot start."""
    # This is one explicit WP06 ledger control, not another alleged sender row.
    family = "direct_dispatcher"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store = _admitted_store(PROJECT_A)
    identity = _identity(family, BarrierPhase.AFTER_ATTEMPT_COMMIT_BEFORE_SEND)
    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _spec(identity))
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_target_admissions SET configuration_generation = 5, admission_generation = '2' WHERE project_uuid = ?",
            (PROJECT_A,),
        )

    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError),
    ):
        mark_transport_started(unit, context, identity.attempt_id)

    row = _attempt_row(store, identity.attempt_id)
    assert row is not None
    assert row[0] == DeliveryAttemptState.PREPARED.value
    with store.unit_of_work() as unit:
        authority = unit.execute(
            "SELECT target_generation, admission_generation, binding_audience FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_A, identity.attempt_id),
        ).fetchone()
    assert authority is not None
    assert tuple(authority) == (4, "1", "private-teamspace:teamspace-1")


def _repo(tmp_path: Path, project_uuid: str = PROJECT_A) -> Path:
    root = tmp_path / f"repo-{project_uuid[0]}"
    config = root / ".kittify" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        f"project:\n  uuid: {project_uuid}\n  slug: project-{project_uuid[0]}\n  node_id: node-wp09\n  repo_slug: private/wp09\n  build_id: build-wp09\n",
        encoding="utf-8",
    )
    return root


@pytest.mark.parametrize("family", TRANSPORT_FAMILIES)
def test_kill_then_public_opt_out_then_late_recovery_is_terminal_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
) -> None:
    """T043 compound ordering: kill -> opt-out -> recovery, with B live."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / family / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store_a = ProjectSyncStore(PROJECT_A) if family == "history_import" else _admitted_store(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B) if family == "history_import" else _admitted_store(PROJECT_B)
    phase = BarrierPhase.RESPONSE_RECEIVED_BEFORE_RESULT
    identity = _identity(family, phase)
    process, barrier = _spawn_worker(
        tmp_path / "barriers",
        _repo(tmp_path),
        identity,
        phase,
    )
    _prove_project_b_progress(
        store_b,
        family,
        _repo(tmp_path / "project-b", PROJECT_B),
    )

    _kill(process)
    captured = barrier.captured_bytes()
    row = _production_attempt_row(store_a)
    assert row is not None
    actual_attempt_id = row[0]
    assert actual_attempt_id == barrier.identity.attempt_id
    _assert_exact_authority(store_a, actual_attempt_id, has_result=False)
    admitted_authority = _transport_authority_snapshot(store_a)
    disable_checkout_sync(_repo(tmp_path), actor="wp09-compound")
    assert_exact_transport_evidence(
        evidence_from_barrier(
            barrier,
            outcome="timeout",
            result_expectation=ResultExpectation.OPT_OUT_TERMINAL_UNKNOWN,
            expected_result_outcome=DeliveryOutcome.TERMINAL_UNKNOWN.value,
            hosted_reference_expectation=HostedReferenceExpectation.ABSENT,
        )
    )

    with store_a.unit_of_work() as unit:
        recovery = plan_delivery_attempt_recovery(unit, attempt_id=actual_attempt_id)
    assert recovery.action is RecoveryAction.TERMINALIZED_NOOP
    assert recovery.native_identity == barrier.identity.native_identity == _persisted_native_identity(row[2])
    assert recovery.may_resend is False
    attempts_before_recovery = _attempt_ids(store_a)
    with _temporarily_restore_transport_authority(store_a, admitted_authority):
        if family == "event_relay":
            from unittest.mock import patch

            from specify_cli.sync import events

            with patch.object(
                events,
                "emit_wp_status_changed",
                side_effect=AssertionError("recovery minted a fresh relay Event"),
            ):
                recovery_evidence = recover_production_adapter(
                    _repo(tmp_path),
                    identity,
                    barrier.identity,
                    poison_sink=True,
                )
        else:
            recovery_evidence = recover_production_adapter(
                _repo(tmp_path),
                identity,
                barrier.identity,
                poison_sink=True,
            )
    assert recovery_evidence.request_bytes == b""
    assert recovery_evidence.actual_identity == barrier.identity
    assert _attempt_ids(store_a) == attempts_before_recovery
    assert barrier.captured_bytes() == captured
    row_after = _attempt_row(store_a, actual_attempt_id)
    assert row_after is not None
    assert row_after[0::2] == (
        DeliveryAttemptState.TERMINAL_UNKNOWN.value,
        DeliveryOutcome.TERMINAL_UNKNOWN.value,
    )
    _assert_result_matches_attempt_authority(store_a, actual_attempt_id)
    with (
        acquire_project_transport_lease(store_a) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError),
    ):
        record_delivery_result(
            unit,
            context,
            result_id=f"late-success:{actual_attempt_id}",
            attempt_id=actual_attempt_id,
            outcome=DeliveryOutcome.DELIVERED,
        )
