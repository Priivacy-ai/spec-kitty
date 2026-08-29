"""WP08 daemon discovery and per-project liveness isolation tests."""

from __future__ import annotations

import asyncio
import json
import threading
import urllib.request
from collections.abc import Iterator
from kernel.clock import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from specify_cli.auth import reset_token_manager
from specify_cli.sync.config import BackgroundDaemonPolicy
from specify_cli.sync.client import WebSocketClient
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.daemon import (
    DaemonIntent,
    ensure_sync_daemon_running,
    get_sync_daemon_status,
    stop_sync_daemon,
)
from specify_cli.sync.deny_hints import (
    DenyHintAction,
    DenyHintStatus,
    deny_hint_path,
    enumerate_deny_hint_project_uuids,
    publish_deny_hint,
    read_deny_hint,
)
from specify_cli.sync.layout_generation import LayoutAuthorityError
from specify_cli.migration.envelope_seam import build_teamspace_envelope
from specify_cli.sync.owner import compute_foreground_identity
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.runtime import SyncRuntime, event_project_consents_to_publish

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"
NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


class _AutoDaemonConfig:
    def get_background_daemon(self) -> BackgroundDaemonPolicy:
        return BackgroundDaemonPolicy.AUTO


@pytest.fixture(autouse=True)
def _runtime_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://app.spec-kitty.ai")
    reset_token_manager()
    yield
    reset_token_manager()


def _admit_project(project_uuid: str) -> ProjectSyncStore:
    record_project_opt_in(project_uuid, actor="wp08-test")
    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    try:
        authority.begin_cutover("wp08-daemon")
    except LayoutAuthorityError as exc:
        if "already project-only" not in str(exc):
            raise
    else:
        authority.publish_project_only("wp08-daemon", verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://app.spec-kitty.ai', 'account-1', 'teamspace-1', 4, "
            "'admitted', '1', 'private-teamspace:teamspace-1')",
            (project_uuid,),
        )
    return store


def _fetch_daemon_health(url: str) -> dict[str, object]:
    with urllib.request.urlopen(f"{url}/api/health", timeout=1.0) as response:  # nosec B310 - loopback daemon under test
        payload = json.loads(response.read().decode("utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_owner_identity_uses_canonical_target_without_legacy_queue() -> None:
    identity = compute_foreground_identity(allow_network=False)

    assert identity["server_url"] == "https://app.spec-kitty.ai"
    assert identity["auth_scope"] is None
    assert "/queues/queue-" in str(identity["queue_db_path"])
    assert not str(identity["queue_db_path"]).endswith("/queue.db")


def test_daemon_remains_live_for_project_b_after_project_a_opt_out() -> None:
    _admit_project(PROJECT_A)
    _admit_project(PROJECT_B)

    try:
        outcome = ensure_sync_daemon_running(
            intent=DaemonIntent.REMOTE_REQUIRED,
            config=_AutoDaemonConfig(),
            health_wait_seconds=5.0,
        )
        assert outcome.started is True
        status = get_sync_daemon_status(timeout=0.5)
        assert status.healthy is True
        assert status.url is not None
        health = _fetch_daemon_health(status.url)
        owner = health.get("owner")
        assert isinstance(owner, dict)
        assert owner["server_url"] == "https://app.spec-kitty.ai"
        assert "/queues/queue-" in str(owner["queue_db_path"])
        assert not str(owner["queue_db_path"]).endswith("/queue.db")

        record_project_opt_out(PROJECT_A, actor="wp08-test")

        status = get_sync_daemon_status(timeout=0.5)
        assert status.healthy is True
        assert status.pid == outcome.pid
    finally:
        stop_sync_daemon(timeout=5.0)


def test_deny_hint_discovery_never_creates_project_store_or_consent() -> None:
    publish_deny_hint(
        PROJECT_A,
        action=DenyHintAction.REVOKE,
        authority_generation=2,
        reason_category="explicit_opt_out",
        now=NOW,
    )
    runtime = deny_hint_path(PROJECT_A).parents[2]

    discovered = enumerate_deny_hint_project_uuids()

    assert tuple(str(value) for value in discovered) == (PROJECT_A,)
    assert not (runtime / "projects" / PROJECT_A / "sync" / "sync.db").exists()


def test_stale_or_missing_deny_hint_requires_project_authority() -> None:
    assert read_deny_hint(PROJECT_A, expected_generation=1, now=NOW).requires_authority

    publish_deny_hint(
        PROJECT_A,
        action=DenyHintAction.DENY,
        authority_generation=1,
        reason_category="absent",
        now=NOW - timedelta(hours=1),
        ttl=timedelta(minutes=1),
    )
    stale = read_deny_hint(PROJECT_A, expected_generation=1, now=NOW)
    generation_mismatch = read_deny_hint(PROJECT_A, expected_generation=2, now=NOW - timedelta(minutes=30))

    assert stale.status is DenyHintStatus.STALE_DENY
    assert stale.requires_authority is True
    assert generation_mismatch.status is DenyHintStatus.STALE_DENY
    assert generation_mismatch.requires_authority is True


def test_fresh_exact_deny_hint_is_the_only_skip_authority_case() -> None:
    publish_deny_hint(
        PROJECT_A,
        action=DenyHintAction.REVOKE,
        authority_generation=2,
        reason_category="explicit_opt_out",
        now=NOW,
    )

    probe = read_deny_hint(PROJECT_A, expected_generation=2, now=NOW + timedelta(seconds=1))

    assert probe.status is DenyHintStatus.VALID_DENY
    assert probe.requires_authority is False


@pytest.mark.parametrize(
    "document",
    (
        "{not-json",
        "[]",
        '{"action":"grant","authority_generation":2,"expires_at":"2026-08-10T12:05:00+00:00","layout_version":1,"reason_category":"explicit_opt_out","checksum":"bad"}',
        '{"action":"pending","authority_generation":2,"expires_at":"2026-08-10T12:05:00+00:00","layout_version":1,"reason_category":"explicit_opt_out","checksum":"bad"}',
        '{"action":"unknown","authority_generation":2,"expires_at":"2026-08-10T12:05:00+00:00","layout_version":1,"reason_category":"explicit_opt_out","checksum":"bad"}',
        '{"action":"deny","authority_generation":2,"expires_at":"2026-08-10T12:05:00+00:00","layout_version":1,"reason_category":"explicit_opt_out","checksum":"bad","extra":"field"}',
    ),
)
def test_deny_hint_mutants_never_grant_or_skip_authority(document: str) -> None:
    path = deny_hint_path(PROJECT_A)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")

    probe = read_deny_hint(PROJECT_A, expected_generation=2, now=NOW)

    assert probe.requires_authority is True
    assert probe.status is not DenyHintStatus.VALID_DENY


def test_daemon_publish_missing_project_store_denies_without_creation() -> None:
    store = ProjectSyncStore(PROJECT_A)
    assert not store.database_path.exists()

    allowed = event_project_consents_to_publish({"project_uuid": PROJECT_A, "event_id": "evt-a"})

    assert allowed is False
    assert not store.database_path.exists()


def test_daemon_publish_uses_project_store_admission_and_keeps_b_live_after_a_revokes() -> None:
    store_a = _admit_project(PROJECT_A)
    store_b = _admit_project(PROJECT_B)

    with store_a.unit_of_work() as unit_a:
        unit_a.execute(
            "UPDATE project_consent_decisions SET state = 'refused', generation = 2, action = 'explicit_opt_out' WHERE project_uuid = ?",
            (PROJECT_A,),
        )

    assert event_project_consents_to_publish({"project_uuid": PROJECT_A, "event_id": "evt-a"}) is False
    assert event_project_consents_to_publish({"project_uuid": PROJECT_B, "event_id": "evt-b"}) is True
    assert store_b.database_path.exists()


def _install_current_audience(monkeypatch: pytest.MonkeyPatch, *, account: str = "account-1", team: str = "teamspace-1") -> None:
    manager = SimpleNamespace(
        get_current_session=lambda: SimpleNamespace(
            email=account,
            teams=[SimpleNamespace(id=team, is_private_teamspace=True)],
        )
    )
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: manager)


class _RecordingWebSocket:
    connected = True

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    async def send_event(self, event: dict[str, object]) -> bool:
        self.events.append(event)
        return True


class _AckingWebSocket:
    def __init__(self, client: WebSocketClient, response: object) -> None:
        self.client = client
        self.response = response
        self.frames: list[dict[str, object]] = []

    async def send(self, raw: str) -> None:
        frame = json.loads(raw)
        assert isinstance(frame, dict)
        self.frames.append(frame)
        response = self.response(frame) if callable(self.response) else self.response
        if response is not None:
            await self.client._handle_message(response)


def _runtime_event() -> dict[str, object]:
    event: dict[str, object] = build_teamspace_envelope(
        event_id="01KZT032DAEMONACK000000001",
        event_type="WPStatusChanged",
        aggregate_id="WP08",
        aggregate_type="WorkPackage",
        build_id="build-1",
        payload={
            "wp_id": "WP08",
            "from_lane": "planned",
            "to_lane": "in_progress",
            "actor": "agent",
        },
        node_id="node-1",
        lamport_clock=1,
        causation_id=None,
        correlation_id="01KZT032DAEMONACK000000001",
        timestamp="2026-08-11T12:00:00+00:00",
        project_uuid=PROJECT_B,
        project_slug="private-engagement",
        repo_slug="private/project",
    ).model_dump()
    event.update(
        team_slug="teamspace-1",
        git_branch="develop",
        head_commit_sha="a" * 40,
        drain_blocked_reason=None,
    )
    return event


def _close_runtime_loop(
    loop: asyncio.AbstractEventLoop,
    loop_thread: threading.Thread,
) -> None:
    """Drain the test loop's executor before the leak guard snapshots threads."""
    asyncio.run_coroutine_threadsafe(loop.shutdown_default_executor(), loop).result(timeout=5)
    loop.call_soon_threadsafe(loop.stop)
    loop_thread.join(timeout=2)
    assert not loop_thread.is_alive()
    loop.close()


@pytest.mark.parametrize(
    ("status", "expected", "attempt_state", "outcome"),
    [
        ("accepted", True, "succeeded", "delivered"),
        ("duplicate", True, "succeeded", "duplicate"),
        ("rejected", False, "refused", "refused"),
    ],
)
def test_runtime_publish_waits_for_exact_event_ack_and_records_full_disclosure(
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    expected: bool,
    attempt_state: str,
    outcome: str,
) -> None:
    store = _admit_project(PROJECT_B)
    _install_current_audience(monkeypatch)
    client = WebSocketClient()
    client.connected = True

    def response(frame: dict[str, object]) -> dict[str, object]:
        if status == "rejected":
            return {
                "type": "error",
                "event_id": frame["event_id"],
                "status": "rejected",
                "error_category": "project_not_admitted",
                "retryable": False,
            }
        return {"type": "ack", "event_id": frame["event_id"], "status": status}

    websocket = _AckingWebSocket(client, response)
    client.ws = cast(Any, websocket)
    runtime = SyncRuntime()
    runtime.started = True
    runtime.ws_client = client
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    runtime._async_loop = loop
    event = _runtime_event()

    try:
        assert runtime.publish_event(event) is expected
    finally:
        _close_runtime_loop(loop, loop_thread)

    assert len(websocket.frames) == 1
    wire = websocket.frames[0]
    assert wire["project_uuid"] == PROJECT_B
    assert wire["admission_generation"] == 1
    assert wire["binding_audience"] == "private-teamspace:teamspace-1"
    with store.unit_of_work() as unit:
        attempt = unit.execute(
            "SELECT state, epoch_id, consent_generation, target_generation, admission_generation, binding_audience FROM delivery_attempts"
        ).fetchone()
        result = unit.execute("SELECT outcome, terminal_refusal_category FROM delivery_results").fetchone()
    assert attempt == (
        attempt_state,
        1,
        1,
        4,
        "1",
        "private-teamspace:teamspace-1",
    )
    assert result == (
        outcome,
        "project_not_admitted" if status == "rejected" else None,
    )


@pytest.mark.parametrize("response_kind", ["mismatch", "timeout"])
def test_runtime_publish_ack_mismatch_or_timeout_stays_unknown_without_replay(
    monkeypatch: pytest.MonkeyPatch,
    response_kind: str,
) -> None:
    store = _admit_project(PROJECT_B)
    _install_current_audience(monkeypatch)
    client = WebSocketClient()
    client.connected = True
    client.ACK_TIMEOUT_SECONDS = 0.01
    response = {"type": "ack", "event_id": "foreign-event", "status": "accepted"} if response_kind == "mismatch" else None
    websocket = _AckingWebSocket(client, response)
    client.ws = cast(Any, websocket)
    runtime = SyncRuntime(ws_client=client, started=True)
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    runtime._async_loop = loop

    try:
        assert runtime.publish_event(_runtime_event()) is False
        assert runtime.publish_event(_runtime_event()) is False
    finally:
        _close_runtime_loop(loop, loop_thread)

    assert len(websocket.frames) == 1
    with store.unit_of_work() as unit:
        assert unit.execute("SELECT state FROM delivery_attempts").fetchone() == ("unknown",)
        assert unit.execute("SELECT outcome FROM delivery_results").fetchone() is None


def test_runtime_publish_withholds_current_account_team_mismatch_before_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _admit_project(PROJECT_B)
    _install_current_audience(monkeypatch, account="other-account", team="other-team")
    runtime = SyncRuntime()
    websocket = _RecordingWebSocket()
    runtime.ws_client = cast(Any, websocket)
    runtime._async_loop = asyncio.new_event_loop()

    try:
        assert runtime.publish_event({"project_uuid": PROJECT_B, "event_id": "evt-b"}) is False
    finally:
        runtime._async_loop.close()

    assert websocket.events == []
    with store.unit_of_work() as unit:
        assert unit.execute("SELECT COUNT(*) FROM delivery_attempts").fetchone()[0] == 0


def test_runtime_attach_emitter_never_injects_raw_websocket() -> None:
    class _Emitter:
        ws_client: object | None = None

        @staticmethod
        def _get_identity() -> None:
            return None

    runtime = SyncRuntime()
    runtime.ws_client = cast(Any, _RecordingWebSocket())
    emitter = _Emitter()

    runtime.attach_emitter(cast(Any, emitter))

    assert emitter.ws_client is None
