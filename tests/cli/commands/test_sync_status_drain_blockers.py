"""Sync status surfaces drain blockers (issue #1075 / FR-7)."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from specify_cli.cli.commands.sync import format_queue_health
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.queue import OfflineQueue, QueueStats
from specify_cli.sync.project_store import ProjectSyncStore


pytestmark = pytest.mark.fast


def test_format_queue_health_renders_drain_blocker_table(tmp_path: Path) -> None:
    """Drain-blocker breakdown appears in the ``sync status`` panel.

    Operators must be able to tell why their local queue is not draining.
    Issue #1075 of the teamspace-local-first-outbox mission requires
    ``sync status`` to surface the most common drain blocker with an
    actionable remediation line.
    """
    buf = StringIO()
    console = Console(file=buf, width=120, force_terminal=False)

    stats = QueueStats(
        total_queued=5,
        max_queue_size=1000,
        total_retried=0,
        oldest_event_age=None,
        retry_distribution={"0 retries": 5},
        top_event_types=[("WPStatusChanged", 5)],
        drain_blocked_counts={"ready": 1, "missing_team": 3, "missing_auth": 1},
    )

    format_queue_health(stats, console)
    output = buf.getvalue()

    # Drain readiness summary line is present.
    assert "Drain Ready" in output
    assert "1 ready" in output
    assert "4 blocked" in output

    # Per-blocker breakdown with remediation hints.
    assert "Drain Blockers" in output
    assert "missing_team" in output
    assert "missing_auth" in output
    # Remediation hints reference the canonical recovery commands so the
    # operator can act without guessing.
    assert "spec-kitty auth login" in output
    assert "Private Teamspace" in output


def test_drain_blocked_counts_zero_when_all_ready() -> None:
    """When the queue is empty, the blocker breakdown is omitted."""
    buf = StringIO()
    console = Console(file=buf, width=120, force_terminal=False)

    stats = QueueStats(
        total_queued=0,
        max_queue_size=1000,
        drain_blocked_counts={},
    )

    format_queue_health(stats, console)
    output = buf.getvalue()

    # No "Drain Blockers" table should render when nothing is blocked.
    assert "Drain Blockers" not in output


def test_queue_get_drain_blocked_counts_persists_through_drain_round_trip(tmp_path: Path) -> None:
    """``get_drain_blocked_counts`` reflects what's currently durable on disk.

    Drives the real queue (not a mock) to prove the JSON scan that powers
    ``sync status`` works against the actual SQLite envelope shape that
    ``EventEmitter._emit`` writes.
    """
    store = ProjectSyncStore("aaaaaaaa-0000-0000-8000-000000000107")
    authority = store.layout_generation()
    authority.begin_cutover("status-drain-blockers")
    authority.publish_project_only("status-drain-blockers", verify_exact=lambda: True)

    blocked_events = [
        {"event_id": f"blocked-{i:026d}", "event_type": "WPStatusChanged", "project_uuid": str(store.project_uuid.storage_token), "drain_blocked_reason": reason}
        for i, reason in enumerate(["missing_team", "missing_team", "saas_disabled"])
    ]
    ready_event = {
        "event_id": "01" + "B" * 24,
        "event_type": "WPStatusChanged",
        "project_uuid": str(store.project_uuid.storage_token),
        "drain_blocked_reason": None,
    }

    with store.unit_of_work() as unit:
        queue = OfflineQueue(unit, authority, max_queue_size=1000)
        for event in [*blocked_events, ready_event]:
            queue.queue_event(event)
        counts = queue.get_drain_blocked_counts()
    assert counts.get("missing_team") == 2
    assert counts.get("saas_disabled") == 1
    assert counts.get("ready") == 1


def test_emitter_drain_blocked_reason_enum_is_documented() -> None:
    """The drain-blocked reason set is exposed for cross-component reuse.

    Issue #1075 / #194 of the SaaS half: the SaaS side reads
    ``drain_blocked_reason`` and uses it to distinguish "user opted out
    of sync" from "syncing in progress" in the dashboard. Keeping the
    string set on the emitter class lets downstream tests assert the
    same vocabulary without sync-time string drift.
    """
    assert "saas_disabled" in EventEmitter.DRAIN_BLOCKED_REASONS
    assert "missing_auth" in EventEmitter.DRAIN_BLOCKED_REASONS
    assert "missing_team" in EventEmitter.DRAIN_BLOCKED_REASONS
