"""Project-owned delivery target repository acceptance tests."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from specify_cli.delivery import DeliveryTargetRegistry, ProjectDeliveryTargetRegistry
from specify_cli.sync.project_context import AdmissionState
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

PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "aaaaaaaa-0000-0000-0000-000000000002"


def _audience(store: ProjectSyncStore, *, origin: str = "https://one.example", generation: int = 1) -> AdmissionAudience:
    return AdmissionAudience(
        normalized_server_origin=origin,
        account_identity="account-1",
        private_teamspace_id="teamspace-1",
        project_uuid=store.project_uuid,
        configuration_generation=generation,
    )


def test_registry_is_connection_free_repository_over_project_unit_of_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)
    registry = ProjectDeliveryTargetRegistry(store)

    with store.unit_of_work() as unit:
        target = registry.register(unit, _audience(store))
        assert registry.get_current(unit) == target

    assert isinstance(registry, DeliveryTargetRegistry)
    source = inspect.getsource(type(registry))
    assert "sqlite3.connect" not in source
    assert ".commit(" not in source
    assert target.project_uuid == store.project_uuid


def test_target_change_invalidates_remote_proof_without_selecting_another_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)
    registry = ProjectDeliveryTargetRegistry(store)
    with store.unit_of_work() as unit:
        registry.register(unit, _audience(store))
        unit.execute(
            "UPDATE project_target_admissions SET admission_state = 'admitted', admission_generation = '7', binding_audience = 'opaque' WHERE project_uuid = ?",
            (PROJECT_A,),
        )
    with store.unit_of_work() as unit:
        changed = registry.register(unit, _audience(store, origin="https://two.example", generation=2))

    assert changed.admission_state == "pending"
    assert changed.admission_generation is None
    assert changed.binding_audience is None
    context = store.create_context()
    assert context.admission_state is AdmissionState.PENDING
    assert context.admission_generation is None
    assert context.binding_audience is None


def test_registry_write_rolls_back_with_outer_project_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)
    registry = ProjectDeliveryTargetRegistry(store)

    with pytest.raises(RuntimeError), store.unit_of_work() as unit:
        registry.register(unit, _audience(store))
        raise RuntimeError("roll back whole action")

    with store.unit_of_work() as unit:
        assert registry.get_current(unit) is None


def test_project_a_and_b_target_rows_are_physically_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store_a = ProjectSyncStore(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B)
    registry_a = ProjectDeliveryTargetRegistry(store_a)
    registry_b = ProjectDeliveryTargetRegistry(store_b)
    with store_a.unit_of_work() as unit_a:
        registry_a.register(unit_a, _audience(store_a))
    with store_b.unit_of_work() as unit_b:
        assert registry_b.get_current(unit_b) is None
        registry_b.register(unit_b, _audience(store_b, origin="https://two.example"))

    assert store_a.database_path != store_b.database_path
    with store_a.unit_of_work() as unit_a:
        assert registry_a.get_current(unit_a).target_identity == "https://one.example"
    with store_b.unit_of_work() as unit_b:
        assert registry_b.get_current(unit_b).target_identity == "https://two.example"


def test_foreign_project_audience_is_rejected_before_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store_a = ProjectSyncStore(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B)
    registry = ProjectDeliveryTargetRegistry(store_a)

    with store_a.unit_of_work() as unit, pytest.raises(ValueError, match="project"):
        registry.register(unit, _audience(store_b))
    with store_a.unit_of_work() as unit:
        assert registry.get_current(unit) is None
