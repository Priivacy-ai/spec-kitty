"""Regression: ``find_repo_root`` must stop at a nested-clone boundary (WP07, FR-007).

A *nested clone* is an independent git clone (its own ``.git`` **directory**)
living inside an outer spec-kitty primary. Two root authorities exist:

* :func:`specify_cli.task_utils.support.find_repo_root` (delegates to
  :func:`specify_cli.core.paths.locate_project_root` +
  :func:`specify_cli.core.paths.get_main_repo_root`), and
* :func:`specify_cli.core.paths.resolve_canonical_root`.

On base they *disagree* for a nested clone that omits ``.kittify``:
``find_repo_root`` re-anchors up to the OUTER primary (because
``locate_project_root`` only stops at a ``.git`` directory when ``.kittify`` is
present, otherwise walking UP), while ``resolve_canonical_root`` correctly stops
at the nested clone's ``.git`` directory (rule 1). These tests pin the fix:
both resolvers must return the nested clone itself.

The nested clone MUST omit ``.kittify`` — with ``.kittify`` present both
resolvers already agree at the nested clone and there is no disagreement to fix.

Pins #2610.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.core.paths import resolve_canonical_root
from specify_cli.task_utils.support import find_repo_root


pytestmark = [pytest.mark.regression, pytest.mark.git_repo]


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo(path: Path) -> Path:
    """Create a real git repo (its own ``.git`` directory)."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "--initial-branch=main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "config", "commit.gpgsign", "false")
    (path / "README.md").write_text("hi\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "init")
    return path.resolve()


def _make_primary(path: Path) -> Path:
    """A spec-kitty primary: a git repo that carries the ``.kittify`` marker."""
    repo = _init_repo(path)
    (repo / ".kittify").mkdir()
    return repo


@pytest.mark.regression
@pytest.mark.git_repo
def test_nested_clone_boundary_resolvers_agree(tmp_path: Path) -> None:
    """Both resolvers must stop at a nested clone that omits ``.kittify``.

    This is the red-first guard for #2610: on base ``find_repo_root``
    re-anchors to the outer primary while ``resolve_canonical_root`` returns
    the nested clone; after the fix both return the nested clone.
    """
    primary = _make_primary(tmp_path / "primary")
    # A nested clone: its own ``.git`` directory, and crucially NO ``.kittify``.
    nested = _init_repo(primary / "vendor" / "nested-clone")
    assert not (nested / ".kittify").exists()

    canonical = resolve_canonical_root(nested)
    detected = find_repo_root(nested)

    # resolve_canonical_root already stops at the nested clone (rule 1).
    assert canonical == nested
    # find_repo_root must agree — not re-anchor up to the outer primary.
    assert detected == nested, f"find_repo_root re-anchored past the nested-clone .git-dir boundary to {detected} instead of stopping at {nested}"
    assert detected != primary


@pytest.mark.regression
@pytest.mark.git_repo
def test_standalone_clone_resolves_to_self_control(tmp_path: Path) -> None:
    """Control: a standalone (non-nested) clone already resolves to self.

    Documents the phantom re-anchor (research Decision 0): a standalone clone
    that is not inside any primary already agrees on both resolvers, so the
    genuine bug is confined to the *nested* case.
    """
    standalone = _init_repo(tmp_path / "standalone-clone")
    assert not (standalone / ".kittify").exists()

    assert resolve_canonical_root(standalone) == standalone
    assert find_repo_root(standalone) == standalone
