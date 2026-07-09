"""WP01 / IC-01 — single context factory + freeze + build-invariant tests.

TDD-first (C-IC01 / FR-009 / D-2): these assert the build-time
``CONTEXT_INVARIANT_VIOLATION`` and the post-build immutability of
``MissionExecutionContext``. They fail on HEAD (no invariant; composite still mutable)
and pass after the freeze + factory land.

Topology-true (NFR-002): the fixtures use a full 26-char ULID ``mission_id`` —
never a fabricated short id. These assertions are pure (construct a context,
assert invariant/immutability), so the ULID realism is the load-bearing part.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fast]

from mission_runtime import (
    ActionContextError,
    BranchRefFragment,
    CommitTarget,
    IdentityFragment,
    MissionExecutionContext,
)
from mission_runtime.resolution import build_execution_context

# Production-shaped 26-char ULID (NFR-002): never a 3-char stand-in.
_MISSION_ID = "01KV8NPC0000000000000000ZZ"
_MISSION_SLUG = "read-path-error-fidelity-adoption-01KV8NPC"
_TARGET_BRANCH = "feat/read-path-error-fidelity"
# The WP lane branch legitimately DIFFERS from the mission target branch (D-2).
_LANE_BRANCH = "kitty/mission-read-path-error-fidelity-adoption-01KV8NPC-lane-a"


def _branch_ref(target_branch: str = _TARGET_BRANCH) -> BranchRefFragment:
    return BranchRefFragment(
        target_branch=target_branch,
        coordination_branch=None,
        destination_ref=CommitTarget(ref=target_branch),
    )


def _identity() -> IdentityFragment:
    return IdentityFragment.derive(mission_id=_MISSION_ID, mission_slug=_MISSION_SLUG)


# ---------------------------------------------------------------------------
# T001 — build-time CONTEXT_INVARIANT_VIOLATION
# ---------------------------------------------------------------------------


def test_build_rejects_target_branch_invariant_violation() -> None:
    """Building with ``target_branch != branch_ref.target_branch`` is rejected."""
    branch_ref = _branch_ref(target_branch="feat/read-path-error-fidelity")
    with pytest.raises(ActionContextError) as excinfo:
        build_execution_context(
            action="specify",
            mission_slug=_MISSION_SLUG,
            feature_dir=f"kitty-specs/{_MISSION_SLUG}",
            target_branch="feat/SOMETHING-ELSE",  # mismatches branch_ref
            detection_method="explicit",
            identity=_identity(),
            branch_ref=branch_ref,
        )
    assert excinfo.value.code == "CONTEXT_INVARIANT_VIOLATION"
    # Both values must be named in the message (operator-debuggable).
    message = str(excinfo.value)
    assert "feat/SOMETHING-ELSE" in message
    assert "feat/read-path-error-fidelity" in message


def test_build_accepts_matching_target_branch() -> None:
    """A consistent composite builds and carries the resolved target branch."""
    context = build_execution_context(
        action="specify",
        mission_slug=_MISSION_SLUG,
        feature_dir=f"kitty-specs/{_MISSION_SLUG}",
        target_branch=_TARGET_BRANCH,
        detection_method="explicit",
        identity=_identity(),
        branch_ref=_branch_ref(),
    )
    assert context.branch_ref is not None
    assert context.target_branch == context.branch_ref.target_branch == _TARGET_BRANCH


def test_build_does_not_assert_branch_name_against_target_branch() -> None:
    """The lane branch may differ from the target branch (D-2 / C-IC01).

    A WP-bearing context whose ``branch_name`` is the lane branch (NOT the
    mission target branch) MUST still build — the invariant is over
    ``target_branch`` only.
    """
    context = build_execution_context(
        action="implement",
        mission_slug=_MISSION_SLUG,
        feature_dir=f"kitty-specs/{_MISSION_SLUG}",
        target_branch=_TARGET_BRANCH,
        detection_method="explicit",
        branch_name=_LANE_BRANCH,  # legitimately differs from target_branch
        identity=_identity(),
        branch_ref=_branch_ref(),
    )
    assert context.branch_name == _LANE_BRANCH
    assert context.branch_name != context.target_branch


# ---------------------------------------------------------------------------
# T002 — MissionExecutionContext immutability (frozen composite)
# ---------------------------------------------------------------------------


def test_built_context_is_immutable() -> None:
    """Assigning ``target_branch`` on a built context raises (C-IC01)."""
    context = build_execution_context(
        action="specify",
        mission_slug=_MISSION_SLUG,
        feature_dir=f"kitty-specs/{_MISSION_SLUG}",
        target_branch=_TARGET_BRANCH,
        detection_method="explicit",
        identity=_identity(),
        branch_ref=_branch_ref(),
    )
    with pytest.raises((AttributeError, TypeError)):
        context.target_branch = "other"  # type: ignore[misc]


def test_built_context_rejects_wp_field_mutation() -> None:
    """The WP-bearing fields are construct-once too — post-build write raises."""
    context = build_execution_context(
        action="specify",
        mission_slug=_MISSION_SLUG,
        feature_dir=f"kitty-specs/{_MISSION_SLUG}",
        target_branch=_TARGET_BRANCH,
        detection_method="explicit",
        identity=_identity(),
        branch_ref=_branch_ref(),
    )
    with pytest.raises((AttributeError, TypeError)):
        context.wp_id = "WP99"  # type: ignore[misc]


def test_direct_construction_is_frozen() -> None:
    """The composite itself is frozen, not just the factory product."""
    context = MissionExecutionContext(
        action="specify",
        mission_slug=_MISSION_SLUG,
        feature_dir=f"kitty-specs/{_MISSION_SLUG}",
        target_branch=_TARGET_BRANCH,
        detection_method="explicit",
    )
    with pytest.raises((AttributeError, TypeError)):
        context.target_branch = "other"  # type: ignore[misc]
