"""Canonical status engine for spec-kitty work package lifecycle.

Public API surface — all consumers import from this package.

The event log (status.events.jsonl) is the sole authority for mutable
WP state. No frontmatter reads or writes occur in this module.
"""

from pathlib import Path

from .models import (
    AgentAssignment,
    DoneEvidence,
    EventStream,
    GuardContext,
    InnerStateChanged,
    Lane,
    NON_DISPLAY_LANES,
    RepoEvidence,
    ReviewApproval,
    ReviewOverride,
    ReviewResult,
    Status,
    StatusEvent,
    StatusSnapshot,
    TransitionRequest,
    ULID_PATTERN,
    VerificationResult,
    WPInnerStateDelta,
    actor_identity_str,
    get_all_lanes,
    get_all_lane_values,
)
from .reducer import (
    SNAPSHOT_FILENAME,
    materialize,
    materialize_snapshot,
    materialize_to_json,
    reduce,
    wp_snapshot_state,
)
from .store import (
    is_retrospective_lifecycle_event,
    EVENTS_FILENAME,
    EventPersistenceError,
    StoreError,
    append_annotations_atomic_verified,
    append_event,
    append_event_verified,
    append_events_atomic_verified,
    append_primary_checkout_event_verified,
    append_primary_checkout_events_atomic_verified,
    read_event_stream,
    read_event_stream_from_text,
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
    annotate,
    wp_state_for,
)
from .emit import (
    TransitionError,
    build_claim_policy_metadata,
    build_resolved_actor,
    build_self_asserting_actor,
    emit_inner_state_changed,
    emit_resolved_binding,
    emit_status_transition,
    parse_agent_boundary_string,
)
from .resolved_binding import (
    ResolvedBinding,
)
from .wp_view import (
    AuthoredGroup,
    ResolvedGroup,
    WPView,
    reconstruct_wp_view,
)
from .wp_metadata import (
    WPMetadata,
    _Builder,
    read_authored_wp_frontmatter,
    read_wp_frontmatter,
)
from .wp_review import (
    resolve_event_stream_review,
    resolve_snapshot_review,
)
from .lane_reader import (
    CanonicalStatusNotFoundError,
    LEGACY_UNINITIALIZED_SENTINEL,
    get_all_wp_lanes,
    get_wp_lane,
    has_event_log,
)
from .views import (
    generate_status_view,
    git_operation_in_progress,
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
    fire_dossier_sync,
    fire_resolved_binding_fanout,
    fire_saas_fanout,
    register_dossier_sync_handler,
    register_lifecycle_saas_fanout_handler,
    register_resolved_binding_fanout_handler,
    register_saas_fanout_handler,
)
from .bootstrap import (
    BootstrapResult,
    bootstrap_canonical_state,
)
from .event_log_merge import (
    EventLogMergeError,
    merge_event_log_files,
    merge_event_log_texts,
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
    is_mission_completed,
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
    LIFECYCLE_EVENT_TYPES,
    PLAN_COMPLETED,
    PLAN_STARTED,
    REVIEWER_SELF_APPROVAL,
    SPECIFY_COMPLETED,
    SPECIFY_STARTED,
    TASKS_COMPLETED,
    TASKS_STARTED,
    MissionNotCompletedError,
    build_saas_lifecycle_queue_event,
    emit_artifact_phase,
    emit_follow_up_recorded,
    emit_mission_created_local,
    emit_mission_reopened,
    emit_project_initialized,
    emit_reviewer_self_approval,
    emit_wp_created_local,
    has_non_bootstrap_status_history,
    repo_root_for_lifecycle_log,
)
from .views import (
    format_post_mission_events,
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
from .doctor_husks import (
    WORKTREES_DIRNAME,
    RegisteredWorktreePaths,
    WorkspaceHuskRegistrationError,
    fix_workspace_husks,
    registered_worktree_paths,
    scan_workspace_husks,
)


def uninitialized_status_error(mission_slug: str, wp_id: str, feature_dir: Path) -> str:
    """Return the cycle-aware missing-status message without eager dependency-graph imports."""
    from .uninitialized_hint import uninitialized_status_error as _uninitialized_status_error

    return str(_uninitialized_status_error(mission_slug, wp_id, feature_dir))

# WP13 (IC-07c) retired ``COORD_OWNED_STATUS_FILES`` -- the canonical status
# artifacts (event log + snapshot) frozenset -- onto the single canonical churn
# owner (``coordination.coherence.is_toolchain_generated_churn`` /
# ``mission_runtime.MissionArtifactKind.STATUS_STATE``, FR-012). Consumers that
# used to import this frozenset now classify by kind/path through that owner
# instead of a locally-duplicated basename set. ``EVENTS_FILENAME`` /
# ``SNAPSHOT_FILENAME`` remain -- only the derived exemption frozenset (and its
# 8 consumer call sites) was retired.

__all__ = [
    "ActiveWPStatus",
    "AgentAssignment",
    "actor_identity_str",
    "ALLOWED_TRANSITIONS",
    "EventStream",
    "InnerStateChanged",
    "ReviewOverride",
    "Status",
    "WPInnerStateDelta",
    "annotate",
    "append_annotations_atomic_verified",
    "build_claim_policy_metadata",
    "build_resolved_actor",
    "parse_agent_boundary_string",
    "emit_inner_state_changed",
    "emit_resolved_binding",
    "ResolvedBinding",
    "AuthoredGroup",
    "ResolvedGroup",
    "WPView",
    "reconstruct_wp_view",
    "resolve_event_stream_review",
    "read_event_stream",
    "read_event_stream_from_text",
    "read_authored_wp_frontmatter",
    "CoordAuthorityUnavailable",
    "EventLogMergeError",
    "FeatureStatusLockTimeoutError",
    "GuardContext",
    "IdentityState",
    "InvalidMissionSlug",
    "MissionMetadataUnavailable",
    "LIFECYCLE_EVENT_TYPES",
    "MissionStatus",
    "PLAN_COMPLETED",
    "PLAN_STARTED",
    "REVIEWER_SELF_APPROVAL",
    "SPECIFY_COMPLETED",
    "SPECIFY_STARTED",
    "TASKS_COMPLETED",
    "TASKS_STARTED",
    "MissionNotCompletedError",
    "TransitionRequest",
    "WorkPackageClaimConflict",
    "WorkPackageStartRejected",
    "build_saas_lifecycle_queue_event",
    "emit_artifact_phase",
    "emit_follow_up_recorded",
    "emit_mission_created_local",
    "emit_mission_reopened",
    "emit_project_initialized",
    "emit_reviewer_self_approval",
    "emit_wp_created_local",
    "format_post_mission_events",
    "has_non_bootstrap_status_history",
    "is_retrospective_lifecycle_event",
    "materialize_snapshot",
    "repo_root_for_lifecycle_log",
    "run_doctor",
    "start_implementation_status",
    "start_review_status",
    "CanonicalStatusNotFoundError",
    "LEGACY_UNINITIALIZED_SENTINEL",
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
    "is_mission_completed",
    "materialize_if_stale",
    "CANONICAL_LANES",
    "DoneEvidence",
    "EVENTS_FILENAME",
    "EventPersistenceError",
    "Lane",
    "NON_DISPLAY_LANES",
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
    "WORKTREES_DIRNAME",
    "RegisteredWorktreePaths",
    "WorkspaceHuskRegistrationError",
    "WPMetadata",
    "_Builder",
    "BootstrapResult",
    "audit_repo",
    "append_event",
    "bootstrap_canonical_state",
    "classify_mission",
    "feature_status_lock",
    "find_ambiguous_selectors",
    "find_duplicate_prefixes",
    "fix_workspace_husks",
    "is_dossier_snapshot",
    "merge_event_log_files",
    "merge_event_log_texts",
    "register_dossier_sync_handler",
    "register_lifecycle_saas_fanout_handler",
    "register_resolved_binding_fanout_handler",
    "register_saas_fanout_handler",
    "summarize",
    "uninitialized_status_error",
    "append_event_verified",
    "append_events_atomic_verified",
    "append_primary_checkout_event_verified",
    "append_primary_checkout_events_atomic_verified",
    "build_self_asserting_actor",
    "emit_status_transition",
    "generate_status_view",
    "get_all_wp_lanes",
    "get_wp_lane",
    "git_operation_in_progress",
    "has_event_log",
    "is_terminal",
    "materialize",
    "materialize_to_json",
    "fire_dossier_sync",
    "fire_resolved_binding_fanout",
    "fire_saas_fanout",
    "read_events",
    "read_events_from_text",
    "read_events_raw",
    "read_wp_frontmatter",
    "reduce",
    "resolve_lane_alias",
    "resolve_snapshot_review",
    "validate_derived_views",
    "validate_done_evidence",
    "validate_event_schema",
    "validate_materialization_drift",
    "validate_transition",
    "validate_transition_legality",
    "wp_snapshot_state",
    "wp_state_for",
    "registered_worktree_paths",
    "scan_workspace_husks",
    "write_derived_views",
]
