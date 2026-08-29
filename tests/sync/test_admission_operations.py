"""Durable admission-operation outbox, retry, and CAS acceptance tests."""

from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest

from specify_cli.saas_client.admission import AdmissionResponse
from specify_cli.sync.admission_operations import (
    AdmissionAction,
    AdmissionOperationConflictError,
    AdmissionOperationService,
    AdmissionOperationState,
    AdmissionTransportUncertain,
)
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.target_authority import AdmissionAudience

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"
KEY_A = "operation-key-00000000000000000001"
KEY_B = "operation-key-00000000000000000002"


class FakeAdmissionClient:
    def __init__(self, outcomes: list[AdmissionResponse | Exception]) -> None:
        self.outcomes = deque(outcomes)
        self.requests: list[object] = []

    def execute(self, request: object) -> AdmissionResponse:
        self.requests.append(request)
        outcome = self.outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    return ProjectSyncStore(PROJECT)


@pytest.fixture
def audience(store: ProjectSyncStore) -> AdmissionAudience:
    return AdmissionAudience(
        normalized_server_origin="https://app.spec-kitty.ai",
        account_identity="account-1",
        private_teamspace_id="teamspace-1",
        project_uuid=store.project_uuid,
        configuration_generation=1,
    )


def _response(state: str, generation: int, binding: str = "opaque-binding") -> AdmissionResponse:
    return AdmissionResponse(
        source_project_uuid=PROJECT,
        state=state,
        generation=generation,
        binding_audience=binding,
    )


def test_timeout_retry_reuses_same_durable_key_and_payload(
    store: ProjectSyncStore,
    audience: AdmissionAudience,
) -> None:
    client = FakeAdmissionClient([AdmissionTransportUncertain("timeout"), _response("admitted", 1)])
    service = AdmissionOperationService(store, client)

    first = service.perform(
        action=AdmissionAction.ADMIT,
        audience=audience,
        operation_key=KEY_A,
        project_slug="display-only",
    )
    second = service.perform(
        action=AdmissionAction.ADMIT,
        audience=audience,
        operation_key=KEY_A,
        project_slug="display-only",
    )

    assert first.state is AdmissionOperationState.UNKNOWN
    assert second.state is AdmissionOperationState.ACKNOWLEDGED
    assert len(client.requests) == 2
    assert client.requests[0] == client.requests[1]
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT state, attempts, request_payload_hash, request_payload_version FROM admission_operations WHERE operation_key = ?",
            (KEY_A,),
        ).fetchone()
    assert tuple(row) == ("acknowledged", 2, second.request_payload_hash, 1)


def test_same_key_cannot_change_action_audience_or_payload(
    store: ProjectSyncStore,
    audience: AdmissionAudience,
) -> None:
    client = FakeAdmissionClient([AdmissionTransportUncertain("timeout")])
    service = AdmissionOperationService(store, client)
    service.perform(
        action=AdmissionAction.ADMIT,
        audience=audience,
        operation_key=KEY_A,
        project_slug="one",
    )

    with pytest.raises(AdmissionOperationConflictError):
        service.perform(
            action=AdmissionAction.REVOKE,
            audience=audience,
            operation_key=KEY_A,
            expected_generation=1,
        )
    with pytest.raises(AdmissionOperationConflictError):
        service.perform(
            action=AdmissionAction.ADMIT,
            audience=audience,
            operation_key=KEY_A,
            project_slug="two",
        )
    assert len(client.requests) == 1


def test_first_acknowledged_result_is_immutable_on_same_key_retry(
    store: ProjectSyncStore,
    audience: AdmissionAudience,
) -> None:
    client = FakeAdmissionClient([_response("admitted", 1, "binding-1"), _response("admitted", 99, "binding-99")])
    service = AdmissionOperationService(store, client)

    first = service.perform(
        action=AdmissionAction.ADMIT,
        audience=audience,
        operation_key=KEY_A,
    )
    retried = service.perform(
        action=AdmissionAction.ADMIT,
        audience=audience,
        operation_key=KEY_A,
    )

    assert retried == first
    assert retried.result_generation == 1
    assert retried.binding_audience == "binding-1"
    assert len(client.requests) == 1


def test_readmit_requires_a_new_key_and_expected_generation_cas(
    store: ProjectSyncStore,
    audience: AdmissionAudience,
) -> None:
    client = FakeAdmissionClient([_response("admitted", 1, "binding-1"), _response("admitted", 3, "binding-3")])
    service = AdmissionOperationService(store, client)
    first = service.perform(
        action=AdmissionAction.ADMIT,
        audience=audience,
        operation_key=KEY_A,
    )
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_target_admissions SET admission_state = 'pending', "
            "admission_generation = '2', binding_audience = 'revoked-binding' "
            "WHERE project_uuid = ?",
            (PROJECT,),
        )

    readmitted = service.perform(
        action=AdmissionAction.ADMIT,
        audience=audience,
        operation_key=KEY_B,
        expected_generation=2,
    )

    assert first.result_generation == 1
    assert readmitted.result_generation == 3
    assert readmitted.operation_key != first.operation_key
    with store.unit_of_work() as unit:
        current = unit.execute(
            "SELECT admission_state, admission_generation, binding_audience FROM project_target_admissions WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
    assert tuple(current) == ("admitted", "3", "binding-3")


def test_delayed_old_admit_result_cannot_revive_newer_revocation(
    store: ProjectSyncStore,
    audience: AdmissionAudience,
) -> None:
    client = FakeAdmissionClient([AdmissionTransportUncertain("timeout"), _response("admitted", 1)])
    service = AdmissionOperationService(store, client)
    service.perform(action=AdmissionAction.ADMIT, audience=audience, operation_key=KEY_A)
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_target_admissions SET admission_state = 'revocation_pending', "
            "admission_generation = '2', binding_audience = 'revoked-binding' "
            "WHERE project_uuid = ?",
            (PROJECT,),
        )

    result = service.perform(
        action=AdmissionAction.ADMIT,
        audience=audience,
        operation_key=KEY_A,
    )

    assert result.state is AdmissionOperationState.ACKNOWLEDGED
    with store.unit_of_work() as unit:
        current = unit.execute(
            "SELECT admission_state, admission_generation, binding_audience FROM project_target_admissions WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
    assert tuple(current) == ("revocation_pending", "2", "revoked-binding")


def test_generation_conflict_is_terminal_refusal_and_preserves_current_target(
    store: ProjectSyncStore,
    audience: AdmissionAudience,
) -> None:
    refusal = AdmissionResponse.refused(
        error_category="admission_generation_conflict",
        current_generation=2,
    )
    client = FakeAdmissionClient([refusal])
    service = AdmissionOperationService(store, client)
    with store.unit_of_work() as unit:
        service.targets.register(unit, audience)
        unit.execute(
            "UPDATE project_target_admissions SET admission_state = 'admitted', "
            "admission_generation = '2', binding_audience = 'current-binding' "
            "WHERE project_uuid = ?",
            (PROJECT,),
        )

    result = service.perform(
        action=AdmissionAction.REVOKE,
        audience=audience,
        operation_key=KEY_B,
        expected_generation=1,
    )

    assert result.state is AdmissionOperationState.REFUSED
    assert result.original_error_category == "admission_generation_conflict"
    with store.unit_of_work() as unit:
        current = unit.execute(
            "SELECT admission_state, admission_generation FROM project_target_admissions WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
    assert tuple(current) == ("admitted", "2")


def test_offline_revoke_reports_remote_unknown_not_acknowledged(
    store: ProjectSyncStore,
    audience: AdmissionAudience,
) -> None:
    client = FakeAdmissionClient([AdmissionTransportUncertain("offline")])
    service = AdmissionOperationService(store, client)
    with store.unit_of_work() as unit:
        service.targets.register(unit, audience)
        unit.execute(
            "UPDATE project_target_admissions SET admission_state = 'admitted', admission_generation = '1', binding_audience = 'binding-1' WHERE project_uuid = ?",
            (PROJECT,),
        )

    result = service.perform(
        action=AdmissionAction.REVOKE,
        audience=audience,
        operation_key=KEY_B,
        expected_generation=1,
    )

    assert result.state is AdmissionOperationState.UNKNOWN
    with store.unit_of_work() as unit:
        current = unit.execute(
            "SELECT admission_state, last_error_category FROM project_target_admissions WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()
    assert tuple(current) == ("revocation_pending", "remote_outcome_unknown")
