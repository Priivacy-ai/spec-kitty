"""Tests for checkout-level sync routing and opt-out behavior."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.namespace import NamespaceRef
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.routing import (
    disable_checkout_sync,
    is_sync_enabled_for_checkout,
    read_local_sync_enabled,
    resolve_checkout_sync_routing,
    resolve_checkout_sync_routing_readonly,
    write_local_sync_enabled,
)

pytestmark = pytest.mark.fast


def _write_repo_config(repo_root: Path, *, project_uuid: str | None = None, repo_slug: str = "acme/spec-kitty") -> None:
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
    write_local_sync_enabled(repo_root, True)

    routing = resolve_checkout_sync_routing()

    assert routing is not None
    assert routing.local_sync_enabled is True
    assert routing.repo_default_sync_enabled is False
    assert routing.effective_sync_enabled is True


def test_local_override_is_persisted_outside_repo_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    _write_repo_config(repo_root)
    monkeypatch.setenv("HOME", str(home))

    original_repo_config = (repo_root / ".kittify" / "config.yaml").read_text(encoding="utf-8")

    write_local_sync_enabled(repo_root, False)

    assert (repo_root / ".kittify" / "config.yaml").read_text(encoding="utf-8") == original_repo_config
    config_toml = (home / ".spec-kitty" / "config.toml").read_text(encoding="utf-8")
    assert str(repo_root.resolve()) in config_toml
    assert "checkout_overrides" in config_toml
    assert "enabled = false" in config_toml


def test_disable_checkout_sync_purges_only_matching_project_body_uploads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    project_uuid = str(uuid4())
    _write_repo_config(repo_root, project_uuid=project_uuid)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo_root)

    queue = OfflineQueue()
    queue.queue_event(
        {
            "event_id": "evt-1",
            "event_type": "BuildRegistered",
            "project_uuid": project_uuid,
            "payload": {"project_uuid": project_uuid},
        }
    )
    queue.queue_event(
        {
            "event_id": "evt-2",
            "event_type": "BuildRegistered",
            "project_uuid": str(uuid4()),
            "payload": {"project_uuid": str(uuid4())},
        }
    )

    body_queue = OfflineBodyUploadQueue(db_path=queue.db_path)
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
    body_queue.enqueue(
        NamespaceRef(
            project_uuid=str(uuid4()),
            mission_slug="001-test",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1",
        ),
        artifact_path="plan.md",
        content_hash="def456",
        content_body="# Plan\n",
        size_bytes=7,
    )

    result = disable_checkout_sync(repo_root)

    assert result.routing.effective_sync_enabled is False
    # C-004 (#3030 WP08): opt-out no longer purges the LEGACY queue. That store has
    # had no drain since WP02, so purging it was retention housekeeping dressed as a
    # delivery control, and it full-decoded every row to do it. Both projects' legacy
    # rows therefore survive here; they converge into the journal via
    # `spec-kitty sync migrate` and are purgeable there.
    #
    # ``removed_events`` now counts journal rows. This fixture seeds no journal, so 0
    # is the honest answer for it; the non-zero journal path is pinned by
    # ``test_disable_checkout_sync_purges_the_projects_queued_journal_rows`` — without
    # that companion this assertion would be the "always 0" the WP warns about.
    assert result.removed_events == 0
    assert queue.size() == 2, "the retired legacy-queue purge no longer runs"
    # Body uploads are a separate, live store and are still purged per project.
    assert result.removed_body_uploads == 1
    assert body_queue.size() == 1
    config_toml = (home / ".spec-kitty" / "config.toml").read_text(encoding="utf-8")
    assert "acme/spec-kitty" in config_toml
    assert "enabled = false" in config_toml


# --- WP01 / FR-003: the sync-enabled gate must fail CLOSED -------------------
# Regression cover for spec-kitty#3030. Before this, `is_sync_enabled_for_checkout`
# returned True whenever routing could not be resolved, so an inability to
# determine consent was read as consent — the inverted default in front of a
# confidentiality boundary.


def test_sync_enabled_denies_when_routing_is_unresolvable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unresolvable routing must DENY, not permit (FR-003, SC-003)."""
    from specify_cli.sync import routing as routing_module

    monkeypatch.setattr(
        routing_module, "resolve_checkout_sync_routing_readonly", lambda start=None: None
    )

    assert routing_module.is_sync_enabled_for_checkout() is False


def test_absence_of_consent_record_denies_capture_and_delivery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def _seed_journal_row(
    journal: Any, event_id: str, project_uuid: str | None, index: int
) -> None:
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


def test_opt_out_purge_targets_the_same_stores_the_drain_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The purge must open the journal/ledger the dispatcher drains, not a twin.

    If opt-out resolved a different producer scope than live capture, it would
    silently purge an empty journal and report 0 removed — the "always 0" failure
    C-004 warns about, invisible in any test that only checks the count it
    produced itself. The CLI's ``sync now`` runtime is the authority for those
    paths, so this compares against it directly.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    from specify_cli.cli.commands import sync as sync_cli
    from specify_cli.delivery.retention import resolve_live_store_paths
    from specify_cli.event_journal.journal import resolve_journal_path

    journal_path, ledger_path = resolve_live_store_paths()
    cli_scope = sync_cli._current_event_sync_scope()

    assert journal_path == resolve_journal_path(
        user_id=cli_scope.user_id, team_slug=cli_scope.team_slug
    ), "opt-out must purge the journal the drain reads, not a differently-scoped twin"
    assert ledger_path == sync_cli._ledger_db_path(), (
        "the ledger path is duplicated from the CLI's private constants; this "
        "assertion is what turns a drift into a red instead of a silent no-op purge"
    )


def test_disable_checkout_sync_purges_the_projects_queued_journal_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-004: the retired legacy-queue purge is replaced by a journal purge.

    ``removed_events`` is user-visible ("Removed N queued event(s)"), so it now
    counts journal rows — the store that actually ships — rather than rows in the
    inert legacy queue. Scope is *queued* (no terminal-success delivery): C-002
    reserves wholesale deletion for the operator's explicit ``sync purge``, and a
    routing toggle must not destroy the record of what already left the machine.
    """
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.delivery.retention import resolve_live_store_paths
    from specify_cli.event_journal.journal import EventJournal

    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    project_uuid = str(uuid4())
    other_uuid = str(uuid4())
    _write_repo_config(repo_root, project_uuid=project_uuid)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    monkeypatch.chdir(repo_root)

    journal_path, ledger_path = resolve_live_store_paths()
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    journal = EventJournal(journal_path)
    _seed_journal_row(journal, "mine-queued", project_uuid, 1)
    _seed_journal_row(journal, "mine-delivered", project_uuid, 2)
    _seed_journal_row(journal, "theirs", other_uuid, 3)
    ledger = SqliteDeliveryLedger(str(ledger_path))
    ledger.record_success("mine-delivered", "tgt")
    ledger.close()

    body_queue = OfflineBodyUploadQueue(db_path=OfflineQueue().db_path)
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

    assert result.removed_events == 1, (
        "one queued row for this project; the delivered one is not 'queued'"
    )
    assert result.removed_body_uploads == 1, "body uploads are a live, separate store"

    remaining = {event.event_id for event in EventJournal(journal_path).read_all()}
    assert remaining == {"mine-delivered", "theirs"}


def test_disable_checkout_sync_reports_zero_without_lying_when_no_store_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No journal on disk yet: nothing to purge, and opt-out must not create one.

    A routing toggle that materialised an empty ledger/journal as a side effect
    would be a surprising write, and 0 here is the true answer rather than the
    "always 0" the WP warns about — the case above proves the non-zero path.
    """
    from specify_cli.delivery.retention import resolve_live_store_paths

    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    _write_repo_config(repo_root, project_uuid=str(uuid4()))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    monkeypatch.chdir(repo_root)

    result = disable_checkout_sync(repo_root)

    assert result.removed_events == 0
    journal_path, ledger_path = resolve_live_store_paths()
    assert not journal_path.exists()
    assert not ledger_path.exists()


def test_the_retired_legacy_queue_purge_is_gone(tmp_path: Path) -> None:
    """C-004: ``OfflineQueue.remove_project_events`` is deleted, not just unused.

    It targeted the store WP02 retired for delivery and full-decoded every row to
    do it. Leaving the method behind would leave a second, disagreeing definition
    of "purge this project's events" for a future caller to pick up.
    """
    assert not hasattr(OfflineQueue, "remove_project_events")


# --- FR-022: an unreadable project-local file must not defer to a stale grant --


def _make_checkout_with_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, case: str
) -> Path:
    """A checkout carrying a machine-level GRANT, in a home of its very own.

    Per-case ``SPEC_KITTY_HOME`` is load-bearing, not hygiene. ``consent.py``'s
    ``_answer_project_local`` reconciles the machine index as a side effect, so a
    readable-refusal case run earlier in a shared home rewrites the index and the
    next case's leak presents as a denial. The FR-021 implementer's first probe read
    "denied" for exactly that reason.
    """
    home = tmp_path / f"{case}-home"
    repo_root = tmp_path / f"{case}-repo"
    home.mkdir()
    repo_root.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    (repo_root / ".kittify").mkdir()
    # The record that survives a clone or a rename — i.e. the one that goes stale.
    write_local_sync_enabled(repo_root, True)
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


def test_readable_project_refusal_still_outranks_a_checkout_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control case: FR-013's rule works when the file parses."""
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="readable")
    _write_project_config(repo_root, _VALID_REFUSAL)

    assert is_sync_enabled_for_checkout(repo_root) is False


def test_unparseable_project_config_denies_instead_of_deferring_to_the_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-022: a syntax error must not void a committed refusal.

    The live path is mundane: an operator commits ``sync.enabled: false``, a later
    edit breaks the YAML, and egress resumes silently. What wins is the checkout
    override — the record that survives a clone or a rename — so what actually
    stands in for the refusal is a *stale grant*.
    """
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="unparseable")
    _write_project_config(repo_root, "sync:\n  enabled: false\n  broken: [unclosed\n")

    assert is_sync_enabled_for_checkout(repo_root) is False


def test_top_level_non_mapping_project_config_denies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file that exists and cannot be understood is not a file that says nothing."""
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="nonmapping")
    _write_project_config(repo_root, "- just\n- a\n- list\n")

    assert is_sync_enabled_for_checkout(repo_root) is False


def test_unreadable_project_config_denies_instead_of_deferring_to_the_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """chmod 000: unreadable is undetermined, and undetermined is not consent."""
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="unreadable")
    path = _write_project_config(repo_root, _VALID_REFUSAL)
    path.chmod(0o000)
    try:
        assert is_sync_enabled_for_checkout(repo_root) is False
    finally:
        path.chmod(0o644)


def test_an_absent_project_config_is_absence_not_a_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The regression guard on the fix: absence must keep falling through.

    Most checkouts on a machine have no project config at all. Treating absence as
    a fault would deny every delivery — so the fix must discriminate "exists and
    unreadable" from "not there", exactly as ``ConfigReadFault`` does.
    """
    repo_root = _make_checkout_with_grant(tmp_path, monkeypatch, case="absent")

    assert is_sync_enabled_for_checkout(repo_root) is True


def test_the_fault_is_reported_not_silently_folded_into_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_opt_in_on_an_unreadable_project_config_refuses_to_write_a_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """You cannot grant consent for a project whose own config cannot be read.

    Without this, the remedy for the FR-022 denial would be to run ``sync opt-in``,
    which would write exactly the machine-level grant that then outlives the broken
    file — manufacturing the stale grant this fix exists to stop honouring. The
    identity guard (T016) already refuses; pinned here because it now also stands in
    front of the fault path, and because it must refuse *before* writing anything.
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

    assert read_local_sync_enabled(repo_root) is None, (
        "no checkout-level grant may be written on the way out"
    )
    assert is_sync_enabled_for_checkout(repo_root) is False
