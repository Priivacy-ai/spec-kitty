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
from .migrate import (
    FeatureMigrationResult,
    MigrationResult,
    WPMigrationDetail,
    migrate_feature,
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
    "FeatureMigrationResult",
    "Lane",
    "LANE_ALIASES",
    "MigrationResult",
    "RepoEvidence",
    "ReviewApproval",
    "SNAPSHOT_FILENAME",
    "StatusEvent",
    "StatusSnapshot",
    "StoreError",
    "TERMINAL_LANES",
    "ULID_PATTERN",
    "VerificationResult",
    "WPMigrationDetail",
    "append_event",
    "is_terminal",
    "materialize",
    "materialize_to_json",
    "migrate_feature",
    "read_events",
    "read_events_raw",
    "reduce",
    "resolve_lane_alias",
    "validate_transition",
]
