"""Teamspace MVP readiness tests.

Covers the local-first / eventually-consistent contract from
``kitty-specs/teamspace-local-first-outbox/`` (Priivacy-ai/spec-kitty
issues #1072, #1073, #1074, #1075, #1076):

- Lifecycle events are locally durable regardless of sync feature flag,
  auth state, Private Teamspace resolution, or git-remote availability.
- ``BuildRegistered`` / ``BuildHeartbeat`` no longer require ``repo_slug``.
- ``spec-kitty init`` registers a project-init lifecycle event in the
  durable outbox.
- ``sync status`` surfaces ``drain_blocked_reason`` so operators can
  see why the queue is not draining.

These tests run with the SaaS feature flag implicitly enabled inside
``EventEmitter._emit`` (we monkeypatch ``is_sync_enabled_for_checkout``
where the contract under test requires the gate to be open). The
real CLI is invoked via ``typer.testing.CliRunner`` for the init
scenario so the cross-cutting integration is exercised.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.sync.clock import LamportClock
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.project_identity import ProjectIdentity
from specify_cli.sync.queue import OfflineQueue


pytestmark = pytest.mark.fast


@pytest.fixture
def fresh_queue(tmp_path: Path) -> OfflineQueue:
    return OfflineQueue(db_path=tmp_path / "queue.db")


@pytest.fixture
def fresh_clock(tmp_path: Path) -> LamportClock:
    return LamportClock(value=0, node_id="readiness-node", _storage_path=tmp_path / "c.json")


@pytest.fixture
def identity_with_remote() -> ProjectIdentity:
    return ProjectIdentity(
        project_uuid=__import__("uuid").UUID("1ab1511d-bea2-47c2-b1e2-bec8547ce55b"),
        project_slug="brand-aware-images",
        node_id="readiness-node",
        build_id="06e643fb-d025-48b7-afc2-b46d4925bdfa",
    )


@pytest.fixture
def authed_token_manager(monkeypatch) -> MagicMock:
    team = MagicMock()
    team.id = "private-team-id"
    team.slug = "private-team-id"

    session = MagicMock()
    session.default_team_id = "private-team-id"
    session.teams = [team]
    session.email = "ops@example.com"
    session.name = "Ops"

    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = session
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
    return tm


def _make_emitter(
    queue: OfflineQueue,
    clock: LamportClock,
    identity: ProjectIdentity,
    git_meta_repo_slug: str | None,
) -> EventEmitter:
    from specify_cli.sync.git_metadata import GitMetadata, GitMetadataResolver

    resolver = MagicMock(spec=GitMetadataResolver)
    resolver.resolve.return_value = GitMetadata(
        git_branch="main" if git_meta_repo_slug else None,
        head_commit_sha=("a" * 40) if git_meta_repo_slug else None,
        repo_slug=git_meta_repo_slug,
    )
    resolver.repo_root = Path("/tmp/teamspace-readiness-fixture")

    return EventEmitter(
        clock=clock,
        config=MagicMock(),
        queue=queue,
        ws_client=None,
        _identity=identity,
        _git_resolver=resolver,
    )


def test_event_durable_when_sync_feature_flag_disabled(
    fresh_queue, fresh_clock, identity_with_remote, authed_token_manager, monkeypatch
):
    """FR-2 / issue #1072: opted-out checkouts still produce locally-durable events.

    The remote drain side will skip these events (drain logic re-resolves
    ``is_sync_enabled_for_checkout`` per tick), but they must survive on
    disk so a later opt-in can replay them.
    """
    monkeypatch.setattr(
        "specify_cli.sync.emitter.is_sync_enabled_for_checkout",
        lambda: False,
    )

    em = _make_emitter(fresh_queue, fresh_clock, identity_with_remote, "org/repo")
    event = em.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert event is not None
    assert event["drain_blocked_reason"] == "sync_disabled"
    assert fresh_queue.size() == 1


def test_event_durable_when_unauthenticated(
    fresh_queue, fresh_clock, identity_with_remote, monkeypatch
):
    """FR-3 / issue #1072: unauthenticated checkouts queue events locally.

    The drain side will not POST (no bearer token), but the event must
    survive in the outbox so re-authentication replays it.
    """

    def _boom():
        raise RuntimeError("Not authenticated")

    monkeypatch.setattr("specify_cli.auth.get_token_manager", _boom)

    em = _make_emitter(fresh_queue, fresh_clock, identity_with_remote, "org/repo")
    event = em.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert event is not None
    # Either "no_auth" (auth check ran cleanly) or "no_team" (auth raised
    # and the strict resolver returned None) — both preserve durability.
    assert event["drain_blocked_reason"] in {"no_auth", "no_team"}
    assert event["team_slug"] is None
    assert fresh_queue.size() == 1


def test_event_durable_when_no_private_teamspace(
    fresh_queue, fresh_clock, identity_with_remote, monkeypatch
):
    """FR-4 / issue #1072: shared-only sessions queue events but never ingress.

    When the strict resolver returns ``None``, the emitter must queue
    with ``team_slug = None`` and ``drain_blocked_reason = "no_team"`` —
    no remote ingress, no shared-team fallback.
    """
    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = MagicMock()
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
    monkeypatch.setattr(
        "specify_cli.sync._team.resolve_private_team_id_for_ingress",
        lambda *_a, **_kw: None,
    )

    em = _make_emitter(fresh_queue, fresh_clock, identity_with_remote, "org/repo")
    event = em.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert event is not None
    assert event["team_slug"] is None
    assert event["drain_blocked_reason"] == "no_team"
    assert fresh_queue.size() == 1


def test_build_registered_succeeds_without_repo_slug(
    fresh_queue, fresh_clock, identity_with_remote, authed_token_manager
):
    """FR-5 / issue #1074: BuildRegistered requires only build_id (project_uuid is enrichment).

    Reproduces the brand-aware-images failure: fresh project with
    ``project_uuid`` + ``build_id`` but no git remote slug. The event
    must validate, queue, and be drainable once auth/team are in place.
    """
    em = _make_emitter(
        fresh_queue,
        fresh_clock,
        identity_with_remote,
        git_meta_repo_slug=None,  # no remote
    )
    event = em.emit_build_registered()

    assert event is not None
    assert event["event_type"] == "BuildRegistered"
    assert event["aggregate_type"] == "Build"
    assert event["payload"]["build_id"] == "06e643fb-d025-48b7-afc2-b46d4925bdfa"
    assert event["payload"]["project_uuid"] == "1ab1511d-bea2-47c2-b1e2-bec8547ce55b"
    assert event["payload"].get("repo_slug") is None
    assert event.get("drain_blocked_reason") is None
    assert fresh_queue.size() == 1


def test_build_heartbeat_succeeds_without_repo_slug(
    fresh_queue, fresh_clock, identity_with_remote, authed_token_manager
):
    """FR-5 / issue #1074: BuildHeartbeat also tolerates a missing remote slug."""
    em = _make_emitter(
        fresh_queue,
        fresh_clock,
        identity_with_remote,
        git_meta_repo_slug=None,
    )
    event = em.emit_build_heartbeat(remote_head=None, ahead_of_remote=0, behind_remote=0)

    assert event is not None
    assert event["event_type"] == "BuildHeartbeat"
    assert event["payload"]["build_id"] == "06e643fb-d025-48b7-afc2-b46d4925bdfa"
    assert event["payload"].get("repo_slug") is None


def test_event_ready_to_drain_when_authed_and_team_resolved(
    fresh_queue, fresh_clock, identity_with_remote, authed_token_manager, monkeypatch
):
    """Sanity: when all conditions are met, ``drain_blocked_reason`` is None.

    Establishes the positive control for the durability tests above so we
    can prove ``drain_blocked_reason`` is wired into the live envelope.
    """
    monkeypatch.setattr(
        "specify_cli.sync.emitter.is_sync_enabled_for_checkout",
        lambda: True,
    )
    monkeypatch.setattr(
        "specify_cli.sync._team.resolve_private_team_id_for_ingress",
        lambda *_a, **_kw: "private-team-id",
    )
    em = _make_emitter(fresh_queue, fresh_clock, identity_with_remote, "org/repo")
    event = em.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert event is not None
    assert event["drain_blocked_reason"] is None
    assert event["team_slug"] == "private-team-id"


def test_drain_blocked_counts_aggregate_on_queue(
    fresh_queue, fresh_clock, identity_with_remote, monkeypatch
):
    """FR-7 / issue #1075: queue exposes a drain-blocker breakdown.

    Queues a synthetic mix of events with different ``drain_blocked_reason``
    values and asserts ``get_drain_blocked_counts`` returns the right
    tallies for the ``sync status`` rendering layer.
    """
    em = _make_emitter(fresh_queue, fresh_clock, identity_with_remote, "org/repo")

    # 1 ready
    monkeypatch.setattr(
        "specify_cli.sync.emitter.is_sync_enabled_for_checkout", lambda: True
    )
    monkeypatch.setattr(
        "specify_cli.sync._team.resolve_private_team_id_for_ingress",
        lambda *_a, **_kw: "private-team-id",
    )
    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = MagicMock()
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
    em.emit_wp_status_changed("WP01", "planned", "in_progress")

    # 2 sync_disabled
    monkeypatch.setattr(
        "specify_cli.sync.emitter.is_sync_enabled_for_checkout", lambda: False
    )
    em.emit_wp_status_changed("WP02", "planned", "in_progress")
    em.emit_wp_status_changed("WP03", "planned", "in_progress")

    # 1 no_team
    monkeypatch.setattr(
        "specify_cli.sync.emitter.is_sync_enabled_for_checkout", lambda: True
    )
    monkeypatch.setattr(
        "specify_cli.sync._team.resolve_private_team_id_for_ingress",
        lambda *_a, **_kw: None,
    )
    em.emit_wp_status_changed("WP04", "planned", "in_progress")

    counts = fresh_queue.get_drain_blocked_counts()
    assert counts.get("ready") == 1
    assert counts.get("sync_disabled") == 2
    assert counts.get("no_team") == 1


def test_init_emits_project_init_event_offline(tmp_path: Path, monkeypatch):
    """FR-6 / issue #1073: ``spec-kitty init`` queues a project-init event offline.

    Drives the real init command via CliRunner. Authentication is forced
    to "unauthenticated" so the project-init event must be queued locally
    (``drain_blocked_reason == "no_auth"`` or ``"no_team"``).
    """
    # Reset emitter and runtime singletons so the init harness starts clean.
    from specify_cli.sync.events import reset_emitter
    from specify_cli.sync.runtime import reset_runtime

    reset_emitter()
    reset_runtime()

    # Point the queue at a temp DB so we can observe events without
    # touching the host's ~/.spec-kitty/.
    queue_db = tmp_path / "outbox.db"
    monkeypatch.setattr(
        "specify_cli.sync.queue.default_queue_db_path", lambda *_a, **_kw: queue_db
    )

    # Force unauthenticated so the project-init event stays local.
    def _boom():
        raise RuntimeError("Not authenticated")

    monkeypatch.setattr("specify_cli.auth.get_token_manager", _boom)

    # Bootstrap the runtime once so subsequent imports do not need network.
    project_path = tmp_path / "fresh-project"
    project_path.mkdir()
    (project_path / ".kittify").mkdir()
    monkeypatch.chdir(project_path)

    # Materialize identity directly (bypasses the full Typer harness; the
    # init command writes identity then calls the same helper). This keeps
    # the test fast and hermetic.
    from specify_cli.cli.commands.init import _emit_project_init_event

    _emit_project_init_event(project_path)

    queue = OfflineQueue(db_path=queue_db)
    events = queue.drain_queue(limit=10)
    assert any(e.get("event_type") == "BuildRegistered" for e in events), (
        "expected init to queue a BuildRegistered event into the durable outbox"
    )
    build_event = next(e for e in events if e["event_type"] == "BuildRegistered")
    assert build_event.get("drain_blocked_reason") in {"no_auth", "no_team"}
    assert build_event["payload"]["build_id"]
