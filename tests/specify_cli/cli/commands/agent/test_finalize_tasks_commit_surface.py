"""WP00 / FR-009(e) / site #14: the finalize-tasks COMMIT resolves target_branch.

The live dogfood repro (``research/dogfood-finalize-tasks-repro.md``):
``finalize-tasks`` REFUSED to commit its planning artifacts —

    Refusing to commit planning artifacts to the protected branch 'main'.

— because its commit path resolved the planning-commit surface to the protected repo
primary ``main`` instead of the mission's ``target_branch`` (``feat/...``). The
``finalize_tasks`` body commits the TASKS_INDEX artifact through the canonical
``commit_for_mission`` entry point (``mission.py`` ~line 3927, ``kind=TASKS_INDEX``).
``commit_for_mission`` resolves the placement via ``resolve_placement_only`` /
``_resolve_primary_target_branch``, BOTH of which read ``get_feature_target_branch``
internally. Under coord topology that resolver anchored on the coord candidate (no
``meta.json``) and fell back to ``main`` → the placement landed on protected ``main``
→ the #2106 FR-008 guard correctly refused. The resolution to ``main`` is the bug.

This drives the REAL commit machinery the finalize-tasks body uses (``commit_for_mission``
with the SAME ``kind=TASKS_INDEX``), NOT a private resolver. On the unfixed
``get_feature_target_branch`` it is RED (the commit is refused with the protected-``main``
diagnostic / the placement resolves ``main``); after re-pointing the resolver onto the
PRIMARY surface it is GREEN (the TASKS_INDEX placement / commit lands on ``target_branch``).
The #2106 protected-primary guard is preserved — the fix is the resolution, not the guard.

Uses git (a real coordination worktree is needed to reproduce the bug).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind, resolve_placement_only
from specify_cli.coordination.commit_router import commit_for_mission
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.git.protection_policy import ProtectionPolicy

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

MISSION_SLUG = "gate-read-surface-completion"
MID8 = "01KVW9B0"  # 8-char Crockford base32 mid8 (= mission_id[:8])
MISSION_ID = "01KVW9B0XFXPKTBE77QT3KRSW8"  # 26-char ULID
MISSION_DIRNAME = f"{MISSION_SLUG}-{MID8}"  # composed primary dir — never bare slug
COORD_BRANCH = f"kitty/mission-{MISSION_DIRNAME}"
TARGET = "feat/gate-read-surface-completion"
PROTECTED_REFUSAL = "Refusing to commit planning artifacts to the protected branch"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


def _set_origin_head_main(repo: Path) -> None:
    """Pin ``origin/HEAD`` → ``main`` so the resolver's primary fallback is ``main``.

    Production-shaped: a real clone has ``origin/HEAD`` set, so a buggy resolver falls
    back to the protected repo primary ``main`` even while the operator stands on
    ``feat`` (the dogfood state). Without it the fixture would fall through to the
    current branch and mask the bug.
    """
    _git(repo, "update-ref", "refs/remotes/origin/main", "refs/heads/main")
    _git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")


@pytest.fixture
def coord_repo(tmp_path: Path) -> Path:
    """Coord-topology mission on a non-protected feature branch.

    The primary checkout carries ``meta.json`` (``target_branch=feat/...``); the
    materialized coordination worktree's mission dir carries only the status surface
    (NO ``meta.json``). The working checkout is ``feat`` — exactly the live dogfood
    state (spec/plan committed to ``feat`` fine; finalize-tasks then refused).
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")

    feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": MISSION_SLUG,
                "mission_id": MISSION_ID,
                "mid8": MID8,
                "coordination_branch": COORD_BRANCH,
                "target_branch": TARGET,
                "merge_target_branch": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "seed mission")
    _set_origin_head_main(repo)

    # Coord branch carries the mission dir without meta.json (the real shape).
    _git(repo, "checkout", "-q", "-b", COORD_BRANCH)
    (feature_dir / "meta.json").unlink()
    (feature_dir / "status.events.jsonl").write_text("", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "coord surface without meta")

    # Land on the mission's feature branch (where planning artifacts live), then
    # materialize the coord worktree so the topology-aware candidate prefers it.
    _git(repo, "checkout", "-q", "main")
    _git(repo, "checkout", "-q", "-b", TARGET)
    coord_worktree = CoordinationWorkspace.worktree_path(repo, MISSION_SLUG, MID8)
    _git(repo, "worktree", "add", "-q", str(coord_worktree), COORD_BRANCH)
    return repo


def test_finalize_tasks_index_placement_resolves_target_branch(coord_repo: Path) -> None:
    """The TASKS_INDEX placement (what finalize-tasks commits) resolves target_branch.

    RED on the unfixed resolver (placement.ref == 'main'); GREEN after re-pointing
    ``get_feature_target_branch`` onto the primary surface (placement.ref == feat/...).
    """
    placement = resolve_placement_only(
        coord_repo, MISSION_DIRNAME, kind=MissionArtifactKind.TASKS_INDEX
    )
    assert placement.ref == TARGET, (
        "the finalize-tasks TASKS_INDEX commit must resolve the mission's "
        f"target_branch, not the protected repo primary (got {placement.ref!r})"
    )


def test_finalize_tasks_commit_lands_on_target_not_refused(coord_repo: Path) -> None:
    """Drive the real commit machinery finalize-tasks uses; commit lands on target_branch.

    ``finalize_tasks`` commits its tasks artifacts via ``commit_for_mission(...,
    kind=TASKS_INDEX)``. On the unfixed resolver the placement is the protected
    ``main`` and the commit is REFUSED with the protected-branch diagnostic
    (``no_op_wrong_surface``). After the fix the placement is ``target_branch`` and the
    commit is created there. The #2106 protected-primary guard is unchanged.
    """
    feature_dir = coord_repo / "kitty-specs" / MISSION_DIRNAME
    tasks_file = feature_dir / "tasks.md"
    tasks_file.write_text("# Tasks\n\n- WP01\n", encoding="utf-8")

    result = commit_for_mission(
        repo_root=coord_repo,
        mission_slug=MISSION_DIRNAME,
        files=(tasks_file,),
        message=f"Add tasks for feature {MISSION_DIRNAME}",
        policy=ProtectionPolicy.resolve(coord_repo),
        kind=MissionArtifactKind.TASKS_INDEX,
        target_branch=TARGET,
    )

    # The commit must NOT be refused with the protected-main diagnostic.
    assert not (
        result.diagnostic and PROTECTED_REFUSAL in result.diagnostic
    ), f"finalize-tasks commit was refused on protected main: {result.diagnostic!r}"
    # The placement landed on the mission's target_branch (not protected main).
    assert result.placement_ref == TARGET, (
        f"finalize-tasks commit landed on {result.placement_ref!r}, expected {TARGET!r}"
    )
    assert result.status == "committed", (
        f"expected a real commit on {TARGET}, got status={result.status!r} "
        f"diagnostic={result.diagnostic!r}"
    )
