"""Acceptance contract for the machine layout-generation write barrier."""

from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path

import pytest
from filelock import FileLock, Timeout

from specify_cli.sync.layout_generation import (
    LayoutAuthorityCorruptError,
    LayoutAuthorityLockedError,
    LayoutDestination,
    LayoutGenerationAuthority,
    LayoutMode,
    LayoutTestHooks,
    LayoutVerificationError,
    LayoutWritePermit,
    StaleLayoutWritePermitError,
)
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


def _store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    return ProjectSyncStore(PROJECT_UUID)


def _legacy_generation_permit(
    store: ProjectSyncStore,
    authority: LayoutGenerationAuthority,
) -> LayoutWritePermit:
    """Bind a permit to the machine's initial legacy generation.

    Post cutover-flip (WP03/IC-02) ``issue_write_permit`` is the write-path
    resolution seam: on a greenfield root it publishes ``project_only`` *before*
    any legacy persist, and on a legacy-data root it auto-migrates — so it no
    longer hands back a raw ``LEGACY`` permit. These barrier tests exercise how
    ``execute_write`` treats a permit a writer obtained *under the legacy
    generation, before cutover advanced*. ``read_state`` establishes that
    generation on disk (mode ``legacy``, generation 1) and we bind a permit to it
    directly, modelling exactly that pre-cutover writer.
    """
    state = authority.read_state()
    assert state.mode is LayoutMode.LEGACY
    return LayoutWritePermit(
        project_uuid=store.project_uuid,
        generation=state.generation,
        destination=LayoutDestination.LEGACY,
    )


def test_layout_authority_can_only_be_constructed_by_project_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    with pytest.raises(TypeError):
        LayoutGenerationAuthority(store.project_uuid, tmp_path / "foreign-runtime")

    authority = store.layout_generation()
    assert authority.record_path == (tmp_path / "runtime" / "projects" / ".layout-generation.json")
    assert authority.lock_path == (tmp_path / "runtime" / "projects" / ".layout-generation.lock")
    assert authority.marker_path == (tmp_path / "runtime" / "projects" / ".layout-generation.initialized")


def test_layout_peek_is_read_only_when_authority_is_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    projects = authority.record_path.parent

    state = authority.peek_state()

    assert state.mode is LayoutMode.LEGACY
    assert not projects.exists()
    assert not authority.record_path.exists()
    assert not authority.marker_path.exists()
    assert not authority.lock_path.exists()


def test_layout_peek_detects_missing_record_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    authority.read_state()
    authority.record_path.unlink()
    before_marker = authority.marker_path.read_bytes()
    authority.lock_path.unlink(missing_ok=True)

    with pytest.raises(LayoutAuthorityCorruptError, match="record is missing"):
        authority.peek_state()

    assert authority.marker_path.read_bytes() == before_marker
    assert not authority.record_path.exists()
    assert not authority.lock_path.exists()


def test_cutover_requires_exact_verification_and_project_only_has_no_legacy_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    legacy = _legacy_generation_permit(store, authority)
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
    stale = _legacy_generation_permit(store, authority)
    authority.begin_cutover("migration-1")
    authority.publish_project_only("migration-1", verify_exact=lambda: True)

    with pytest.raises(StaleLayoutWritePermitError):
        authority.revalidate(stale)

    inserts: list[LayoutWritePermit] = []
    refreshed = authority.execute_write(stale, inserts.append)
    assert inserts == [refreshed]
    assert refreshed.destination is LayoutDestination.PROJECT_STORE
    assert refreshed.redirect_count == 1
    assert refreshed.generation == authority.read_state().generation

    already_redirected = replace(stale, redirect_count=1)
    unexpected_inserts: list[LayoutWritePermit] = []
    with pytest.raises(StaleLayoutWritePermitError):
        authority.execute_write(already_redirected, unexpected_inserts.append)
    assert unexpected_inserts == []


def test_writer_racing_generation_advance_is_redirected_without_loss_or_double_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    writer_a_permit = _legacy_generation_permit(store, authority)
    permit_acquired = threading.Event()
    allow_revalidation = threading.Event()
    inserted: list[LayoutWritePermit] = []
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


def test_writer_first_holds_layout_lock_until_legacy_insert_finishes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    permit = _legacy_generation_permit(store, authority)
    writer_entered = threading.Event()
    release_writer = threading.Event()
    cutover_attempting = threading.Event()
    cutover_done = threading.Event()
    inserts: list[LayoutWritePermit] = []
    failures: list[BaseException] = []

    def writer_callback(candidate: object) -> None:
        inserts.append(candidate)
        writer_entered.set()
        assert release_writer.wait(timeout=5), "test coordination timed out"

    def writer() -> None:
        try:
            authority.execute_write(permit, writer_callback)
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    def cutover() -> None:
        try:
            cutover_attempting.set()
            authority.begin_cutover("migration-1")
            authority.publish_project_only("migration-1", verify_exact=lambda: True)
            cutover_done.set()
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    writer_thread = threading.Thread(target=writer)
    cutover_thread = threading.Thread(target=cutover)
    writer_thread.start()
    assert writer_entered.wait(timeout=5)
    cutover_thread.start()
    assert cutover_attempting.wait(timeout=5)

    expected_lock_path = tmp_path / "runtime" / "projects" / ".layout-generation.lock"
    try:
        with pytest.raises(Timeout), FileLock(str(expected_lock_path), timeout=0):
            pytest.fail("writer callback must retain the machine layout lock")
        assert not cutover_done.is_set()
    finally:
        release_writer.set()
        writer_thread.join(timeout=5)
        cutover_thread.join(timeout=5)
    assert not writer_thread.is_alive()
    assert not cutover_thread.is_alive()
    assert failures == []
    assert len(inserts) == 1
    assert inserts[0].destination is LayoutDestination.LEGACY
    assert authority.read_state().mode is LayoutMode.PROJECT_ONLY


def test_published_record_loss_fails_closed_without_legacy_reset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    # Post-flip, the first write on a greenfield root resolves straight to
    # project_only (auto-published before any legacy persist), which writes both
    # the authority record and its durable initialization marker.
    permit = authority.issue_write_permit()
    assert permit.destination is LayoutDestination.PROJECT_STORE
    assert authority.marker_path.is_file()
    authority.record_path.unlink()

    with pytest.raises(LayoutAuthorityCorruptError, match="missing"):
        authority.issue_write_permit()

    assert not authority.record_path.exists()
    assert authority.marker_path.is_file()


def test_malformed_layout_record_is_preserved_and_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    authority.issue_write_permit()
    evidence = b"{not-json\x00incident-evidence"
    authority.record_path.write_bytes(evidence)

    with pytest.raises(LayoutAuthorityCorruptError):
        authority.read_state()

    assert authority.record_path.read_bytes() == evidence


def test_layout_lock_contention_fails_closed_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    authority = store.layout_generation()
    authority.issue_write_permit()
    before = authority.record_path.read_bytes()
    contending = store.layout_generation(lock_timeout_seconds=0)

    with (
        FileLock(str(authority.lock_path), timeout=0),
        pytest.raises(LayoutAuthorityLockedError),
    ):
        contending.read_state()

    assert authority.record_path.read_bytes() == before


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
