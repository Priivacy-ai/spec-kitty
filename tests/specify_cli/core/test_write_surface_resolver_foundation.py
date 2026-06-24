"""WP00 / FR-004 / FR-009(e): write-surface resolvers anchor on the PRIMARY meta.

Under coordination topology the topology-aware ``candidate_feature_dir_for_mission``
resolves to the coordination worktree, whose mission dir holds only
``status.events.jsonl`` / ``status.json`` — **no ``meta.json``**. The two write-branch
resolvers (:func:`get_feature_target_branch` in ``core.paths`` and
:func:`resolve_target_branch` in ``core.git_ops``) read ``meta.json`` to resolve a
mission's commit/branch surface; anchoring that read on the coord candidate found
nothing and silently fell back to the protected repo primary ``main`` — the exact
class that refused ``finalize-tasks`` / blocked the implement loop (see
``research/dogfood-finalize-tasks-repro.md`` / ``research/debbie-posttasks.md``).

The fix re-points both onto ``primary_feature_dir_for_mission`` — the already-proven
shape of :func:`resolve_merge_target_branch` (``core/paths.py:630-675``). This is the
WRITE twin of the read-side consolidation (G-6). The status/coord destinations are
UNCHANGED (this only fixes the planning commit/branch resolution).

Red-first (NFR-002 / DIRECTIVE_034): the fixture is the coord-topology shape debbie
reproduced — a composed ``<slug>-<mid8>`` primary dir with a real ``meta.json``
(``target_branch=feat/...``) plus a materialized coordination worktree whose mission
dir has NO ``meta.json``. On the unfixed resolver these assertions are RED (resolve
``main``); after the re-point they are GREEN (resolve ``target_branch``). Reverting the
resolver to ``candidate_feature_dir_for_mission`` turns them RED again.

Uses git (a real coordination worktree is needed to reproduce the bug).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.core.git_ops import resolve_target_branch
from specify_cli.core.paths import get_feature_target_branch

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

MISSION_SLUG = "gate-read-surface-completion"
MID8 = "01KVW9B0"  # 8-char Crockford base32 mid8 (= mission_id[:8]); the on-disk form
MISSION_ID = "01KVW9B0XFXPKTBE77QT3KRSW8"  # 26-char ULID
MISSION_DIRNAME = f"{MISSION_SLUG}-{MID8}"  # composed primary dir — never bare slug
COORD_BRANCH = f"kitty/mission-{MISSION_DIRNAME}"
TARGET = "feat/gate-read-surface-completion"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


def _set_origin_head_main(repo: Path) -> None:
    """Pin ``origin/HEAD`` → ``main`` so ``resolve_primary_branch`` returns ``main``.

    Production-shaped (the realistic-test-data standing): a real clone has
    ``origin/HEAD`` set, so the resolver's primary-branch fallback is the repo
    default (``main``) REGARDLESS of the current checkout — which is exactly why the
    dogfood repro saw ``main`` while the operator stood on ``feat``. A fixture without
    ``origin/HEAD`` would fall through to "current branch", masking the bug when the
    test happens to stand on ``feat`` (a false green).
    """
    _git(repo, "update-ref", "refs/remotes/origin/main", "refs/heads/main")
    _git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")


@pytest.fixture
def coord_repo(tmp_path: Path) -> Path:
    """Coord-topology mission: primary meta sets target_branch; coord worktree has no meta.

    This is the exact shape debbie reproduced — the primary checkout carries
    ``meta.json`` (with ``target_branch``); the materialized coordination worktree's
    mission dir carries only ``status.events.jsonl`` (NO ``meta.json``), so the
    topology-aware candidate prefers the coord worktree and finds no meta. The repo
    default is pinned to ``main`` via ``origin/HEAD`` and the working checkout stands
    on ``feat`` — the production-shaped dogfood state (the resolver's fallback to the
    protected ``main`` is the bug; standing on ``feat`` does not mask it).
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

    # Coord branch carries the mission dir but NO meta.json (the real shape); then
    # materialize the coord worktree so the topology-aware candidate prefers it.
    _git(repo, "checkout", "-q", "-b", COORD_BRANCH)
    (feature_dir / "meta.json").unlink()
    (feature_dir / "status.events.jsonl").write_text("", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "coord surface without meta")
    # Stand on the mission's feature branch (where planning artifacts live) — the
    # production-shaped dogfood checkout. The resolver's fallback is origin/HEAD=main,
    # so a buggy resolver still returns the protected primary here.
    _git(repo, "checkout", "-q", "main")
    _git(repo, "checkout", "-q", "-b", TARGET)
    coord_worktree = CoordinationWorkspace.worktree_path(repo, MISSION_SLUG, MID8)
    _git(repo, "worktree", "add", "-q", str(coord_worktree), COORD_BRANCH)
    return repo


def test_get_feature_target_branch_resolves_primary_under_coord_topology(
    coord_repo: Path,
) -> None:
    """``get_feature_target_branch`` reads the PRIMARY target_branch, not main.

    RED on the unfixed resolver (candidate → coord worktree → no meta → fallback
    ``main``); GREEN after re-pointing to ``primary_feature_dir_for_mission``.
    """
    branch = get_feature_target_branch(coord_repo, MISSION_DIRNAME)
    assert branch == TARGET, (
        "write-branch resolution must anchor on the primary meta.json "
        f"(got {branch!r}; the coord candidate has no meta.json so the bug "
        "falls back to the protected repo primary 'main')"
    )


def test_resolve_target_branch_resolves_primary_under_coord_topology(
    coord_repo: Path,
) -> None:
    """``resolve_target_branch`` reads the PRIMARY target_branch, not main."""
    resolution = resolve_target_branch(
        MISSION_DIRNAME,
        coord_repo,
        current_branch="feat/some-other-branch",
        respect_current=True,
    )
    assert resolution.target == TARGET, (
        "resolve_target_branch must anchor on the primary meta.json "
        f"(got {resolution.target!r})"
    )


def test_write_twin_two_surface_behavior(coord_repo: Path) -> None:
    """Write-twin (G-6 / IC-11): planning commit/branch → target_branch; status → coord.

    The planning-branch resolution lands on the mission's ``target_branch`` (PRIMARY
    surface), while the coordination surface is UNCHANGED — the materialized coord
    worktree still exists and still carries the status surface. This kills both the
    "always coord" and the "always primary" mutants for the write side.
    """
    # Planning/write branch resolves to the primary target_branch.
    assert get_feature_target_branch(coord_repo, MISSION_DIRNAME) == TARGET

    # The coord surface is UNCHANGED: the materialized worktree still holds the
    # status surface (status.events.jsonl) and NO meta.json — the write-side fix
    # did not touch the coord/status destination (C-002 / C-003).
    coord_worktree = CoordinationWorkspace.worktree_path(coord_repo, MISSION_SLUG, MID8)
    coord_mission_dir = coord_worktree / "kitty-specs" / MISSION_DIRNAME
    assert (coord_mission_dir / "status.events.jsonl").exists()
    assert not (coord_mission_dir / "meta.json").exists()


def test_flattened_mission_resolution_unchanged(tmp_path: Path) -> None:
    """NFR-001: a flattened mission (meta on the only checkout) is a no-op for the fix.

    No coordination worktree, ``coordination_branch: None`` — the primary candidate
    and the topology candidate coincide, so the resolution is the same before and
    after the fix.
    """
    repo = tmp_path / "flat"
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
                "coordination_branch": None,
                "target_branch": TARGET,
                "merge_target_branch": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "seed flat mission")
    _set_origin_head_main(repo)

    assert get_feature_target_branch(repo, MISSION_DIRNAME) == TARGET
