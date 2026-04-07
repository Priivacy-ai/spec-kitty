"""Canonical status engine for spec-kitty work package lifecycle.

Public API surface — all consumers import from this package.

The event log (status.events.jsonl) is the sole authority for mutable
WP state. No frontmatter reads or writes occur in this module.
"""

from .models import (
    DoneEvidence,
    Lane,
    RepoEvidence,
    ReviewApproval,
    ReviewResult,
    StatusEvent,
    StatusSnapshot,
    ULID_PATTERN,
    VerificationResult,
    get_all_lanes,
    get_all_lane_values,
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
from .transition_context import (
    TransitionContext,
)
from .wp_state import (
    InvalidTransitionError,
    WPState,
    wp_state_for,
)
from .emit import (
    TransitionError,
    emit_status_transition,
)
from .wp_metadata import (
    WPMetadata,
    read_wp_frontmatter,
)
from .lane_reader import (
    CanonicalStatusNotFoundError,
    get_all_wp_lanes,
    get_wp_lane,
    has_event_log,
)
from .views import (
    generate_status_view,
    materialize_if_stale,
    write_derived_views,
)
from .progress import (
    DEFAULT_LANE_WEIGHTS,
    ProgressResult,
    WPProgress,
    compute_weighted_progress,
    generate_progress_json,
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
    "CanonicalStatusNotFoundError",
    "DEFAULT_LANE_WEIGHTS",
    "InvalidTransitionError",
    "ProgressResult",
    "ReviewResult",
    "TransitionContext",
    "WPProgress",
    "WPState",
    "compute_weighted_progress",
    "generate_progress_json",
    "materialize_if_stale",
    "CANONICAL_LANES",
    "DoneEvidence",
    "EVENTS_FILENAME",
    "Lane",
    "get_all_lanes",
    "get_all_lane_values",
    "LANE_ALIASES",
    "RepoEvidence",
    "ReviewApproval",
    "SNAPSHOT_FILENAME",
    "StatusEvent",
    "StatusSnapshot",
    "StoreError",
    "TERMINAL_LANES",
    "TransitionError",
    "ULID_PATTERN",
    "ValidationResult",
    "VerificationResult",
    "WPMetadata",
    "append_event",
    "emit_status_transition",
    "generate_status_view",
    "get_all_wp_lanes",
    "get_wp_lane",
    "has_event_log",
    "is_terminal",
    "materialize",
    "materialize_to_json",
    "read_events",
    "read_events_raw",
    "read_wp_frontmatter",
    "reduce",
    "resolve_lane_alias",
    "validate_derived_views",
    "validate_done_evidence",
    "validate_event_schema",
    "validate_materialization_drift",
    "validate_transition",
    "validate_transition_legality",
    "wp_state_for",
    "write_derived_views",
]
