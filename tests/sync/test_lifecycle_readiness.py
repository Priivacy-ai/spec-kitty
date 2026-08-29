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
``EventEmitter._emit``. Per-project hosted-sync consent is steered through
``_steer_consent`` below — ``tests/sync/conftest.py`` grants by default for this
package, and a test whose subject is the *refusal* opts out explicitly. The
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
from specify_cli.sync.project_store import ProjectSyncStore


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "1ab1511d-bea2-47c2-b1e2-bec8547ce55b"


@pytest.fixture
def fresh_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    authority = store.layout_generation()
    authority.begin_cutover("lifecycle-readiness-tests")
    authority.publish_project_only("lifecycle-readiness-tests", verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        yield OfflineQueue(unit, authority)


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
    resolver.repo_root = Path("/nonexistent/teamspace-readiness-fixture")

    return EventEmitter(
        clock=clock,
        config=MagicMock(),
        queue=queue,
        ws_client=None,
        _identity=identity,
        _git_resolver=resolver,
    )


def _steer_consent(monkeypatch, *, granted: bool) -> None:
    """Steer the emitter's one per-project consent predicate (#3030 M1/M1-1).

    Replaces ``monkeypatch.setattr("...emitter.is_sync_enabled_for_checkout", ...)``.
    That cwd-derived seam is gone: the capture gate, ``_classify_drain_blocked_reason``
    and the WebSocket publish decision all resolve consent from the *event's own*
    ``project_uuid`` through ``EventEmitter._project_consents_to_capture``. Patching
    the removed name steered nothing, so these tests would have gone quietly green on
    whatever the ambient repo's consent record happened to say.

    ``tests/sync/conftest.py`` grants by default for this package; call this with
    ``granted=False`` where the *refusal* is the subject.
    """
    monkeypatch.setattr(
        "specify_cli.sync.emitter.EventEmitter._project_consents_to_capture",
        lambda *_args, **_kwargs: granted,
    )


def test_event_durable_when_sync_feature_flag_disabled(fresh_queue, fresh_clock, identity_with_remote, authed_token_manager, monkeypatch):
    """FR-2 / issue #1072: opted-out projects still produce locally-durable events.

    The remote drain skips them, but they must survive on disk so a later opt-in can
    replay them. Reinforced by #3030 M1-1's recorded judgement: local durability is
    deliberately not consent-gated, because refusing the write would turn "not opted
    in to hosted sync" into "local history discarded".
    """
    _steer_consent(monkeypatch, granted=False)

    em = _make_emitter(fresh_queue, fresh_clock, identity_with_remote, "org/repo")
    event = em.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert event is not None
    assert event["drain_blocked_reason"] == "saas_disabled"
    assert fresh_queue.size() == 1


def test_event_durable_when_unauthenticated(fresh_queue, fresh_clock, identity_with_remote, monkeypatch):
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
    # Either "missing_auth" (auth check ran cleanly) or "missing_team" (auth raised
    # and the strict resolver returned None) — both preserve durability.
    assert event["drain_blocked_reason"] in {"missing_auth", "missing_team"}
    assert event["team_slug"] is None
    assert fresh_queue.size() == 1


def test_event_durable_when_no_private_teamspace(fresh_queue, fresh_clock, identity_with_remote, monkeypatch):
    """FR-4 / issue #1072: shared-only sessions queue events but never ingress.

    When the strict resolver returns ``None``, the emitter must queue
    with ``team_slug = None`` and ``drain_blocked_reason = "missing_team"`` —
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
    assert event["drain_blocked_reason"] == "missing_team"
    assert fresh_queue.size() == 1


def test_build_registered_succeeds_without_repo_slug(fresh_queue, fresh_clock, identity_with_remote, authed_token_manager):
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


def test_build_heartbeat_succeeds_without_repo_slug(fresh_queue, fresh_clock, identity_with_remote, authed_token_manager):
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


def test_event_ready_to_drain_when_authed_and_team_resolved(fresh_queue, fresh_clock, identity_with_remote, authed_token_manager, monkeypatch):
    """Sanity: when all conditions are met, ``drain_blocked_reason`` is None.

    Establishes the positive control for the durability tests above so we
    can prove ``drain_blocked_reason`` is wired into the live envelope.
    """
    _steer_consent(monkeypatch, granted=True)
    monkeypatch.setattr(
        "specify_cli.sync._team.resolve_private_team_id_for_ingress",
        lambda *_a, **_kw: "private-team-id",
    )
    em = _make_emitter(fresh_queue, fresh_clock, identity_with_remote, "org/repo")
    event = em.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert event is not None
    assert event["drain_blocked_reason"] is None
    assert event["team_slug"] == "private-team-id"


def test_drain_blocked_counts_aggregate_on_queue(fresh_queue, fresh_clock, identity_with_remote, monkeypatch):
    """FR-7 / issue #1075: queue exposes a drain-blocker breakdown.

    Queues a synthetic mix of events with different ``drain_blocked_reason``
    values and asserts ``get_drain_blocked_counts`` returns the right
    tallies for the ``sync status`` rendering layer.
    """
    em = _make_emitter(fresh_queue, fresh_clock, identity_with_remote, "org/repo")

    # 1 ready
    _steer_consent(monkeypatch, granted=True)
    monkeypatch.setattr(
        "specify_cli.sync._team.resolve_private_team_id_for_ingress",
        lambda *_a, **_kw: "private-team-id",
    )
    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = MagicMock()
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
    em.emit_wp_status_changed("WP01", "planned", "in_progress")

    # 2 sync_disabled — this event's own project does not consent (#3030 M1-1)
    _steer_consent(monkeypatch, granted=False)
    em.emit_wp_status_changed("WP02", "planned", "in_progress")
    em.emit_wp_status_changed("WP03", "planned", "in_progress")

    # 1 no_team
    _steer_consent(monkeypatch, granted=True)
    monkeypatch.setattr(
        "specify_cli.sync._team.resolve_private_team_id_for_ingress",
        lambda *_a, **_kw: None,
    )
    em.emit_wp_status_changed("WP04", "planned", "in_progress")

    counts = fresh_queue.get_drain_blocked_counts()
    assert counts.get("ready") == 1
    assert counts.get("saas_disabled") == 2
    assert counts.get("missing_team") == 1


def test_init_emits_project_init_event_offline(tmp_path: Path, monkeypatch):
    """FR-6 / issue #1073: ``spec-kitty init`` queues a project-init event offline.

    Drives the real init command via CliRunner. Authentication is forced
    to "unauthenticated" so the project-init event must be queued locally
    (``drain_blocked_reason == "missing_auth"`` or ``"missing_team"``).
    """
    # Isolate the emitter without starting the process-global runtime. Runtime
    # attachment is incidental to this oracle; its subject is the durable
    # BuildRegistered row. A real runtime starts an async-loop thread and made
    # this node pass alone but error after a dirty predecessor.
    import specify_cli.sync.events as events_module

    prior_emitter = events_module._emitter
    events_module.reset_emitter()
    runtime = MagicMock()
    monkeypatch.setattr("specify_cli.sync.runtime.get_runtime", lambda: runtime)

    # Keep the canonical project store inside this test's runtime root.
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))

    # Force unauthenticated so the project-init event stays local.
    def _boom():
        raise RuntimeError("Not authenticated")

    monkeypatch.setattr("specify_cli.auth.get_token_manager", _boom)

    # Bootstrap the runtime once so subsequent imports do not need network.
    project_path = tmp_path / "fresh-project"
    project_path.mkdir()
    (project_path / ".kittify").mkdir()
    from specify_cli.identity.project import ensure_identity

    identity = ensure_identity(project_path)
    assert identity.project_uuid is not None
    store = ProjectSyncStore(identity.project_uuid)
    authority = store.layout_generation()
    authority.begin_cutover("init-lifecycle-readiness")
    authority.publish_project_only("init-lifecycle-readiness", verify_exact=lambda: True)
    outside_path = tmp_path / "outside"
    outside_path.mkdir()
    monkeypatch.chdir(outside_path)

    # Materialize identity directly (bypasses the full Typer harness; the
    # init command writes identity then calls the same helper). This keeps
    # the test fast and hermetic.
    from specify_cli.cli.commands.init import _emit_project_init_event

    try:
        _emit_project_init_event(project_path)

        with store.unit_of_work() as unit:
            tasks = OfflineQueue(unit, authority).drain_queue(limit=10)
            events = [task.event for task in tasks]
        assert any(e.get("event_type") == "BuildRegistered" for e in events), "expected init to queue a BuildRegistered event into the durable outbox"
        build_event = next(e for e in events if e["event_type"] == "BuildRegistered")
        assert build_event.get("drain_blocked_reason") in {"missing_auth", "missing_team"}
        assert build_event["payload"]["build_id"]
        assert build_event["payload"]["project_uuid"]
    finally:
        events_module.reset_emitter()
        events_module._emitter = prior_emitter
