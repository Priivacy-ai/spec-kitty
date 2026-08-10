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
    mark_transport_started,
    prepare_delivery_attempt,
    record_delivery_result,
)
from specify_cli.sync.transport_lease import acquire_project_transport_lease


PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


def _seed_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
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
