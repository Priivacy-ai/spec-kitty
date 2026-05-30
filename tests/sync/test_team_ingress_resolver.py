"""WP04 — Direct-ingress resolver coverage for queue + emitter call sites.

These tests are sync (no @pytest.mark.asyncio); the call sites under test are
sync. ``respx.mock`` intercepts the sync ``httpx.Client`` GET issued by
``TokenManager.rehydrate_membership_if_needed``; ``unittest.mock.patch``
intercepts the ``FileFallbackStorage`` boundary used by the queue scope path.

See:
- src/specify_cli/sync/_team.py — the resolver under test
- src/specify_cli/sync/queue.py:read_queue_scope_from_session — queue site
- src/specify_cli/sync/emitter.py:EventEmitter._current_team_slug — emitter site
- kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/contracts/api.md §4
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from specify_cli.auth.secure_storage import SecureStorage
from specify_cli.auth.session import StoredSession, Team
from specify_cli.auth.token_manager import TokenManager
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.queue import default_queue_db_path, read_queue_scope_from_session

pytestmark = pytest.mark.fast

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
    now = datetime.now(UTC)
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
# read_queue_scope_from_session() reads from FileFallbackStorage and
# constructs a transient TokenManager that calls the shared helper. We patch
# the storage boundary and TokenManager construction so the rehydrate path
# uses our fixture URL (so respx intercepts) and our shared-only session.
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
def test_queue_ingress_rehydrates_and_sends_private(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Queue ingress path: rehydrate-success surfaces the private team id in scope."""
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

    # Make FileFallbackStorage().read() return our shared-only session so the
    # queue scope path enters the helper.
    fake_storage = MagicMock()
    fake_storage.read.return_value = (
        token_manager_with_shared_only_session.get_current_session()
    )
    monkeypatch.setattr(
        "specify_cli.auth.secure_storage.file_fallback.FileFallbackStorage",
        lambda *args, **kwargs: fake_storage,  # noqa: ARG005
    )
    _patched_token_manager(monkeypatch, token_manager_with_shared_only_session)

    scope = read_queue_scope_from_session()

    assert scope is not None
    assert "t-private" in scope
    assert me_route.call_count == 1


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

    path = default_queue_db_path(allow_rehydrate=False)

    assert path.name == "queue.db"
    assert me_route.call_count == 0


@respx.mock
def test_queue_ingress_skipped_on_no_private_team(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Queue ingress path: rehydrate-fails returns None + structured warning."""
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

    fake_storage = MagicMock()
    fake_storage.read.return_value = (
        token_manager_with_shared_only_session.get_current_session()
    )
    monkeypatch.setattr(
        "specify_cli.auth.secure_storage.file_fallback.FileFallbackStorage",
        lambda *args, **kwargs: fake_storage,  # noqa: ARG005
    )
    _patched_token_manager(monkeypatch, token_manager_with_shared_only_session)

    with caplog.at_level(logging.WARNING, logger="specify_cli.sync._team"):
        scope = read_queue_scope_from_session()

    assert scope is None
    matching = [
        record
        for record in caplog.records
        if "direct_ingress_missing_private_team" in record.getMessage()
    ]
    assert matching, "expected structured warning with category direct_ingress_missing_private_team"
    record = matching[0]
    # Structured payload travels via ``extra`` and is exposed as record attrs.
    assert getattr(record, "category", None) == "direct_ingress_missing_private_team"
    assert getattr(record, "rehydrate_attempted", None) is True
    assert getattr(record, "ingress_sent", None) is False
    assert getattr(record, "endpoint", None) == "/api/v1/events/batch/"


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
    tmp_path,
) -> None:
    """Local durability holds, ingress safety holds (issue #1072 / FR-002).

    When the strict resolver returns ``None``:

    1. The public emit method now RETURNS the event (it is locally durable),
       with ``team_slug = None`` and ``drain_blocked_reason in {"no_team",
       "no_auth"}`` so the drain side knows not to ship it remotely.
    2. The event IS appended to the durable ``OfflineQueue`` — it would
       otherwise be lost if auth/team conditions never resolve in this
       process.
    3. Ingress safety: the WebSocket client is NOT used (blocked events
       skip opportunistic publish). The batch drain path also re-resolves
       the team on every tick and skips POSTing while the resolver still
       returns ``None`` (see ``tests/sync/test_batch_*`` for that surface).
    """
    from unittest.mock import MagicMock

    from specify_cli.sync.clock import LamportClock
    from specify_cli.sync.queue import OfflineQueue

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
    # Force the sync gate open so _emit reaches the team_slug step.
    monkeypatch.setattr(
        "specify_cli.sync.emitter.is_sync_enabled_for_checkout",
        lambda: True,
    )

    queue = OfflineQueue(db_path=tmp_path / "queue.db")
    clock = LamportClock(value=0, node_id="test", _storage_path=tmp_path / "c.json")
    config = MagicMock()
    ws_client = MagicMock()
    ws_client.send_event = MagicMock()
    ws_client.connected = True  # ensure the WS short-circuit is checked

    emitter = EventEmitter(clock=clock, config=config, queue=queue, ws_client=ws_client)

    event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    # 1. Locally durable: event is produced and queued for later drain.
    assert event is not None
    assert event["team_slug"] is None
    assert event["drain_blocked_reason"] in {"no_team", "no_auth"}

    # 2. Persisted on disk.
    assert queue.size() == 1

    # 3. Ingress safety: no opportunistic WS publish for a blocked event.
    ws_client.send_event.assert_not_called()
