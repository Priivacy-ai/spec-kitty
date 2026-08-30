"""SC-001: reproduce the six-project incident on project-owned stores (#3030)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal import CaptureGateState, EventJournal
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore

if TYPE_CHECKING:
    from specify_cli.sync.emitter import EventEmitter

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

SILENT_REPOS = (
    "client-a/confidential-audit",
    "client-b/merger-diligence",
    "client-c/payroll-migration",
    "client-d/security-review",
    "client-e/board-reporting",
)
EVENTS_PER_PROJECT = 3


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    # The WP06 transport lease binds egress eligibility only while the machine
    # kill switch is armed (arming is NOT consent — #3030; the per-project
    # consent records still decide what ships).
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    yield


def _emitter(project_slug: str | None, repo_slug: str | None) -> EventEmitter:
    from specify_cli.sync.emitter import EventEmitter
    from specify_cli.sync.git_metadata import GitMetadata

    emitter = EventEmitter()
    emitter._identity = SimpleNamespace(
        build_id=f"build-{project_slug}",
        project_uuid=None if project_slug is None else uuid4(),
        project_slug=project_slug,
    )
    emitter._get_git_metadata = lambda: GitMetadata(repo_slug=repo_slug)
    emitter._capture_gate_state = lambda _team, **_kwargs: CaptureGateState(
        saas_enabled=True,
        checkout_enabled=True,
        authenticated=True,
        team_slug="team",
    )
    return emitter


def _initialize(emitter: EventEmitter, *, decision: str) -> ProjectSyncStore:
    project_uuid = str(emitter._identity.project_uuid)
    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover("incident-test")
        authority.publish_project_only("incident-test", verify_exact=lambda: True)
    if decision == "grant":
        record_project_opt_in(project_uuid, actor="incident-test")
        with store.unit_of_work() as unit:
            unit.execute(
                "INSERT INTO project_target_admissions "
                "(project_uuid, target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, admission_state, admission_generation, binding_audience) "
                "VALUES (?, 'https://hosted.example.com', 'operator@example.com', 'team', 1, "
                "'admitted', '1', 'private-teamspace:team')",
                (project_uuid,),
            )
    elif decision == "refuse":
        record_project_opt_out(project_uuid, actor="incident-test")
    return store


def _emit_batch(emitter: EventEmitter) -> set[str]:
    ids: set[str] = set()
    for index in range(EVENTS_PER_PROJECT):
        envelope = emitter._emit(
            event_type="ErrorLogged",
            aggregate_id=f"WP{index:02d}",
            aggregate_type="WorkPackage",
            payload={"error_type": "runtime", "error_message": f"boom {index}", "wp_id": f"WP{index:02d}"},
        )
        assert envelope is not None
        ids.add(str(envelope["event_id"]))
    return ids


def _population() -> tuple[
    EventEmitter,
    ProjectSyncStore,
    set[str],
    list[tuple[ProjectSyncStore, set[str]]],
]:
    consenting = _emitter("engagement-assistant", "my-org/engagement-assistant")
    consenting_store = _initialize(consenting, decision="grant")
    consenting_ids = _emit_batch(consenting)

    isolated: list[tuple[ProjectSyncStore, set[str]]] = []
    for repo in SILENT_REPOS:
        emitter = _emitter(repo.split("/")[1], repo)
        store = _initialize(emitter, decision="silent")
        isolated.append((store, _emit_batch(emitter)))
    refused = _emitter("explicitly-declined", "client-f/explicitly-declined")
    refused_store = _initialize(refused, decision="refuse")
    isolated.append((refused_store, _emit_batch(refused)))
    return consenting, consenting_store, consenting_ids, isolated


def test_sc001_only_the_consented_project_is_delivered(tmp_path: Path) -> None:
    del tmp_path
    _emitter_instance, store, consented_ids, isolated = _population()
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None
    receiver = StubReceiver()
    dispatch(
        store=store,
        receiver=receiver,
        target=target,
        context=store.create_context(),
    )
    assert set(receiver.received_event_ids()) == consented_ids
    for isolated_store, expected_ids in isolated:
        with isolated_store.unit_of_work() as unit:
            rows = EventJournal(unit, isolated_store.layout_generation()).read_all()
        assert {row.event_id for row in rows} == expected_ids

    identityless = _emitter(None, None)
    _emit_batch(identityless)
    assert identityless._identity.project_uuid is None


def test_delivered_identities_are_a_subset_of_consented(tmp_path: Path) -> None:
    del tmp_path
    consenting, store, _ids, _isolated = _population()
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None
    receiver = StubReceiver()
    dispatch(
        store=store,
        receiver=receiver,
        target=target,
        context=store.create_context(),
    )
    with store.unit_of_work() as unit:
        rows = {row.event_id: row for row in EventJournal(unit, store.layout_generation()).read_all()}
    delivered_uuids = {rows[event_id].project_uuid for event_id in receiver.received_event_ids()}
    assert None not in delivered_uuids
    assert delivered_uuids == {str(consenting._identity.project_uuid)}
