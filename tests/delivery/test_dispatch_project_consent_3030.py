"""Per-project stores keep one checkout from shipping a sibling's events (#3030)."""

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
from specify_cli.sync.consent import record_project_opt_in
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


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    yield


def _stub_emitter(*, project_slug: str, build_id: str) -> EventEmitter:
    from specify_cli.sync.emitter import EventEmitter
    from specify_cli.sync.git_metadata import GitMetadata

    emitter = EventEmitter()
    emitter._identity = SimpleNamespace(build_id=build_id, project_uuid=uuid4(), project_slug=project_slug)
    emitter._get_git_metadata = lambda: GitMetadata(repo_slug=f"org/{project_slug}")
    # The emit path stamps the envelope's drain_blocked_reason from these two
    # seams (not from _capture_gate_state); a fully-ready session must stub
    # them too or every capture is stamped blocked and never selected.
    emitter._is_authenticated = lambda: True
    emitter._get_team_slug = lambda: "team"
    emitter._capture_gate_state = lambda _team, **_kwargs: CaptureGateState(
        saas_enabled=True,
        checkout_enabled=True,
        authenticated=True,
        team_slug="team",
    )
    return emitter


def _initialize(project_uuid: str, *, admitted: bool = False) -> ProjectSyncStore:
    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover("project-consent-test")
        authority.publish_project_only("project-consent-test", verify_exact=lambda: True)
    if admitted:
        record_project_opt_in(project_uuid, actor="project-consent-test")
        with store.unit_of_work() as unit:
            unit.execute(
                "INSERT INTO project_target_admissions "
                "(project_uuid, target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, admission_state, admission_generation, binding_audience) "
                "VALUES (?, 'https://hosted.example.com', 'operator@example.com', 'team', 1, "
                "'admitted', '1', 'private-teamspace:team')",
                (project_uuid,),
            )
    return store


def _emit(emitter: EventEmitter) -> str:
    envelope = emitter._emit(
        event_type="ErrorLogged",
        aggregate_id="WP04",
        aggregate_type="WorkPackage",
        payload={"error_type": "runtime", "error_message": "boom", "wp_id": "WP04"},
    )
    assert envelope is not None
    return str(envelope["event_id"])


def test_consenting_project_leaks_sibling_project_event_through_shared_journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The historical node now proves the leak is impossible by store ownership."""
    del tmp_path, monkeypatch
    consenting = _stub_emitter(project_slug="engagement", build_id="build-a")
    silent = _stub_emitter(project_slug="confidential", build_id="build-b")
    consenting_store = _initialize(str(consenting._identity.project_uuid), admitted=True)
    silent_store = _initialize(str(silent._identity.project_uuid))

    consenting_id = _emit(consenting)
    silent_id = _emit(silent)
    with consenting_store.unit_of_work() as unit:
        consenting_rows = EventJournal(unit, consenting_store.layout_generation()).read_all()
        target = ProjectDeliveryTargetRegistry(consenting_store).get_current(unit)
    with silent_store.unit_of_work() as unit:
        silent_rows = EventJournal(unit, silent_store.layout_generation()).read_all()
    assert {row.event_id for row in consenting_rows} == {consenting_id}
    assert {row.event_id for row in silent_rows} == {silent_id}
    assert target is not None

    receiver = StubReceiver()
    dispatch(
        store=consenting_store,
        receiver=receiver,
        target=target,
        context=consenting_store.create_context(),
    )
    assert set(receiver.received_event_ids()) == {consenting_id}
    with silent_store.unit_of_work() as unit:
        assert EventJournal(unit, silent_store.layout_generation()).count() == 1


def test_a_never_opted_in_project_no_longer_reaches_the_journal_at_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Silent projects retain locally but cannot enter another project's drain."""
    del tmp_path, monkeypatch
    silent = _stub_emitter(project_slug="silent", build_id="build-silent")
    store = _initialize(str(silent._identity.project_uuid))
    event_id = _emit(silent)
    with store.unit_of_work() as unit:
        rows = EventJournal(unit, store.layout_generation()).read_all()
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert [row.event_id for row in rows] == [event_id]
    assert target is None, "no admission exists, so no hosted drain can start"
