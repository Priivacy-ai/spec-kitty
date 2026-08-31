"""Protected-branch remedies for coordination-less mission topologies."""

from __future__ import annotations

import ast
import inspect
import subprocess
from pathlib import Path

import pytest
from mission_runtime import MissionTopology

from specify_cli.coordination import commit_router
from specify_cli.coordination import policy as policy_module
from specify_cli.coordination.policy import WorkflowMutationPolicy
from specify_cli.coordination.types import (
    PROTECTED_BRANCH_REFUSED,
    GitChangeSet,
    Refused,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

_COORD_MESSAGE = (
    "Refusing to record 'emit_status_transition': destination ref 'main' is on "
    "this project's protected branch list. Bookkeeping commits must target the "
    "coordination branch."
)
_COORD_NEXT_STEP = "Re-run the command through the coordination transaction; the coord worktree is auto-resolved."


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def _protected_change(repo: Path) -> GitChangeSet:
    return GitChangeSet(
        destination_ref="main",
        repo_root=repo,
        worktree_root=repo,
        paths=(),
        message="m",
        operation="emit_status_transition",
    )


def test_no_coord_remedy_is_followable(repo: Path) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(
        _protected_change(repo),
        coord_available=False,
    )
    assert isinstance(verdict, Refused)
    assert verdict.error_code == PROTECTED_BRANCH_REFUSED
    combined = f"{verdict.message}\n{verdict.next_step}".lower()
    assert "coordination branch" not in combined
    assert "coordination transaction" not in combined
    assert "SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS" in verdict.next_step


@pytest.mark.parametrize("coord_available", [True, None])
def test_coord_remedy_is_unchanged(
    repo: Path,
    coord_available: bool | None,
) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(
        _protected_change(repo),
        coord_available=coord_available,
    )
    assert isinstance(verdict, Refused)
    assert verdict.error_code == PROTECTED_BRANCH_REFUSED
    assert verdict.message == _COORD_MESSAGE
    assert verdict.next_step == _COORD_NEXT_STEP


def test_default_call_preserves_coord_remedy(repo: Path) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(_protected_change(repo))
    assert isinstance(verdict, Refused)
    assert verdict.next_step == _COORD_NEXT_STEP


def test_shared_predicate_is_coordination_availability_source(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topologies = (
        (MissionTopology.LANES, False),
        (MissionTopology.SINGLE_BRANCH, False),
        (MissionTopology.COORD, True),
        (MissionTopology.LANES_WITH_COORD, True),
    )
    for topology, expected in topologies:
        monkeypatch.setattr(
            commit_router,
            "resolve_topology",
            lambda *_args, value=topology, **_kwargs: value,
        )
        assert (
            commit_router.mission_has_coordination_branch(
                repo,
                "some-mission-01ABCDEF",
            )
            is expected
        )


def test_policy_does_not_mint_local_topology_check() -> None:
    tree = ast.parse(inspect.getsource(policy_module))
    referenced = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "resolve_topology" not in referenced
    assert "routes_through_coordination" not in referenced
    assert "coordination_branch" not in referenced
