"""#3536 — followable no-coord protected-branch refusal remedy (WP05 / FR-005).

The ``PROTECTED_BRANCH_REFUSED`` refusal built by
:meth:`specify_cli.coordination.policy.WorkflowMutationPolicy.assert_allowed`
prescribes "re-run through the coordination transaction / target the
coordination branch". On a ``lanes`` / ``single_branch`` topology NO coordination
branch is ever minted, so that remedy is un-followable. This module pins the fix:

* INV-3536-1 — a no-coord topology (``coord_available=False``) gets a remedy that
  does NOT mention "the coordination branch" and names a real, followable action.
* INV-3536-2 — a coord-available topology's remedy is UNCHANGED (regression guard).
* INV-3536-3 — the no-coord answer is sourced from the shared commit-router
  predicate (``mission_has_coordination_branch``), not a fresh
  ``coordination_branch is None`` check minted inside ``policy.py`` (#2739
  convergence).
"""

from __future__ import annotations

import ast
import inspect
import subprocess
from pathlib import Path

import pytest

from mission_runtime import MissionTopology
from specify_cli.coordination import commit_router, policy as policy_module
from specify_cli.coordination.policy import WorkflowMutationPolicy
from specify_cli.coordination.types import PROTECTED_BRANCH_REFUSED, GitChangeSet, Refused

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# The exact coord-available remedy strings on ``main`` before this WP. INV-3536-2
# asserts these are reproduced byte-for-byte when coordination is available.
_COORD_MESSAGE = (
    "Refusing to record 'emit_status_transition': destination ref 'main' is on "
    "this project's protected branch list. Bookkeeping commits must target the "
    "coordination branch."
)
_COORD_NEXT_STEP = (
    "Re-run the command through the coordination transaction; the coord worktree "
    "is auto-resolved."
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Tmp repo whose default branch ``main`` is on the protected list."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / "seed.txt").write_text("seed\n")
    _git(r, "add", "seed.txt")
    _git(r, "commit", "-q", "-m", "initial")
    return r


def _protected_change(repo: Path) -> GitChangeSet:
    return GitChangeSet(
        destination_ref="main",
        repo_root=repo,
        worktree_root=repo,
        paths=(),
        message="m",
        operation="emit_status_transition",
    )


# ---------------------------------------------------------------------------
# INV-3536-1 — no-coord topology → followable remedy
# ---------------------------------------------------------------------------


def test_no_coord_remedy_is_followable(repo: Path) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(
        _protected_change(repo), coord_available=False,
    )
    assert isinstance(verdict, Refused)
    assert verdict.error_code == PROTECTED_BRANCH_REFUSED

    combined = f"{verdict.message}\n{verdict.next_step}".lower()
    # The impossible instruction is gone.
    assert "coordination branch" not in combined
    assert "coordination transaction" not in combined
    # A real, followable action is named: the operator escape hatch.
    assert "SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS" in verdict.next_step


# ---------------------------------------------------------------------------
# INV-3536-2 — coord-available topology → remedy UNCHANGED
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("coord_available", [True, None])
def test_coord_remedy_unchanged(repo: Path, coord_available: bool | None) -> None:
    verdict = WorkflowMutationPolicy.assert_allowed(
        _protected_change(repo), coord_available=coord_available,
    )
    assert isinstance(verdict, Refused)
    assert verdict.error_code == PROTECTED_BRANCH_REFUSED
    assert verdict.message == _COORD_MESSAGE
    assert verdict.next_step == _COORD_NEXT_STEP


def test_default_call_is_coord_remedy(repo: Path) -> None:
    """No caller passing the fact (existing behavior) keeps the coord remedy."""
    verdict = WorkflowMutationPolicy.assert_allowed(_protected_change(repo))
    assert isinstance(verdict, Refused)
    assert verdict.next_step == _COORD_NEXT_STEP


# ---------------------------------------------------------------------------
# INV-3536-3 — the no-coord answer comes from the shared predicate
# ---------------------------------------------------------------------------


def test_shared_predicate_is_the_coord_availability_source(
    repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``mission_has_coordination_branch`` is the single SSOT the fix reads.

    It composes ``routes_through_coordination(resolve_topology(...))`` — the same
    predicate the router already uses for ``use_coord`` — so a ``lanes`` /
    ``single_branch`` topology yields ``False`` (no coord) and a ``coord`` topology
    yields ``True``. #2739's protected-primary sub-issues consume THIS answer.
    """
    for topology, expected in (
        (MissionTopology.LANES, False),
        (MissionTopology.SINGLE_BRANCH, False),
        (MissionTopology.COORD, True),
        (MissionTopology.LANES_WITH_COORD, True),
    ):
        monkeypatch.setattr(
            commit_router, "resolve_topology", lambda *_a, t=topology, **_k: t,
        )
        assert (
            commit_router.mission_has_coordination_branch(repo, "some-mission-01ABCDEF")
            is expected
        )


def test_policy_does_not_mint_local_topology_check() -> None:
    """policy.py must NOT restate a local ``coordination_branch is None`` check.

    The topology fact is threaded in (INV-3536-3); the policy stays a pure function
    of its inputs and never re-derives coord-availability locally. We walk the AST
    (not the raw source) so legitimate docstring mentions of the shared predicate
    do not false-positive — what is forbidden is executable code that re-derives
    the topology inside ``policy.py``.
    """
    tree = ast.parse(inspect.getsource(policy_module))
    referenced: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
    # No local re-derivation of the topology / coord-branch presence.
    assert "resolve_topology" not in referenced
    assert "routes_through_coordination" not in referenced
    assert "coordination_branch" not in referenced
