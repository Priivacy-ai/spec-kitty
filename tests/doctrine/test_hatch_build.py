"""Unit coverage for the doctrine wheel's custom build hook (FR-010, D7).

``tests/architectural/test_doctrine_wheel_closure.py`` pins the manifest
shape and confirms an actually-executed ``hatch build`` (research.md §D7).
These tests instead drive ``DoctrinePacksSiblingBuildHook.initialize`` directly
in-process, so ordinary pytest coverage instrumentation sees the hook's own
logic (the real ``hatch build`` subprocess in D7 runs outside pytest and
is invisible to coverage.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

# The pre-review regression gate captures its baseline in an ephemeral ``uv run``
# worktree whose venv installs neither ``[build-system].requires`` nor the
# ``test`` extra's build-only members, so ``hatchling`` is absent there (it
# resolves only under ``extra == 'test'`` in uv.lock). Guard the transitive
# ``doctrine.hatch_build`` -> ``hatchling`` import below so that degenerate venv
# SKIPS this module cleanly at collection instead of raising ModuleNotFoundError
# and being miscounted as a "new failure" (issue #3224). The normal test job
# installs the ``test`` extra, so ``hatchling`` is present and every test runs.
pytest.importorskip("hatchling")

from doctrine.hatch_build import DoctrinePacksSiblingBuildHook

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ``build_data["force_include"]`` is always a ``dict[str, str]`` mapping an
# absolute source path to its in-wheel destination; typed explicitly (rather
# than hatchling's own ``dict[str, Any]``) so index/containment assertions
# below type-check under mypy --strict.
_BuildData = dict[str, dict[str, str]]


def _make_hook(root: Path, target_name: str = "wheel") -> DoctrinePacksSiblingBuildHook:
    return DoctrinePacksSiblingBuildHook(
        root=str(root),
        config={},
        build_config=None,
        metadata=None,  # type: ignore[arg-type]
        directory=str(root / "dist"),
        target_name=target_name,
    )


def _make_doctrine_project(tmp_path: Path, *, with_packs: bool) -> Path:
    """Build a scratch ``.../src/doctrine`` project tree, optionally with a
    repo-root sibling ``packs/`` two levels up."""
    repo_root = tmp_path / "repo"
    doctrine_root = repo_root / "src" / "doctrine"
    doctrine_root.mkdir(parents=True)
    (doctrine_root / "__init__.py").write_text("")
    (doctrine_root / "resolver.py").write_text("")
    (doctrine_root / "agent_profiles").mkdir()
    (doctrine_root / "pyproject.toml").write_text("")
    (doctrine_root / "hatch_build.py").write_text("")
    (doctrine_root / "dist").mkdir()
    (doctrine_root / "__pycache__").mkdir()
    if with_packs:
        (repo_root / "packs" / "built-in").mkdir(parents=True)
    return doctrine_root


def test_non_wheel_target_is_a_no_op(tmp_path: Path) -> None:
    doctrine_root = _make_doctrine_project(tmp_path, with_packs=True)
    hook = _make_hook(doctrine_root, target_name="sdist")
    build_data: _BuildData = {}
    hook.initialize("0.0.0", build_data)
    assert build_data == {}


def test_wheel_target_force_includes_package_children_and_packs(tmp_path: Path) -> None:
    doctrine_root = _make_doctrine_project(tmp_path, with_packs=True)
    hook = _make_hook(doctrine_root)
    build_data: _BuildData = {}
    hook.initialize("0.0.0", build_data)

    force_include = build_data["force_include"]
    assert force_include[str(doctrine_root / "__init__.py")] == "doctrine/__init__.py"
    assert force_include[str(doctrine_root / "resolver.py")] == "doctrine/resolver.py"
    assert force_include[str(doctrine_root / "agent_profiles")] == "doctrine/agent_profiles"

    # Build-only entries are never force-included under doctrine/.
    assert str(doctrine_root / "pyproject.toml") not in force_include
    assert str(doctrine_root / "hatch_build.py") not in force_include
    assert str(doctrine_root / "dist") not in force_include
    assert str(doctrine_root / "__pycache__") not in force_include

    # packs/ resolves two levels up from self.root and lands as a sibling.
    packs_dir = doctrine_root.parent.parent / "packs"
    assert force_include[str(packs_dir)] == "packs"


def test_missing_packs_sibling_is_skipped_silently(tmp_path: Path) -> None:
    doctrine_root = _make_doctrine_project(tmp_path, with_packs=False)
    hook = _make_hook(doctrine_root)
    build_data: _BuildData = {}

    hook.initialize("0.0.0", build_data)

    force_include = build_data["force_include"]
    packs_dir = doctrine_root.parent.parent / "packs"
    assert str(packs_dir) not in force_include
    # The doctrine package entries are still force-included.
    assert force_include[str(doctrine_root / "resolver.py")] == "doctrine/resolver.py"


def test_repeated_initialize_merges_into_existing_force_include(tmp_path: Path) -> None:
    """``build_data.setdefault`` must not clobber a pre-populated force_include."""
    doctrine_root = _make_doctrine_project(tmp_path, with_packs=True)
    hook = _make_hook(doctrine_root)
    build_data: _BuildData = {"force_include": {"/already/there": "kept"}}

    hook.initialize("0.0.0", build_data)

    force_include = build_data["force_include"]
    assert force_include["/already/there"] == "kept"
    assert force_include[str(doctrine_root / "resolver.py")] == "doctrine/resolver.py"
