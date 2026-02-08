"""Canonical status engine for spec-kitty work package lifecycle.

Public API surface — all consumers import from this package.
"""

from .models import (
    DoneEvidence,
    Lane,
    RepoEvidence,
    ReviewApproval,
    StatusEvent,
    StatusSnapshot,
    ULID_PATTERN,
    VerificationResult,
)
from .store import (
    EVENTS_FILENAME,
    StoreError,
    append_event,
    read_events,
    read_events_raw,
)
from .transitions import (
    ALLOWED_TRANSITIONS,
    CANONICAL_LANES,
    LANE_ALIASES,
    TERMINAL_LANES,
    is_terminal,
    resolve_lane_alias,
    validate_transition,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "CANONICAL_LANES",
    "DoneEvidence",
    "EVENTS_FILENAME",
    "Lane",
    "LANE_ALIASES",
    "RepoEvidence",
    "ReviewApproval",
    "StatusEvent",
    "StatusSnapshot",
    "StoreError",
    "TERMINAL_LANES",
    "ULID_PATTERN",
    "VerificationResult",
    "append_event",
    "is_terminal",
    "read_events",
    "read_events_raw",
    "resolve_lane_alias",
    "validate_transition",
]
