"""WP04 — Direct-ingress resolver coverage for queue + emitter call sites.

These tests are sync (no @pytest.mark.asyncio); the call sites under test are
sync. ``respx.mock`` intercepts the sync ``httpx.Client`` GET issued by
``TokenManager.rehydrate_membership_if_needed``; ``unittest.mock.patch``
intercepts the ``FileFallbackStorage`` boundary used by the queue scope path.

See:
- src/specify_cli/sync/_team.py — the resolver under test
- src/specify_cli/sync/queue.py:read_queue_scope_from_session — queue site
  (post per-project-store cutover this site performs NO membership rehydrate at
  all: live payload queues are selected by ``ProjectSyncStore`` and the queue
  scope is a recorded legacy artifact, read without ingress I/O)
- src/specify_cli/sync/emitter.py:EventEmitter._current_team_slug — emitter site
- kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/contracts/api.md §4
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from kernel.clock import now_utc, timedelta
from specify_cli.auth.secure_storage import SecureStorage
from specify_cli.auth.session import StoredSession, Team
from specify_cli.auth.token_manager import TokenManager
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.queue import default_queue_db_path, read_queue_scope_from_session

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

_SAAS_BASE_URL = "https://saas.example"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


class _IngressFakeStorage(SecureStorage):  # type: ignore[misc]
    """Minimal in-memory ``SecureStorage``. Mirrors the WP02 test fake."""

    def __init__(self) -> None:
        self._session: StoredSession | None = None

    def read(self) -> StoredSession | None:
        return self._session

    def write(self, session: StoredSession) -> None:
        self._session = session

    def delete(self) -> None:
        self._session = None

    @property
    def backend_name(self) -> str:
        return "file"


def _build_ingress_session(*, teams: list[Team]) -> StoredSession:
    """Build a ``StoredSession`` with the supplied teams."""
    now = now_utc()
    return StoredSession(
        user_id="user-1",
        email="u@example.com",
        name="U",
        teams=teams,
        default_team_id=teams[0].id if teams else "",
        access_token="access-v1",
        refresh_token="refresh-v1",
        session_id="sess",
        issued_at=now,
        access_token_expires_at=now + timedelta(seconds=900),
        refresh_token_expires_at=None,
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


@pytest.fixture
def token_manager_with_shared_only_session() -> TokenManager:
    """A ``TokenManager`` whose loaded session has only a shared team."""
    storage = _IngressFakeStorage()
    tm = TokenManager(storage, saas_base_url=_SAAS_BASE_URL)
    tm._session = _build_ingress_session(
        teams=[
            Team(
                id="t-shared",
                name="Shared",
                role="member",
                is_private_teamspace=False,
            )
        ]
    )
    return tm


# ---------------------------------------------------------------------------
# Queue ingress path
#
# Since the per-project-store cutover, read_queue_scope_from_session() no
# longer consults TokenManager or the shared resolver at all: it reads the
# recorded ``active_queue_scope`` / session ``queue_scope`` artifacts under
# SPEC_KITTY_HOME without any ingress I/O, and default_queue_db_path() refuses
# outright (live payload queues are selected by ProjectSyncStore; legacy paths
# are WP10 migration inputs). The tests below pin exactly that: a token
# manager is available and respx is armed, and the queue site still never
# issues a membership rehydrate GET.
# ---------------------------------------------------------------------------


def _patched_token_manager(
    monkeypatch: pytest.MonkeyPatch,
    tm: TokenManager,
) -> None:
    """Patch ``specify_cli.auth.get_token_manager`` to return ``tm``.

    The queue path now calls the process-wide singleton via
    ``get_token_manager()`` so the rehydrate negative cache + threading.Lock
    state survive across multiple queue-scope reads (NFR-001 fix).
    Patching the singleton accessor lets respx (keyed on ``_SAAS_BASE_URL``)
    intercept the rehydrate GET against our fixture instance.
    """

    monkeypatch.setattr(
        "specify_cli.auth.get_token_manager",
        lambda: tm,
    )


@respx.mock
def test_queue_scope_reads_recorded_scope_without_ingress(
    canonical_home: None,
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Queue scope path: the recorded scope is returned with zero ingress I/O.

    The pre-cutover contract here was "rehydrate-success surfaces the private
    team id in scope". The queue site no longer resolves teams at all — the
    recorded ``active_queue_scope`` artifact answers, and even with a token
    manager available and a private team on offer, no membership GET is issued.
    """
    me_route = respx.get(f"{_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-private",
                        "name": "Private",
                        "role": "owner",
                        "is_private_teamspace": True,
                    }
                ],
            },
        )
    )

    _patched_token_manager(monkeypatch, token_manager_with_shared_only_session)
    from specify_cli.sync.queue import write_active_scope

    write_active_scope("scope-recorded-by-login")

    scope = read_queue_scope_from_session()

    assert scope == "scope-recorded-by-login"
    assert me_route.call_count == 0


@respx.mock
def test_queue_scope_local_only_skips_rehydrate(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local-only scope reads must not call TeamSpace membership rehydrate."""
    me_route = respx.get(f"{_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-private",
                        "name": "Private",
                        "role": "owner",
                        "is_private_teamspace": True,
                    }
                ],
            },
        )
    )

    _patched_token_manager(monkeypatch, token_manager_with_shared_only_session)

    scope = read_queue_scope_from_session(allow_rehydrate=False)

    assert scope is None
    assert me_route.call_count == 0


@respx.mock
def test_default_queue_db_path_local_only_skips_rehydrate(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local-only queue path resolution must not call TeamSpace membership rehydrate."""
    me_route = respx.get(f"{_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-private",
                        "name": "Private",
                        "role": "owner",
                        "is_private_teamspace": True,
                    }
                ],
            },
        )
    )

    _patched_token_manager(monkeypatch, token_manager_with_shared_only_session)

    from specify_cli.sync.queue import LegacyQueueMigrationRequiredError

    # Post-cutover there is no legacy queue path to resolve at all: live payload
    # queues are selected by ProjectSyncStore, and the retired resolver refuses
    # rather than answering — still with zero membership rehydrate I/O.
    with pytest.raises(LegacyQueueMigrationRequiredError):
        default_queue_db_path(allow_rehydrate=False)

    assert me_route.call_count == 0


@respx.mock
def test_queue_ingress_skipped_on_no_private_team(
    canonical_home: None,
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Queue scope path: no recorded scope resolves to None with zero ingress I/O.

    Pre-cutover this asserted the resolver's structured warning at the queue
    site. The queue site no longer calls the resolver at all — no scope on
    record means ``None``, and no membership rehydrate GET is ever attempted,
    which is strictly safer than warn-and-skip. The structured-warning contract
    itself is still pinned below at the emitter site.
    """
    me_route = respx.get(f"{_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-shared",
                        "name": "Shared",
                        "role": "member",
                        "is_private_teamspace": False,
                    }
                ],
            },
        )
    )

    _patched_token_manager(monkeypatch, token_manager_with_shared_only_session)

    scope = read_queue_scope_from_session()

    assert scope is None
    assert me_route.call_count == 0


# ---------------------------------------------------------------------------
# Emitter ingress path
# ---------------------------------------------------------------------------


@respx.mock
def test_emitter_ingress_rehydrates_and_sends_private(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Emitter ingress path: rehydrate-success surfaces the private team id."""
    me_route = respx.get(f"{_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-private",
                        "name": "Private",
                        "role": "owner",
                        "is_private_teamspace": True,
                    }
                ],
            },
        )
    )
    monkeypatch.setattr(
        "specify_cli.auth.get_token_manager",
        lambda: token_manager_with_shared_only_session,
    )

    slug = EventEmitter._current_team_slug()

    assert slug == "t-private"
    assert me_route.call_count == 1


@respx.mock
def test_emitter_ingress_skipped_on_no_private_team(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Emitter ingress path: rehydrate-fails returns None + structured warning."""
    respx.get(f"{_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-shared",
                        "name": "Shared",
                        "role": "member",
                        "is_private_teamspace": False,
                    }
                ],
            },
        )
    )
    monkeypatch.setattr(
        "specify_cli.auth.get_token_manager",
        lambda: token_manager_with_shared_only_session,
    )

    with caplog.at_level(logging.WARNING, logger="specify_cli.sync._team"):
        slug = EventEmitter._current_team_slug()

    assert slug is None
    matching = [
        record
        for record in caplog.records
        if "direct_ingress_missing_private_team" in record.getMessage()
    ]
    assert matching, "expected structured warning with category direct_ingress_missing_private_team"
    record = matching[0]
    assert getattr(record, "category", None) == "direct_ingress_missing_private_team"
    assert getattr(record, "rehydrate_attempted", None) is True
    assert getattr(record, "ingress_sent", None) is False
    assert getattr(record, "endpoint", None) == "/api/v1/events/batch/"


@respx.mock
def test_emitter_emit_queues_event_when_no_private_team_no_remote_ingress(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
    temp_queue,
    temp_clock,
    mock_identity,
    mock_git_resolver,
) -> None:
    """Local durability holds, ingress safety holds (issue #1072 / FR-002).

    When the strict resolver returns ``None``:

    1. The public emit method now RETURNS the event (it is locally durable),
       with ``team_slug = None`` and ``drain_blocked_reason in {"missing_team",
       "missing_auth"}`` so the drain side knows not to ship it remotely.
    2. The event IS appended to the durable ``OfflineQueue`` — it would
       otherwise be lost if auth/team conditions never resolve in this
       process.
    3. Ingress safety: the WebSocket client is NOT used (blocked events
       skip opportunistic publish). The batch drain path also re-resolves
       the team on every tick and skips POSTing while the resolver still
       returns ``None`` (see ``tests/sync/test_batch_*`` for that surface).
    """
    respx.get(f"{_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-shared",
                        "name": "Shared",
                        "role": "member",
                        "is_private_teamspace": False,
                    }
                ],
            },
        )
    )
    monkeypatch.setattr(
        "specify_cli.auth.get_token_manager",
        lambda: token_manager_with_shared_only_session,
    )
    # The sync gate is held open for this package by
    # ``tests/sync/conftest.py::_consented_checkout_by_default`` so _emit reaches the
    # team_slug step. The explicit ``is_sync_enabled_for_checkout`` override that used
    # to sit here was removed with #3030 M1-1: the emitter no longer imports that
    # cwd-derived name, so patching it steered nothing.

    # ``OfflineQueue`` no longer takes ``db_path``: the shared ``temp_queue``
    # fixture supplies a project-store outbox over an active unit of work whose
    # owner matches ``mock_identity`` (events must carry their store owner's
    # project uuid to be accepted).
    config = MagicMock()
    ws_client = MagicMock()
    ws_client.send_event = MagicMock()
    ws_client.connected = True  # ensure the WS short-circuit is checked

    emitter = EventEmitter(
        clock=temp_clock,
        config=config,
        queue=temp_queue,
        ws_client=ws_client,
        _identity=mock_identity,
        _git_resolver=mock_git_resolver,
    )

    event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    # 1. Locally durable: event is produced and queued for later drain.
    assert event is not None
    assert event["team_slug"] is None
    assert event["drain_blocked_reason"] in {"missing_team", "missing_auth"}

    # 2. Persisted on disk.
    assert temp_queue.size() == 1

    # 3. Ingress safety: no opportunistic WS publish for a blocked event.
    ws_client.send_event.assert_not_called()
