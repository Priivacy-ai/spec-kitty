"""WP02 deactivation guard tests — the runtime surface must no-op when sync is inactive.

These tests live in ``tests/deactivation/`` on purpose: they MUST run on the
**default (inactive)** path, so they must NOT be under ``tests/sync/`` (which WP05
gates off via module-level ``skipif``).

**Conftest interaction (BINDING, WP02 post-tasks correction).** The suite conftest
(``tests/conftest.py``) has an autouse fixture that *unconditionally* sets
``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` for every test (only de-masked in WP04, which
WP02 does not depend on). So a guard test cannot rely on the "default off" state
existing at collection/run time — it must force sync-inactive **in-test** by
``delenv``-ing the enable flag (and normalizing the disable vars). The
``_force_sync_inactive`` fixture below does exactly that; without it,
``sync_active()`` is True and the ``assert_not_called`` spies below are vacuous.

Assertions are **seam-not-reached** (spies), per NFR-001/SC-001 — not "absence of
log text". The spy patterns mirror ``tests/sync/test_emitter_observability.py``
(``monkeypatch.setattr(emitter, "_queue_event_locally", ...)``).

The named implicit daemon-spawn seam is ``sync.daemon._spawn_sync_daemon_process``
(the OS-level spawn); the ``sync_active()`` gate inside ``_daemon_start_skip_reason``
returns a non-None skip reason before ``ensure_sync_daemon_running`` can reach it.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.status import adapters as status_adapters
from specify_cli.sync import daemon as daemon_mod
from specify_cli.sync import events as events_mod
from specify_cli.sync import register_default_handlers
from specify_cli.sync.config import BackgroundDaemonPolicy
from specify_cli.sync.daemon import DaemonIntent, ensure_sync_daemon_running
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.sync_doctor_core import (
    _SYNC_INACTIVE_ADVISORY,
    _SYNC_INACTIVE_ORPHAN_HINT,
    DoctorFacts,
    build_doctor_report,
)

pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# Fixtures: force the sync surface inactive / armed, overriding the autouse
# conftest default (which sets SPEC_KITTY_ENABLE_SAAS_SYNC=1).
# ---------------------------------------------------------------------------
def _isolate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin HOME + runtime to temp so no test can touch the real ~/.spec-kitty."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))


@pytest.fixture
def _force_sync_inactive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``sync_active()`` return False regardless of the conftest default."""
    _isolate_home(tmp_path, monkeypatch)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", raising=False)


@pytest.fixture
def _force_sync_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Arm the sync surface (opt-in) — the FR-015 lossless-re-enable arm."""
    _isolate_home(tmp_path, monkeypatch)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", raising=False)


@pytest.fixture(autouse=True)
def _reset_registry() -> Any:
    """Leave the shared status-adapter registry clean around every test."""
    status_adapters.reset_handlers()
    yield
    status_adapters.reset_handlers()


def _registry_is_empty() -> bool:
    return not (
        status_adapters._dossier_handlers
        or status_adapters._saas_handlers
        or status_adapters._lifecycle_saas_handlers
    )


# ---------------------------------------------------------------------------
# T007 — emitter ``_emit`` gate: capture/queue NOT reached, envelope STILL returned.
# Each parametrized case stands in for one of the 9 emission surfaces
# (create / mark-status / move-task / issue-verdict / accept / implement /
# merge / doctor / next) — they all funnel through ``EventEmitter._emit``.
# ---------------------------------------------------------------------------
def _emit_calls() -> list[tuple[str, Any]]:
    return [
        ("emit_wp_created", lambda e: e.emit_wp_created("WP01", "Title", "001-mission")),
        (
            "emit_wp_status_changed",
            lambda e: e.emit_wp_status_changed("WP01", "planned", "claimed"),
        ),
        ("emit_history_added", lambda e: e.emit_history_added("WP01", "note", "hi")),
        (
            "emit_error_logged",
            lambda e: e.emit_error_logged("Boom", "something failed"),
        ),
    ]


@pytest.mark.parametrize("name,call", _emit_calls(), ids=[c[0] for c in _emit_calls()])
def test_emit_returns_envelope_but_captures_nothing_when_inactive(
    name: str,
    call: Any,
    _force_sync_inactive: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-1: inactive ⇒ no local-capture / no local-queue, yet emit_* returns a non-None envelope."""
    emitter = EventEmitter()
    capture_spy = MagicMock()
    queue_spy = MagicMock(return_value=True)
    monkeypatch.setattr(emitter, "_capture_to_journal", capture_spy)
    monkeypatch.setattr(emitter, "_queue_event_locally", queue_spy)

    result = call(emitter)

    # Envelope contract: the constructed envelope is returned (never None) so the
    # emit_*-returns-non-None contract stays green.
    assert isinstance(result, dict), f"{name} must return the constructed envelope"
    # Seam-not-reached: nothing was captured to the journal or queued locally.
    capture_spy.assert_not_called()
    queue_spy.assert_not_called()


def test_emit_reaches_capture_when_active(
    _force_sync_active: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-015 lossless re-enable: armed ⇒ the capture seam IS reached again."""
    emitter = EventEmitter()
    capture_spy = MagicMock()
    queue_spy = MagicMock(return_value=True)
    monkeypatch.setattr(emitter, "_capture_to_journal", capture_spy)
    monkeypatch.setattr(emitter, "_queue_event_locally", queue_spy)

    emitter.emit_history_added("WP01", "note", "hi")

    capture_spy.assert_called_once()


# ---------------------------------------------------------------------------
# T005 — register_default_handlers is a call-time no-op when inactive.
# ---------------------------------------------------------------------------
def test_register_default_handlers_noops_when_inactive(
    _force_sync_inactive: None,
) -> None:
    """FR-003 / C-006: inactive ⇒ zero handlers registered, function still callable."""
    status_adapters.reset_handlers()
    register_default_handlers()
    assert _registry_is_empty(), "no handlers must be registered on the inactive path"


def test_register_default_handlers_registers_when_active(
    _force_sync_active: None,
) -> None:
    """FR-015 / C-006: armed ⇒ the same call registers the lifecycle fan-out handlers."""
    status_adapters.reset_handlers()
    register_default_handlers()
    assert not _registry_is_empty(), "handlers must register once the surface is armed"


# ---------------------------------------------------------------------------
# T006 — daemon implicit spawn does not reach ``_spawn_sync_daemon_process``.
# ---------------------------------------------------------------------------
def test_implicit_daemon_spawn_not_reached_when_inactive(
    _force_sync_inactive: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-004: inactive ⇒ the implicit spawn seam is never called and start is skipped."""
    spawn_spy = MagicMock()
    monkeypatch.setattr(daemon_mod, "_spawn_sync_daemon_process", spawn_spy)

    outcome = ensure_sync_daemon_running(intent=DaemonIntent.REMOTE_REQUIRED)

    spawn_spy.assert_not_called()
    assert outcome.started is False
    assert outcome.skipped_reason is not None


def test_daemon_skip_reason_gate_flips_with_arming(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C-008: ``sync_active()`` is the implicit-spawn arming decision (replace, not stack)."""
    _isolate_home(tmp_path, monkeypatch)
    # Inactive: the implicit path is skipped with a diagnostic reason.
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", raising=False)
    assert (
        daemon_mod._daemon_start_skip_reason(
            DaemonIntent.REMOTE_REQUIRED, BackgroundDaemonPolicy.AUTO
        )
        == "rollout_disabled"
    )

    # Armed: arming is reached (no rollout/disable skip) — the gate returns None.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    assert (
        daemon_mod._daemon_start_skip_reason(
            DaemonIntent.REMOTE_REQUIRED, BackgroundDaemonPolicy.AUTO
        )
        is None
    )

    # Disable env wins even when armed (sync_active() is stricter than rollout).
    monkeypatch.setenv("SPEC_KITTY_SYNC_DISABLE", "1")
    assert (
        daemon_mod._daemon_start_skip_reason(
            DaemonIntent.REMOTE_REQUIRED, BackgroundDaemonPolicy.AUTO
        )
        == "SPEC_KITTY_SYNC_DISABLE is set"
    )


# ---------------------------------------------------------------------------
# T006 — events emit/publish + dashboard-trigger no-op when inactive.
# ---------------------------------------------------------------------------
def test_events_publish_and_request_noop_when_inactive(
    _force_sync_inactive: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-005: inactive ⇒ neither publish nor dashboard-trigger touches the daemon."""
    status_spy = MagicMock()
    monkeypatch.setattr(daemon_mod, "get_sync_daemon_status", status_spy)
    repo_root = tmp_path

    events_mod._publish_event_via_sync_daemon({"project_uuid": "p"}, repo_root)
    events_mod._request_dashboard_sync(repo_root)

    status_spy.assert_not_called()


# ---------------------------------------------------------------------------
# T008 — FR-018 doctor advisory renders when inactive (and is NOT an issue).
# ---------------------------------------------------------------------------
def _healthy_facts() -> DoctorFacts:
    session = SimpleNamespace(
        access_token_expires_at=None,
        refresh_token_expires_at=None,
        email="user@example.com",
        name="User",
        teams=[],
        default_team_id=None,
    )
    return DoctorFacts(
        queue_error=None,
        queue_stats=SimpleNamespace(
            total_queued=0, max_queue_size=1000, oldest_event_age=None, top_event_types=[]
        ),
        body_diagnostics={"total_tasks": 0, "recorded_failure_count": 0, "recent_failures": []},
        queue_db="/data/queue.db",
        session=session,
        session_present=True,
        access_token_ok=True,
        refresh_token_ok=True,
        server_url="https://sync.example.com",
        connection_status="[green]Connected[/green]",
        connection_note="",
        connection_is_healthy=True,
        connection_is_auth_owned=False,
        singleton_report=SimpleNamespace(orphan_count=0, orphan_processes=[]),
        singleton_scan_diagnostic=None,
        per_project_report=None,
        per_project_open_error=None,
        per_project_group_error=None,
        consent_index_health=SimpleNamespace(fault=None),
        consent_index_error=None,
        consent_local_fault=None,
        consent_local_error=None,
        consent_repo_root_present=True,
        tracker_local_verdict=SimpleNamespace(
            destination=SimpleNamespace(value="local_subprocess"),
            channel1_state="granted",
            message="egress",
            refused=False,
        ),
        tracker_hosted_verdict=SimpleNamespace(
            destination=SimpleNamespace(value="hosted_service"),
            channel1_state="granted",
            message="egress",
            refused=False,
        ),
        tracker_binding_present=True,
        orphan_records=[],
        orphan_record_count=0,
        owner_record_path="/data/owner.json",
    )


def test_doctor_advisory_present_when_inactive(
    _force_sync_inactive: None,
) -> None:
    """FR-018: inactive ⇒ opt-in advisory + orphan-cleanup hint, without flipping healthy."""
    report = build_doctor_report(_healthy_facts())
    assert _SYNC_INACTIVE_ADVISORY in report.advisories
    assert _SYNC_INACTIVE_ORPHAN_HINT in report.advisories
    # Advisories are informational, not faults: a clean surface stays healthy.
    assert report.healthy is True


def test_doctor_advisory_absent_when_active(
    _force_sync_active: None,
) -> None:
    """Armed ⇒ no inactive advisory (the surface is on, nothing to advise)."""
    report = build_doctor_report(_healthy_facts())
    assert report.advisories == []
    assert report.healthy is True
