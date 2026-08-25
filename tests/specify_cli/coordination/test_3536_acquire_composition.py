"""#3536 — end-to-end composition of the no-coord remedy through ``acquire``.

The unit tests in ``test_3536_no_coord_remedy.py`` exercise
:meth:`WorkflowMutationPolicy.assert_allowed` DIRECTLY with an explicit
``coord_available`` argument, and prove the predicate
``mission_has_coordination_branch`` in isolation. Neither drives the LIVE WIRING
at ``coordination/transaction.py`` where ``acquire`` computes
``coord_available = mission_has_coordination_branch(repo_root, safe_mission_slug)``
and threads it into ``assert_allowed``.

That wiring had ZERO composition coverage: a regression hardcoding
``coord_available=True`` at that call site would keep every existing test green
(they pass the fact in themselves) while silently restoring the un-followable
coord remedy for a no-coord mission. This module closes that gap by driving a
REAL ``single_branch`` (no ``coordination_branch``) mission through
``BookkeepingTransaction.acquire`` against a PROTECTED destination ref and
asserting the composed refusal carries the no-coord remedy.

Fixture recipe mirrors ``test_transaction_legacy_topology_routing.py``'s
production-shaped real-git-repo + real linked-worktree pattern.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from specify_cli.coordination.transaction import BookkeepingTransaction
from specify_cli.coordination.transaction_errors import BookkeepingPolicyRefused
from specify_cli.coordination.types import PROTECTED_BRANCH_REFUSED

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_HATCH_ENV = "SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    """Tmp repo whose default branch ``main`` is on the protected list."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / "README.md").write_text("seed\n", encoding="utf-8")
    _git(r, "add", "README.md")
    _git(r, "commit", "-q", "-m", "seed")
    return r


def _make_single_branch_mission(repo_root: Path) -> dict[str, Any]:
    """A modern coordination-LESS mission: stored ``topology: single_branch``,
    NO ``coordination_branch``. ``mission_has_coordination_branch`` -> False.
    """
    mission_slug = "no-coord-remedy-compose"
    mission_id = "01M3536COMPOSEZZZZZZZZZZZZ"
    mid8 = mission_id[:8]
    feature_dir = repo_root / "kitty-specs" / f"{mission_slug}-{mid8}"
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = {
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "mid8": mid8,
        "mission_type": "research",  # sidesteps the software-dev currency guard
        "target_branch": "main",
        "topology": "single_branch",
        "created_at": "2026-01-01T00:00:00+00:00",
        "friendly_name": "#3536 acquire-composition mission",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    _git(repo_root, "add", "kitty-specs")
    _git(repo_root, "commit", "-q", "-m", "seed mission scaffold")
    # A real lane branch + linked worktree so _is_legacy_mission's shape holds.
    lane_branch = f"kitty/mission-{mission_slug}-{mid8}-lane-a"
    _git(repo_root, "branch", lane_branch, "main")
    lane_worktree = repo_root / ".worktrees" / f"{mission_slug}-{mid8}-lane-a"
    lane_worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(repo_root, "worktree", "add", str(lane_worktree), lane_branch)
    return {
        "mission_slug": mission_slug,
        "mission_id": mission_id,
        "mid8": mid8,
        "lane_branch": lane_branch,
        "lane_worktree": lane_worktree,
    }


def test_acquire_composes_no_coord_remedy_for_single_branch_mission(
    repo_root: Path,
) -> None:
    """LIVE WIRING: ``acquire`` sources ``coord_available`` from the router
    predicate and threads it to the policy, so a no-coord mission committing to a
    protected ref surfaces the FOLLOWABLE remedy (the operator escape hatch), NOT
    the un-followable coordination remedy.

    A regression hardcoding ``coord_available=True`` at the transaction.py gate
    makes ``next_step`` lose ``SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`` and
    revert to the coord remedy — this test fails in that case.
    """
    mission = _make_single_branch_mission(repo_root)

    with pytest.raises(BookkeepingPolicyRefused) as excinfo:
        BookkeepingTransaction.acquire(
            repo_root=repo_root,
            mission_id=mission["mission_id"],
            mission_slug=mission["mission_slug"],
            mid8=mission["mid8"],
            # PROTECTED destination ref (default-protected 'main'); the caller
            # already resolves this CWD-invariantly for a coordination-less
            # mission, and the modern coordination-less route keeps it verbatim.
            destination_ref="main",
            operation="emit_status_transition",
        )

    verdict = excinfo.value.verdict
    assert verdict.error_code == PROTECTED_BRANCH_REFUSED
    # (a) the followable action is named — the load-bearing regression signal.
    assert _HATCH_ENV in verdict.next_step, (
        "no-coord remedy must name the operator escape hatch; a hardcoded "
        "coord_available=True at the transaction.py gate would drop it"
    )
    # (b) the un-followable coordination remedy is gone.
    assert "coordination branch" not in verdict.next_step.lower()
