"""Coverage for the MissionCreated daemon/dashboard fan-out branch (#2271).

PR #2172 (CORE↛INTEGRATION boundary, closes #614) relocated the MissionCreated
daemon-push + dashboard-sync side effect into ``_lifecycle_saas_fanout_handler``,
gated on ``event_type == "MissionCreated"``. Existing tests either replace the
handler with a spy (``test_mission_creation_fire_once``) or run SaaS-disabled
(so the handler self-no-ops), so the relocated branch had no direct behavioural
pin: a regression that dropped the daemon-push / dashboard-sync side effect (or
fired it for the wrong event type) would still pass CI.

These tests drive the REAL handler with SaaS enabled and stubbed identity/queue
boundaries, asserting the daemon publish + dashboard sync fire exactly once for
MissionCreated and not at all for other lifecycle events. The daemon/dashboard
calls are stubbed (no real port), so this runs safely in parallel.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync import _lifecycle_saas_fanout_handler

# Pure-logic, fully mock-patched (no real subprocess/git/port I/O beyond
# tmp_path) — matches this repo's `fast` marker definition and is what
# fast-tests-sync (tests/sync/, `-m "fast and not windows_ci"`) selects.
# Without this marker the file is invisible to every CI gate (landing fold,
# PR #2393 — same defect class caught on PR #2398's new test file).
from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


def _envelope(event_type: str) -> dict[str, Any]:
    """A minimally-valid queueable lifecycle envelope for ``event_type``.

    _lifecycle_saas_fanout_handler's ``envelope`` parameter is documented
    (lifecycle_events.py) as the LOCAL lifecycle-log shape, intentionally
    kept non-canonical -- no spec_kitty_events model represents it
    (spec_kitty_events.Event is the WIRE envelope with a disjoint, larger
    required-field set and no aggregate_type field at all), so a raw
    fixture is the correct unit-under-test input for this handler's real
    parameter contract.
    """
    # canonical-event-exempt(exception-flow): see docstring above -- no canonical model represents this handler's actual (non-canonical-by-design) input shape.
    return {
        "event_type": event_type,
        "payload": {"mission_id": "01JEXAMPLE0000000000000000"},
        "aggregate_type": "Mission",
    }


@contextlib.contextmanager
def _drive_handler(tmp_path: Path) -> Iterator[tuple[MagicMock, MagicMock]]:
    """Patch the handler's boundaries so control reaches the MissionCreated gate.

    Everything up to the ``if event_type == "MissionCreated"`` branch is stubbed
    to succeed (SaaS enabled, a scope, a resolvable identity, a queueable event,
    a no-op offline queue). Yields the ``(publish_spy, dashboard_spy)`` mocks for
    the two MissionCreated-only side effects.
    """
    identity = MagicMock(
        # Must parse as a CanonicalProjectUUID: the handler now routes the
        # queued event through ProjectSyncStore(str(project_uuid)), which
        # rejects non-UUID text at construction.
        project_uuid="aaaaaaaa-0000-0000-0000-000000000001",
        build_id="build-id",
        project_slug="slug",
        node_id="node-1",
    )
    clock = MagicMock()
    clock.tick.return_value = 1
    clock.node_id = "node-1"
    publish_spy = MagicMock(name="_publish_event_via_sync_daemon")
    dashboard_spy = MagicMock(name="_request_dashboard_sync")

    with (
        patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True),
        patch("specify_cli.sync.queue.read_queue_scope_from_session", return_value=MagicMock()),
        patch("specify_cli.status.repo_root_for_lifecycle_log", return_value=tmp_path),
        patch("specify_cli.identity.project.resolve_identity", return_value=identity),
        patch("specify_cli.sync.clock.LamportClock.load", return_value=clock),
        patch(
            "specify_cli.status.build_saas_lifecycle_queue_event",
            return_value={"event_type": "queued"},
        ),
        patch("specify_cli.core.contract_gate.validate_outbound_payload"),
        patch("spec_kitty_events.Event", MagicMock()),
        # Per-project store cutover: the handler queues via
        # ProjectSyncStore(...).unit_of_work() + OfflineQueue(unit, authority);
        # both stay stubbed as the no-op queue boundary.
        patch("specify_cli.sync.project_store.ProjectSyncStore"),
        patch("specify_cli.sync.queue.OfflineQueue"),
        patch("specify_cli.sync.events._publish_event_via_sync_daemon", publish_spy),
        patch("specify_cli.sync.events._request_dashboard_sync", dashboard_spy),
    ):
        yield publish_spy, dashboard_spy


def test_mission_created_fires_daemon_and_dashboard_once(tmp_path: Path) -> None:
    """MissionCreated => daemon publish + dashboard sync each fire exactly once."""
    with _drive_handler(tmp_path) as (publish_spy, dashboard_spy):
        _lifecycle_saas_fanout_handler(
            envelope=_envelope("MissionCreated"),
            log_path=tmp_path / "status.events.jsonl",
        )

    assert publish_spy.call_count == 1, "daemon publish must fire exactly once for MissionCreated"
    assert dashboard_spy.call_count == 1, "dashboard sync must fire exactly once for MissionCreated"


@pytest.mark.parametrize("event_type", ["WPStatusChanged", "Started", "MissionCompleted"])
def test_non_mission_created_does_not_fire_daemon_or_dashboard(tmp_path: Path, event_type: str) -> None:
    """Non-MissionCreated lifecycle events must not trigger the daemon/dashboard branch."""
    with _drive_handler(tmp_path) as (publish_spy, dashboard_spy):
        _lifecycle_saas_fanout_handler(
            envelope=_envelope(event_type),
            log_path=tmp_path / "status.events.jsonl",
        )

    assert publish_spy.call_count == 0, f"daemon publish must not fire for {event_type}"
    assert dashboard_spy.call_count == 0, f"dashboard sync must not fire for {event_type}"


def test_ingress_does_not_fall_back_to_credentials_scope(tmp_path: Path) -> None:
    """Fail-closed ingress: no drift to the credentials file's team_slug (#738/#911).

    When ``read_queue_scope_from_session`` cannot resolve the Private Teamspace it
    returns None. The handler must then skip — never reroute to
    ``read_queue_scope_from_credentials`` (which returns whatever team_slug the
    credentials TOML last stored, often a shared/primary team). Reaching that
    fallback is what forked the producer journal and materialized the project
    under the wrong team on the server.
    """
    publish_spy = MagicMock(name="_publish_event_via_sync_daemon")
    with (
        patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True),
        patch("specify_cli.sync.queue.read_queue_scope_from_session", return_value=None),
        patch("specify_cli.sync.queue.read_queue_scope_from_credentials") as creds_fallback,
        patch("specify_cli.sync.events._publish_event_via_sync_daemon", publish_spy),
    ):
        _lifecycle_saas_fanout_handler(
            envelope=_envelope("MissionCreated"),
            log_path=tmp_path / "status.events.jsonl",
        )

    creds_fallback.assert_not_called()  # the fail-open fallback is gone
    publish_spy.assert_not_called()  # nothing published under a drifted scope
