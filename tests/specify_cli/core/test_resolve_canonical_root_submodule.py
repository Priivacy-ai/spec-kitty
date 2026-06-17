"""WP06 / FR-007 / C-IC06 — submodule root unification for ``resolve_canonical_root``.

These tests pin the launch-blocker (#6 / #2011): invoked from inside a real git
submodule (whose ``.git`` is a FILE with a ``gitdir: ../.git/modules/<name>``
pointer), ``resolve_canonical_root`` must STOP at the submodule root rather than
walking UP into the parent repository. After the fix the two root authorities —
``resolve_canonical_root`` and ``locate_project_root`` — must AGREE across the
{primary, coord-worktree, submodule} topology matrix (NFR-001).

Topology-true discipline (NFR-002): every fixture is a REAL git topology built
with real ``git`` invocations — a real ``git submodule add`` child whose ``.git``
is a FILE, a real ``git worktree add`` coordination worktree, and a full 26-char
ULID ``mission_id``. A fabricated single-repo stand-in cannot exhibit the
non-worktree ``.git``-FILE pointer path and would pass vacuously — the exact trap
the prior mission hit.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import specify_cli.core.paths as paths_module
from specify_cli.core.paths import (
    _read_worktree_gitdir,
    locate_project_root,
    resolve_canonical_root,
)
from specify_cli.workspace.assert_initialized import (
    SpecKittyNotInitialized,
    assert_initialized,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# A real, full-length (26-char) ULID for the submodule's mission. NFR-002 forbids
# fabricated short ids; this is the canonical machine-identity shape.
SUBMODULE_MISSION_ID = "01KV8NPCDEBBIESUBMODULE001"
SUBMODULE_MISSION_SLUG = "elissar-mission-01kv8npc"
COORD_MISSION_ID = "01KV8NPCWP06COORDREPRO0001"


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
    """``git init`` a repo with a deterministic identity and an initial commit."""
    root.mkdir(parents=True, exist_ok=True)
    _run_git(root, "init", "-q")
    _run_git(root, "config", "user.email", "wp06@example.test")
    _run_git(root, "config", "user.name", "WP06 Fixture")
    # Allow file-protocol submodule add inside the test sandbox.
    _run_git(root, "config", "protocol.file.allow", "always")
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    _run_git(root, "add", "README.md")
    _run_git(root, "commit", "-q", "-m", "init")


def _write_kittify_mission(repo: Path, *, mission_id: str, slug: str) -> Path:
    """Write a ``.kittify/config.yaml`` + a mission dir carrying a real ULID id."""
    kittify = repo / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text("agents: {}\n", encoding="utf-8")

    mission_dir = repo / "kitty-specs" / slug
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "mission_slug": slug,
                "target_branch": "main",
            }
        ),
        encoding="utf-8",
    )
    return mission_dir


def _build_submodule_fixture(tmp_path: Path) -> Path:
    """Build a REAL git submodule and return the submodule working-tree path.

    Layout::

        <tmp>/econcept-next/            parent repo, .git is a DIRECTORY, NO .kittify
        <tmp>/econcept-next/elissar-api/  submodule, .git is a FILE (gitdir: pointer),
                                          carries its own .kittify + a ULID mission

    The submodule's ``.git`` FILE is the topology that makes
    ``_read_worktree_gitdir`` return ``None`` (non-worktree pointer) — the exact
    branch the fix targets.
    """
    parent = tmp_path / "econcept-next"
    child_source = tmp_path / "elissar-api-source"
    _init_repo(parent)
    _init_repo(child_source)
    # Give the child a substantive commit so it can be added as a submodule.
    _write_kittify_mission(
        child_source, mission_id=SUBMODULE_MISSION_ID, slug=SUBMODULE_MISSION_SLUG
    )
    _run_git(child_source, "add", "-A")
    _run_git(child_source, "commit", "-q", "-m", "kittify + mission")

    # Real submodule add: this is what makes the child's .git a FILE pointer.
    # ``-c protocol.file.allow=always`` is required because the submodule clone
    # uses the local ``file`` transport, which modern git refuses by default.
    _run_git(
        parent,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(child_source),
        "elissar-api",
    )
    _run_git(parent, "commit", "-q", "-m", "add elissar-api submodule")

    submodule = parent / "elissar-api"
    # Ensure the submodule carries its own .kittify + mission on disk (it tracks
    # the committed child content, but re-assert to be explicit and robust).
    if not (submodule / ".kittify" / "config.yaml").exists():
        _write_kittify_mission(
            submodule, mission_id=SUBMODULE_MISSION_ID, slug=SUBMODULE_MISSION_SLUG
        )
    return submodule


def _build_primary_fixture(tmp_path: Path) -> Path:
    """A plain (non-submodule) spec-kitty repo: ``.git`` DIRECTORY + ``.kittify``."""
    primary = tmp_path / "primary-checkout"
    _init_repo(primary)
    _write_kittify_mission(primary, mission_id=COORD_MISSION_ID, slug="primary-mission-01kv8npc")
    _run_git(primary, "add", "-A")
    _run_git(primary, "commit", "-q", "-m", "kittify + mission")
    return primary


def _build_coord_worktree_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Build a real coordination ``git worktree add`` and return (main, worktree).

    The worktree's ``.git`` is a FILE with the ``.git/worktrees/<name>`` topology,
    so ``resolve_canonical_root`` must follow the pointer back to the main repo.
    """
    main = tmp_path / "coord-main"
    _init_repo(main)
    _write_kittify_mission(main, mission_id=COORD_MISSION_ID, slug="coord-mission-01kv8npc")
    _run_git(main, "add", "-A")
    _run_git(main, "commit", "-q", "-m", "kittify + mission")

    worktree = tmp_path / "coord-worktree"
    _run_git(main, "worktree", "add", "-q", "-b", "coord-branch", str(worktree))
    return main, worktree


# ---------------------------------------------------------------------------
# T029 — resolve_canonical_root must return the SUBMODULE root (real submodule)
# ---------------------------------------------------------------------------


class TestResolveCanonicalRootSubmodule:
    """The submodule's own root — never the enclosing parent repo."""

    def test_submodule_git_is_a_file_nonworktree_pointer(self, tmp_path: Path) -> None:
        """Guard the fixture: the submodule ``.git`` is a FILE that is NOT a
        worktree pointer (``_read_worktree_gitdir`` returns ``None``).  A reviewer
        relies on this to confirm the fixture exercises the real bug branch.
        """
        submodule = _build_submodule_fixture(tmp_path)
        git_marker = submodule / ".git"
        assert git_marker.is_file(), "submodule .git must be a FILE, not a directory"
        assert _read_worktree_gitdir(git_marker) is None, (
            "submodule .git pointer must NOT be a worktrees-topology pointer "
            "(it points at .git/modules/<name>)"
        )

    def test_resolve_canonical_root_returns_submodule_root(self, tmp_path: Path) -> None:
        """The failing assertion before the fix: pre-fix resolves the PARENT."""
        submodule = _build_submodule_fixture(tmp_path)
        resolved = resolve_canonical_root(submodule)
        assert resolved == submodule.resolve(), (
            f"resolve_canonical_root must stop at the submodule root; "
            f"got {resolved!r} (parent={submodule.parent.resolve()!r})"
        )

    def test_assert_initialized_does_not_raise_in_submodule(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Operator-facing symptom (#6): ``assert_initialized`` from inside an
        initialized submodule must NOT raise ``SPEC_KITTY_REPO_NOT_INITIALIZED``.
        """
        submodule = _build_submodule_fixture(tmp_path)
        monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
        monkeypatch.chdir(submodule)
        try:
            resolved = assert_initialized()
        except SpecKittyNotInitialized as exc:  # pragma: no cover - failure path
            pytest.fail(
                f"assert_initialized raised inside an initialized submodule: {exc}"
            )
        assert resolved == submodule.resolve()


# ---------------------------------------------------------------------------
# T031 — equivalence over {primary, coord-worktree, submodule}: both resolvers agree
# ---------------------------------------------------------------------------


class TestResolverEquivalence:
    """``resolve_canonical_root`` and ``locate_project_root`` agree (NFR-001)."""

    def test_primary_checkout_resolvers_agree(self, tmp_path: Path) -> None:
        primary = _build_primary_fixture(tmp_path)
        canonical = resolve_canonical_root(primary)
        located = locate_project_root(primary)
        assert canonical == located == primary.resolve()

    def test_coord_worktree_resolvers_agree(self, tmp_path: Path) -> None:
        main, worktree = _build_coord_worktree_fixture(tmp_path)
        canonical = resolve_canonical_root(worktree)
        located = locate_project_root(worktree)
        # Both must follow the worktree pointer back to the MAIN repo.
        assert canonical == located == main.resolve()
        assert canonical != worktree.resolve()

    def test_submodule_resolvers_agree(self, tmp_path: Path) -> None:
        submodule = _build_submodule_fixture(tmp_path)
        canonical = resolve_canonical_root(submodule)
        located = locate_project_root(submodule)
        assert canonical == located == submodule.resolve()


def test_module_under_test_is_the_worktree_copy() -> None:
    """Tripwire: confirm the test exercises THIS lane's ``paths.py``.

    The editable install may point at the primary checkout; running with
    ``PYTHONPATH=<worktree>/src`` makes the worktree copy authoritative. This
    keeps the captured red/green trustworthy (live-evidence discipline).
    """
    assert paths_module.__file__.endswith("src/specify_cli/core/paths.py")
