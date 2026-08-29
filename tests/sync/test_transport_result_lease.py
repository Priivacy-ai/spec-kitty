"""WP06 transport/result lease ordering contract."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
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
from specify_cli.sync.transport_lease import acquire_project_transport_lease, transport_lease_is_live

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


def _seed_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    store = ProjectSyncStore(PROJECT_UUID)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_consent_decisions "
            "(project_uuid, state, generation, action, actor, decided_at, decision_schema_version) "
            "VALUES (?, 'granted', 3, 'explicit_opt_in', 'tester', '2026-08-10T00:00:00Z', 1)",
            (PROJECT_UUID,),
        )
        unit.execute(
            "INSERT INTO consent_epochs (epoch_id, project_uuid, opened_at_tail, state, consent_generation, reason) VALUES (7, ?, 0, 'eligible', 3, 'opt_in')",
            (PROJECT_UUID,),
        )
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://app.spec-kitty.ai', 'account-1', 'teamspace-1', 4, "
            "'admitted', 'server-generation-1', 'private-teamspace:teamspace-1')",
            (PROJECT_UUID,),
        )
    return store


def _attempt() -> DeliveryAttemptSpec:
    return DeliveryAttemptSpec(
        attempt_id="attempt-lease",
        write_kind="history_disclosure",
        native_identity="operation-key:abc",
        payload_hash="sha256:history",
        payload_reference="history:abc",
        deadline_at="2999-01-01T00:00:00Z",
        reconciliation_policy="native_identity_query",
    )


def test_transport_start_and_result_recording_require_lease_bound_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with store.unit_of_work() as unit:
        unlocked_context = store.create_context()
        prepare_delivery_attempt(unit, unlocked_context, _attempt())
        with pytest.raises(ProjectStoreError, match="requires the project transport lease"):
            mark_transport_started(unit, unlocked_context, "attempt-lease")

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        assert context.egress_eligible is True
        mark_transport_started(unit, context, "attempt-lease")
        record_delivery_result(
            unit,
            context,
            result_id="result-lease",
            attempt_id="attempt-lease",
            outcome=DeliveryOutcome.DELIVERED,
        )

    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, "attempt-lease"),
        ).fetchone()
    assert row is not None
    assert row[0] == DeliveryAttemptState.SUCCEEDED.value


def test_cached_context_after_lock_release_cannot_start_or_record_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _attempt())
        stale_context = context

    with store.unit_of_work() as unit, pytest.raises(ProjectStoreError, match="live project transport lease"):
        mark_transport_started(unit, stale_context, "attempt-lease")

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        mark_transport_started(unit, context, "attempt-lease")

    with store.unit_of_work() as unit, pytest.raises(ProjectStoreError, match="live project transport lease"):
        record_delivery_result(
            unit,
            stale_context,
            result_id="stale-result",
            attempt_id="attempt-lease",
            outcome=DeliveryOutcome.DELIVERED,
        )


def test_same_label_reacquisition_does_not_reactivate_cached_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with (
        acquire_project_transport_lease(store, lease_identity="stable-label") as lease,
        lease.unit_of_work() as (
            unit,
            context,
        ),
    ):
        prepare_delivery_attempt(unit, context, _attempt())
        stale_context = context

    with (
        acquire_project_transport_lease(store, lease_identity="stable-label") as lease,
        lease.unit_of_work() as (
            unit,
            live_context,
        ),
    ):
        assert live_context.transport_lease_identity != stale_context.transport_lease_identity
        with pytest.raises(ProjectStoreError, match="live project transport lease"):
            mark_transport_started(unit, stale_context, "attempt-lease")


def test_forked_child_does_not_inherit_live_lease_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)
    child_report = tmp_path / "fork-report.txt"

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (_unit, context):
        pid = os.fork()
        if pid == 0:
            child_report.write_text(str(transport_lease_is_live(context.transport_lease_identity)))
            os._exit(0)
        _, status = os.waitpid(pid, 0)

    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 0
    assert child_report.read_text() == "False"


def test_transport_lease_excludes_a_second_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)
    script = textwrap.dedent(
        f"""
        from specify_cli.sync.project_store import ProjectStoreLockedError, ProjectSyncStore
        from specify_cli.sync.transport_lease import acquire_project_transport_lease

        store = ProjectSyncStore({PROJECT_UUID!r})
        try:
            with acquire_project_transport_lease(store, lock_timeout_seconds=0.05):
                raise SystemExit(2)
        except ProjectStoreLockedError:
            raise SystemExit(0)
        """
    )

    with acquire_project_transport_lease(store):
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            env={
                **os.environ,
                "PYTHONPATH": str(Path.cwd() / "src"),
                "SPEC_KITTY_HOME": str(tmp_path / "runtime"),
                "SPEC_KITTY_ENABLE_SAAS_SYNC": "1",
            },
            text=True,
            capture_output=True,
            timeout=5,
        )

    assert result.returncode == 0, result.stderr


def test_lease_bound_context_rechecks_opt_out_before_transport_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _attempt())

    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_consent_decisions SET state = 'refused', generation = 4, action = 'explicit_opt_out' WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        assert context.egress_eligible is False
        with pytest.raises(ProjectStoreError, match="requires the project transport lease"):
            mark_transport_started(unit, context, "attempt-lease")


def test_kill_switch_off_denies_transport_lease_eligibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        assert context.egress_eligible is False
        prepare_delivery_attempt(unit, context, _attempt())
        with pytest.raises(ProjectStoreError, match="transport/result operation requires the project transport lease"):
            mark_transport_started(unit, context, "attempt-lease")


def test_transport_start_rejects_stale_persisted_authority_tuple(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _attempt())

    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_consent_decisions SET generation = 5 WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )
        unit.execute(
            "UPDATE consent_epochs SET state = 'sealed' WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )
        unit.execute(
            "INSERT INTO consent_epochs (epoch_id, project_uuid, opened_at_tail, state, consent_generation, reason) VALUES (8, ?, 0, 'eligible', 5, 'renewed')",
            (PROJECT_UUID,),
        )
        unit.execute(
            "UPDATE project_target_admissions SET target_identity = 'https://app.spec-kitty.ai/v2', "
            "account_identity = 'account-2', private_teamspace_id = 'teamspace-2', "
            "configuration_generation = 9, admission_generation = 'server-generation-2', "
            "binding_audience = 'private-teamspace:teamspace-2' WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        assert context.egress_eligible is True
        with pytest.raises(ProjectStoreError, match="authority no longer matches"):
            mark_transport_started(unit, context, "attempt-lease")


def test_result_records_attempt_original_tuple_and_rejects_current_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _attempt())
        mark_transport_started(unit, context, "attempt-lease")

    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_consent_decisions SET generation = 5 WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )
        unit.execute(
            "UPDATE consent_epochs SET state = 'sealed' WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )
        unit.execute(
            "INSERT INTO consent_epochs (epoch_id, project_uuid, opened_at_tail, state, consent_generation, reason) VALUES (8, ?, 0, 'eligible', 5, 'renewed')",
            (PROJECT_UUID,),
        )
        unit.execute(
            "UPDATE project_target_admissions SET target_identity = 'https://app.spec-kitty.ai/v2', "
            "account_identity = 'account-2', private_teamspace_id = 'teamspace-2', "
            "configuration_generation = 9, admission_generation = 'server-generation-2', "
            "binding_audience = 'private-teamspace:teamspace-2' WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )

    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match="authority no longer matches"),
    ):
        record_delivery_result(
            unit,
            context,
            result_id="result-substituted",
            attempt_id="attempt-lease",
            outcome=DeliveryOutcome.DELIVERED,
        )

    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_consent_decisions SET generation = 3 WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )
        unit.execute(
            "UPDATE consent_epochs SET state = 'eligible' WHERE project_uuid = ? AND epoch_id = 7",
            (PROJECT_UUID,),
        )
        unit.execute(
            "UPDATE consent_epochs SET state = 'sealed' WHERE project_uuid = ? AND epoch_id = 8",
            (PROJECT_UUID,),
        )
        unit.execute(
            "UPDATE project_target_admissions SET target_identity = 'https://app.spec-kitty.ai', "
            "account_identity = 'account-1', private_teamspace_id = 'teamspace-1', "
            "configuration_generation = 4, admission_generation = 'server-generation-1', "
            "binding_audience = 'private-teamspace:teamspace-1' WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        record_delivery_result(
            unit,
            context,
            result_id="result-original",
            attempt_id="attempt-lease",
            outcome=DeliveryOutcome.DELIVERED,
        )

    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT target_generation, admission_generation, outcome FROM delivery_results WHERE project_uuid = ? AND result_id = ?",
            (PROJECT_UUID, "result-original"),
        ).fetchone()

    assert row == (4, "server-generation-1", DeliveryOutcome.DELIVERED.value)


def test_refused_result_is_terminal_with_category_and_native_identity_cannot_be_reused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-refused",
                write_kind="history_disclosure",
                native_identity="operation-key:refused",
                payload_hash="sha256:refused",
                payload_reference="history:refused",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        mark_transport_started(unit, context, "attempt-refused")
        record_delivery_result(
            unit,
            context,
            result_id="result-refused",
            attempt_id="attempt-refused",
            outcome=DeliveryOutcome.REFUSED,
            terminal_refusal_category="project_not_admitted",
        )

    with store.unit_of_work() as unit:
        attempt_row = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, "attempt-refused"),
        ).fetchone()
        result_row = unit.execute(
            "SELECT outcome, terminal_refusal_category, target_generation, admission_generation FROM delivery_results WHERE project_uuid = ? AND result_id = ?",
            (PROJECT_UUID, "result-refused"),
        ).fetchone()
        decision = plan_delivery_attempt_recovery(unit, attempt_id="attempt-refused")

    assert attempt_row == (DeliveryAttemptState.REFUSED.value,)
    assert result_row == ("refused", "project_not_admitted", 4, "server-generation-1")
    assert decision.action is RecoveryAction.OPERATOR_REVIEW
    assert decision.may_resend is False

    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match="native transport identity already belongs"),
    ):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-refused-replay",
                write_kind="history_disclosure",
                native_identity="operation-key:refused",
                payload_hash="sha256:different",
                payload_reference="history:different",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )


@pytest.mark.parametrize("category", [None, "", "   "])
def test_refused_result_requires_category_and_writes_no_terminal_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    category: str | None,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-refused-missing-category",
                write_kind="history_disclosure",
                native_identity="operation-key:missing-category",
                payload_hash="sha256:missing-category",
                payload_reference="history:missing-category",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        mark_transport_started(unit, context, "attempt-refused-missing-category")
        with pytest.raises(ProjectStoreError, match="requires a terminal refusal category"):
            record_delivery_result(
                unit,
                context,
                result_id="result-refused-missing-category",
                attempt_id="attempt-refused-missing-category",
                outcome=DeliveryOutcome.REFUSED,
                terminal_refusal_category=category,
            )

    with store.unit_of_work() as unit:
        attempt_row = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, "attempt-refused-missing-category"),
        ).fetchone()
        result_count = unit.execute(
            "SELECT COUNT(*) FROM delivery_results WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, "attempt-refused-missing-category"),
        ).fetchone()

    assert attempt_row == (DeliveryAttemptState.IN_FLIGHT.value,)
    assert result_count == (0,)


@pytest.mark.parametrize("outcome", [DeliveryOutcome.DELIVERED, DeliveryOutcome.DUPLICATE])
def test_successful_result_rejects_terminal_refusal_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: DeliveryOutcome,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id=f"attempt-{outcome.value}-with-category",
                write_kind="history_disclosure",
                native_identity=f"operation-key:{outcome.value}-with-category",
                payload_hash=f"sha256:{outcome.value}-with-category",
                payload_reference=f"history:{outcome.value}-with-category",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        mark_transport_started(unit, context, f"attempt-{outcome.value}-with-category")
        with pytest.raises(ProjectStoreError, match="cannot include a terminal refusal category"):
            record_delivery_result(
                unit,
                context,
                result_id=f"result-{outcome.value}-with-category",
                attempt_id=f"attempt-{outcome.value}-with-category",
                outcome=outcome,
                terminal_refusal_category="project_not_admitted",
            )

    with store.unit_of_work() as unit:
        result_count = unit.execute(
            "SELECT COUNT(*) FROM delivery_results WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, f"attempt-{outcome.value}-with-category"),
        ).fetchone()
    assert result_count == (0,)


def test_duplicate_result_is_truthful_idempotent_success_on_original_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-duplicate",
                write_kind="history_disclosure",
                native_identity="operation-key:duplicate",
                payload_hash="sha256:duplicate",
                payload_reference="history:duplicate",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )
        mark_transport_started(unit, context, "attempt-duplicate")
        record_delivery_result(
            unit,
            context,
            result_id="result-duplicate",
            attempt_id="attempt-duplicate",
            outcome=DeliveryOutcome.DUPLICATE,
        )

    with store.unit_of_work() as unit:
        attempt_row = unit.execute(
            "SELECT state FROM delivery_attempts WHERE project_uuid = ? AND attempt_id = ?",
            (PROJECT_UUID, "attempt-duplicate"),
        ).fetchone()
        result_row = unit.execute(
            "SELECT outcome, target_generation, admission_generation FROM delivery_results WHERE project_uuid = ? AND result_id = ?",
            (PROJECT_UUID, "result-duplicate"),
        ).fetchone()

    assert attempt_row == (DeliveryAttemptState.SUCCEEDED.value,)
    assert result_row == ("duplicate", 4, "server-generation-1")


def test_corrupt_existing_metadata_blocks_possibly_colliding_fresh_native_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _attempt())

    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE delivery_attempts SET payload_reference = ? WHERE project_uuid = ? AND attempt_id = ?",
            ("{not-json", PROJECT_UUID, "attempt-lease"),
        )

    with (
        acquire_project_transport_lease(store) as lease,
        lease.unit_of_work() as (unit, context),
        pytest.raises(ProjectStoreError, match="operator repair"),
    ):
        prepare_delivery_attempt(
            unit,
            context,
            DeliveryAttemptSpec(
                attempt_id="attempt-possible-collision",
                write_kind="history_disclosure",
                native_identity="operation-key:abc",
                payload_hash="sha256:history-2",
                payload_reference="history:abc-2",
                deadline_at="2999-01-01T00:00:00Z",
                reconciliation_policy="native_identity_query",
            ),
        )


def test_same_attempt_native_identity_reprepare_fails_before_payload_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _attempt())
        with pytest.raises(ProjectStoreError, match="recover the original attempt"):
            prepare_delivery_attempt(unit, context, _attempt())
        with pytest.raises(ProjectStoreError, match="different payload hash"):
            prepare_delivery_attempt(
                unit,
                context,
                DeliveryAttemptSpec(
                    attempt_id="attempt-lease",
                    write_kind="history_disclosure",
                    native_identity="operation-key:abc",
                    payload_hash="sha256:changed",
                    payload_reference="history:abc",
                    deadline_at="2999-01-01T00:00:00Z",
                    reconciliation_policy="native_identity_query",
                ),
            )


@pytest.mark.parametrize(
    ("write_kind", "native_identity", "message"),
    [
        ("event", "operation-key:abc", "different write kind"),
        ("history_disclosure", "operation-key:changed", "different native identity"),
    ],
)
def test_same_attempt_changed_identity_scope_fails_at_protocol_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    write_kind: str,
    native_identity: str,
    message: str,
) -> None:
    store = _seed_store(tmp_path, monkeypatch)

    with acquire_project_transport_lease(store) as lease, lease.unit_of_work() as (unit, context):
        prepare_delivery_attempt(unit, context, _attempt())
        with pytest.raises(ProjectStoreError, match=message):
            prepare_delivery_attempt(
                unit,
                context,
                DeliveryAttemptSpec(
                    attempt_id="attempt-lease",
                    write_kind=write_kind,
                    native_identity=native_identity,
                    payload_hash="sha256:history",
                    payload_reference="history:abc",
                    deadline_at="2999-01-01T00:00:00Z",
                    reconciliation_policy="native_identity_query",
                ),
            )
