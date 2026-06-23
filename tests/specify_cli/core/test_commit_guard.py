"""Unit tests for the commit-guard policy module (WP02, T005).

Mission ``tooling-stability-guard-coherence-01KTRC04`` (FR-001, FR-008,
contracts C-GUARD-2 / C-GUARD-3a). These pin the pure decision in
``specify_cli.core.commit_guard.evaluate``:

* placement-match (non-protected ref) allows;
* a protected-ref mismatch refuses, with the resolved destination in the reason;
* each capability authorizes ONLY its protected-branch flow;
* NO capability grants a push (a push is not a verdict this guard can emit);
* the capability is a parameter — never derived from message/file/env;
* the resolved destination ECHOES ``CommitTarget.ref`` (C-GUARD-3a).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fast]

from mission_runtime.context import CommitTarget
from specify_cli.core.commit_guard import (
    GuardCapability,
    GuardVerdict,
    ProtectionState,
    evaluate,
)

_UNPROTECTED = ProtectionState(is_protected=False)
_PROTECTED = ProtectionState(is_protected=True)

_LANE_TARGET = CommitTarget(
    ref="kitty/mission-foo-01ABCDEF-lane-b",
)
_MAIN_TARGET = CommitTarget(ref="main")


# ---------------------------------------------------------------------------
# Placement match — non-protected destination is always allowed
# ---------------------------------------------------------------------------


def test_placement_match_on_unprotected_ref_is_allowed() -> None:
    verdict = evaluate(_LANE_TARGET, _UNPROTECTED)
    assert verdict.allowed is True
    assert verdict.resolved_destination == _LANE_TARGET.ref


def test_default_capability_is_standard() -> None:
    # No capability argument → STANDARD; an unprotected commit is allowed.
    verdict = evaluate(_LANE_TARGET, _UNPROTECTED)
    assert verdict.allowed is True


# ---------------------------------------------------------------------------
# Protected-ref mismatch — STANDARD is refused, reason names the destination
# ---------------------------------------------------------------------------


def test_standard_commit_to_protected_ref_is_refused() -> None:
    verdict = evaluate(_MAIN_TARGET, _PROTECTED, GuardCapability.STANDARD)
    assert verdict.allowed is False
    assert verdict.resolved_destination == "main"
    # The resolved destination MUST appear in the refusal reason (messaging).
    assert "main" in verdict.reason


def test_refusal_reason_names_the_resolved_destination() -> None:
    target = CommitTarget(ref="master")
    verdict = evaluate(target, _PROTECTED)
    assert verdict.allowed is False
    assert "master" in verdict.reason


# ---------------------------------------------------------------------------
# Each capability authorizes ONLY its protected-branch flow
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "capability",
    [
        GuardCapability.RELEASE_FLOW,
        GuardCapability.UPGRADE_BOOKKEEPING,
        GuardCapability.MERGE_BOOKKEEPING,
        GuardCapability.TEST_MODE,
    ],
)
def test_bookkeeping_capability_authorizes_protected_commit(
    capability: GuardCapability,
) -> None:
    verdict = evaluate(_MAIN_TARGET, _PROTECTED, capability)
    assert verdict.allowed is True
    assert verdict.resolved_destination == "main"


def test_standard_is_the_only_capability_refused_on_protected_ref() -> None:
    # STANDARD does not authorize any protected-branch flow.
    assert evaluate(_MAIN_TARGET, _PROTECTED, GuardCapability.STANDARD).allowed is False
    # Every non-standard capability does.
    for capability in GuardCapability:
        if capability is GuardCapability.STANDARD:
            continue
        assert evaluate(_MAIN_TARGET, _PROTECTED, capability).allowed is True


# ---------------------------------------------------------------------------
# No capability grants a push (push is not a verdict this guard emits)
# ---------------------------------------------------------------------------


def test_verdict_has_no_push_affordance() -> None:
    """A GuardVerdict can only express allow/refuse for a *local* commit.

    There is no field or value through which any capability could request a
    push; direct-push protection is structurally out of this guard's reach.
    """
    verdict = evaluate(_MAIN_TARGET, _PROTECTED, GuardCapability.RELEASE_FLOW)
    assert set(GuardVerdict.__dataclass_fields__) == {
        "allowed",
        "resolved_destination",
        "reason",
    }
    # The strongest verdict is still just "allowed to commit locally".
    assert verdict.allowed is True


# ---------------------------------------------------------------------------
# C-GUARD-3a — evaluate ECHOES CommitTarget.ref, never re-derives
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ref",
    ["main", "kitty/mission-x-01ABCDEF-coord", "develop", "feature/anything"],
)
def test_resolved_destination_echoes_commit_target_ref(ref: str) -> None:
    target = CommitTarget(ref=ref)
    # The verdict's destination is exactly the target's ref under both outcomes.
    assert evaluate(target, _UNPROTECTED).resolved_destination == ref
    assert evaluate(target, _PROTECTED).resolved_destination == ref


# ---------------------------------------------------------------------------
# Capability is a parameter — purity / no ambient derivation
# ---------------------------------------------------------------------------


def test_evaluate_is_pure_and_ignores_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting the legacy env hatches changes nothing — evaluate reads no env."""
    monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
    monkeypatch.setenv("SPEC_KITTY_TEST_MODE", "1")
    # Even with both hatches set, a STANDARD commit to a protected ref is refused
    # by evaluate(): the env is not a privilege channel for the policy decision.
    verdict = evaluate(_MAIN_TARGET, _PROTECTED, GuardCapability.STANDARD)
    assert verdict.allowed is False
