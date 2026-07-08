"""Red-first regression: create-time meta commit destination (WP02 T006 / C-006).

``_commit_feature_file`` (``core/mission_creation.py``) commits the freshly
written ``meta.json`` via ``CommitTarget(ref=current_branch)`` -- deriving the
commit destination from the operator's CURRENT CHECKOUT rather than the
mission's placement-seam-resolved home (research.md D5, the create-time
split-brain root; this is the highest-leverage unowned target the whole
mission's Context section blames).

Under a coord-routing mission whose explicit ``target_branch`` differs from
the checkout (a legitimate ``mission create --target-branch design/coord-target``
invocation while the operator stays parked on ``main``), the metadata commit
lands on ``main`` instead of the mission's actual primary home
``design/coord-target`` -- a real data-integrity bug: ``meta.json`` itself
declares ``target_branch: design/coord-target`` but its own git history lives
on ``main``.

This test drives the real ``create_mission_core`` entry point end-to-end
(not ``_commit_feature_file`` directly, per the WP) and captures the
``CommitTarget`` handed to ``safe_commit``, proving the destination is
derived from the checkout, not the seam
(``mission_runtime.placement_seam(...).write_target``).

RED pre-fix: the captured ref is ``"main"`` (the checkout) -- wrong.
GREEN post-fix (T007): the captured ref is ``"design/coord-target"`` (the
seam-resolved PRIMARY_METADATA/SPEC home), matching parity for both coord
and non-coord topologies (T008).
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from mission_runtime import CommitTarget, MissionTopology
from specify_cli.core.mission_creation import create_mission_core
from specify_cli.git.commit_helpers import CommitResult

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_CORE_MODULE = "specify_cli.core.mission_creation"
_CHECKOUT_BRANCH = "main"
_TARGET_BRANCH = "design/coord-target"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _init_git_repo(repo: Path) -> None:
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    _git(repo, "init", "-q", "-b", _CHECKOUT_BRANCH)
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "commit", "-m", "init", "--allow-empty")
    # The mission's real target branch exists as a ref but is NEVER checked
    # out -- the operator stays parked on _CHECKOUT_BRANCH throughout create.
    _git(repo, "branch", _TARGET_BRANCH, _CHECKOUT_BRANCH)


def _mission_summary(slug: str) -> dict[str, str]:
    title = slug.replace("-", " ").strip() or "test mission"
    return {
        "friendly_name": title.title(),
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (
            f"This mission delivers {title} so product and engineering can move "
            "forward with a clear outcome and shared understanding."
        ),
    }


def _capturing_safe_commit(captured: list[CommitTarget]) -> Callable[..., CommitResult]:
    """Stand in for ``safe_commit`` that records the ``target`` it was given.

    The assertion under test is about DESTINATION DERIVATION (C-001) -- which
    branch ``_commit_feature_file`` decides to commit to -- not the downstream
    git mechanics of ``safe_commit`` itself (which legitimately refuses a
    HEAD/destination mismatch; that refusal is orthogonal to this WP). A fake
    keeps the test focused and avoids requiring the operator to actually be
    checked out on the seam-resolved branch just to observe the decision.
    """

    def _fake(*, target: CommitTarget, worktree_root: Path, **_kwargs: Any) -> CommitResult:
        captured.append(target)
        return CommitResult(sha="0" * 40, destination_ref=target.ref, worktree_root=worktree_root)

    return _fake


def test_meta_commit_destination_comes_from_seam_not_checkout(tmp_path: Path) -> None:
    """Coord-routing mission, checkout ("main") != target_branch (design/coord-target).

    The meta.json commit destination must be the seam-resolved PRIMARY home
    (``target_branch``), never the operator's current checkout.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    captured_targets: list[CommitTarget] = []

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=repo),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch("specify_cli.status.fire_dossier_sync"),
        patch(f"{_CORE_MODULE}.safe_commit", side_effect=_capturing_safe_commit(captured_targets)),
    ):
        create_mission_core(
            repo,
            "coord-checkout-mismatch",
            target_branch=_TARGET_BRANCH,
            topology=MissionTopology.COORD,
            **_mission_summary("coord-checkout-mismatch"),
        )

    assert captured_targets, "expected _commit_feature_file to call safe_commit for meta.json"
    meta_commit_target = captured_targets[0]
    assert meta_commit_target.ref == _TARGET_BRANCH, (
        "meta.json commit destination must be the seam-resolved primary target "
        f"({_TARGET_BRANCH!r}), not the operator's checkout ({_CHECKOUT_BRANCH!r}); "
        f"got {meta_commit_target.ref!r} -- the create-time split-brain root "
        "(research.md D5) is still deriving from the checkout, not the seam."
    )


def test_non_coord_single_branch_meta_commit_still_targets_target_branch(tmp_path: Path) -> None:
    """Parity (T008): a SINGLE_BRANCH mission with checkout != target_branch
    also lands meta.json on the seam-resolved target, not the checkout.

    SINGLE_BRANCH skips the coordination-branch mint entirely, so this pins
    that the fix is not accidentally coord-topology-specific.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    captured_targets: list[CommitTarget] = []

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=repo),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch("specify_cli.status.fire_dossier_sync"),
        patch(f"{_CORE_MODULE}.safe_commit", side_effect=_capturing_safe_commit(captured_targets)),
    ):
        create_mission_core(
            repo,
            "flat-checkout-mismatch",
            target_branch=_TARGET_BRANCH,
            topology=MissionTopology.SINGLE_BRANCH,
            **_mission_summary("flat-checkout-mismatch"),
        )

    assert captured_targets, "expected _commit_feature_file to call safe_commit for meta.json"
    meta_commit_target = captured_targets[0]
    assert meta_commit_target.ref == _TARGET_BRANCH, (
        f"got {meta_commit_target.ref!r}, expected {_TARGET_BRANCH!r} "
        "(SINGLE_BRANCH parity with COORD)"
    )


def test_meta_commit_matches_seam_write_target_when_checkout_equals_target(tmp_path: Path) -> None:
    """Parity (T007): normal create (checkout == target_branch) is unaffected.

    No behavior change to WHICH surface meta.json lands on when the operator
    is already parked on the mission's target -- only the DERIVATION changes
    (seam, not checkout). This regression-locks that the common-case create
    flow keeps committing meta.json to the branch it always has.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    captured_targets: list[CommitTarget] = []

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=repo),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch("specify_cli.status.fire_dossier_sync"),
        patch(f"{_CORE_MODULE}.safe_commit", side_effect=_capturing_safe_commit(captured_targets)),
    ):
        create_mission_core(
            repo,
            "no-mismatch",
            topology=MissionTopology.COORD,
            **_mission_summary("no-mismatch"),
        )

    assert captured_targets
    assert captured_targets[0].ref == _CHECKOUT_BRANCH
