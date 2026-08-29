"""Integration coverage for the negotiated-admission fix on ``sync now`` (#3620, WP1).

Drives :func:`specify_cli.sync.sync_dispatch_exec._run_event_sync_dispatch` —
the SOLE event-delivery path — through the REAL entry point: real
``ProjectSyncStore``, real checkout routing, real consent + admission SQL, a
real journal event, and the real WP07 dispatcher. Only the outermost HTTP POST
is faked (a deterministic ``_poster`` double injected at
``DefaultReceiverFactory.build_teamspace`` — no network, no
``requests``/``urlopen`` reachable).

Before #3620, ``AC-1``/``AC-2`` were unreachable: a consented project's
``delivery_target`` was always ``None`` (Gate A), so ``sync now`` never
attempted delivery against the deployed (non-strict) SaaS. This module proves
the negotiated-admission fix restores it end to end.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from kernel.clock import now_utc, timedelta

from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands.sync import _AdmissionGatedNoDelivery, _EventSyncScope
from specify_cli.delivery.config import DefaultReceiverFactory
from specify_cli.delivery.dispatcher import DispatchFailure, DispatchSummary
from specify_cli.delivery.receivers import TeamspaceReceiver
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.admission_negotiation import STRICT_ADMISSION_ENV_VAR, reset_strict_admission_cache
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-000000000020"
TEAM_SLUG = "private-teamspace-1"


class _FakeHttpResponse:
    def __init__(self, status_code: int, body: dict[str, Any]) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> dict[str, Any]:
        return self._body


def _success_poster(event_id: str):
    """A deterministic, network-free ``HttpPoster`` double: one event, one success."""

    def _poster(url: str, *, data: bytes, headers: dict[str, str], timeout: float) -> _FakeHttpResponse:
        # Sanity-check the request actually carries the seeded event, so a
        # future dispatcher change that silently drops it reds this test
        # instead of the double papering over it.
        import gzip

        body = json.loads(gzip.decompress(data).decode("utf-8"))
        sent_ids = {event["event_id"] for event in body["events"]}
        assert sent_ids == {event_id}
        return _FakeHttpResponse(200, {"results": [{"event_id": event_id, "status": "success"}]})

    return _poster


def _session() -> StoredSession:
    now = now_utc()
    team = Team(id="team-private-1", name="Private", role="owner", is_private_teamspace=True)
    return StoredSession(
        user_id="user-1",
        email="operator@example.com",
        name="Operator",
        teams=[team],
        default_team_id=team.id,
        access_token="access-token",
        refresh_token="refresh-token",
        session_id="session-1",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=None,
        scope="offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="device_code",
    )


class _FakeTokenManager:
    is_authenticated = True

    def __init__(self, session: StoredSession) -> None:
        self._session = session

    def get_current_session(self) -> StoredSession:
        return self._session

    async def get_access_token(self) -> str:
        return self._session.access_token


def _write_repo_config(repo_root: Path, *, project_uuid: str) -> None:
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  uuid: {project_uuid}",
                "  slug: spec-kitty-local",
                "  node_id: node12345678",
                "  repo_slug: acme/spec-kitty",
                "  build_id: build-123",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _seed_event(store: ProjectSyncStore, *, event_id: str, project_uuid: str) -> None:
    payload = {"event_id": event_id, "event_type": "mission.updated"}
    with store.unit_of_work() as unit:
        EventJournal(unit, store.layout_generation()).append(
            Event(
                event_id=event_id,
                event_type="mission.updated",
                payload=json.dumps(payload).encode("utf-8"),
                occurred_at="2026-08-21T00:00:00+00:00",
                created_at="2026-08-21T00:00:01+00:00",
                project_uuid=project_uuid,
            )
        )


@pytest.fixture(autouse=True)
def _isolated_strict_admission_cache() -> None:
    reset_strict_admission_cache()
    yield
    reset_strict_admission_cache()


def _prepare_consented_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    event_id: str,
) -> ProjectSyncStore:
    """Real repo checkout + real consent + one real journal event."""
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    _write_repo_config(repo_root, project_uuid=PROJECT)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    monkeypatch.chdir(repo_root)

    record_project_opt_in(PROJECT, actor="wp1-integration-test")
    store = ProjectSyncStore(PROJECT)
    _seed_event(store, event_id=event_id, project_uuid=PROJECT)
    return store


def _protocol_mismatch_poster(
    *,
    error_code: str = "client-too-new",
    guidance: str = "Pin spec-kitty to a supported release or wait for the SaaS rollout.",
):
    """A network-free ``HttpPoster`` double answering the server's 412 handshake body (#1553)."""

    def _poster(url: str, *, data: bytes, headers: dict[str, str], timeout: float) -> _FakeHttpResponse:
        return _FakeHttpResponse(
            412,
            {
                "ok": False,
                "error_code": error_code,
                "error_description": "Client protocol version is outside the supported range.",
                "sync_protocol": {"contract_version": "sync-protocol-handshake.v1", "upgrade_guidance": guidance},
            },
        )

    return _poster


def _wire_delivery_doubles(monkeypatch: pytest.MonkeyPatch, *, event_id: str, poster: Any = None) -> None:
    """Real routing/store/dispatcher; only the outermost HTTP POST is faked."""
    manager = _FakeTokenManager(_session())
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: manager)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr(
        "specify_cli.cli.commands.sync._current_event_sync_scope",
        lambda: _EventSyncScope(team_slug=TEAM_SLUG),
    )

    def _fake_build_teamspace(self: DefaultReceiverFactory, *, resolved_server_url: str) -> TeamspaceReceiver:
        return TeamspaceReceiver(
            resolved_server_url=resolved_server_url,
            auth_token=self.teamspace_auth_token,
            poster=_success_poster(event_id) if poster is None else poster,
        )

    monkeypatch.setattr(DefaultReceiverFactory, "build_teamspace", _fake_build_teamspace)


class TestNegotiatedAdmissionRestoresDelivery:
    """AC-1/AC-2: a consented, non-strict-server project delivers via ``sync now``."""

    def test_consented_nonstrict_project_delivers(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        event_id = "evt-3620-happy-path"
        _prepare_consented_checkout(tmp_path, monkeypatch, event_id=event_id)
        _wire_delivery_doubles(monkeypatch, event_id=event_id)

        from specify_cli.sync.sync_dispatch_exec import _run_event_sync_dispatch

        result = _run_event_sync_dispatch()

        # A plain DispatchSummary (not _AdmissionGatedNoDelivery, not None)
        # structurally proves neither gate fired — Gate A (delivery_target is
        # None) nor Gate B (receiver gate blocked) — so "admission_not_current"
        # was never printed (Finding 2 territory) and delivery was attempted.
        assert isinstance(result, DispatchSummary)
        assert result.selected == 1
        assert result.delivered == 1
        assert result.rejected == 0
        assert result.transient == 0
        assert result.terminal_failed == 0

    def test_repeated_dispatch_does_not_duplicate_admission(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-3: a second ``sync now`` does not re-mint or re-admit."""
        event_id = "evt-3620-idempotent"
        store = _prepare_consented_checkout(tmp_path, monkeypatch, event_id=event_id)
        _wire_delivery_doubles(monkeypatch, event_id=event_id)

        from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
        from specify_cli.sync.sync_dispatch_exec import _run_event_sync_dispatch

        first = _run_event_sync_dispatch()
        assert isinstance(first, DispatchSummary)
        assert first.delivered == 1

        with store.unit_of_work() as unit:
            targets_after_first = ProjectDeliveryTargetRegistry(store).list_targets(unit)
        assert len(targets_after_first) == 1

        # Nothing left to deliver, but the runtime open (and its
        # maybe_admit_locally call) still runs; it must stay a no-op.
        second = _run_event_sync_dispatch()
        assert isinstance(second, DispatchSummary)
        assert second.selected == 0

        with store.unit_of_work() as unit:
            targets_after_second = ProjectDeliveryTargetRegistry(store).list_targets(unit)
        assert targets_after_second == targets_after_first


class TestStrictAdmissionStaysGated:
    """AC-4: an explicit strict signal keeps the gate closed (no local admission)."""

    def test_strict_signal_yields_admission_gated_marker(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        event_id = "evt-3620-strict"
        _prepare_consented_checkout(tmp_path, monkeypatch, event_id=event_id)
        _wire_delivery_doubles(monkeypatch, event_id=event_id)
        monkeypatch.setenv(STRICT_ADMISSION_ENV_VAR, "1")

        from specify_cli.sync.sync_dispatch_exec import _run_event_sync_dispatch

        result = _run_event_sync_dispatch()

        assert isinstance(result, _AdmissionGatedNoDelivery)
        assert result.reason == "admission_not_current"
        assert result.summary.delivered == 0


class TestProtocolMismatchHaltsAndGuides:
    """#1553: an HTTP 412 halts the pass, parks nothing, and prints the server's guidance."""

    def test_412_prints_server_guidance_and_retains_event(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from rich.console import Console

        event_id = "evt-1553-protocol-skew"
        store = _prepare_consented_checkout(tmp_path, monkeypatch, event_id=event_id)
        _wire_delivery_doubles(monkeypatch, event_id=event_id, poster=_protocol_mismatch_poster())
        recorder = Console(record=True, width=400, soft_wrap=True)
        monkeypatch.setattr("specify_cli.cli.commands.sync.console", recorder)

        from specify_cli.sync.sync_dispatch_exec import _run_event_sync_dispatch

        result = _run_event_sync_dispatch()

        assert isinstance(result, DispatchSummary)
        assert result.selected == 1
        assert result.transient == 1
        assert result.terminal_failed == 0
        assert result.delivered == 0

        rendered = recorder.export_text()
        # The command that hit the 412 surfaces the server's own guidance (for a
        # too-NEW client that is "pin", not "upgrade") — not a hardcoded pip line.
        assert "Pin spec-kitty to a supported release or wait for the SaaS rollout." in rendered
        assert "412" in rendered
        assert "pip install" not in rendered

        # The journal row is retained and still selectable: not parked.
        from specify_cli.delivery.ledger import SqliteDeliveryLedger

        with store.unit_of_work() as unit:
            ledger = SqliteDeliveryLedger(unit, store.layout_generation())
            row = ledger.get(event_id, result.target_id or "")
        assert row is not None
        assert row.status == "failed_transient"

    def test_mixed_local_failure_and_412_halts_before_next_batch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A local terminal row must not hide a correlated 412 halt signal."""
        mixed = DispatchSummary(
            target_id="target",
            selected=2,
            delivered=0,
            duplicate=0,
            pending=0,
            rejected=0,
            transient=1,
            terminal_failed=1,
            failures=(
                DispatchFailure(
                    event_id="remote",
                    outcome="transient",
                    http_status=412,
                    error="Pin this CLI.",
                ),
                DispatchFailure(event_id="local", outcome="terminal_failed"),
            ),
            retryable_event_ids=("remote",),
        )
        calls = 0

        def _dispatch_once(**_: object) -> DispatchSummary:
            nonlocal calls
            calls += 1
            if calls > 1:
                pytest.fail("batch driver continued after HTTP 412")
            return mixed

        monkeypatch.setattr("specify_cli.delivery.dispatcher.dispatch", _dispatch_once)
        monkeypatch.setattr("specify_cli.cli.commands.sync._EVENT_SYNC_DISPATCH_BATCH_LIMIT", 2)

        from specify_cli.sync.sync_dispatch_exec import _run_dispatch_batches

        result = _run_dispatch_batches(SimpleNamespace(store=object(), context=object()), object(), object())

        assert calls == 1
        assert result.transient == 1
        assert result.terminal_failed == 1
