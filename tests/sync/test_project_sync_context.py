"""Acceptance contract for immutable store-derived sync capabilities."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from specify_cli.sync.project_context import (
    AdmissionState,
    ConsentState,
    ProjectSyncContext,
    TargetAudience,
)
from specify_cli.sync.project_store import ProjectSyncStore


PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"


def _store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)
    with store.unit_of_work():
        pass
    return store


def test_context_can_only_be_constructed_from_a_verified_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    with pytest.raises(TypeError):
        ProjectSyncContext(project_uuid=store.project_uuid)  # type: ignore[call-arg]

    context = store.create_context()
    assert context.project_uuid == store.project_uuid
    assert context.store_identity.project_uuid == store.project_uuid
    assert context.store_identity.database_path == store.database_path
    assert context.consent_state is None
    assert context.egress_eligible is False


def test_context_rejects_cross_project_and_partial_authority_pairs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    foreign_audience = TargetAudience(
        project_uuid=PROJECT_B,
        target_identity="https://app.spec-kitty.ai",
        account_identity="account-1",
        private_teamspace_id="teamspace-1",
        configuration_generation=4,
    )

    with pytest.raises(ValueError, match="project UUID"):
        store.create_context(target_audience=foreign_audience)
    with pytest.raises(ValueError, match="consent"):
        store.create_context(consent_state=ConsentState.GRANTED)
    with pytest.raises(ValueError, match="admission"):
        store.create_context(
            admission_state=AdmissionState.ADMITTED,
            admission_generation="server-generation-1",
        )
    with pytest.raises(ValueError, match="transport lease"):
        store.create_context(transport_lease_identity="lease-without-authority")


def test_eligibility_is_pure_and_context_is_frozen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    audience = TargetAudience(
        project_uuid=PROJECT_A,
        target_identity="https://app.spec-kitty.ai",
        account_identity="account-1",
        private_teamspace_id="teamspace-1",
        configuration_generation=4,
    )
    context = store.create_context(
        consent_state=ConsentState.GRANTED,
        consent_generation=3,
        epoch_id=7,
        target_audience=audience,
        admission_state=AdmissionState.ADMITTED,
        admission_generation="server-generation-1",
        binding_audience="private-teamspace:teamspace-1",
        kill_switch_allows=True,
        transport_lease_identity="lease-1",
    )

    before = context
    assert context.egress_eligible is True
    assert context is before
    assert context.consent_state is ConsentState.GRANTED
    with pytest.raises(FrozenInstanceError):
        context.consent_generation = 99  # type: ignore[misc]


def test_capture_and_maintenance_capabilities_cannot_carry_loose_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    context = store.create_context(epoch_id=2)

    capture = context.capture_capability()
    maintenance = context.maintenance_capability()
    assert capture.project_uuid == context.project_uuid
    assert capture.store_identity is context.store_identity
    assert capture.epoch_id == 2
    assert maintenance.project_uuid == context.project_uuid
    assert maintenance.store_identity is context.store_identity
    assert not hasattr(capture, "database_path")
    assert not hasattr(maintenance, "database_path")
