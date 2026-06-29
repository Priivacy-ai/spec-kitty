"""Append-only, producer-scoped event journal (WP03).

A separate core domain (C-001) from ``specify_cli.events`` and
``specify_cli.sync.queue``. It durably retains event payloads independent of any
delivery target (FR-003), never deletes on the normal path (FR-001), and is the
capture-first store the emit layer writes to before delivery gates (FR-017).
"""
from __future__ import annotations

from .journal import (
    ANONYMOUS_PRODUCER,
    CaptureGateState,
    CoalesceDecision,
    CoalesceStrategy,
    EventJournal,
    JournalTransaction,
    TeamspaceBoundDropError,
    capture_teamspace_bound,
    classify_drain_blocked_reason,
    get_journal,
    register_coalesce_strategy,
    reset_coalesce_strategy,
    reset_journal_cache,
    resolve_journal_path,
)
from .models import (
    DRAIN_BLOCKED_DAEMON_LOCK,
    DRAIN_BLOCKED_MISSING_AUTH,
    DRAIN_BLOCKED_MISSING_TEAM,
    DRAIN_BLOCKED_NETWORK,
    DRAIN_BLOCKED_PRIVATE_TEAMSPACE,
    DRAIN_BLOCKED_REASONS,
    DRAIN_BLOCKED_SAAS_DISABLED,
    Event,
    event_to_params,
    row_to_event,
)

__all__ = [
    "ANONYMOUS_PRODUCER",
    "CaptureGateState",
    "CoalesceDecision",
    "CoalesceStrategy",
    "DRAIN_BLOCKED_DAEMON_LOCK",
    "DRAIN_BLOCKED_MISSING_AUTH",
    "DRAIN_BLOCKED_MISSING_TEAM",
    "DRAIN_BLOCKED_NETWORK",
    "DRAIN_BLOCKED_PRIVATE_TEAMSPACE",
    "DRAIN_BLOCKED_REASONS",
    "DRAIN_BLOCKED_SAAS_DISABLED",
    "Event",
    "EventJournal",
    "JournalTransaction",
    "TeamspaceBoundDropError",
    "capture_teamspace_bound",
    "classify_drain_blocked_reason",
    "event_to_params",
    "get_journal",
    "register_coalesce_strategy",
    "reset_coalesce_strategy",
    "reset_journal_cache",
    "resolve_journal_path",
    "row_to_event",
]
