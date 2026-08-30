"""Integration wiring tests for the canonical Target Authority (WP02, contract §1).

WP01 produced the descriptive :class:`ResolvedSyncTarget` and proved its
invariants at the resolver level. WP02 *wires the live runtime surfaces onto
it*: readiness, the daemon-owner identity, and the sync-boundary preflight
identity must all key off the **one** resolved target so that env/config
disagreement can never derive the queue scope for one target while a surface
posts to another (SC-008), and a stale ``active_queue_scope`` is never used as
authority (contract §1 rule, C-002).

These assert **observable state** (URLs, scope strings, db paths) across the
rewired surfaces — never internal call order (NFR-001). No network, no daemon,
no real port: the resolver and every probe here are pure/in-process.
"""

from __future__ import annotations

from kernel.clock import now_utc, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.auth.session import StoredSession, Team
from specify_cli.saas import readiness
from specify_cli.sync import sharing_client
from specify_cli.sync.background import BackgroundSyncService
from specify_cli.sync.config import SyncConfig
from specify_cli.sync.namespace import UploadOutcome, UploadStatus
from specify_cli.sync.owner import compute_foreground_identity
from specify_cli.sync.preflight import collect_foreground_identity
from specify_cli.sync.queue import write_active_scope
from specify_cli.sync.runtime import SyncRuntime
from specify_cli.sync.target_authority import (
    QueueScopeStatus,
    SyncTargetSplitBrainError,
    resolve_sync_target,
)
from specify_cli.tracker.saas_client import SaaSTrackerClient

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

CONFIG_URL = "https://config.example.com"
ENV_URL = "https://env.example.com"
USER = "alice@example.com"
PRIVATE_TEAMSPACE_ID = "teamspace-private-red"


class _NoSession:
    """Token-manager stub exposing no current session (read-only, no network)."""

    def get_current_session(self) -> None:
        return None

    def rehydrate_membership_if_needed(self, *, force: bool = False) -> bool:
        del force
        return False


class _SessionManager:
    """Token-manager stub backed by local StoredSession data."""

    def __init__(self, session: StoredSession, *, rehydrate_session: StoredSession | None = None) -> None:
        self._session = session
        self._rehydrate_session = rehydrate_session
        self.rehydrate_calls = 0

    def get_current_session(self) -> StoredSession:
        return self._session

    def rehydrate_membership_if_needed(self, *, force: bool = False) -> bool:
        del force
        self.rehydrate_calls += 1
        if self._rehydrate_session is None:
            return False
        self._session = self._rehydrate_session
        return True


def _stored_session(
    *,
    email: str = USER,
    private_teamspace_id: str | None = PRIVATE_TEAMSPACE_ID,
) -> StoredSession:
    now = now_utc()
    teams = (
        [
            Team(
                id=private_teamspace_id,
                name="Private Teamspace",
                role="owner",
                is_private_teamspace=True,
            )
        ]
        if private_teamspace_id is not None
        else [
            Team(
                id="shared-team",
                name="Shared Team",
                role="member",
                is_private_teamspace=False,
            )
        ]
    )
    return StoredSession(
        user_id="user-1",
        email=email,
        name="Alice",
        teams=teams,
        default_team_id=teams[0].id,
        access_token="access-token",
        refresh_token="refresh-token",
        session_id="session-1",
        issued_at=now,
        access_token_expires_at=now + timedelta(minutes=30),
        refresh_token_expires_at=None,
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="device_code",
    )


def _install_token_manager(
    monkeypatch: pytest.MonkeyPatch,
    manager: object,
) -> None:
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: manager)
    monkeypatch.setattr("specify_cli.auth.manager.get_token_manager", lambda: manager)


@pytest.fixture
def wiring_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolate all sync global state under a throwaway ``SPEC_KITTY_HOME``.

    Clears ``SPEC_KITTY_SAAS_URL`` and neutralises the local auth-session seam
    so identity is driven only by the test-installed session manager,
    ``config.toml`` and the env var — deterministic and network-free. Tests that
    want an env override re-set ``SPEC_KITTY_SAAS_URL`` explicitly.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    # Resolver diagnostics read cached scope only to classify stale state; owner
    # identity reads the TokenManager session, installed below as unauthenticated
    # by default.
    monkeypatch.setattr(
        "specify_cli.sync.target_authority.read_queue_scope_from_session",
        lambda *, allow_rehydrate=True: None,
    )
    monkeypatch.setattr(
        "specify_cli.sync.queue.read_queue_scope_from_session",
        lambda *, allow_rehydrate=True: None,
    )
    _install_token_manager(monkeypatch, _NoSession())
    return tmp_path


def _write_config(root: Path, server_url: str) -> None:
    (root / "config.toml").write_text(f'[sync]\nserver_url = "{server_url}"\n', encoding="utf-8")


# ---------------------------------------------------------------------------
# T008 — readiness keys off the resolved target (not a separate env-only read)
# ---------------------------------------------------------------------------


def test_readiness_host_config_keys_off_resolved_target(wiring_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When env opts in, readiness reports the single resolved target URL.

    The D-5 opt-in gate is via ``SPEC_KITTY_SAAS_URL``; once set, the URL is the
    canonical ``resolved_server_url`` so readiness and sync agree (contract §1).
    """
    _write_config(wiring_root, CONFIG_URL)

    # #3130 fold: monkeypatch.setenv restores the pre-test value in teardown
    # (the raw os.environ[...] = ... this replaced left SPEC_KITTY_SAAS_URL
    # set for the rest of the worker process -- WP04's own E52 row).
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", CONFIG_URL)  # env == config, opted in

    probed = readiness._probe_host_config()
    resolved = resolve_sync_target().resolved_server_url

    assert probed == CONFIG_URL
    assert probed == resolved


def test_readiness_targets_env_under_whole_process_override(wiring_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When env overrides config, readiness probes the env (resolved) URL.

    This is the readiness SC-008 proof: readiness can never green-light the
    config URL while sync posts to the env URL — both are the one resolved
    target.
    """
    _write_config(wiring_root, CONFIG_URL)
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", ENV_URL)

    probed = readiness._probe_host_config()
    target = resolve_sync_target()

    assert target.resolved_server_url == ENV_URL
    assert probed == ENV_URL  # same resolved target, not the config URL


def test_readiness_env_presence_gate_preserved(wiring_root: Path) -> None:
    """D-5 opt-in gate preserved: config-only (env unset) ⇒ absent host.

    Config-file ``[sync].server_url`` alone never opts a machine into hosted
    readiness; only ``SPEC_KITTY_SAAS_URL`` does. Owner/preflight still derive
    their scope from the resolved (config) target — readiness simply requires
    the explicit env opt-in.
    """
    _write_config(wiring_root, CONFIG_URL)
    # env cleared by the fixture, config present.
    assert readiness._probe_host_config() is None


def test_readiness_host_config_absent_when_no_source(wiring_root: Path) -> None:
    """Neither config nor env configured ⇒ readiness reports an absent host."""
    # No config.toml written; env cleared by the fixture.
    assert readiness._probe_host_config() is None


# ---------------------------------------------------------------------------
# T009 / SC-008 — owner identity scope + URL follow the one resolved target
# ---------------------------------------------------------------------------


def test_owner_identity_follows_resolved_target_under_split_brain(wiring_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Daemon-owner identity cannot scope one target while posting to another.

    config and env disagree; the whole-process override resolves env. The owner
    record's ``server_url`` AND ``auth_scope`` AND ``queue_db_path`` must all
    reflect that single resolved (env) target — the structural SC-008 fix.
    """
    _write_config(wiring_root, CONFIG_URL)
    _install_token_manager(monkeypatch, _SessionManager(_stored_session()))
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", ENV_URL)  # disagrees with config

    identity = compute_foreground_identity(allow_network=False)
    target = resolve_sync_target(user_id=USER, team_slug=PRIVATE_TEAMSPACE_ID)

    assert identity["server_url"] == ENV_URL
    assert identity["auth_principal"] == USER
    assert identity["auth_team"] == PRIVATE_TEAMSPACE_ID
    assert identity["auth_scope"] == target.derived_queue_scope
    assert identity["queue_db_path"] == str(target.queue_db_path)
    # Queue scope is intentionally opaque SHA-256, not a parsed
    # ``server|user|team`` string.
    assert len(str(identity["auth_scope"])) == 64
    assert str(identity["auth_scope"]).isascii()


def test_owner_identity_without_session_keeps_auth_scope_absent(wiring_root: Path) -> None:
    _write_config(wiring_root, CONFIG_URL)

    identity = compute_foreground_identity(allow_network=False)
    target = resolve_sync_target()

    assert identity["server_url"] == CONFIG_URL
    assert identity["auth_principal"] is None
    assert identity["auth_team"] is None
    assert identity["auth_scope"] is None
    assert identity["queue_db_path"] == str(target.queue_db_path)


def test_owner_identity_with_private_teamspace_does_not_rehydrate_before_health(
    wiring_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_config(wiring_root, CONFIG_URL)
    manager = _SessionManager(_stored_session())
    _install_token_manager(monkeypatch, manager)

    identity = compute_foreground_identity(allow_network=False)
    target = resolve_sync_target(user_id=USER, team_slug=PRIVATE_TEAMSPACE_ID)

    assert manager.rehydrate_calls == 0
    assert identity["auth_principal"] == USER
    assert identity["auth_team"] == PRIVATE_TEAMSPACE_ID
    assert identity["auth_scope"] == target.derived_queue_scope


def test_owner_identity_missing_private_teamspace_does_not_rehydrate_before_health(
    wiring_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_config(wiring_root, CONFIG_URL)
    manager = _SessionManager(_stored_session(private_teamspace_id=None))
    _install_token_manager(monkeypatch, manager)

    identity = compute_foreground_identity(allow_network=False)
    target = resolve_sync_target(user_id=USER, team_slug=None)

    assert manager.rehydrate_calls == 0
    assert identity["auth_principal"] == USER
    assert identity["auth_team"] is None
    assert identity["auth_scope"] == target.derived_queue_scope


def test_owner_identity_rehydrates_after_health_when_allowed(
    wiring_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_config(wiring_root, CONFIG_URL)
    manager = _SessionManager(
        _stored_session(private_teamspace_id=None),
        rehydrate_session=_stored_session(private_teamspace_id=PRIVATE_TEAMSPACE_ID),
    )
    _install_token_manager(monkeypatch, manager)

    identity = compute_foreground_identity(allow_network=True)
    target = resolve_sync_target(user_id=USER, team_slug=PRIVATE_TEAMSPACE_ID)

    assert manager.rehydrate_calls == 1
    assert identity["auth_team"] == PRIVATE_TEAMSPACE_ID
    assert identity["auth_scope"] == target.derived_queue_scope


def test_owner_identity_preserves_missing_private_teamspace_when_rehydrate_fails(
    wiring_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_config(wiring_root, CONFIG_URL)
    manager = _SessionManager(_stored_session(private_teamspace_id=None))
    _install_token_manager(monkeypatch, manager)

    identity = compute_foreground_identity(allow_network=True)
    target = resolve_sync_target(user_id=USER, team_slug=None)

    assert manager.rehydrate_calls == 1
    assert identity["auth_team"] is None
    assert identity["auth_scope"] == target.derived_queue_scope


def test_owner_identity_propagates_split_brain_target_error(
    wiring_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_config(wiring_root, CONFIG_URL)
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", ENV_URL)
    monkeypatch.setattr(
        "specify_cli.sync.target_authority.resolve_sync_target",
        lambda **_kwargs: (_ for _ in ()).throw(
            SyncTargetSplitBrainError(
                configured_server_url=CONFIG_URL,
                env_server_url=ENV_URL,
            )
        ),
    )

    with pytest.raises(SyncTargetSplitBrainError):
        compute_foreground_identity(allow_network=False)


def test_preflight_identity_follows_resolved_target_under_split_brain(wiring_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Preflight foreground identity derives scope from the resolved target."""
    _write_config(wiring_root, CONFIG_URL)
    _install_token_manager(monkeypatch, _SessionManager(_stored_session()))
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", ENV_URL)

    fg = collect_foreground_identity(repo_root=wiring_root)
    target = resolve_sync_target(user_id=USER, team_slug=PRIVATE_TEAMSPACE_ID)

    assert fg.server_url == ENV_URL
    assert fg.queue_db_path == target.queue_db_path
    assert "env.example.com" not in str(target.queue_db_path)  # digest is opaque


# ---------------------------------------------------------------------------
# T009 / contract §1 — stale active_queue_scope reported, never authoritative
# ---------------------------------------------------------------------------


def test_stale_active_queue_scope_ignored_by_owner_identity(wiring_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A stale cached scope is a diagnostic only — the derived scope wins."""
    _write_config(wiring_root, CONFIG_URL)
    _install_token_manager(monkeypatch, _SessionManager(_stored_session()))
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", ENV_URL)
    write_active_scope("https://stale.example.com|ghost@example.com|old-team")

    identity = compute_foreground_identity(allow_network=False)
    target = resolve_sync_target(user_id=USER, team_slug=PRIVATE_TEAMSPACE_ID)

    # Identity uses the freshly derived scope, not the stale cache.
    assert identity["auth_scope"] == target.derived_queue_scope
    assert str(identity["auth_scope"]) != "https://stale.example.com|ghost@example.com|old-team"
    # The cache is still surfaced as a diagnostic (never as authority).
    assert target.active_queue_scope_status is QueueScopeStatus.STALE_NON_AUTHORITATIVE


# ---------------------------------------------------------------------------
# T011 — single-target coherence: every surface shares one resolved URL
# ---------------------------------------------------------------------------


def test_single_resolved_url_across_surfaces(wiring_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Readiness, owner, and preflight all share the one resolved-target URL.

    Env and config agree (no override): every surface — including readiness,
    which is opted in by the matching env var — keys off the same
    ``resolved_server_url``.
    """
    _write_config(wiring_root, CONFIG_URL)
    _install_token_manager(monkeypatch, _SessionManager(_stored_session()))
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", CONFIG_URL)  # opt readiness in; no override

    target = resolve_sync_target(user_id=USER, team_slug=PRIVATE_TEAMSPACE_ID)
    readiness_url = readiness._probe_host_config()
    owner_url = compute_foreground_identity(allow_network=False)["server_url"]
    preflight_url = collect_foreground_identity(repo_root=wiring_root).server_url

    assert target.resolved_server_url == CONFIG_URL
    assert readiness_url == CONFIG_URL
    assert owner_url == CONFIG_URL
    assert preflight_url == CONFIG_URL


# ---------------------------------------------------------------------------
# #2146 — remaining runtime clients (tracker, sharing, background sync) key off
# the one resolved target, not the raw config.toml accessor. Robert's #2246
# review named these three as still reading ``get_server_url()`` (hardcoded
# default), so they could post to the config target while auth/readiness point
# at the env override. These prove they now resolve the same URL (SC-008).
# ---------------------------------------------------------------------------


def test_tracker_client_base_url_follows_resolved_target(wiring_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The tracker SaaS client hits the resolved (env-override) target, not config."""
    _write_config(wiring_root, CONFIG_URL)
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", ENV_URL)

    client = SaaSTrackerClient()
    resolved = resolve_sync_target().resolved_server_url

    assert client._base_url == ENV_URL
    assert client._base_url == resolved  # same single target as auth/readiness


def test_sharing_client_base_url_follows_resolved_target(wiring_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The repository-sharing client resolves the env-override target, not config."""
    _write_config(wiring_root, CONFIG_URL)
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", ENV_URL)

    assert sharing_client._base_url() == ENV_URL
    assert sharing_client._base_url() == resolve_sync_target().resolved_server_url


def test_background_full_sync_posts_to_resolved_target(wiring_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The background daemon posts body uploads to the resolved (env) target.

    Captures the ``server_url`` the daemon actually hands to the body poster —
    observable state, not call order (NFR-001) — under a whole-process override.

    The daemon's *event* drain was removed with the legacy queue (#3030 FR-012);
    body uploads are the surviving daemon POST surface, and the Target Authority
    contract (§1, C-002) still binds it.
    """
    _write_config(wiring_root, CONFIG_URL)
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", ENV_URL)

    captured: dict[str, str] = {}

    def _fake_push_content_with_transport_gate(
        task: object,
        auth_token: str,
        target: object,
        server_url: str,
    ) -> UploadOutcome:
        del task, auth_token, target
        captured["server_url"] = server_url
        return UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="ok",
        )

    monkeypatch.setattr("specify_cli.sync.background.is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr("specify_cli.sync.background._fetch_access_token_sync", lambda: "tok")
    monkeypatch.setattr(
        "specify_cli.sync.body_transport.push_content_with_transport_gate",
        _fake_push_content_with_transport_gate,
    )
    monkeypatch.setattr(
        "specify_cli.sync.background.BackgroundSyncService._resolve_body_delivery_target",
        lambda _self, task, server_url: object(),
    )

    # #3030 T025: the body drain resolves consent from each task's own
    # ``project_uuid`` and denies on absence, so the queued task needs a real,
    # consenting identity for the poster to be reached at all. Consent is a
    # precondition here — this test's subject is *which* server_url the daemon posts
    # to; the refusal path is pinned in ``tests/sync/test_body_drain_consent_3030.py``.
    # ``wiring_root`` already isolates ``SPEC_KITTY_HOME``, so the grant is throwaway.
    from specify_cli.sync.consent import record_project_opt_in

    consenting_uuid = "11111111-2222-3333-4444-555555555555"
    record_project_opt_in(consenting_uuid, actor="wp08-test")
    task = MagicMock()
    task.project_uuid = consenting_uuid
    task.row_id = "body-row-1"

    body_queue = MagicMock()
    body_queue.remove_stale.return_value = 0
    body_queue.drain.return_value = [task]
    service = BackgroundSyncService(queue=MagicMock(), config=SyncConfig())
    service._body_queue = body_queue
    service._perform_full_sync()

    assert "server_url" in captured, "_fake_push_content was not called — _perform_full_sync did not reach the body poster"
    assert captured["server_url"] == ENV_URL
    assert captured["server_url"] == resolve_sync_target().resolved_server_url


def test_runtime_start_does_not_recreate_retired_shared_body_queue(
    wiring_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime startup has no project UoW, so body queues must be installed elsewhere."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr("specify_cli.sync.runtime._auto_start_enabled", lambda: True)
    monkeypatch.setattr("specify_cli.sync.runtime.SyncRuntime._ensure_async_loop", lambda _self: None)
    monkeypatch.setattr("specify_cli.sync.runtime.SyncRuntime._connect_websocket_if_authenticated", lambda _self: None)
    monkeypatch.setattr(
        "specify_cli.sync.body_queue.OfflineBodyUploadQueue",
        lambda *args, **kwargs: pytest.fail("retired shared body queue constructor must not be called"),
    )

    service = MagicMock()
    service.queue.size.return_value = 0
    service.queue.db_path = wiring_root / "legacy-queue.db"
    service._body_queue = object()
    monkeypatch.setattr("specify_cli.sync.background.get_sync_service", lambda: service)

    runtime = SyncRuntime()
    runtime.start()

    assert runtime.started is True
    assert runtime.body_queue is None
    assert service._body_queue is None
    service.wake.assert_not_called()
