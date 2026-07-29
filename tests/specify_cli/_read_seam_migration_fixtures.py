"""Shared real-git + coord-state scaffolding for the read-seam migration suites.

Mission ``read-side-seam-primary-primitive-closure-01KYKMMT`` (WP03-WP08) added
five sibling test modules that each independently re-implemented the same
"build a real git repo, then shape a coord-topology mission's on-disk state"
scaffolding:

* ``tests/specify_cli/missions/test_primary_read_delegation.py`` (WP03)
* ``tests/specify_cli/missions/test_topology_routed_read_migration.py`` (WP04)
* ``tests/specify_cli/cli/commands/test_lifecycle_read_seam_migration.py`` (WP06)
* ``tests/specify_cli/status/test_aggregate_read_seam_migration.py`` (WP07)
* ``tests/specify_cli/acceptance/test_trio_read_seam_migration.py`` (WP05)

This module hoists the byte-identical/near-identical pieces (a real ``git``
runner, a minimal repo builder, and the five recurring coord-state on-disk
shapes: flat / coord-materialized / coord-husk / coord-worktree-empty /
coord-branch-deleted) into ONE place, following the same precedent as
``tests/integration/coord_topology_fixture.py`` -- a plain, cross-directory
importable module, real git throughout, no resolver ever patched.

Each consuming module keeps its OWN:

* ``_write_meta`` -- deliberately NOT centralized here. It is an established
  repo-wide convention (~40 test modules define their own ``_write_meta``),
  and its call signature differs slightly per module (some pass ``mission_id``
  / ``topology`` explicitly, others derive ``topology`` from whether a
  ``coordination_branch`` was supplied). The ``build_*`` functions below never
  write ``meta.json`` content themselves -- they accept a
  ``write_primary_meta`` (and, for the materialized case, ``write_coord_meta``)
  callback so each module's own ``_write_meta`` stays the single source of
  truth for that module's meta.json shape.
* production-shaped fixture identity (mission id / mid8 / human slug) and the
  ``Fixture`` / ``_Fixture`` dataclass wrapper used to carry the built paths
  back to its own tests.
* any extra per-fixture content (e.g. planting a WP task file or an
  analysis-report decoy) that is specific to that module's call sites.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path


def git_cmd(repo: Path, *args: str) -> str:
    """Run a git command in *repo*, returning stripped stdout."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def make_git_repo(
    tmp_path: Path,
    name: str,
    *,
    user_email: str,
    user_name: str,
    readme_text: str,
    quiet: bool = False,
) -> Path:
    """A minimal real git repo with the ``.kittify`` marker + ``kitty-specs/``.

    Identity (``user_email`` / ``user_name``) and the README seed text are
    caller-supplied so each consuming test module keeps its own
    production-shaped fixture identity (NFR-003 test-data convention) even
    though the repo-scaffolding steps themselves are shared. ``quiet=True``
    mirrors the ``-q`` flags the WP05 trio suite passes to ``git init`` /
    ``git commit``; it changes only subprocess verbosity, never the resulting
    repo state.
    """
    repo = tmp_path / name
    repo.mkdir(parents=True)
    init_args = ["init", "-q", "-b", "main"] if quiet else ["init", "-b", "main"]
    subprocess.run(["git", *init_args, str(repo)], check=True, capture_output=True)
    git_cmd(repo, "config", "user.email", user_email)
    git_cmd(repo, "config", "user.name", user_name)
    git_cmd(repo, "config", "commit.gpgsign", "false")
    (repo / ".kittify").mkdir()
    (repo / "kitty-specs").mkdir()
    (repo / "README.md").write_text(readme_text, encoding="utf-8")
    git_cmd(repo, "add", ".")
    commit_args = ["commit", "-q", "-m", "init"] if quiet else ["commit", "-m", "init"]
    git_cmd(repo, *commit_args)
    return repo


def coord_branch_name(handle: str) -> str:
    """The coordination branch name for a mission ``handle`` (composed slug)."""
    return f"kitty/mission-{handle}"


def coord_worktree_root(repo: Path, handle: str) -> Path:
    """The manual ``.worktrees/<handle>-coord`` root.

    For fixtures that build the coord-worktree path by hand rather than going
    through the production ``CoordinationWorkspace.worktree_path`` seam (both
    forms are used across the read-seam migration suites; callers that use
    the production seam instead simply pass its result as ``coord_root`` to
    the ``build_coord_*`` functions below).
    """
    return repo / ".worktrees" / f"{handle}-coord"


# --------------------------------------------------------------------------- #
# Coord-state on-disk shape builders -- the five fixtures recurring across the
# read-seam migration suites (quickstart.md §4 rows). None of these write
# meta.json content directly; callers supply that via the write_*_meta
# callbacks so each module's own (intentionally uncentralized) _write_meta
# stays authoritative for that module's meta.json shape.
# --------------------------------------------------------------------------- #


def build_flat(
    repo: Path,
    handle: str,
    *,
    write_primary_meta: Callable[[Path], None],
) -> Path:
    """Flat (no coordination) topology -- the simplest materialized fixture.

    Returns the primary dir (after ``write_primary_meta`` has populated it).
    """
    primary_dir = repo / "kitty-specs" / handle
    write_primary_meta(primary_dir)
    return primary_dir


def build_coord_materialized(
    repo: Path,
    handle: str,
    branch: str,
    coord_root: Path,
    *,
    write_primary_meta: Callable[[Path], None],
    write_coord_meta: Callable[[Path], None],
) -> tuple[Path, Path]:
    """A coord-topology mission whose coordination worktree is FULLY
    populated (carries its own ``meta.json`` too).

    Returns ``(primary_dir, coord_mission_dir)``.
    """
    git_cmd(repo, "branch", branch)
    primary_dir = repo / "kitty-specs" / handle
    write_primary_meta(primary_dir)
    coord_mission_dir = coord_root / "kitty-specs" / handle
    write_coord_meta(coord_mission_dir)
    return primary_dir, coord_mission_dir


def build_coord_husk(
    repo: Path,
    handle: str,
    branch: str,
    coord_root: Path,
    *,
    write_primary_meta: Callable[[Path], None],
) -> Path:
    """Coord worktree materialized, but its mission dir has NO meta.json (husk).

    Returns the primary dir.
    """
    git_cmd(repo, "branch", branch)
    primary_dir = repo / "kitty-specs" / handle
    write_primary_meta(primary_dir)
    coord_mission_dir = coord_root / "kitty-specs" / handle
    coord_mission_dir.mkdir(parents=True)
    (coord_mission_dir / "status.events.jsonl").write_text("", encoding="utf-8")
    assert not (coord_mission_dir / "meta.json").exists(), "husk invariant: no coord meta.json"
    return primary_dir


def build_coord_worktree_empty(
    repo: Path,
    handle: str,
    branch: str,
    coord_root: Path,
    *,
    write_primary_meta: Callable[[Path], None],
) -> Path:
    """Coord root materialized (create window) but no mission dir under it yet.

    Returns the primary dir.
    """
    git_cmd(repo, "branch", branch)
    primary_dir = repo / "kitty-specs" / handle
    write_primary_meta(primary_dir)
    coord_root.mkdir(parents=True)  # EMPTY -- no kitty-specs/ under it at all
    return primary_dir


def build_coord_branch_deleted(
    repo: Path,
    handle: str,
    branch: str,
    *,
    write_primary_meta: Callable[[Path], None],
) -> Path:
    """``meta.json`` declares a coordination_branch that was never created in git.

    Returns the primary dir.
    """
    primary_dir = repo / "kitty-specs" / handle
    write_primary_meta(primary_dir)
    assert not (repo / ".worktrees").exists(), "no coord worktree for the deleted-branch case"
    return primary_dir
