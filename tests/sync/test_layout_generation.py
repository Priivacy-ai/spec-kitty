"""Acceptance contract for the machine layout-generation write barrier."""

from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path

import pytest

from specify_cli.sync.layout_generation import (
    LayoutDestination,
    LayoutMode,
    LayoutTestHooks,
    LayoutVerificationError,
    StaleLayoutWritePermitError,
)
from specify_cli.sync.project_store import ProjectSyncStore


PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


def _store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    return ProjectSyncStore(PROJECT_UUID)


def test_cutover_requires_exact_verification_and_project_only_has_no_legacy_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    legacy = authority.issue_write_permit()
    assert legacy.destination is LayoutDestination.LEGACY
    assert legacy.project_uuid == store.project_uuid
    assert legacy.redirect_count == 0

    pending = authority.begin_cutover("migration-1")
    assert pending.mode is LayoutMode.CUTOVER_PENDING
    with pytest.raises(LayoutVerificationError):
        authority.publish_project_only("migration-1", verify_exact=lambda: False)
    assert authority.read_state().mode is LayoutMode.CUTOVER_PENDING

    project_only = authority.publish_project_only(
        "migration-1",
        verify_exact=lambda: True,
    )
    assert project_only.mode is LayoutMode.PROJECT_ONLY
    permit = authority.issue_write_permit()
    assert permit.destination is LayoutDestination.PROJECT_STORE
    assert not hasattr(permit, "legacy_path")
    assert tuple(permit.__dataclass_fields__) == (
        "project_uuid",
        "generation",
        "destination",
        "redirect_count",
    )


def test_stale_permit_never_reaches_insert_and_redirects_exactly_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    stale = authority.issue_write_permit()
    authority.begin_cutover("migration-1")
    authority.publish_project_only("migration-1", verify_exact=lambda: True)

    with pytest.raises(StaleLayoutWritePermitError):
        authority.revalidate(stale)

    inserts = []
    refreshed = authority.execute_write(stale, inserts.append)
    assert inserts == [refreshed]
    assert refreshed.destination is LayoutDestination.PROJECT_STORE
    assert refreshed.redirect_count == 1
    assert refreshed.generation == authority.read_state().generation

    already_redirected = replace(stale, redirect_count=1)
    unexpected_inserts = []
    with pytest.raises(StaleLayoutWritePermitError):
        authority.execute_write(already_redirected, unexpected_inserts.append)
    assert unexpected_inserts == []


def test_writer_racing_generation_advance_is_redirected_without_loss_or_double_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    writer_a_permit = authority.issue_write_permit()
    permit_acquired = threading.Event()
    allow_revalidation = threading.Event()
    inserted = []
    failures: list[BaseException] = []

    def pause_after_permit(_permit: object) -> None:
        permit_acquired.set()
        assert allow_revalidation.wait(timeout=5), "test coordination timed out"

    def writer_a() -> None:
        try:
            authority.execute_write(
                writer_a_permit,
                inserted.append,
                test_hooks=LayoutTestHooks(before_revalidate=pause_after_permit),
            )
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    thread = threading.Thread(target=writer_a)
    thread.start()
    assert permit_acquired.wait(timeout=5), "writer did not reach deterministic hook"

    authority.begin_cutover("migration-1")
    authority.publish_project_only("migration-1", verify_exact=lambda: True)
    writer_b_permit = authority.issue_write_permit()
    authority.execute_write(writer_b_permit, inserted.append)
    allow_revalidation.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert failures == []
    assert len(inserted) == 2
    assert all(permit.destination is LayoutDestination.PROJECT_STORE for permit in inserted)
    assert sorted(permit.redirect_count for permit in inserted) == [0, 1]


def test_layout_authority_is_machine_shared_but_project_permits_are_not(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store_a = ProjectSyncStore(PROJECT_UUID)
    store_b = ProjectSyncStore("bbbbbbbb-0000-0000-0000-000000000002")
    authority_a = store_a.layout_generation()
    authority_b = store_b.layout_generation()

    authority_a.begin_cutover("migration-1")
    authority_a.publish_project_only("migration-1", verify_exact=lambda: True)

    permit_b = authority_b.issue_write_permit()
    assert permit_b.project_uuid == store_b.project_uuid
    assert permit_b.destination is LayoutDestination.PROJECT_STORE
    with pytest.raises(ValueError, match="project UUID"):
        authority_a.revalidate(permit_b)
