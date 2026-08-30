"""Tests for checkout diagnostics and explicit UUID-owned sync authority.

Legacy checkout/repository values remain observable diagnostics, but they never
grant hosted egress. Opt-in/out decisions and payload retention are exercised
through one explicit :class:`ProjectSyncStore` and its unit of work.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from specify_cli.identity.project import ProjectIdentity
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.retention import (
    purge_project_body_uploads,
    purge_project_events,
    purge_project_payloads,
)
from specify_cli.event_journal.journal import EventJournal
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.consent import (
    ConsentAuthorityStatus,
    read_project_consent_decision,
    record_project_opt_in,
    record_project_opt_out,
)
from specify_cli.sync.namespace import NamespaceRef
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.routing import (
    _build_checkout_sync_routing,
    disable_checkout_sync,
    is_sync_enabled_for_checkout,
    read_local_sync_enabled,
    resolve_checkout_sync_routing,
    resolve_checkout_sync_routing_readonly,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


def _write_repo_config(
    repo_root: Path,
    *,
    project_uuid: str | None = None,
    repo_slug: str = "acme/spec-kitty",
) -> str:
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    if project_uuid is None:
        project_uuid = str(uuid4())
    (config_dir / "config.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  uuid: {project_uuid}",
                "  slug: spec-kitty-local",
                "  node_id: node12345678",
                f"  repo_slug: {repo_slug}",
                "  build_id: build-123",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return project_uuid


def _project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    authority.begin_cutover("routing-test")
    authority.publish_project_only("routing-test", verify_exact=lambda: True)


def test_resolve_checkout_sync_routing_uses_global_repo_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    _write_repo_config(repo_root)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo_root)

    config_file = home / ".spec-kitty" / "config.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        '[sync.repo_defaults."acme/spec-kitty"]\nenabled = false\n',
        encoding="utf-8",
    )

    routing = resolve_checkout_sync_routing()

    assert routing is not None
    assert routing.repo_slug == "acme/spec-kitty"
    assert routing.local_sync_enabled is None
    assert routing.repo_default_sync_enabled is False
    assert routing.effective_sync_enabled is False


def test_readonly_routing_does_not_create_project_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    (repo_root / ".kittify").mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo_root)

    routing = resolve_checkout_sync_routing_readonly()

    assert routing is not None
    assert routing.project_uuid is None
    assert routing.project_slug is None
    assert not (repo_root / ".kittify" / "config.yaml").exists()


def test_local_override_beats_global_repo_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit project opt-in grants while a legacy repo default stays diagnostic."""
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    project_uuid = _write_repo_config(repo_root)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    monkeypatch.chdir(repo_root)

    config_file = home / ".spec-kitty" / "config.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        '[sync.repo_defaults."acme/spec-kitty"]\nenabled = false\n',
        encoding="utf-8",
    )
    record_project_opt_in(project_uuid, actor="routing-test")

    routing = resolve_checkout_sync_routing()

    assert routing is not None
    assert routing.local_sync_enabled is None
    assert routing.repo_default_sync_enabled is False
    assert routing.effective_sync_enabled is True


def test_local_override_is_persisted_outside_repo_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A project refusal persists in its store without writing either legacy config."""
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    project_uuid = _write_repo_config(repo_root)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))

    original_repo_config = (repo_root / ".kittify" / "config.yaml").read_text(encoding="utf-8")

    record_project_opt_out(project_uuid, actor="routing-test")

    assert (repo_root / ".kittify" / "config.yaml").read_text(encoding="utf-8") == original_repo_config
    assert read_local_sync_enabled(repo_root) is None
    assert read_project_consent_decision(project_uuid).status is ConsentAuthorityStatus.REFUSED
    assert not (home / ".spec-kitty" / "config.toml").exists()


def test_disable_checkout_sync_purges_only_matching_project_body_uploads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Opt-out retains payloads; an explicit purge can touch only its project store."""
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    project_uuid = str(uuid4())
    _write_repo_config(repo_root, project_uuid=project_uuid)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    monkeypatch.chdir(repo_root)
    other_uuid = str(uuid4())
    store = ProjectSyncStore(project_uuid)
    other_store = ProjectSyncStore(other_uuid)
    _project_only(store)

    for current_store, current_uuid, event_id, artifact_path in (
        (store, project_uuid, "evt-1", "spec.md"),
        (other_store, other_uuid, "evt-2", "plan.md"),
    ):
        with current_store.unit_of_work() as unit:
            OfflineQueue(unit, current_store.layout_generation()).queue_event(
                {
                    "event_id": event_id,
                    "event_type": "BuildRegistered",
                    "project_uuid": current_uuid,
                    "payload": {"project_uuid": current_uuid},
                }
            )
            OfflineBodyUploadQueue(unit, current_store.layout_generation()).enqueue(
                NamespaceRef(
                    project_uuid=current_uuid,
                    mission_slug="001-test",
                    target_branch="main",
                    mission_type="software-dev",
                    manifest_version="1",
                ),
                artifact_path=artifact_path,
                content_hash=f"hash-{event_id}",
                content_body="# Body\n",
                size_bytes=7,
            )

    result = disable_checkout_sync(repo_root)

    assert result.routing.effective_sync_enabled is False
    assert result.removed_events == 0
    assert result.removed_body_uploads == 0

    with store.unit_of_work() as unit:
        purge = purge_project_payloads(unit, store.layout_generation())
    assert (purge.target_before, purge.target_after) == (1, 0)
    assert (purge.body_before, purge.body_after) == (1, 0)

    with other_store.unit_of_work() as unit:
        assert OfflineQueue(unit, other_store.layout_generation()).size() == 1
        assert OfflineBodyUploadQueue(unit, other_store.layout_generation()).size() == 1
    assert read_project_consent_decision(project_uuid).status is ConsentAuthorityStatus.REFUSED


# --- WP01 / FR-003: the sync-enabled gate must fail CLOSED -------------------
# Regression cover for spec-kitty#3030. Before this, `is_sync_enabled_for_checkout`
# returned True whenever routing could not be resolved, so an inability to
# determine consent was read as consent — the inverted default in front of a
# confidentiality boundary.


def test_sync_enabled_denies_when_routing_is_unresolvable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unresolvable routing must DENY, not permit (FR-003, SC-003)."""
    from specify_cli.sync import routing as routing_module

    monkeypatch.setattr(routing_module, "resolve_checkout_sync_routing_readonly", lambda start=None: None)

    assert routing_module.is_sync_enabled_for_checkout() is False


def test_absence_of_consent_record_denies_capture_and_delivery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A checkout with NO consent record denies, for capture AND delivery.

    This assertion was inverted on 2026-07-28 and corrected on 2026-07-29. The
    earlier version asserted capture still proceeds, on capture-first grounds
    (NFR-005 as originally written). The operator has since ruled that capture
    yields: a non-consenting project's events must never reach the journal
    (#3031 Defect 3), so NFR-005 now applies only to consenting projects.

    Pinned upstream by
    ``test_sync_consent_default_deny.py::test_unconfigured_checkout_does_not_consent_to_sync``.
    """
    repo_root = tmp_path / "never-opted-in"
    repo_root.mkdir()
    _write_repo_config(repo_root, project_uuid=str(uuid4()), repo_slug="acme/never-opted-in")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo_root)

    routing = resolve_checkout_sync_routing_readonly()

    assert routing is not None
    assert routing.local_sync_enabled is None
    assert routing.repo_default_sync_enabled is None
    assert routing.effective_sync_enabled is False


# --- C-004: opt-out purges the store that actually ships (#3030 WP08) ---------


def _seed_journal_row(journal: Any, event_id: str, project_uuid: str | None, index: int) -> None:
    from specify_cli.event_journal.models import Event

    payload = {"event_id": event_id, "event_type": "mission.updated"}
    if project_uuid is not None:
        payload["project_uuid"] = project_uuid
    journal.append(
        Event(
            event_id=event_id,
            event_type="mission.updated",
            payload=json.dumps(payload).encode("utf-8"),
            occurred_at="2026-07-29T00:00:00+00:00",
            created_at=f"2026-07-29T00:00:{index:02d}+00:00",
            project_uuid=project_uuid,
        )
    )


@pytest.mark.usefixtures("canonical_home")  # R1b (#3121): the canonical owner pins SPEC_KITTY_HOME=tmp_path/home
def test_opt_out_purge_targets_the_same_stores_the_drain_reads() -> None:
    """Journal, ledger, and retention share one verified physical project store."""
    project_uuid = str(uuid4())
    store = ProjectSyncStore(project_uuid)
    _project_only(store)

    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        _seed_journal_row(journal, "queued", project_uuid, 1)
        ledger.record_success("queued", "target")
        assert journal.project_uuid == project_uuid
        assert ledger.project_uuid == project_uuid
        assert unit.store_identity.database_path == store.database_path

    with store.unit_of_work() as unit:
        assert EventJournal(unit, store.layout_generation()).read_by_id("queued") is not None
        assert SqliteDeliveryLedger(unit, store.layout_generation()).delivered_anywhere("queued")


def test_disable_checkout_sync_purges_the_projects_queued_journal_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Opt-out retains history; explicit undelivered purge preserves delivered rows."""
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    project_uuid = str(uuid4())
    _write_repo_config(repo_root, project_uuid=project_uuid)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    monkeypatch.chdir(repo_root)

    store = ProjectSyncStore(project_uuid)
    _project_only(store)
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        _seed_journal_row(journal, "mine-queued", project_uuid, 1)
        _seed_journal_row(journal, "mine-delivered", project_uuid, 2)
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        ledger.record_success("mine-delivered", "tgt")
        body_queue = OfflineBodyUploadQueue(unit, store.layout_generation())
        body_queue.enqueue(
            NamespaceRef(
                project_uuid=project_uuid,
                mission_slug="001-test",
                target_branch="main",
                mission_type="software-dev",
                manifest_version="1",
            ),
            artifact_path="spec.md",
            content_hash="abc123",
            content_body="# Spec\n",
            size_bytes=7,
        )

    result = disable_checkout_sync(repo_root)

    assert result.removed_events == 0
    assert result.removed_body_uploads == 0
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        event_purge = purge_project_events(
            project_uuid,
            journal=journal,
            ledger=ledger,
            dry_run=False,
            undelivered_only=True,
        )
        body_purge = purge_project_body_uploads(
            project_uuid,
            body_queue=OfflineBodyUploadQueue(unit, store.layout_generation()),
            dry_run=False,
        )
        remaining = {event.event_id for event in journal.read_all()}

    assert event_purge.purged_event_ids == ("mine-queued",)
    assert body_purge.removed == 1
    assert remaining == {"mine-delivered"}


def test_disable_checkout_sync_reports_zero_without_lying_when_no_store_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No payload store means zero removed; the refusal itself is durably created."""
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    project_uuid = _write_repo_config(repo_root, project_uuid=str(uuid4()))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    monkeypatch.chdir(repo_root)

    store = ProjectSyncStore(project_uuid)
    assert not store.database_path.exists()

    result = disable_checkout_sync(repo_root)

    assert result.removed_events == 0
    assert result.removed_body_uploads == 0
    assert store.database_path.exists(), "the explicit refusal is itself durable state"
    with store.unit_of_work() as unit:
        assert EventJournal(unit, store.layout_generation()).count() == 0
        assert SqliteDeliveryLedger(unit, store.layout_generation()).rows() == []


def test_the_retired_legacy_queue_purge_is_gone(tmp_path: Path) -> None:
    """C-004: ``OfflineQueue.remove_project_events`` is deleted, not just unused.

    It targeted the store WP02 retired for delivery and full-decoded every row to
    do it. Leaving the method behind would leave a second, disagreeing definition
    of "purge this project's events" for a future caller to pick up.
    """
    assert not hasattr(OfflineQueue, "remove_project_events")


# --- FR-022: project-config faults must fail closed around a store grant --------


def _make_checkout_with_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, case: str) -> Path:
    """A checkout with one explicit UUID-owned grant in an isolated store."""
    home = tmp_path / f"{case}-home"
    repo_root = tmp_path / f"{case}-repo"
    home.mkdir()
    repo_root.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    (repo_root / ".kittify").mkdir()
    record_project_opt_in("11111111-1111-1111-1111-111111111111", actor="routing-test")
    return repo_root


def _write_project_config(repo_root: Path, body: str) -> Path:
    path = repo_root / ".kittify" / "config.yaml"
    path.write_text(body, encoding="utf-8")
    return path


_VALID_REFUSAL = "\n".join(
    [
        "project:",
        "  uuid: 11111111-1111-1111-1111-111111111111",
        "  slug: spec-kitty-local",
        "  repo_slug: acme/spec-kitty",
        "sync:",
        "  enabled: false",
        "",
    ]
)


def test_readable_project_refusal_still_outranks_a_checkout_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The explicit project-store refusal supersedes its earlier project grant."""
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="readable")
    _write_project_config(repo_root, _VALID_REFUSAL)
    record_project_opt_out("11111111-1111-1111-1111-111111111111", actor="routing-test")

    assert is_sync_enabled_for_checkout(repo_root) is False


def test_unparseable_project_config_denies_instead_of_deferring_to_the_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-022: a syntax error must deny even when the store contains a grant."""
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="unparseable")
    _write_project_config(repo_root, "sync:\n  enabled: false\n  broken: [unclosed\n")

    assert is_sync_enabled_for_checkout(repo_root) is False


def test_top_level_non_mapping_project_config_denies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A file that exists and cannot be understood is not a file that says nothing."""
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="nonmapping")
    _write_project_config(repo_root, "- just\n- a\n- list\n")

    assert is_sync_enabled_for_checkout(repo_root) is False


def test_unreadable_project_config_denies_instead_of_deferring_to_the_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """chmod 000: unreadable is undetermined, and undetermined is not consent."""
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="unreadable")
    path = _write_project_config(repo_root, _VALID_REFUSAL)
    path.chmod(0o000)
    try:
        assert is_sync_enabled_for_checkout(repo_root) is False
    finally:
        path.chmod(0o644)


def test_an_absent_project_config_is_absence_not_a_fault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An absent identity cannot bind even an existing store grant to a checkout."""
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="absent")

    assert is_sync_enabled_for_checkout(repo_root) is False


def test_the_fault_is_reported_not_silently_folded_into_absence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Denying is half the fix; an operator also has to be able to see why.

    A denial indistinguishable from "no record" sends them looking for a missing
    opt-in instead of a broken file.
    """
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="reported")
    _write_project_config(repo_root, "sync:\n  enabled: false\n  broken: [unclosed\n")

    routing = resolve_checkout_sync_routing_readonly(repo_root)

    assert routing is not None
    assert routing.effective_sync_enabled is False
    assert routing.project_local_fault is not None
    assert "config.yaml" in routing.project_local_fault.detail


def test_opt_in_on_an_unreadable_project_config_refuses_to_write_a_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """You cannot grant consent for a project whose own config cannot be read.

    The identity guard (T016) must refuse before writing a UUID-owned decision when
    the checkout cannot supply a trustworthy project UUID.
    """
    from specify_cli.sync.routing import (
        ConsentIdentityUnresolvedError,
        enable_checkout_sync,
    )

    home = tmp_path / "optin-home"
    repo_root = tmp_path / "optin-repo"
    home.mkdir()
    repo_root.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    (repo_root / ".kittify").mkdir()
    _write_project_config(repo_root, "sync:\n  enabled: false\n  broken: [unclosed\n")

    with pytest.raises(ConsentIdentityUnresolvedError):
        enable_checkout_sync(repo_root)

    assert read_local_sync_enabled(repo_root) is None, "no checkout-level grant may be written on the way out"
    assert is_sync_enabled_for_checkout(repo_root) is False


# --- FR-027: the same fall-through at *field* level -----------------------------
#
# FR-022 fenced the file being unreadable. The field being unusable walked straight
# past it, because ``project_local_consent_fault`` did not call a bad *value* a fault.
# These cases retain an explicit store grant behind the malformed file, proving the
# diagnostic fence remains fail-closed without treating the file as grant authority.


def test_a_misspelled_refusal_does_not_defer_to_a_checkout_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-027: ``enabled: no`` is a *string* under ruamel's YAML 1.2 loader.

    A malformed diagnostic must fail closed even though the UUID-owned store holds
    a grant; it must never be interpreted as a second granting authority.
    """
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="misspelled")
    _write_project_config(repo_root, _VALID_REFUSAL.replace("enabled: false", "enabled: no"))

    assert is_sync_enabled_for_checkout(repo_root) is False


def test_an_unusable_project_uuid_denies_rather_than_capturing_without_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-024's measured residual, closed by the same notion.

    FR-024 stopped ``uuid: "<<<<<<< HEAD"`` *crashing* the policy read. What it left
    behind was ``granted=True`` with ``project_uuid=None``: not a cross-project grant,
    but events captured with **no identity**, which is exactly the population
    FR-011/FR-017 then have to clean up. A merge-conflict marker in a tracked,
    hand-edited file is the realistic route in.
    """
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="baduuid")
    _write_project_config(repo_root, "project:\n  uuid: <<<<<<< HEAD\n  slug: spec-kitty-local\n")

    routing = resolve_checkout_sync_routing_readonly(repo_root)

    assert is_sync_enabled_for_checkout(repo_root) is False
    assert routing is not None
    assert routing.project_uuid is None
    assert routing.project_local_fault is not None, (
        "denying is half of it; an operator told only 'sync is disabled' goes looking for a missing opt-in instead of the conflict marker that caused it"
    )
    assert "uuid" in routing.project_local_fault.detail


def test_a_healthy_config_with_no_consent_key_still_honours_the_checkout_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A healthy identity reaches the explicit store grant without a legacy key."""
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="healthy")
    _write_project_config(
        repo_root,
        "project:\n  uuid: 11111111-1111-1111-1111-111111111111\n  slug: spec-kitty-local\n",
    )

    assert is_sync_enabled_for_checkout(repo_root) is True


# --- #3112: the fail-closed invariant is local to _build_checkout_sync_routing --


def test_build_checkout_sync_routing_denies_directly_on_a_faulted_project_local_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The invariant must not depend on the caller running the fence first.

    Every production caller (``resolve_checkout_sync_routing`` and its read-only
    twin) already runs ``_routing_for_unreadable_project_config`` before reaching
    ``_build_checkout_sync_routing``, so the fence-based tests above cannot observe
    what happens when a caller skips it. Calling ``_build_checkout_sync_routing``
    directly — as a future caller might — is the only way to prove the fail-closed
    answer does not depend on that ordering convention (#3112).
    """
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="direct-call-fault")
    path = _write_project_config(repo_root, _VALID_REFUSAL)
    path.chmod(0o000)
    try:
        routing = _build_checkout_sync_routing(repo_root, ProjectIdentity())
    finally:
        path.chmod(0o644)

    assert routing.effective_sync_enabled is False, (
        "an unreadable project-local consent file must fail closed even when _build_checkout_sync_routing is called directly, skipping the fence"
    )
    assert routing.project_local_fault is not None
