"""Deterministic workflow fixtures for release reliability regressions.

These helpers build local mission/work-package state only. Tests for hosted
sync behavior should use the fake sync clients in this package unless a work
package explicitly scopes a hosted path. On this computer, command paths that
exercise SaaS, tracker, hosted auth, or sync behavior must be run with
``SPEC_KITTY_ENABLE_SAAS_SYNC=1``.
"""

from .branch import BranchDivergenceState, branch_divergence_state
from .mission import (
    DEFAULT_CREATED_AT,
    BranchContext,
    MissionFixture,
    ReviewArtifactSpec,
    SharedLaneContext,
    WorkPackageSpec,
    append_status_event,
    create_mission_fixture,
    materialize_status,
    write_review_artifact,
    write_shared_lane_context,
    write_work_package,
)
from .review_prompt import (
    FIXED_REVIEW_CREATED_AT,
    FIXED_REVIEW_INVOCATION_ID,
    ReviewPromptIdentity,
    assert_prompt_metadata_identity,
    concurrent_review_prompt_identities,
    write_review_prompt,
)
from .sync import (
    CommandOutput,
    ControlledSyncFailure,
    FakeSyncClient,
    SyncDiagnostic,
    assert_json_stdout_parseable,
    assert_stderr_contains_diagnostic_codes,
)

__all__ = [
    "DEFAULT_CREATED_AT",
    "FIXED_REVIEW_CREATED_AT",
    "FIXED_REVIEW_INVOCATION_ID",
    "BranchContext",
    "BranchDivergenceState",
    "CommandOutput",
    "ControlledSyncFailure",
    "FakeSyncClient",
    "MissionFixture",
    "ReviewArtifactSpec",
    "ReviewPromptIdentity",
    "SharedLaneContext",
    "SyncDiagnostic",
    "WorkPackageSpec",
    "append_status_event",
    "assert_json_stdout_parseable",
    "assert_prompt_metadata_identity",
    "assert_stderr_contains_diagnostic_codes",
    "branch_divergence_state",
    "concurrent_review_prompt_identities",
    "create_mission_fixture",
    "materialize_status",
    "write_review_artifact",
    "write_review_prompt",
    "write_shared_lane_context",
    "write_work_package",
]
