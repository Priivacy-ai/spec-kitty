"""Regression tests for the unborn-HEAD create guard (#4033).

A freshly ``git init``-ed repository has an unborn HEAD: HEAD names a branch ref
that does not exist yet, because there are no commits. Git cannot create a
branch in that state, so a coordination-bearing mission created there declares a
``coordination_branch`` in ``meta.json`` that could never be minted.

Before the guard, creation ran to completion and reported success anyway. The
beginner path — ``git init`` then Getting Started — produced missions that were
broken on arrival with no error, recoverable only via
``doctor coordination --fix``. See the reproduction on #4033.

The guard refuses *before* any scaffold is written (so there is nothing to clean
up) and only for topologies that actually mint a coordination branch.
"""

from __future__ import annotations

from contextlib import contextmanager
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from mission_runtime import MissionTopology
from specify_cli.core.git_ops import has_unborn_head
from specify_cli.core.mission_creation import MissionCreationError, create_mission_core

from tests._factories import provision_test_charter

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_CORE_MODULE = "specify_cli.core.mission_creation"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)


def _scaffold_project(repo: Path) -> None:
    """Provision a Spec Kitty project WITHOUT making an initial commit."""
    (repo / ".kittify").mkdir(exist_ok=True)
    provision_test_charter(repo)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    # ``-b main`` so the real branch matches the patched ``get_current_branch``;
    # otherwise the coord mint takes its does-not-resolve skip path and the
    # success case below would pass for the wrong reason.
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    # Deliberately NO commit: this is the unborn-HEAD state under test.


def _mission_summary(slug: str) -> dict[str, str]:
    title = slug.replace("-", " ").strip() or "test mission"
    return {
        "friendly_name": title.title(),
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (f"This mission delivers {title} so product and engineering can move forward with a clear outcome and shared understanding."),
    }


@contextmanager
def _patched_context(tmp_path: Path):
    """Patch the context seams, but leave the real ``has_unborn_head`` in place."""
    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        yield


# ---------------------------------------------------------------------------
# The predicate
# ---------------------------------------------------------------------------


def test_has_unborn_head_true_before_first_commit(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    assert has_unborn_head(tmp_path) is True


def test_has_unborn_head_false_once_a_commit_exists(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@test.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "commit", "-m", "init", "--allow-empty")
    assert has_unborn_head(tmp_path) is False


def test_has_unborn_head_false_for_a_non_repository(tmp_path: Path) -> None:
    """Never the thing that reports 'no commits' for a directory that is not a repo.

    Callers guard on ``is_git_repo`` separately; conflating the two would make
    the create error tell a non-repo user to run ``git commit``.
    """
    assert has_unborn_head(tmp_path) is False


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_coord_create_refuses_on_unborn_head(tmp_path: Path) -> None:
    """The #4033 defect: coord create on a commitless repo used to report success."""
    _scaffold_project(tmp_path)

    with _patched_context(tmp_path), pytest.raises(MissionCreationError) as excinfo:
        create_mission_core(
            tmp_path,
            "unborn-coord",
            topology=MissionTopology.COORD,
            **_mission_summary("unborn-coord"),
        )

    message = str(excinfo.value)
    assert "no commits yet" in message
    # The error must be actionable — it names the recovery, not just the fault.
    assert "git commit" in message


def test_refusal_writes_no_scaffold(tmp_path: Path) -> None:
    """Fail before mutating: a refused create leaves nothing to recover.

    The pre-guard behavior left a ``kitty-specs/<slug>/`` scaffold plus a
    dangling ``coordination_branch`` declaration behind.
    """
    _scaffold_project(tmp_path)

    with _patched_context(tmp_path), pytest.raises(MissionCreationError):
        create_mission_core(
            tmp_path,
            "unborn-no-residue",
            topology=MissionTopology.COORD,
            **_mission_summary("unborn-no-residue"),
        )

    assert list((tmp_path / "kitty-specs").iterdir()) == []


@pytest.mark.parametrize(
    "topology",
    [MissionTopology.SINGLE_BRANCH, MissionTopology.LANES],
    ids=["single_branch", "lanes"],
)
def test_branch_flat_topologies_are_not_blocked(tmp_path: Path, topology: MissionTopology) -> None:
    """Branch-flat shapes mint no coordination branch, so an unborn HEAD is harmless.

    Blocking them would be a gratuitous refusal. This is the narrowing that
    keeps ``test_coordinationless_create_persists_topology_so_2453_routing_is_not_cwd``
    passing.
    """
    _scaffold_project(tmp_path)

    with _patched_context(tmp_path), patch("specify_cli.missions._create.ensure_coordination_branch"):
        result = create_mission_core(
            tmp_path,
            "unborn-flat",
            topology=topology,
            **_mission_summary("unborn-flat"),
        )

    assert result.feature_dir.exists()


def test_coord_create_succeeds_after_the_first_commit(tmp_path: Path) -> None:
    """The remedy the error message prescribes actually works.

    Pins the whole loop: refuse, the user commits, create succeeds. A guard that
    blocks without a working recovery is worse than the bug.
    """
    _scaffold_project(tmp_path)
    _git(tmp_path, "commit", "-m", "init", "--allow-empty")

    # The mint is deliberately NOT patched here: the point is that a real
    # coordination branch can now be created, which is exactly what the unborn
    # HEAD made impossible.
    with _patched_context(tmp_path):
        result = create_mission_core(
            tmp_path,
            "born-coord",
            topology=MissionTopology.COORD,
            **_mission_summary("born-coord"),
        )

    assert result.feature_dir.exists()
    assert result.coordination_branch is not None
    # The declaration in meta.json now resolves to a ref that actually exists —
    # the invariant #4033 violated.
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", result.coordination_branch],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert resolved.returncode == 0, f"declared branch {result.coordination_branch!r} does not exist"
