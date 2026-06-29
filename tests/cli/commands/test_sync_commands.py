"""WP12 — observable-output tests for the event-sync ``sync`` CLI wiring.

These tests pin the **user-observable** behaviour of the new wiring (NFR-001):
each subcommand is invoked through the Typer ``CliRunner`` and the assertions
look at printed output **and** the resulting on-disk journal / delivery-ledger
state — never the internal call order or which domain function fired when.

The wiring is THIN: every piece of logic lives in a domain module (WP07
dispatcher, WP09 config, WP11 status-report/retention, WP01 target authority).
A localhost :class:`StubReceiver` (WP06) stands in for the network so the suite
needs no Teamspace credentials (SC-005).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_command
from specify_cli.cli.commands.sync import app
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import (
    DeliveryResult,
    GateKind,
    OutboundEvent,
    ReceiverGate,
    StubReceiver,
)
from specify_cli.delivery.status_report import ADDITIVE_SECTION_KEYS
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal, resolve_journal_path
from specify_cli.event_journal.models import Event
from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR


pytestmark = pytest.mark.fast

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin every global path under ``tmp_path`` so no real state is touched."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.delenv(SAAS_SYNC_ENV_VAR, raising=False)
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    # Journals are cached per-path across tests; clear so each test's isolated
    # home starts from a clean instance.
    from specify_cli.event_journal.journal import reset_journal_cache

    reset_journal_cache()
    return tmp_path


class _OkPreflight:
    ok = True

    def render(self, console: object) -> None:  # pragma: no cover - never called when ok
        return None


def _populate_journal(count: int = 3) -> EventJournal:
    """Append *count* JSON-object events to the CLI-resolved journal."""
    journal = EventJournal(resolve_journal_path())
    for index in range(count):
        journal.append(
            Event(
                event_id=f"evt-{index}",
                event_type="mission.updated",
                payload=json.dumps({"n": index}).encode("utf-8"),
                occurred_at="2026-06-29T00:00:00+00:00",
                created_at=f"2026-06-29T00:00:0{index}+00:00",
            )
        )
    return journal


def _enable_now_machinery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralise the legacy ``sync now`` preflight/queue/gate so the test can
    exercise the additive event-sync dispatch path in isolation."""
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        sync_command, "enforce_teamspace_mission_state_ready", lambda **_: None
    )
    monkeypatch.setattr(
        "specify_cli.sync.preflight.run_preflight", lambda **_: _OkPreflight()
    )

    class _EmptyQueue:
        def size(self) -> int:
            return 0

    class _Service:
        queue = _EmptyQueue()

        def drain_body_uploads_only(self) -> None:
            # Body-ONLY drain: the new ``sync now`` flushes attachments via this
            # entry point and never runs the destructive legacy event drain.
            return None

    monkeypatch.setattr(
        "specify_cli.sync.background.get_sync_service", lambda: _Service()
    )


def _patch_stub_receiver(monkeypatch: pytest.MonkeyPatch) -> list[StubReceiver]:
    """Make the CLI resolve a fresh :class:`StubReceiver` per dispatch; return
    the list of stubs created (so a test can inspect what each received)."""
    created: list[StubReceiver] = []

    def _factory(_target: object, _config: object, **_: object) -> StubReceiver:
        stub = StubReceiver()
        created.append(stub)
        return stub

    monkeypatch.setattr(sync_command, "_resolve_active_receiver", _factory)
    return created


def _open_ledger() -> SqliteDeliveryLedger:
    ledger_path = sync_command._ledger_db_path()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteDeliveryLedger(str(ledger_path))


def _open_registry() -> SqliteDeliveryTargetRegistry:
    registry_path = sync_command._registry_db_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteDeliveryTargetRegistry(str(registry_path))


def _set_server_url(url: str) -> None:
    from specify_cli.sync.config import SyncConfig

    SyncConfig().set_server_url(url)


# ---------------------------------------------------------------------------
# T071 — sync now -> dispatcher (non-destructive ledger delivery)
# ---------------------------------------------------------------------------


def test_sync_now_dispatches_and_retains_journal(monkeypatch: pytest.MonkeyPatch) -> None:
    """``sync now`` delivers via the dispatcher, writes ledger rows, and keeps
    every journal payload (success is non-destructive — FR-001)."""
    _enable_now_machinery(monkeypatch)
    stubs = _patch_stub_receiver(monkeypatch)
    journal = _populate_journal(3)

    result = runner.invoke(app, ["now"])
    assert result.exit_code == 0, result.output
    assert "delivered 3" in result.output

    # Journal payloads were NOT deleted on success.
    assert journal.count() == 3
    # The stub actually received all three events.
    assert set(stubs[-1].received_event_ids()) == {"evt-0", "evt-1", "evt-2"}
    # Ledger recorded terminal-success delivery for each event.
    ledger = _open_ledger()
    for index in range(3):
        assert ledger.delivered_anywhere(f"evt-{index}") is True


def test_sync_now_posts_retained_events_in_1000_event_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Large retained sets are chunked before POSTing to a receiver."""
    _enable_now_machinery(monkeypatch)

    class _BatchSpyReceiver(StubReceiver):
        def __init__(self) -> None:
            super().__init__()
            self.batch_sizes: list[int] = []

        def deliver(self, batch: Sequence[OutboundEvent]) -> Sequence[DeliveryResult]:
            events = list(batch)
            self.batch_sizes.append(len(events))
            return super().deliver(events)

    receiver = _BatchSpyReceiver()
    monkeypatch.setattr(
        sync_command,
        "_resolve_active_receiver",
        lambda *_args, **_kwargs: receiver,
    )
    journal = _populate_journal(1001)

    result = runner.invoke(app, ["now"])
    assert result.exit_code == 0, result.output
    assert receiver.batch_sizes == [1000, 1]
    assert journal.count() == 1001


def test_sync_now_empty_journal_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """``sync now`` with nothing captured prints a zero summary and exits 0."""
    _enable_now_machinery(monkeypatch)
    _patch_stub_receiver(monkeypatch)

    result = runner.invoke(app, ["now"])
    assert result.exit_code == 0, result.output
    assert "delivered 0" in result.output


def test_sync_now_gate_block_does_not_call_receiver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsatisfied receiver gates block before any POST/deliver call."""
    _enable_now_machinery(monkeypatch)
    _populate_journal(1)

    class _AuthGatedReceiver(StubReceiver):
        delivered = False

        def gates(self) -> tuple[ReceiverGate, ...]:
            return (ReceiverGate(GateKind.AUTH),)

        def deliver(self, batch: Sequence[OutboundEvent]) -> Sequence[DeliveryResult]:
            self.delivered = True
            return super().deliver(batch)

    receiver = _AuthGatedReceiver()
    monkeypatch.setattr(sync_command, "_event_sync_access_token", lambda: "")
    monkeypatch.setattr(
        sync_command,
        "_resolve_active_receiver",
        lambda *_args, **_kwargs: receiver,
    )

    result = runner.invoke(app, ["now"])
    assert result.exit_code in (1, 4), result.output
    assert "Event sync gated" in result.output
    assert receiver.delivered is False


def test_sync_now_strict_fails_when_retained_work_dispatch_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retained journal work cannot disappear into a strict success on infra failure."""
    _enable_now_machinery(monkeypatch)
    _populate_journal(1)
    monkeypatch.setattr(sync_command, "_run_event_sync_dispatch", lambda: None)

    result = runner.invoke(app, ["now"])
    assert result.exit_code == 1, result.output


def test_sync_now_success_path_runs_dispatch_and_body_drain(monkeypatch: pytest.MonkeyPatch) -> None:
    """``sync now`` delivers via the dispatcher ALONE and flushes body uploads.

    The destructive legacy offline-queue event drain is retired: the command
    must NOT call ``service.sync_now()`` (which double-POSTed every event the
    dispatcher also delivers — the dual-drain P1 defect), and instead drains
    body uploads via the body-ONLY entry point."""
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        sync_command, "enforce_teamspace_mission_state_ready", lambda **_: None
    )
    monkeypatch.setattr(
        "specify_cli.sync.preflight.run_preflight", lambda **_: _OkPreflight()
    )

    drained = {"body": False}

    class _Queue:
        def size(self) -> int:
            return 0

    class _Service:
        queue = _Queue()

        def sync_now(self, *_, **__):  # pragma: no cover - must never be called
            raise AssertionError("legacy destructive event drain must not run")

        def drain_body_uploads_only(self) -> None:
            drained["body"] = True

    monkeypatch.setattr(
        "specify_cli.sync.background.get_sync_service", lambda: _Service()
    )
    stubs = _patch_stub_receiver(monkeypatch)
    journal = _populate_journal(2)

    result = runner.invoke(app, ["now"])
    assert result.exit_code == 0, result.output
    # The single event-delivery path (dispatcher) ran.
    assert "Event sync" in result.output
    assert "delivered 2" in result.output
    # Body uploads still drained (the body-ONLY entry point).
    assert drained["body"] is True
    # Event journal delivered + retained (non-destructive).
    assert journal.count() == 2
    assert set(stubs[-1].received_event_ids()) == {"evt-0", "evt-1"}
    assert _open_ledger().delivered_anywhere("evt-0") is True


# ---------------------------------------------------------------------------
# T071/FR-005 — sync server <url> then replay to a fresh target (US1)
# ---------------------------------------------------------------------------


def test_server_switch_replays_retained_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting a new server re-delivers the same retained events to it (FR-005)."""
    _enable_now_machinery(monkeypatch)
    stubs = _patch_stub_receiver(monkeypatch)
    journal = _populate_journal(3)

    _set_server_url("https://target-a.example")
    first = runner.invoke(app, ["now"])
    assert first.exit_code == 0, first.output
    assert set(stubs[-1].received_event_ids()) == {"evt-0", "evt-1", "evt-2"}

    # Switch the active target; the same retained events re-select for B.
    _set_server_url("https://target-b.example")
    second = runner.invoke(app, ["now"])
    assert second.exit_code == 0, second.output
    assert "delivered 3" in second.output
    assert set(stubs[-1].received_event_ids()) == {"evt-0", "evt-1", "evt-2"}

    # Still fully retained after BOTH drains.
    assert journal.count() == 3


def test_sync_server_no_arg_shows_url() -> None:
    """Backward-compat: ``sync server`` with no argument still prints the URL."""
    _set_server_url("https://shown.example")
    result = runner.invoke(app, ["server"])
    assert result.exit_code == 0, result.output
    assert "Server URL" in result.output
    assert "https://shown.example" in result.output


# ---------------------------------------------------------------------------
# T072 — sync status --check --json carries legacy fields PLUS 7 sections
# ---------------------------------------------------------------------------


def test_status_check_json_is_additive(monkeypatch: pytest.MonkeyPatch) -> None:
    """``sync status --check --json`` keeps the legacy top-level fields and adds
    the seven WP11 sections (FR-009, FR-019, NFR-006)."""
    _populate_journal(2)

    result = runner.invoke(app, ["status", "--check", "--json"])
    assert result.exit_code in (0, 2), result.output
    payload = json.loads(result.output.strip())

    # Legacy top-level fields preserved (backward-compat).
    for legacy_key in ("ok", "exit_code", "foreground", "daemon_owner_record", "active_queue", "legacy_queue", "mismatches", "orphan_records"):
        assert legacy_key in payload, legacy_key

    # The seven additive sections are present.
    for section in ADDITIVE_SECTION_KEYS:
        assert section in payload, section

    # Sections are populated from the journal, not recomputed in the CLI.
    assert payload["event_journal"]["retained_event_count"] == 2
    # Terminology Canon: no feature* keys anywhere.
    assert "feature" not in json.dumps(payload).lower().replace("feature_flags", "")


def test_status_check_json_does_not_create_event_sync_databases() -> None:
    """Read-only status keeps absent event-sync stores absent."""
    from specify_cli.paths import get_runtime_root

    base = get_runtime_root().base
    result = runner.invoke(app, ["status", "--check", "--json"])
    assert result.exit_code in (0, 2), result.output
    assert not (base / "event_journal").exists()
    assert not (base / "delivery").exists()


def test_status_human_view_shows_mode() -> None:
    """``sync status`` surfaces the active event-sync mode (US2 observability)."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "Event Sync" in result.output
    assert "TEAMSPACE" in result.output  # default mode


# ---------------------------------------------------------------------------
# T073 — sync gc / sync archive are explicit-only and preserve ledger history
# ---------------------------------------------------------------------------


def test_sync_gc_purges_only_delivered(monkeypatch: pytest.MonkeyPatch) -> None:
    """``sync gc`` purges payloads delivered to ALL known targets, skips those
    still owed to a known target, and keeps the ledger (FR-005 / FR-010).

    ``gc`` now derives its target universe from the registry
    (``known_target_ids``): a payload is reclaimable only once it has a
    terminal-success delivery to every registered target."""
    journal = _populate_journal(3)
    # Register the single known target so gc has a non-empty target universe.
    registry = _open_registry()
    target = registry.register(
        url="https://gc-target.example", team_slug=None, user_email=None
    )
    registry.close()
    # Mark evt-0 and evt-1 delivered to that known target; evt-2 stays undelivered.
    ledger = _open_ledger()
    ledger.record_success("evt-0", target.target_id)
    ledger.record_success("evt-1", target.target_id)
    ledger.close()

    result = runner.invoke(app, ["gc"])
    assert result.exit_code == 0, result.output
    assert "purged 2" in result.output
    assert "skipped 1" in result.output

    # Delivered payloads gone; undelivered payload retained (durability).
    assert journal.read_by_id("evt-0") is None
    assert journal.read_by_id("evt-1") is None
    assert journal.read_by_id("evt-2") is not None
    # Ledger history survives the purge.
    reopened = _open_ledger()
    assert reopened.delivered_anywhere("evt-0") is True


def test_sync_gc_purges_nothing_without_known_targets() -> None:
    """With no registered targets the universe is empty, so gc reclaims nothing
    (the safe purge-nothing default — it cannot establish full delivery)."""
    journal = _populate_journal(2)
    ledger = _open_ledger()
    ledger.record_success("evt-0", "phantom-target")
    ledger.close()

    result = runner.invoke(app, ["gc"])
    assert result.exit_code == 0, result.output
    assert "purged 0" in result.output
    # Nothing was deleted because no known target universe exists.
    assert journal.read_by_id("evt-0") is not None
    assert journal.read_by_id("evt-1") is not None


def test_sync_archive_is_nondestructive() -> None:
    """``sync archive`` stamps the archive marker but deletes no bytes (FR-010)."""
    journal = _populate_journal(3)

    result = runner.invoke(app, ["archive"])
    assert result.exit_code == 0, result.output
    assert "archived 3" in result.output

    # Nothing deleted — every row still present, now archived.
    assert journal.count() == 3
    for index in range(3):
        stored = journal.read_by_id(f"evt-{index}")
        assert stored is not None and stored.archived_at is not None


# ---------------------------------------------------------------------------
# T074 — sync mode -> WP09 EventSyncConfig (A7 operator surface)
# ---------------------------------------------------------------------------


def test_sync_mode_show_default() -> None:
    """``sync mode`` with no argument prints the current (default) mode."""
    result = runner.invoke(app, ["mode"])
    assert result.exit_code == 0, result.output
    assert "TEAMSPACE" in result.output


def test_sync_mode_set_and_persist() -> None:
    """Setting a mode persists it; a subsequent read reflects it (round-trip)."""
    set_result = runner.invoke(app, ["mode", "local_retention"])
    assert set_result.exit_code == 0, set_result.output
    assert "LOCAL_RETENTION" in set_result.output

    show = runner.invoke(app, ["mode"])
    assert show.exit_code == 0, show.output
    assert "LOCAL_RETENTION" in show.output


def test_sync_mode_invalid_token_rejected_by_wp09() -> None:
    """An unknown mode token is refused through WP09 validation, not the CLI."""
    result = runner.invoke(app, ["mode", "not-a-mode"])
    assert result.exit_code == 1, result.output
    assert "not-a-mode" in result.output


def test_sync_mode_external_requires_endpoint() -> None:
    """``EXTERNAL_RECEIVER`` with no endpoint surfaces WP09's error."""
    result = runner.invoke(app, ["mode", "external_receiver"])
    assert result.exit_code == 1, result.output
    assert "endpoint" in result.output.lower()


def test_local_retention_mode_attempts_no_delivery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Under LOCAL_RETENTION, ``sync now`` journals but does not deliver."""
    _enable_now_machinery(monkeypatch)
    # Do NOT patch the receiver: the real resolver returns None for delivery NONE.
    runner.invoke(app, ["mode", "local_retention"])
    _populate_journal(2)

    result = runner.invoke(app, ["now"])
    assert result.exit_code == 0, result.output
    assert "retention only" in result.output.lower()
    # No ledger delivery rows were written.
    ledger = _open_ledger()
    assert ledger.delivered_anywhere("evt-0") is False


def test_opt_out_surfaces_c008_note() -> None:
    """Selecting OPT_OUT surfaces the C-008 fail-closed note (never silent drop)."""
    result = runner.invoke(app, ["mode", "opt_out"])
    assert result.exit_code == 0, result.output
    assert "OPT_OUT" in result.output
    assert "C-008" in result.output


# ---------------------------------------------------------------------------
# Receiver resolution (unit) — covers the real _resolve_active_receiver body
# ---------------------------------------------------------------------------


def test_resolve_active_receiver_per_mode() -> None:
    """The real receiver resolver routes each mode through WP09 correctly."""
    from specify_cli.delivery.config import EventSyncConfig, Mode
    from specify_cli.delivery.receivers import ExternalReceiver, TeamspaceReceiver

    class _Target:
        resolved_server_url = "https://t.example"

    teamspace = sync_command._resolve_active_receiver(
        _Target(), EventSyncConfig.from_mode(Mode.TEAMSPACE)
    )
    assert isinstance(teamspace, TeamspaceReceiver)

    external = sync_command._resolve_active_receiver(
        _Target(),
        EventSyncConfig.from_mode(Mode.EXTERNAL_RECEIVER, external_endpoint="https://x.example/e"),
    )
    assert isinstance(external, ExternalReceiver)

    local = sync_command._resolve_active_receiver(
        _Target(), EventSyncConfig.from_mode(Mode.LOCAL_RETENTION)
    )
    assert local is None


# ---------------------------------------------------------------------------
# Focused branch coverage for the thin event-sync helpers
# ---------------------------------------------------------------------------


def _captured_console(monkeypatch: pytest.MonkeyPatch) -> StringIO:
    buf = StringIO()
    monkeypatch.setattr(sync_command, "console", Console(file=buf, force_terminal=False))
    return buf


def test_access_token_authenticated_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """The access-token helper returns the live token, or '' on absence/error."""

    class _AuthedTM:
        is_authenticated = True

        async def get_access_token(self) -> str:
            return "tok-123"

    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: _AuthedTM())
    assert sync_command._event_sync_access_token() == "tok-123"

    class _UnauthedTM:
        is_authenticated = False

    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: _UnauthedTM())
    assert sync_command._event_sync_access_token() == ""

    def _boom() -> object:
        raise RuntimeError("no auth")

    monkeypatch.setattr("specify_cli.auth.get_token_manager", _boom)
    assert sync_command._event_sync_access_token() == ""


def test_read_event_sync_table_handles_corrupt_config() -> None:
    """A corrupt config.toml degrades to an empty event-sync table."""
    path = sync_command._event_sync_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("this is = = not valid toml ][", encoding="utf-8")
    assert sync_command._read_event_sync_table() == {}


def test_load_event_sync_config_falls_back_on_bad_token() -> None:
    """A persisted but unknown mode token falls back to TEAMSPACE, never raises."""
    from specify_cli.delivery.config import Mode

    path = sync_command._event_sync_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('[event_sync]\nmode = "bogus-mode"\n', encoding="utf-8")
    assert sync_command._load_event_sync_config().mode is Mode.TEAMSPACE


def test_mode_external_persists_endpoint_over_existing_config() -> None:
    """EXTERNAL_RECEIVER set persists the endpoint and round-trips through load."""
    from specify_cli.delivery.config import Mode

    _set_server_url("https://present.example")  # ensure config.toml already exists
    result = runner.invoke(
        app, ["mode", "external_receiver", "--endpoint", "https://recv.example/e"]
    )
    assert result.exit_code == 0, result.output
    loaded = sync_command._load_event_sync_config()
    assert loaded.mode is Mode.EXTERNAL_RECEIVER
    assert loaded.external_endpoint == "https://recv.example/e"


def test_mode_set_over_corrupt_config_recovers() -> None:
    """Setting a mode over a corrupt config.toml recovers rather than raising."""
    from specify_cli.delivery.config import Mode

    path = sync_command._event_sync_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("= = corrupt ][", encoding="utf-8")

    result = runner.invoke(app, ["mode", "local_retention"])
    assert result.exit_code == 0, result.output
    assert sync_command._load_event_sync_config().mode is Mode.LOCAL_RETENTION


def test_open_active_body_queue_degrades_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure opening the body-upload queue yields None (section reports zeros)."""

    def _boom(*_: object, **__: object) -> object:
        raise RuntimeError("no queue")

    monkeypatch.setattr("specify_cli.sync.queue.OfflineQueue", _boom)
    assert sync_command._open_active_body_queue() is None


def test_run_event_sync_dispatch_noop_when_saas_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """With SaaS sync off, the dispatch is a clean no-op (no output, no raise)."""
    buf = _captured_console(monkeypatch)
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: False)
    sync_command._run_event_sync_dispatch()
    assert buf.getvalue() == ""


def test_run_event_sync_dispatch_degrades_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """An infrastructure failure prints a notice and never raises (NFR-006)."""
    buf = _captured_console(monkeypatch)
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: True)

    def _boom() -> object:
        raise RuntimeError("runtime down")

    monkeypatch.setattr(sync_command, "_open_event_sync_runtime", _boom)
    sync_command._run_event_sync_dispatch()  # must not raise
    assert "Event sync unavailable" in buf.getvalue()


def test_render_event_sync_status_survives_runtime_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """The status summary shows the mode even when the runtime cannot open."""
    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False)

    def _boom() -> object:
        raise RuntimeError("runtime down")

    monkeypatch.setattr(sync_command, "_open_event_sync_runtime", _boom)
    sync_command._render_event_sync_status(test_console)
    output = buf.getvalue()
    assert "Event Sync" in output
    assert "TEAMSPACE" in output


def test_render_event_sync_status_shows_gc_suggestion(monkeypatch: pytest.MonkeyPatch) -> None:
    """A GC suggestion from the report surfaces in the status summary."""
    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False)

    class _FakeRuntime:
        def close(self) -> None:
            return None

    monkeypatch.setattr(sync_command, "_open_event_sync_runtime", lambda: _FakeRuntime())
    monkeypatch.setattr(
        sync_command,
        "_event_sync_report",
        lambda base, runtime: {
            "event_journal": {"retained_event_count": 1, "gc_suggested": True},
            "delivery_ledger": {
                "delivered_current_target": 0,
                "delivered_previous_target": 0,
            },
            "terminal_failures": {"count": 0},
        },
    )
    sync_command._render_event_sync_status(test_console)
    assert "GC suggested" in buf.getvalue()


# ---------------------------------------------------------------------------
# WP12 P1 — status sections are ALWAYS present + migration conflicts surface
# ---------------------------------------------------------------------------


def test_status_check_json_keeps_sections_on_runtime_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the event-sync runtime cannot open, ``--check --json`` still emits all
    seven additive sections (in their empty/default shape) plus an error marker —
    a partial section set must never reach a consumer (FR-019, SC-010)."""

    def _boom() -> object:
        raise RuntimeError("runtime down")

    # Either seam raising must converge on the same fallback.
    monkeypatch.setattr(sync_command, "_open_event_sync_runtime", _boom)

    result = runner.invoke(app, ["status", "--check", "--json"])
    assert result.exit_code in (0, 2), result.output
    payload = json.loads(result.output.strip())

    for section in ADDITIVE_SECTION_KEYS:
        assert section in payload, section
    # The fallback marks itself so the partial-data cause is diagnosable.
    assert "event_sync_status_error" in payload
    # Default shapes are present (not None / not missing keys).
    assert payload["migration_conflicts"] == {
        "count": 0,
        "cleanup_blocked": False,
        "conflicts": [],
    }


def test_status_check_json_surfaces_migration_conflicts() -> None:
    """A recorded migration conflict surfaces in ``migration_conflicts`` with the
    cleanup-blocked flag set, sourced from the on-disk audit store (SC-011)."""
    from specify_cli.paths import get_runtime_root
    from specify_cli.sync.migrate_journal import (
        AUDIT_DB_NAME,
        MigrationAudit,
        MigrationConflict,
    )

    _populate_journal(1)  # ensure the runtime opens cleanly (happy path)

    audit_path = get_runtime_root().base / AUDIT_DB_NAME
    audit = MigrationAudit(audit_path)
    audit.record_conflict(
        MigrationConflict(
            event_id="evt-x",
            source_digest="legacy",
            existing_sha="aaa",
            incoming_sha="bbb",
            detail="divergent canonical payload for an existing event_id",
        )
    )
    audit.commit()
    audit.close()

    result = runner.invoke(app, ["status", "--check", "--json"])
    assert result.exit_code in (0, 2), result.output
    payload = json.loads(result.output.strip())

    conflicts = payload["migration_conflicts"]
    assert conflicts["count"] == 1
    assert conflicts["cleanup_blocked"] is True
    assert conflicts["conflicts"][0]["event_id"] == "evt-x"


# ---------------------------------------------------------------------------
# WP12 P1 — sync now is a SINGLE non-destructive event POST + body drain
# ---------------------------------------------------------------------------


def test_sync_now_posts_exactly_once_and_drains_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``sync now`` POSTs the batch endpoint exactly ONCE (no dual-drain) and
    still flushes body uploads via the body-ONLY entry point."""
    import gzip as _gzip

    from specify_cli.delivery.receivers import BATCH_ENDPOINT_PATH, TeamspaceReceiver

    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        sync_command, "enforce_teamspace_mission_state_ready", lambda **_: None
    )
    monkeypatch.setattr(
        "specify_cli.sync.preflight.run_preflight", lambda **_: _OkPreflight()
    )

    posts: list[str] = []

    class _Resp:
        status_code = 200

        def __init__(self, ids: list[str]) -> None:
            self._ids = ids

        def json(self) -> dict[str, object]:
            return {"results": [{"event_id": i, "status": "success"} for i in self._ids]}

    def _poster(url: str, *, data: bytes, headers: object, timeout: float) -> _Resp:
        posts.append(url)
        body = json.loads(_gzip.decompress(data).decode("utf-8"))
        return _Resp([event["event_id"] for event in body["events"]])

    receiver = TeamspaceReceiver(
        resolved_server_url="https://t.example", auth_token="tok", poster=_poster
    )
    monkeypatch.setattr(sync_command, "_event_sync_access_token", lambda: "tok")
    monkeypatch.setattr(
        sync_command,
        "_current_event_sync_scope",
        lambda: sync_command._EventSyncScope(team_slug="team"),
    )
    monkeypatch.setattr(sync_command, "_resolve_active_receiver", lambda *_, **__: receiver)

    drained = {"body": False}

    class _Queue:
        def size(self) -> int:
            return 0

    class _Service:
        queue = _Queue()

        def drain_body_uploads_only(self) -> None:
            drained["body"] = True

    monkeypatch.setattr(
        "specify_cli.sync.background.get_sync_service", lambda: _Service()
    )

    # The wire envelope is the event's own JSON payload (``event_id`` is carried
    # on the OutboundEvent, not the body), so embed it in the payload here so the
    # fake server can echo a per-event success result keyed on it.
    journal = EventJournal(resolve_journal_path(team_slug="team"))
    journal.append(
        Event(
            event_id="evt-solo",
            event_type="mission.updated",
            payload=json.dumps({"event_id": "evt-solo", "n": 1}).encode("utf-8"),
            occurred_at="2026-06-29T00:00:00+00:00",
            created_at="2026-06-29T00:00:00+00:00",
        )
    )

    result = runner.invoke(app, ["now"])
    assert result.exit_code == 0, result.output

    # Exactly ONE POST, to the batch endpoint (no legacy + dispatch double-POST).
    assert len(posts) == 1, posts
    assert posts[0].endswith(BATCH_ENDPOINT_PATH)
    # Body uploads still drained.
    assert drained["body"] is True
    assert "delivered 1" in result.output


# ---------------------------------------------------------------------------
# WP12 P1 — sync migrate has a production caller (queue.db -> journal)
# ---------------------------------------------------------------------------


def test_sync_migrate_imports_queue_db_into_journal() -> None:
    """``sync migrate`` lifts currently-queued legacy ``queue.db`` rows into the
    event journal and renders the migration result (the otherwise-dead WP10
    migration now has a production CLI caller)."""
    import sqlite3

    from specify_cli.paths import get_runtime_root

    base = get_runtime_root().base
    base.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(base / "queue.db"))
    conn.execute(
        "CREATE TABLE queue (id INTEGER PRIMARY KEY, event_id TEXT, "
        "event_type TEXT, data TEXT, timestamp INTEGER)"
    )
    conn.executemany(
        "INSERT INTO queue (event_id, event_type, data, timestamp) VALUES (?, ?, ?, ?)",
        [
            ("evt-m0", "mission.updated", json.dumps({"a": 1}), 1700000000),
            ("evt-m1", "mission.updated", json.dumps({"a": 2}), 1700000001),
        ],
    )
    conn.commit()
    conn.close()

    result = runner.invoke(app, ["migrate"])
    assert result.exit_code == 0, result.output
    assert "imported 2" in result.output

    # Rows actually landed in the CLI-resolved journal.
    journal = EventJournal(resolve_journal_path())
    assert journal.read_by_id("evt-m0") is not None
    assert journal.read_by_id("evt-m1") is not None
