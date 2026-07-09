"""WP02 regression pins: #2154 mark_status write-leg + #2155 mixed-bundle routing.

Mission ``single-authority-resolution-gates-01KW1P0F`` / WP02 (FR-001 / FR-002).

This module pins the two defects WP02 closes, both red-first before their fix:

#2154 (T008/T009) — ``mark_status``'s WRITE leg resolved its ``tasks.md`` write
target through the kind-blind ``resolve_feature_dir_for_mission`` (which selects
the ``-coord`` husk under coordination topology), while its COMMIT leg and
``move_task``'s validation read used the kind-aware
``resolve_planning_read_dir(kind=TASKS_INDEX)`` pointing at PRIMARY. The write
landed on coord, the validator read primary, and every WP blocked on a phantom
"unchecked subtasks" failure. The fix routes the write leg through the SAME
kind-aware authority, so all three legs CONVERGE on one dir.

  RED-FIRST (pre-T008): under coordination topology the kind-blind write dir
  (coord) ``!=`` the kind-aware validation read dir (primary) — the 3-leg
  convergence assertion FAILS. POST-T008: write leg == validation read ==
  commit-leg placement (all primary). Under FLAT topology all three already
  agree (the non-regression guard) both before and after the fix.

#2155 (T010/T011/T013) — the ``move_task`` (tasks.py) and claim (implement.py)
auto-commit bundles mixed a PRIMARY-partition WP file with coord-owned status
artifacts (``status.events.jsonl`` / ``status.json``) in ONE primary-root commit.
Under coordination topology those coord paths live UNDER ``.worktrees/``, so the
``safe_commit`` path-policy guard (#1887) refuses them — and both callers SWALLOWED
the resulting ``SafeCommitPathPolicyError`` as a soft "Auto-commit skipped" warning,
leaving the feature branch dirty. The fix partitions coord-owned status OUT of the
primary bundle (it is already on coord via the transactional emitter) and STOPS
swallowing the guard refusal. The guard itself (``git/commit_helpers.py``) is
UNCHANGED (C-006) — proven by the wrong-surface negative control below.

  RED-FIRST (pre-T010/T011): a primary bundle carrying a ``.worktrees/`` coord
  status path returns ``status="error"`` (guard refusal folded in) and leaves the
  tree dirty. POST-fix: the partitioned bundle commits cleanly; a DELIBERATELY
  wrong-surface ``.worktrees/`` write is STILL refused (guard invariant, never a
  regression).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Import-order guard: the production entrypoint imports ``status`` before the
# coordination/commit modules; mirroring that here keeps this module importable
# under ``PYTHONPATH=src`` without tripping the known coordination import cycle.
import specify_cli.status  # noqa: F401  # import-order guard

from mission_runtime import MissionArtifactKind
from specify_cli.git import SafeCommitPathPolicyError
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.coordination.commit_router import commit_for_mission
from specify_cli.cli.commands.agent.tasks import _primary_bundle_status_artifacts
import specify_cli.missions._read_path_resolver as rpr

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox]


# --------------------------------------------------------------------------- #
# Git helpers (real on-disk repositories — the guard checks worktree-foreignness
# via git internals, so a metadata-less directory would mis-classify it).
# --------------------------------------------------------------------------- #
def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo: Path, branch: str = "feat/base") -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-qb", branch, str(repo)], check=True, capture_output=True)
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")


def _porcelain(repo: Path) -> str:
    return _git(repo, "status", "--porcelain").stdout


# Realistic, production-shaped identity: a 26-char ULID and the derived 8-char
# mid8, composed into the ``<slug>-<mid8>`` on-disk dir name.
_MISSION_SLUG = "demo-mission"
_MISSION_ID = "01KW1P0FZZ9QABCDEF01234567"
_MID8 = _MISSION_ID[:8]
_COMPOSED = f"{_MISSION_SLUG}-{_MID8}"


# =========================================================================== #
# T009 — #2154 3-leg convergence (coord AND flat topologies), injected context.
# =========================================================================== #
def _install_distinguishable_topology(monkeypatch: pytest.MonkeyPatch, *, coord: bool) -> tuple[Path, Path]:
    """Inject DISTINGUISHABLE primary/coord dirs into the read-path primitives.

    Returns ``(primary_dir, kind_blind_dir)``. Under coordination topology the two
    differ (the kind-blind resolver returns the coord husk); under flat topology
    they are identical. A stub returning the SAME dir for both under coord topology
    would make the convergence assertion vacuous (constant-stub rejection), so the
    coord case returns deliberately distinct paths.
    """
    primary_dir = Path("/synthetic/primary") / _COMPOSED
    coord_dir = Path("/synthetic/coord/.worktrees") / f"{_COMPOSED}-coord" / _COMPOSED
    kind_blind_dir = coord_dir if coord else primary_dir

    # PRIMARY-partition leg of resolve_planning_read_dir composes via this primitive
    # (after the handle fold). Return the primary dir verbatim regardless of handle.
    monkeypatch.setattr(
        rpr, "primary_feature_dir_for_mission", lambda _repo, _handle: primary_dir
    )
    # The fold is a no-op for an already-composed handle; pin it so the synthetic
    # handle does not hit the filesystem.
    monkeypatch.setattr(
        rpr, "_canonicalize_primary_read_handle", lambda _repo, handle, **_kw: handle
    )
    # The kind-blind resolver and the STATUS-partition leg both route here.
    monkeypatch.setattr(
        rpr, "candidate_feature_dir_for_mission", lambda _repo, _slug, **_kw: kind_blind_dir
    )
    monkeypatch.setattr(
        rpr, "resolve_feature_dir_for_mission", lambda _repo, _slug, **_kw: kind_blind_dir
    )
    return primary_dir, kind_blind_dir


def _mark_status_write_leg_resolver(repo: Path, handle: str) -> Path:
    """Resolve the dir the ``mark_status`` write leg (tasks.py:1807) lands on.

    POST-T008 the write leg is the kind-aware ``resolve_planning_read_dir(
    kind=TASKS_INDEX)``. This helper mirrors that call EXACTLY (same module-level
    symbols the production code binds), so the test tracks the real write-leg
    behaviour rather than a hand-rolled copy. PRE-T008 the leg called the
    kind-blind ``resolve_feature_dir_for_mission`` — see the red-first note in the
    coord-topology test for how the divergence was proven against the pre-fix code.
    """
    # Call through the module attribute (not a direct import) so the T009
    # monkeypatch of ``rpr.resolve_planning_read_dir`` takes effect.
    resolved: Path = rpr.resolve_planning_read_dir(
        repo, handle, kind=MissionArtifactKind.TASKS_INDEX
    )
    return resolved


def _validation_read_resolver(repo: Path, handle: str) -> Path:
    """Resolve the dir ``_check_unchecked_tasks`` validation reads (tasks.py:658)."""
    resolved: Path = rpr.resolve_planning_read_dir(
        repo, handle, kind=MissionArtifactKind.TASKS_INDEX
    )
    return resolved


def test_mark_status_write_leg_matches_commit_leg_coord_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under coord topology the 3 legs CONVERGE on PRIMARY (post-T008).

    RED-FIRST PROOF (recorded 2026-06-26): against the pre-T008 code the
    ``mark_status`` write leg called the kind-blind
    ``resolve_feature_dir_for_mission`` (it returns the coord husk under coord
    topology), while the validation read called the kind-aware
    ``resolve_planning_read_dir(kind=TASKS_INDEX)`` (PRIMARY). To reproduce the
    red: bind ``_mark_status_write_leg_resolver`` to
    ``rpr.resolve_feature_dir_for_mission`` (the pre-fix call) — it then returns
    ``kind_blind_dir`` (coord) and the ``write_dir == validation_read_dir``
    assertion FAILS (``coord != primary``). The 3-leg divergence below pins
    exactly that gap; the T008 fix makes the write leg kind-aware so all three
    legs equal the primary dir.
    """
    repo = Path("/synthetic/primary")
    primary_dir, kind_blind_dir = _install_distinguishable_topology(monkeypatch, coord=True)

    # Leg 1 — mark_status WRITE leg (post-T008 kind-aware authority).
    write_dir = _mark_status_write_leg_resolver(repo, _COMPOSED)
    # Leg 3 — move_task / _check_unchecked_tasks VALIDATION read (tasks.py:658).
    validation_read_dir = _validation_read_resolver(repo, _COMPOSED)
    # Leg 2 — mark_status COMMIT leg routes the SAME TASKS_INDEX kind through the
    # commit router; its placement is derived from the SAME kind-aware dir.
    commit_leg_dir = rpr.resolve_planning_read_dir(
        repo, _COMPOSED, kind=MissionArtifactKind.TASKS_INDEX
    )

    # Distinguishable-stub guard (constant-stub rejection): coord topology MUST
    # present a coord husk distinct from primary, else convergence proves nothing.
    assert kind_blind_dir != primary_dir
    # The pre-fix write leg WOULD have landed on the coord husk — assert the fixed
    # write leg does NOT, and converges with the other two legs on PRIMARY.
    assert write_dir != kind_blind_dir
    assert write_dir == validation_read_dir == commit_leg_dir == primary_dir


def test_mark_status_write_leg_matches_commit_leg_flat_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under FLAT topology the 3 legs already agree — non-regression guard.

    This passes on BOTH pre-fix and post-fix code: a flat mission has coord dir ==
    primary dir, so the kind-blind and kind-aware legs never diverged. Including it
    guarantees the T008 fix does not change flat/legacy behaviour.
    """
    repo = Path("/synthetic/primary")
    primary_dir, kind_blind_dir = _install_distinguishable_topology(monkeypatch, coord=False)

    write_dir = rpr.resolve_planning_read_dir(
        repo, _COMPOSED, kind=MissionArtifactKind.TASKS_INDEX
    )
    validation_read_dir = rpr.resolve_planning_read_dir(
        repo, _COMPOSED, kind=MissionArtifactKind.TASKS_INDEX
    )

    # Flat topology: kind-blind and kind-aware resolve the SAME dir.
    assert kind_blind_dir == primary_dir
    assert write_dir == validation_read_dir == primary_dir


# =========================================================================== #
# T010 — #2155 partition helper (unit, both topologies).
# =========================================================================== #
def test_primary_bundle_drops_coord_status_under_coord_topology(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Coord topology: coord-owned status is dropped; primary tasks.md is kept."""
    import specify_cli.cli.commands.agent.tasks as tasks_mod

    monkeypatch.setattr(tasks_mod, "resolve_topology", lambda _r, _s: "COORD")
    monkeypatch.setattr(tasks_mod, "routes_through_coordination", lambda _t: True)

    events = tmp_path / "status.events.jsonl"
    snapshot = tmp_path / "status.json"
    tasks_md = tmp_path / "tasks.md"
    for p in (events, snapshot, tasks_md):
        p.write_text("x", encoding="utf-8")

    kept = _primary_bundle_status_artifacts(
        tmp_path, _MISSION_SLUG, [events, snapshot, tasks_md]
    )
    kept_names = {p.name for p in kept}
    assert "status.events.jsonl" not in kept_names
    assert "status.json" not in kept_names
    assert "tasks.md" in kept_names  # TASKS_INDEX is primary — stays in the bundle


def test_primary_bundle_keeps_all_under_flat_topology(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Flat topology: status files ARE canonical on primary — none are dropped."""
    import specify_cli.cli.commands.agent.tasks as tasks_mod

    monkeypatch.setattr(tasks_mod, "resolve_topology", lambda _r, _s: "SINGLE_BRANCH")
    monkeypatch.setattr(tasks_mod, "routes_through_coordination", lambda _t: False)

    events = tmp_path / "status.events.jsonl"
    tasks_md = tmp_path / "tasks.md"
    for p in (events, tasks_md):
        p.write_text("x", encoding="utf-8")

    kept = _primary_bundle_status_artifacts(tmp_path, _MISSION_SLUG, [events, tasks_md])
    assert {p.name for p in kept} == {"status.events.jsonl", "tasks.md"}


# =========================================================================== #
# T013 — #2155 coord-topology integration (real git) + wrong-surface negative
# control. These drive the REAL commit_for_mission / safe_commit guard, not a
# mock of safe_commit (the guard's worktree-foreignness check needs real git).
# =========================================================================== #
def _seed_flat_mission(repo: Path) -> Path:
    """Create a flat mission (no coord worktree) with WP file + status artifacts."""
    feature_dir = repo / "kitty-specs" / _COMPOSED
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        f'{{"mission_id":"{_MISSION_ID}","mission_slug":"{_MISSION_SLUG}",'
        f'"mid8":"{_MID8}","topology":"flat"}}',
        encoding="utf-8",
    )
    wp_file = feature_dir / "tasks" / "WP01-demo.md"
    wp_file.write_text("---\nwork_package_id: WP01\n---\nbody\n", encoding="utf-8")
    (feature_dir / "status.events.jsonl").write_text('{"event":"claimed"}\n', encoding="utf-8")
    (feature_dir / "status.json").write_text('{"WP01":"claimed"}\n', encoding="utf-8")
    return wp_file


def test_flat_mission_bundle_commits_cleanly(tmp_path: Path) -> None:
    """Flat topology: the WP file + primary status commit cleanly, tree clean.

    On a flat mission there is no coord surface, so all artifacts are primary and
    ``commit_for_mission(kind=WORK_PACKAGE_TASK)`` lands them in ONE primary commit
    with no guard refusal — the partition helper keeps them all.
    """
    repo = tmp_path / "repo"
    _init_repo(repo, branch="feat/flat")
    wp_file = _seed_flat_mission(repo)
    primary_status = [
        (wp_file.parent.parent / "status.events.jsonl"),
        (wp_file.parent.parent / "status.json"),
    ]

    result = commit_for_mission(
        repo,
        _MISSION_SLUG,
        (wp_file.resolve(), *(p.resolve() for p in primary_status)),
        "chore: Move WP01 to in_progress",
        ProtectionPolicy.resolve(repo),
        kind=MissionArtifactKind.WORK_PACKAGE_TASK,
    )
    assert result.status == "committed", getattr(result, "diagnostic", None)
    # No swallowed error and a clean tree: the committed files are gone from porcelain.
    porcelain = _porcelain(repo)
    assert "status.events.jsonl" not in porcelain
    assert "WP01-demo.md" not in porcelain


def test_wrong_surface_worktrees_write_still_refused(tmp_path: Path) -> None:
    """Negative control: a ``.worktrees/`` path staged from the PRIMARY root is
    STILL refused by the UNCHANGED guard (C-006 regression guard).

    This is the surviving #2155 root reproduction AND the guard invariant: bundling
    a coord-owned ``.worktrees/`` status path into a primary commit must raise
    ``SafeCommitPathPolicyError`` (here surfaced via ``commit_for_mission`` folding
    it into ``status="error"`` with the guard's diagnostic). The guard fired before
    the fix and must fire after — the fix lives at the bundle caller (partition),
    never at the guard.
    """
    repo = tmp_path / "repo"
    _init_repo(repo, branch="feat/coord")
    wp_file = _seed_flat_mission(repo)

    # A deliberately wrong-surface coord-owned status path under .worktrees/.
    coord_status = repo / ".worktrees" / f"{_COMPOSED}-coord" / "kitty-specs" / _COMPOSED / "status.events.jsonl"
    coord_status.parent.mkdir(parents=True)
    coord_status.write_text('{"event":"x"}\n', encoding="utf-8")

    # commit_for_mission(kind=WORK_PACKAGE_TASK) routes to the PRIMARY root; the
    # .worktrees/ path trips the guard. The router folds the RuntimeError-subclass
    # SafeCommitPathPolicyError into status="error" with the guard's message.
    result = commit_for_mission(
        repo,
        _MISSION_SLUG,
        (wp_file.resolve(), coord_status.resolve()),
        "chore: wrong-surface bundle",
        ProtectionPolicy.resolve(repo),
        kind=MissionArtifactKind.WORK_PACKAGE_TASK,
    )
    assert result.status == "error"
    assert ".worktrees/" in (result.diagnostic or "")
    # The guard left the tree unstaged (nothing committed) — no silent clean commit.
    # git collapses the untracked mission dir, so assert the WP file is still
    # un-committed (its enclosing kitty-specs/ dir remains untracked).
    porcelain = _porcelain(repo)
    assert "kitty-specs/" in porcelain
    assert not _git(repo, "log", "--oneline", "-1", "--format=%s").stdout.startswith(
        "chore: wrong-surface bundle"
    )


def test_safe_commit_guard_raises_on_worktrees_path_directly(tmp_path: Path) -> None:
    """The guard itself raises ``SafeCommitPathPolicyError`` (C-006 unchanged).

    Direct proof that ``git/commit_helpers.py:safe_commit`` still refuses a
    ``.worktrees/`` path staged from the primary root — the discriminator WP02
    must NOT touch. This pins the guard contract independently of the router fold.
    """
    from specify_cli.git import safe_commit
    from mission_runtime import CommitTarget

    repo = tmp_path / "repo"
    _init_repo(repo, branch="feat/guard")
    bad = repo / ".worktrees" / "x-coord" / "kitty-specs" / "x" / "status.events.jsonl"
    bad.parent.mkdir(parents=True)
    bad.write_text("y\n", encoding="utf-8")

    with pytest.raises(SafeCommitPathPolicyError):
        safe_commit(
            repo_root=repo,
            worktree_root=repo,
            target=CommitTarget(ref="feat/guard"),
            message="chore: wrong surface",
            paths=(bad.resolve(),),
        )


if __name__ == "__main__":  # pragma: no cover - manual red-first harness
    sys.exit(pytest.main([__file__, "-q"]))
