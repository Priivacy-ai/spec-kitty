"""WP07 — git-op guard + context-aware staleness on ``materialize_if_stale``.

Covers (mission ``execution-context-unification-01KTPKST``):

* **T023 / FR-005 / C-RT-1 (#1789/#1062)** — ``materialize_if_stale`` must NOT
  re-materialize tracked status while a git operation (rebase / merge /
  cherry-pick / revert / held ``index.lock``) is in progress, and the detection
  is exposed as a reusable public helper (``git_operation_in_progress``) for
  WP11 (dashboard).
* **T024 / FR-012** — the staleness key is context-aware (resolved from the
  canonical mission slug), so the same mission is not falsely stale across
  primary / lane / coordination CWDs.
* **T025 / SC-5** — a *real* ``git rebase`` on a mission branch (not mocked)
  completes with the guard active and no tracked status-file clobber.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.status import git_operation_in_progress
from specify_cli.status.views import (
    _GIT_OP_MARKERS,
    _resolve_git_dirs,
    _stale_check_slug,
    materialize_if_stale,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _git(args: list[str], cwd: Path) -> None:
    """Run a git command, raising on non-zero exit."""
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo_root: Path) -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    _git(["init", "--initial-branch=main"], repo_root)
    _git(["config", "user.email", "wp07@example.com"], repo_root)
    _git(["config", "user.name", "WP07 Test"], repo_root)
    _git(["config", "commit.gpgsign", "false"], repo_root)


# ---------------------------------------------------------------------------
# T023 — git_operation_in_progress detection (reusable public helper for WP11)
# ---------------------------------------------------------------------------


def test_no_git_op_when_clean(tmp_path: Path) -> None:
    """A clean repo has no in-progress git operation."""
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    (repo_root / "f.txt").write_text("x", encoding="utf-8")
    _git(["add", "."], repo_root)
    _git(["commit", "-m", "init"], repo_root)

    assert git_operation_in_progress(repo_root) is False


def test_non_repo_path_is_conservative_false(tmp_path: Path) -> None:
    """A path without a .git resolves to False (never blocks materialization, C-004)."""
    assert git_operation_in_progress(tmp_path / "not-a-repo") is False
    assert _resolve_git_dirs(tmp_path / "not-a-repo") == ()


@pytest.mark.parametrize("marker", _GIT_OP_MARKERS)
def test_each_marker_detected_in_primary_checkout(tmp_path: Path, marker: str) -> None:
    """Every enumerated git-op marker is detected in a primary checkout's gitdir."""
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    (repo_root / "f.txt").write_text("x", encoding="utf-8")
    _git(["add", "."], repo_root)
    _git(["commit", "-m", "init"], repo_root)

    git_dir = repo_root / ".git"
    target = git_dir / marker
    # rebase markers are directories; file markers are plain files. The detector
    # only checks existence, so either kind triggers it.
    if marker.startswith("rebase-"):
        target.mkdir()
    else:
        target.write_text("marker", encoding="utf-8")

    assert git_operation_in_progress(repo_root) is True

    target.rmdir() if target.is_dir() else target.unlink()
    assert git_operation_in_progress(repo_root) is False


def test_marker_in_worktree_gitdir_detected(tmp_path: Path) -> None:
    """A marker in a linked worktree's per-worktree gitdir is detected.

    Worktrees store ``.git`` as a *file* pointing at
    ``<common>/worktrees/<name>``; the detector must resolve that pointer and
    probe the per-worktree gitdir, not just ``<worktree>/.git`` (which is a file).
    """
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    (repo_root / "f.txt").write_text("x", encoding="utf-8")
    _git(["add", "."], repo_root)
    _git(["commit", "-m", "init"], repo_root)
    _git(["branch", "lane"], repo_root)

    worktree = tmp_path / "wt"
    _git(["worktree", "add", str(worktree), "lane"], repo_root)

    git_dirs = _resolve_git_dirs(worktree)
    # Both the per-worktree gitdir and the shared common gitdir are resolved.
    assert len(git_dirs) == 2

    worktree_gitdir = git_dirs[0]
    rebase_dir = worktree_gitdir / "rebase-merge"
    rebase_dir.mkdir()
    assert git_operation_in_progress(worktree) is True
    rebase_dir.rmdir()
    assert git_operation_in_progress(worktree) is False


def test_marker_in_common_gitdir_detected_from_worktree(tmp_path: Path) -> None:
    """A marker in the shared common gitdir is detected from a linked worktree.

    ``MERGE_HEAD`` / ``index.lock`` may live in the common gitdir; a worktree
    caller must still see the hazard.
    """
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    (repo_root / "f.txt").write_text("x", encoding="utf-8")
    _git(["add", "."], repo_root)
    _git(["commit", "-m", "init"], repo_root)
    _git(["branch", "lane"], repo_root)

    worktree = tmp_path / "wt"
    _git(["worktree", "add", str(worktree), "lane"], repo_root)

    common_gitdir = repo_root / ".git"
    lock = common_gitdir / "index.lock"
    lock.write_text("locked", encoding="utf-8")
    assert git_operation_in_progress(worktree) is True
    lock.unlink()
    assert git_operation_in_progress(worktree) is False


# ---------------------------------------------------------------------------
# T024 — context-aware staleness key (FR-012)
# ---------------------------------------------------------------------------


def test_stale_key_uses_canonical_slug_from_meta(tmp_path: Path) -> None:
    """The staleness key is the canonical mission slug, not the dir name (FR-012)."""
    feature_dir = tmp_path / ".worktrees" / "physically-different-dir-name"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_slug": "canonical-mission", "mission_type": "software-dev"}),
        encoding="utf-8",
    )

    assert _stale_check_slug(feature_dir) == "canonical-mission"


def test_stale_key_invariant_across_cwds(tmp_path: Path) -> None:
    """Same mission, two physical dir names → identical staleness key (no false-stale)."""
    primary = tmp_path / "kitty-specs" / "my-mission"
    primary.mkdir(parents=True)
    lane = tmp_path / ".worktrees" / "my-mission-mid8-lane-a"
    lane.mkdir(parents=True)
    meta = json.dumps({"mission_slug": "my-mission", "mission_type": "software-dev"})
    (primary / "meta.json").write_text(meta, encoding="utf-8")
    (lane / "meta.json").write_text(meta, encoding="utf-8")

    assert _stale_check_slug(primary) == _stale_check_slug(lane) == "my-mission"


def test_stale_key_falls_back_to_dir_name_without_meta(tmp_path: Path) -> None:
    """Legacy missions without meta.json fall back to dir name (C-004 preserved)."""
    feature_dir = tmp_path / "kitty-specs" / "034-legacy"
    feature_dir.mkdir(parents=True)
    assert _stale_check_slug(feature_dir) == "034-legacy"


# ---------------------------------------------------------------------------
# T023 — materialize_if_stale defers regeneration during a git op
# ---------------------------------------------------------------------------


def _seed_feature(repo_root: Path, slug: str) -> Path:
    feature_dir = repo_root / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_slug": slug, "mission_type": "software-dev"}),
        encoding="utf-8",
    )
    # An event log so reduce() yields a real snapshot.
    (feature_dir / "status.events.jsonl").write_text("", encoding="utf-8")
    return feature_dir


def test_materialize_if_stale_skips_during_git_op(tmp_path: Path) -> None:
    """With a git op in progress, stale derived views are NOT regenerated (FR-005)."""
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    feature_dir = _seed_feature(repo_root, "guard-mission")
    (repo_root / ".kittify").mkdir(exist_ok=True)
    _git(["add", "."], repo_root)
    _git(["commit", "-m", "init"], repo_root)

    derived_root = repo_root / ".kittify" / "derived" / "guard-mission"

    # Simulate an in-progress rebase.
    rebase_dir = repo_root / ".git" / "rebase-merge"
    rebase_dir.mkdir()

    snapshot = materialize_if_stale(feature_dir, repo_root)

    # Derived views must NOT have been written while the op is in progress.
    assert not (derived_root / "status.json").exists()
    # The in-memory snapshot is still returned (read-only reduce path).
    assert snapshot is not None

    rebase_dir.rmdir()

    # Once the op clears, materialization proceeds normally.
    materialize_if_stale(feature_dir, repo_root)
    assert (derived_root / "status.json").exists()


# ---------------------------------------------------------------------------
# T025 / SC-5 — long real rebase on a mission branch, no status clobber
# ---------------------------------------------------------------------------


def test_sc5_real_rebase_no_status_clobber(tmp_path: Path) -> None:
    """SC-5: a real ``git rebase`` on a mission branch does not clobber status.

    Builds a genuine repo with a mission branch that diverges from main, then
    drives a real (non-mocked) rebase. While the rebase is conflicted/in
    progress, a runtime writer calling ``materialize_if_stale`` must NOT
    regenerate the tracked derived views; after the rebase completes the tree is
    clean and the pre-rebase status content is intact.
    """
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    slug = "rebase-mission"
    feature_dir = _seed_feature(repo_root, slug)
    (repo_root / ".kittify").mkdir(exist_ok=True)
    # Derived views are output-only artifacts, never tracked in git (mirrors the
    # real project's .gitignore); keep them out of the rebase replay.
    (repo_root / ".gitignore").write_text(".kittify/derived/\n", encoding="utf-8")

    # Establish a derived status.json (the artifact we must not clobber).
    derived_dir = repo_root / ".kittify" / "derived"
    sentinel = derived_dir / slug / "status.json"
    materialize_if_stale(feature_dir, repo_root)
    assert sentinel.exists()
    sentinel_before = sentinel.read_text(encoding="utf-8")

    _git(["add", "."], repo_root)
    _git(["commit", "-m", "chore: baseline"], repo_root)

    # Diverge: main advances, mission branch advances on the SAME file to force
    # a long (conflicted) rebase that pauses mid-operation.
    conflict = repo_root / "conflict.txt"
    _git(["checkout", "-b", f"kitty/mission-{slug}"], repo_root)
    conflict.write_text("mission-line\n", encoding="utf-8")
    _git(["add", "conflict.txt"], repo_root)
    _git(["commit", "-m", "feat: mission change"], repo_root)

    _git(["checkout", "main"], repo_root)
    conflict.write_text("main-line\n", encoding="utf-8")
    _git(["add", "conflict.txt"], repo_root)
    _git(["commit", "-m", "feat: main change"], repo_root)

    _git(["checkout", f"kitty/mission-{slug}"], repo_root)

    # Start the rebase; it will stop on conflict (the long-op pause window).
    rebase = subprocess.run(
        ["git", "rebase", "main"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert rebase.returncode != 0, "rebase should pause on conflict"
    assert git_operation_in_progress(repo_root) is True

    # A runtime writer fires mid-rebase. Force staleness so the guard is the only
    # thing preventing a write.
    sentinel.unlink()
    materialize_if_stale(feature_dir, repo_root)
    assert not sentinel.exists(), (
        "materialize_if_stale clobbered tracked status during an active rebase "
        "(FR-005 / SC-5 violation)"
    )

    # Resolve the conflict and complete the rebase.
    conflict.write_text("resolved\n", encoding="utf-8")
    _git(["add", "conflict.txt"], repo_root)
    import os

    rebase_env = {**os.environ, "GIT_EDITOR": "true"}
    cont = subprocess.run(
        ["git", "rebase", "--continue"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env=rebase_env,
    )
    assert cont.returncode == 0, f"rebase --continue failed: {cont.stderr}"

    assert git_operation_in_progress(repo_root) is False
    # Tree is clean after the rebase.
    status_porcelain = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    assert status_porcelain.stdout.strip() == "", "working tree dirty after rebase"

    # After the op clears, materialization resumes and regenerates the view.
    materialize_if_stale(feature_dir, repo_root)
    assert sentinel.exists()
    assert sentinel.read_text(encoding="utf-8") == sentinel_before, (
        "regenerated status content diverged from the pre-rebase snapshot"
    )
