"""Canonical status engine for spec-kitty work package lifecycle.

Public API surface — all consumers import from this package.

The event log (status.events.jsonl) is the sole authority for mutable
WP state. No frontmatter reads or writes occur in this module.
"""

from pathlib import Path

from .models import (
    AgentAssignment,
    DoneEvidence,
    GuardContext,
    Lane,
    RepoEvidence,
    ReviewApproval,
    ReviewResult,
    StatusEvent,
    StatusSnapshot,
    TransitionRequest,
    ULID_PATTERN,
    VerificationResult,
    get_all_lanes,
    get_all_lane_values,
)
from .reducer import (
    SNAPSHOT_FILENAME,
    materialize,
    materialize_snapshot,
    materialize_to_json,
    reduce,
)
from .store import (
    EVENTS_FILENAME,
    EventPersistenceError,
    StoreError,
    append_event,
    append_event_verified,
    append_events_atomic_verified,
    append_primary_checkout_event_verified,
    append_primary_checkout_events_atomic_verified,
    read_events,
    read_events_from_text,
    read_events_raw,
)
from .transitions import (
    # Non-authoritative derived projection (NFR-002, I1): re-exported for tests
    # and graph tooling only. Never consult it as an edge/transition gate; route
    # edge questions through wp_state_for(from).may_transition_to(to).
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
    PROGRESS_SEMANTICS,
    ProgressResult,
    WPProgress,
    compute_done_percentage,
    compute_weighted_progress,
    generate_progress_json,
)
from .adapters import (
    fire_saas_fanout,
    register_dossier_sync_handler,
    register_lifecycle_saas_fanout_handler,
    register_saas_fanout_handler,
)
from .bootstrap import (
    bootstrap_canonical_state,
)
from .event_log_merge import (
    EventLogMergeError,
    merge_event_log_files,
)
from .identity_audit import (
    IdentityState,
    audit_repo,
    classify_mission,
    find_ambiguous_selectors,
    find_duplicate_prefixes,
    summarize,
)
from .locking import (
    FeatureStatusLockTimeoutError,
    feature_status_lock,
)
from .preflight import (
    is_dossier_snapshot,
)
from .lifecycle import (
    DERIVED_LIFECYCLE_FILENAME,
    MISSION_ABANDONED_THRESHOLD_DAYS,
    MISSION_RECENT_COMPLETION_WINDOW_DAYS,
    MISSION_STALE_THRESHOLD_DAYS,
    MissionLifecycleResult,
    derive_mission_lifecycle,
    generate_lifecycle_json,
)
from .validate import (
    ValidationResult,
    validate_derived_views,
    validate_done_evidence,
    validate_event_schema,
    validate_materialization_drift,
    validate_transition_legality,
)
from .aggregate import (
    ActiveWPStatus,
    CoordAuthorityUnavailable,
    InvalidMissionSlug,
    MissionMetadataUnavailable,
    MissionStatus,
)
from .lifecycle_events import (
    PLAN_COMPLETED,
    PLAN_STARTED,
    REVIEWER_SELF_APPROVAL,
    SPECIFY_COMPLETED,
    SPECIFY_STARTED,
    TASKS_COMPLETED,
    TASKS_STARTED,
    build_saas_lifecycle_queue_event,
    emit_artifact_phase,
    emit_mission_created_local,
    emit_project_initialized,
    emit_reviewer_self_approval,
    emit_wp_created_local,
    has_non_bootstrap_status_history,
    repo_root_for_lifecycle_log,
)
from .work_package_lifecycle import (
    WorkPackageClaimConflict,
    WorkPackageStartRejected,
    start_implementation_status,
    start_review_status,
)
from .doctor import (
    run_doctor,
)


def uninitialized_status_error(mission_slug: str, wp_id: str, feature_dir: Path) -> str:
    """Return the cycle-aware missing-status message without eager dependency-graph imports."""
    from .uninitialized_hint import uninitialized_status_error as _uninitialized_status_error

    return _uninitialized_status_error(mission_slug, wp_id, feature_dir)

# The canonical status artifacts (event log + snapshot). On coordination-topology
# missions these are owned by the transactional status emitter on the coordination
# branch; the primary checkout's copies are stale and must not clobber the seed
# during finalize/implement (#1589). Single source for both commit paths
# (finalize in agent/mission.py and implement.py) — review M7.
COORD_OWNED_STATUS_FILES = frozenset({EVENTS_FILENAME, SNAPSHOT_FILENAME})

__all__ = [
    "ActiveWPStatus",
    "AgentAssignment",
    "ALLOWED_TRANSITIONS",
    "COORD_OWNED_STATUS_FILES",
    "CoordAuthorityUnavailable",
    "EventLogMergeError",
    "FeatureStatusLockTimeoutError",
    "GuardContext",
    "IdentityState",
    "InvalidMissionSlug",
    "MissionMetadataUnavailable",
    "MissionStatus",
    "PLAN_COMPLETED",
    "PLAN_STARTED",
    "REVIEWER_SELF_APPROVAL",
    "SPECIFY_COMPLETED",
    "SPECIFY_STARTED",
    "TASKS_COMPLETED",
    "TASKS_STARTED",
    "TransitionRequest",
    "WorkPackageClaimConflict",
    "WorkPackageStartRejected",
    "build_saas_lifecycle_queue_event",
    "emit_artifact_phase",
    "emit_mission_created_local",
    "emit_project_initialized",
    "emit_reviewer_self_approval",
    "emit_wp_created_local",
    "has_non_bootstrap_status_history",
    "materialize_snapshot",
    "repo_root_for_lifecycle_log",
    "run_doctor",
    "start_implementation_status",
    "start_review_status",
    "CanonicalStatusNotFoundError",
    "DEFAULT_LANE_WEIGHTS",
    "DERIVED_LIFECYCLE_FILENAME",
    "InvalidTransitionError",
    "MISSION_ABANDONED_THRESHOLD_DAYS",
    "MISSION_RECENT_COMPLETION_WINDOW_DAYS",
    "MISSION_STALE_THRESHOLD_DAYS",
    "MissionLifecycleResult",
    "ProgressResult",
    "ReviewResult",
    "TransitionContext",
    "WPProgress",
    "WPState",
    "PROGRESS_SEMANTICS",
    "compute_done_percentage",
    "compute_weighted_progress",
    "derive_mission_lifecycle",
    "generate_lifecycle_json",
    "generate_progress_json",
    "materialize_if_stale",
    "CANONICAL_LANES",
    "DoneEvidence",
    "EVENTS_FILENAME",
    "EventPersistenceError",
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
    "audit_repo",
    "append_event",
    "bootstrap_canonical_state",
    "classify_mission",
    "feature_status_lock",
    "find_ambiguous_selectors",
    "find_duplicate_prefixes",
    "is_dossier_snapshot",
    "merge_event_log_files",
    "register_dossier_sync_handler",
    "register_lifecycle_saas_fanout_handler",
    "register_saas_fanout_handler",
    "summarize",
    "uninitialized_status_error",
    "append_event_verified",
    "append_events_atomic_verified",
    "append_primary_checkout_event_verified",
    "append_primary_checkout_events_atomic_verified",
    "emit_status_transition",
    "generate_status_view",
    "get_all_wp_lanes",
    "get_wp_lane",
    "has_event_log",
    "is_terminal",
    "materialize",
    "materialize_to_json",
    "fire_saas_fanout",
    "read_events",
    "read_events_from_text",
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
