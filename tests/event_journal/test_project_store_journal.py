"""Public contract for the UUID-owned journal repository."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.layout_generation import (
    LayoutDestination,
    LayoutTestHooks,
    LayoutWritePermit,
)
from specify_cli.sync.project_store import ProjectSyncStore

pytestmark = pytest.mark.fast


PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"


def _project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    authority.begin_cutover("wp04-test")
    authority.publish_project_only("wp04-test", verify_exact=lambda: True)


def _event(event_id: str, project_uuid: str) -> Event:
    return Event(
        event_id=event_id,
        event_type="WPStatusChanged",
        payload=json.dumps({"project_uuid": project_uuid}).encode(),
        occurred_at="2026-08-10T00:00:00+00:00",
        created_at="2026-08-10T00:00:01+00:00",
        project_uuid=project_uuid,
        project_slug="same-slug",
        repo_slug="same-slug",
    )


def test_capture_is_owned_sequenced_and_physically_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store_a = ProjectSyncStore(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B)
    _project_only(store_a)

    with store_a.unit_of_work() as unit:
        journal = EventJournal(unit, store_a.layout_generation())
        first = journal.append(_event("event-a-1", PROJECT_A))
        second = journal.append(_event("event-a-2", PROJECT_A))

    assert (first.capture_sequence, second.capture_sequence) == (1, 2)
    assert first.epoch_id == second.epoch_id
    with store_a.unit_of_work() as unit:
        assert [row.event_id for row in EventJournal(unit, store_a.layout_generation()).read_all()] == [
            "event-a-1",
            "event-a-2",
        ]
    with store_b.unit_of_work() as unit:
        assert EventJournal(unit, store_b.layout_generation()).read_all() == []
    assert store_a.database_path != store_b.database_path


def test_capture_rejects_event_declared_for_another_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)
    _project_only(store)

    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        with pytest.raises(ValueError, match="owner"):
            journal.append(_event("foreign", PROJECT_B))

    with store.unit_of_work() as unit:
        assert EventJournal(unit, store.layout_generation()).count() == 0


def test_stale_legacy_permit_redirects_once_before_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime))
    store = ProjectSyncStore(PROJECT_A)
    authority = store.layout_generation()
    # Hold the machine CUTOVER_PENDING under a *foreign* (operator-owned) migration
    # id so the live capture resolves to a LEGACY (pending) permit that must wait
    # for publication. Post cutover-flip (WP03/IC-02) a first write on an
    # unencumbered root resolves straight to project_only, so this pending hold is
    # how we still exercise the stale-legacy-permit → redirect-once seam.
    authority.begin_cutover("operator-owned-race")
    observed_destinations: list[LayoutDestination] = []

    def publish_cutover_between_issue_and_revalidate(
        permit: LayoutWritePermit,
    ) -> None:
        if observed_destinations:
            return
        observed_destinations.append(permit.destination)
        authority.publish_project_only("operator-owned-race", verify_exact=lambda: True)

    with store.unit_of_work() as unit:
        receipt = EventJournal(unit, authority).append(
            _event("event-race", PROJECT_A),
            test_hooks=LayoutTestHooks(before_revalidate=publish_cutover_between_issue_and_revalidate),
        )
        assert EventJournal(unit, authority).count() == 1

    assert observed_destinations == [LayoutDestination.LEGACY]
    assert receipt.inserted is True
    assert list(runtime.rglob("*.db")) == [store.database_path]


def test_same_uuid_store_instances_share_one_physical_journal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    first = ProjectSyncStore(PROJECT_A)
    second = ProjectSyncStore(PROJECT_A)
    _project_only(first)

    with first.unit_of_work() as unit:
        EventJournal(unit, first.layout_generation()).append(_event("event-shared", PROJECT_A))
    with second.unit_of_work() as unit:
        observed = EventJournal(unit, second.layout_generation()).read_all()

    assert first.database_path == second.database_path
    assert [event.event_id for event in observed] == ["event-shared"]


def test_journal_adapter_exposes_no_connection_or_commit_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT_A)
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        assert not hasattr(journal, "connection")
        assert not hasattr(journal, "commit")
        assert not hasattr(journal, "db_path")
