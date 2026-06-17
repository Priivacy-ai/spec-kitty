"""Shared topology-true fixture builders for the write-side characterization net.

Three REAL git topologies (NFR-002 — production-shaped, NO fabricated short ids,
NO single-repo stand-in):

* **primary**  — a real ``git init`` repo, full 26-char ULID ``mission_id``,
  ``kitty-specs/<slug>/`` with a real ``meta.json``, ``.kittify/config.yaml``.
* **coord**    — the primary repo PLUS a real coordination ``git worktree add``
  on a real ``kitty/mission-...`` branch, with ``coordination_branch`` declared
  in ``meta.json`` and the mission dir materialized inside the coord worktree.
* **submodule**— the mission repo embedded as a REAL git submodule (its ``.git``
  is a FILE pointer, not a directory — the #2011 / ``core/paths.py``
  ancestor-walk hazard surface).

Construction mirrors the proven real-topology fixtures in
``tests/specify_cli/core/test_resolve_canonical_root_submodule.py`` and
``tests/specify_cli/coordination/test_worktree_topology.py`` (real ``git``
invocations, real ``git submodule add``, real ``git worktree add``) — this WP
does not reinvent or fabricate them.

The handles returned here expose the primary feature_dir, the coord feature_dir
(when materialized), the repo root, the mission identity, and the expected
target branch, so every characterization test can drive a write site **from a
non-primary CWD without an explicit** ``repo_root=`` and compare the resolved
value against the factory resolver.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Production-shaped identities (NFR-002): full 26-char ULIDs, never short ids.
# ---------------------------------------------------------------------------

PRIMARY_MISSION_ID = "01KV9W0XPRIMARYTOPOLOGY001"
PRIMARY_MISSION_SLUG = "write-side-primary-01kv9w0x"

COORD_MISSION_ID = "01KV9W0XCOORDTOPOLOGY00001"
COORD_MISSION_SLUG = "write-side-coord-01kv9w0x"

SUBMODULE_MISSION_ID = "01KV9W0XSUBMODULETOPOLOGY1"
SUBMODULE_MISSION_SLUG = "write-side-submodule-01kv9w0x"

#: The base/target branch every fixture's ``meta.json`` declares. Distinct from
#: any lane/coord branch a CWD may be parked on, so the FR-004 oracle (git HEAD
#: vs ``target_branch``) is observable.
TARGET_BRANCH = "main"

KITTY_SPECS = "kitty-specs"


def _run_git(cwd: Path, *args: str) -> None:
    """Run a git command in ``cwd``, raising on failure (real topology only)."""
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    """``git init`` a repo (default branch ``main``) with a deterministic id."""
    root.mkdir(parents=True, exist_ok=True)
    _run_git(root, "init", "-q", "-b", TARGET_BRANCH)
    _run_git(root, "config", "user.email", "wp01@example.test")
    _run_git(root, "config", "user.name", "WP01 Fixture")
    # Allow file-protocol submodule add inside the test sandbox.
    _run_git(root, "config", "protocol.file.allow", "always")
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    _run_git(root, "add", "README.md")
    _run_git(root, "commit", "-q", "-m", "init")


def _write_mission(
    repo: Path,
    *,
    mission_id: str,
    slug: str,
    coordination_branch: str | None = None,
) -> Path:
    """Write ``.kittify/config.yaml`` + a mission dir carrying a real ULID id.

    Returns the mission ``feature_dir``.
    """
    kittify = repo / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text("agents: {}\n", encoding="utf-8")

    feature_dir = repo / KITTY_SPECS / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "mission_id": mission_id,
        "mid8": mission_id[:8],
        "mission_slug": slug,
        "target_branch": TARGET_BRANCH,
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    (feature_dir / "meta.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )
    return feature_dir


# ---------------------------------------------------------------------------
# Handles
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrimaryTopology:
    """A plain spec-kitty repo: ``.git`` DIRECTORY, no coord, no lanes."""

    repo_root: Path
    feature_dir: Path
    mission_id: str
    mission_slug: str
    target_branch: str = TARGET_BRANCH

    @property
    def expected_primary_root(self) -> Path:
        return self.repo_root.resolve()


@dataclass(frozen=True)
class CoordTopology:
    """Primary repo + a REAL coordination worktree on a ``kitty/mission`` branch."""

    main_root: Path
    coord_worktree: Path
    coord_branch: str
    primary_feature_dir: Path
    coord_feature_dir: Path
    mission_id: str
    mission_slug: str
    target_branch: str = TARGET_BRANCH

    @property
    def expected_primary_root(self) -> Path:
        return self.main_root.resolve()


@dataclass(frozen=True)
class SubmoduleTopology:
    """Mission repo embedded as a REAL git submodule (``.git`` is a FILE)."""

    superproject_root: Path
    submodule_root: Path
    feature_dir: Path
    mission_id: str
    mission_slug: str
    target_branch: str = TARGET_BRANCH

    @property
    def expected_primary_root(self) -> Path:
        # The submodule's own root — never the enclosing parent repo (#2011).
        return self.submodule_root.resolve()


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def build_primary(tmp_path: Path) -> PrimaryTopology:
    """A plain (non-worktree, non-submodule) spec-kitty repo on ``main``."""
    repo = tmp_path / "primary-checkout"
    _init_repo(repo)
    feature_dir = _write_mission(
        repo, mission_id=PRIMARY_MISSION_ID, slug=PRIMARY_MISSION_SLUG
    )
    _run_git(repo, "add", "-A")
    _run_git(repo, "commit", "-q", "-m", "kittify + mission")
    return PrimaryTopology(
        repo_root=repo,
        feature_dir=feature_dir,
        mission_id=PRIMARY_MISSION_ID,
        mission_slug=PRIMARY_MISSION_SLUG,
    )


def build_coord(tmp_path: Path) -> CoordTopology:
    """Build a real coordination ``git worktree add`` on a ``kitty/mission`` branch.

    The worktree's ``.git`` is a FILE with the ``.git/worktrees/<name>``
    topology, so a canonical resolver must follow the pointer back to the main
    repo. ``meta.json`` (primary + coord) declares ``coordination_branch`` so the
    status surface resolves to the coord authority (C-007), never ``primary_root``.
    """
    main = tmp_path / "coord-main"
    _init_repo(main)
    coord_branch = f"kitty/mission-{COORD_MISSION_SLUG}-{COORD_MISSION_ID[:8].lower()}"
    primary_feature_dir = _write_mission(
        main,
        mission_id=COORD_MISSION_ID,
        slug=COORD_MISSION_SLUG,
        coordination_branch=coord_branch,
    )
    _run_git(main, "add", "-A")
    _run_git(main, "commit", "-q", "-m", "kittify + mission")

    worktree = tmp_path / ".worktrees" / f"{COORD_MISSION_SLUG}-{COORD_MISSION_ID[:8].lower()}-coord"
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _run_git(main, "worktree", "add", "-q", "-b", coord_branch, str(worktree))

    # The coord worktree branches from main, which already carries the mission
    # dir, so the mission dir is materialized inside the coord worktree by
    # checkout (the status/coord write authority). resolve_status_surface lands
    # there, not on primary. Re-assert it exists rather than re-committing
    # identical content (a no-op commit fails).
    coord_feature_dir = worktree / KITTY_SPECS / COORD_MISSION_SLUG
    if not (coord_feature_dir / "meta.json").exists():  # pragma: no cover - defensive
        _write_mission(
            worktree,
            mission_id=COORD_MISSION_ID,
            slug=COORD_MISSION_SLUG,
            coordination_branch=coord_branch,
        )
        _run_git(worktree, "add", "-A")
        _run_git(worktree, "commit", "-q", "-m", "coord mission dir")

    return CoordTopology(
        main_root=main,
        coord_worktree=worktree,
        coord_branch=coord_branch,
        primary_feature_dir=primary_feature_dir,
        coord_feature_dir=coord_feature_dir,
        mission_id=COORD_MISSION_ID,
        mission_slug=COORD_MISSION_SLUG,
    )


def build_submodule(tmp_path: Path) -> SubmoduleTopology:
    """Build a REAL git submodule whose ``.git`` is a FILE pointer.

    Layout::

        <tmp>/superproject/                parent repo, .git DIRECTORY, NO .kittify
        <tmp>/superproject/mission-repo/   submodule, .git FILE (gitdir: pointer),
                                           carries its own .kittify + ULID mission

    The submodule's ``.git`` FILE is the topology that makes the ancestor walk
    hazardous — a naive ``.parent.parent`` walks UP into the superproject; the
    canonical resolver must STOP at the submodule root.
    """
    parent = tmp_path / "superproject"
    child_source = tmp_path / "mission-repo-source"
    _init_repo(parent)
    _init_repo(child_source)
    feature_dir_in_source = _write_mission(
        child_source, mission_id=SUBMODULE_MISSION_ID, slug=SUBMODULE_MISSION_SLUG
    )
    assert feature_dir_in_source  # constructed for clarity
    _run_git(child_source, "add", "-A")
    _run_git(child_source, "commit", "-q", "-m", "kittify + mission")

    _run_git(
        parent,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(child_source),
        "mission-repo",
    )
    _run_git(parent, "commit", "-q", "-m", "add mission-repo submodule")

    submodule = parent / "mission-repo"
    if not (submodule / ".kittify" / "config.yaml").exists():
        _write_mission(
            submodule, mission_id=SUBMODULE_MISSION_ID, slug=SUBMODULE_MISSION_SLUG
        )
    feature_dir = submodule / KITTY_SPECS / SUBMODULE_MISSION_SLUG
    return SubmoduleTopology(
        superproject_root=parent,
        submodule_root=submodule,
        feature_dir=feature_dir,
        mission_id=SUBMODULE_MISSION_ID,
        mission_slug=SUBMODULE_MISSION_SLUG,
    )
