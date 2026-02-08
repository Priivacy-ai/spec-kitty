"""Canonical status engine for spec-kitty work package lifecycle.

Public API surface -- all consumers import from this package.
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
from .phase import (
    DEFAULT_PHASE,
    VALID_PHASES,
    is_01x_branch,
    resolve_phase,
)
from .reducer import (
    SNAPSHOT_FILENAME,
    materialize,
    materialize_to_json,
    reduce,
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
from .validate import (
    ValidationResult,
    validate_derived_views,
    validate_done_evidence,
    validate_event_schema,
    validate_materialization_drift,
    validate_transition_legality,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "CANONICAL_LANES",
    "DEFAULT_PHASE",
    "DoneEvidence",
    "EVENTS_FILENAME",
    "Lane",
    "LANE_ALIASES",
    "RepoEvidence",
    "ReviewApproval",
    "SNAPSHOT_FILENAME",
    "StatusEvent",
    "StatusSnapshot",
    "StoreError",
    "TERMINAL_LANES",
    "ULID_PATTERN",
    "VALID_PHASES",
    "VerificationResult",
    "append_event",
    "is_01x_branch",
    "is_terminal",
    "materialize",
    "materialize_to_json",
    "read_events",
    "read_events_raw",
    "reduce",
    "resolve_lane_alias",
    "resolve_phase",
    "validate_transition",
    "ValidationResult",
    "validate_derived_views",
    "validate_done_evidence",
    "validate_event_schema",
    "validate_materialization_drift",
    "validate_transition_legality",
]
