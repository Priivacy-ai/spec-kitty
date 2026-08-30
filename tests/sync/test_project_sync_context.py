"""Acceptance contract for immutable store-derived sync capabilities."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from specify_cli.sync.project_context import (
    AdmissionState,
    ConsentState,
    ProjectCaptureCapability,
    ProjectStoreMaintenanceCapability,
    ProjectSyncContext,
    VerifiedProjectStoreIdentity,
)
from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore

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


def _store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)
    with store.unit_of_work():
        pass
    return store


def _seed_persisted_authority(store: ProjectSyncStore) -> None:
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_consent_decisions "
            "(project_uuid, state, generation, action, actor, decided_at, "
            "decision_schema_version) "
            "VALUES (?, 'granted', 3, 'explicit_opt_in', 'test-actor', "
            "'2026-08-10T00:00:00Z', 1)",
            (PROJECT_A,),
        )
        unit.execute(
            "INSERT INTO consent_epochs (epoch_id, project_uuid, opened_at_tail, state, consent_generation, reason) VALUES (7, ?, 0, 'eligible', 3, 'opt_in')",
            (PROJECT_A,),
        )
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, "
            "binding_audience) "
            "VALUES (?, 'https://app.spec-kitty.ai', 'account-1', 'teamspace-1', 4, "
            "'admitted', 'server-generation-1', "
            "'private-teamspace:teamspace-1')",
            (PROJECT_A,),
        )


def test_context_can_only_be_constructed_from_a_verified_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    with pytest.raises(TypeError):
        ProjectSyncContext()

    context = store.create_context()
    assert context.project_uuid == store.project_uuid
    assert context.store_identity.project_uuid == store.project_uuid
    assert context.store_identity.database_path == store.database_path
    assert context.consent_state is None
    assert context.egress_eligible is False


def test_context_from_active_unit_reuses_exact_verified_store_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    _seed_persisted_authority(store)

    with store.unit_of_work() as unit:
        context = store.create_context_from_unit(unit)
        assert context.store_identity is unit.store_identity
        assert context.consent_state is ConsentState.GRANTED
        assert context.epoch_id == 7
        assert context.target_audience is not None
        assert context.target_audience.target_identity == "https://app.spec-kitty.ai"
        assert context.kill_switch_allows is False
        assert context.transport_lease_identity is None


def test_context_from_unit_rejects_foreign_and_inactive_units(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store_a = ProjectSyncStore(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B)

    with (
        store_b.unit_of_work() as foreign_unit,
        pytest.raises(ProjectStoreError, match="active store unit"),
    ):
        store_a.create_context_from_unit(foreign_unit)

    with pytest.raises(ProjectStoreError, match="active store unit"):
        store_b.create_context_from_unit(foreign_unit)


def test_context_authority_is_loaded_from_persisted_rows_not_caller_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    assert tuple(inspect.signature(ProjectSyncStore.create_context).parameters) == ("self",)
    with pytest.raises(TypeError):
        store.create_context(consent_state=ConsentState.GRANTED)  # type: ignore[call-arg]

    _seed_persisted_authority(store)
    context = store.create_context()

    assert context.consent_state is ConsentState.GRANTED
    assert context.consent_generation == 3
    assert context.epoch_id == 7
    assert context.target_audience is not None
    assert context.target_audience.project_uuid == store.project_uuid
    assert context.target_audience.target_identity == "https://app.spec-kitty.ai"
    assert context.target_audience.account_identity == "account-1"
    assert context.target_audience.private_teamspace_id == "teamspace-1"
    assert context.target_audience.configuration_generation == 4
    assert context.admission_state is AdmissionState.ADMITTED
    assert context.admission_generation == "server-generation-1"
    assert context.binding_audience == "private-teamspace:teamspace-1"
    assert context.kill_switch_allows is False
    assert context.transport_lease_identity is None
    assert context.egress_eligible is False


def test_empty_store_cannot_be_minted_into_an_egress_eligible_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    context = store.create_context()

    assert context.consent_state is None
    assert context.consent_generation is None
    assert context.epoch_id is None
    assert context.target_audience is None
    assert context.admission_state is None
    assert context.admission_generation is None
    assert context.binding_audience is None
    assert context.kill_switch_allows is False
    assert context.transport_lease_identity is None
    assert context.egress_eligible is False


def test_context_and_capability_constructors_are_not_forgeable_across_stores(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store_a = ProjectSyncStore(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B)
    context_a = store_a.create_context()
    context_b = store_b.create_context()

    with pytest.raises(TypeError):
        VerifiedProjectStoreIdentity(
            store_a.project_uuid,
            store_b.database_path,
            store_b.schema_version,
            store_b.layout_version,
        )
    with pytest.raises(TypeError):
        ProjectCaptureCapability(
            store_a.project_uuid,
            context_b.store_identity,
            None,
        )
    with pytest.raises(TypeError):
        ProjectStoreMaintenanceCapability(
            store_a.project_uuid,
            context_b.store_identity,
        )
    assert context_a.store_identity.database_path != context_b.store_identity.database_path


def test_eligibility_is_pure_and_context_is_frozen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    _seed_persisted_authority(store)
    context = store.create_context()

    before = context
    assert context.egress_eligible is False
    assert context is before
    assert context.consent_state is ConsentState.GRANTED
    with pytest.raises(FrozenInstanceError):
        context.consent_generation = 99  # type: ignore[misc]


def test_capture_and_maintenance_capabilities_are_store_derived(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    _seed_persisted_authority(store)
    context = store.create_context()

    capture = context.capture_capability()
    maintenance = context.maintenance_capability()
    assert capture.project_uuid == context.project_uuid
    assert capture.store_identity is context.store_identity
    assert capture.epoch_id == 7
    assert maintenance.project_uuid == context.project_uuid
    assert maintenance.store_identity is context.store_identity
    assert not hasattr(capture, "database_path")
    assert not hasattr(maintenance, "database_path")
