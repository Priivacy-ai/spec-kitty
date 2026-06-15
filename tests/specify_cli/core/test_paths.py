"""Resolver behaviour for :mod:`specify_cli.core.paths`.

These tests pin the #1965 fix: ``SPECIFY_REPO_ROOT`` is authoritative whenever
the path it names is an existing directory, even if that directory has no
``.kittify/``. The determinism the doctor-skills error-schema test relies on
must flow from this resolver, not from test-local ``monkeypatch`` isolation.

C-003 regression guard: a real ``.kittify/`` project resolves to the *same*
canonical root whether or not ``SPECIFY_REPO_ROOT`` is set, so honouring the
env var changes nothing for already-correct projects.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.paths import locate_project_root

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _init_git_repo(root: Path) -> None:
    """Create a minimal main-repo ``.git`` directory so worktree-pointer
    detection treats ``root`` as a regular checkout (not a worktree)."""
    (root / ".git").mkdir(parents=True, exist_ok=True)


def test_env_root_authoritative_without_kittify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#1965: an existing ``SPECIFY_REPO_ROOT`` with no ``.kittify/`` is honoured.

    Determinism here comes from the resolver: even when the *current* checkout
    has a ``.kittify/`` (the ambient repo), pointing the env var at a
    ``.kittify``-less existing directory must win — the resolver must NOT fall
    through to a Tier-2 walk-up that leaks the ambient checkout.
    """
    # An ambient checkout that *does* have .kittify, used as the search start.
    ambient = tmp_path / "ambient-checkout"
    (ambient / ".kittify").mkdir(parents=True)
    _init_git_repo(ambient)

    # The env-named root: it exists but deliberately has NO .kittify/.
    env_root = tmp_path / "explicit-root"
    env_root.mkdir()

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(env_root))

    # Even starting the walk-up inside the ambient .kittify checkout, the env
    # var must take precedence and return the explicit (kittify-less) root.
    resolved = locate_project_root(start=ambient)

    assert resolved == env_root.resolve()
    assert resolved != ambient.resolve()


def test_env_root_ignored_when_path_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-existent ``SPECIFY_REPO_ROOT`` still falls through."""
    ambient = tmp_path / "ambient-checkout"
    (ambient / ".kittify").mkdir(parents=True)
    _init_git_repo(ambient)

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path / "does-not-exist"))

    resolved = locate_project_root(start=ambient)

    # The env var named a non-existent path → ignored → walk-up finds ambient.
    assert resolved == ambient.resolve()


def test_env_root_ignored_when_path_is_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file-valued ``SPECIFY_REPO_ROOT`` is not accepted as a project root."""
    ambient = tmp_path / "ambient-checkout"
    (ambient / ".kittify").mkdir(parents=True)
    _init_git_repo(ambient)
    marker_file = tmp_path / "not-a-directory"
    marker_file.write_text("not a repo root\n", encoding="utf-8")

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(marker_file))

    resolved = locate_project_root(start=ambient)

    assert resolved == ambient.resolve()


def test_c003_real_kittify_resolves_same_with_and_without_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-003: a real ``.kittify/`` project resolves identically with/without env.

    Honouring ``SPECIFY_REPO_ROOT`` must not change resolution for projects that
    were already correct: both paths flow through ``get_main_repo_root`` on the
    same directory, so the canonical root is identical.
    """
    project = tmp_path / "real-project"
    (project / ".kittify").mkdir(parents=True)
    _init_git_repo(project)

    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    without_env = locate_project_root(start=project)

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(project))
    with_env = locate_project_root(start=project)

    assert without_env == with_env == project.resolve()
