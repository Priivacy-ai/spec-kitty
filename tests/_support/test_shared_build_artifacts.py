"""Unit coverage for the run-scoped shared wheel/sdist build (#80).

The protocol lives in :mod:`tests._support.shared_build_artifacts` so the
session ``build_artifacts`` fixture stays a thin shell; these tests drive that
protocol directly with a fake builder, which keeps them off the real
``python -m build`` entirely. Marked like the other ``tests/_support`` suite
(``unit`` + ``fast``) so the fast-tier shard selects it.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests._support.shared_build_artifacts import (
    SharedBuildError,
    default_wheel_sdist_builder,
    ensure_shared_build_artifacts,
    published_build_artifacts,
    run_scoped_shared_root,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_WHEEL_NAME = "spec_kitty_cli-3.2.0rc39-py3-none-any.whl"
_SDIST_NAME = "spec_kitty_cli-3.2.0rc39.tar.gz"
_SHARED_DIR_NAME = "shared-build-artifacts"


def _fake_factory(base: Path) -> SimpleNamespace:
    """Stand in for pytest's TempPathFactory with just ``getbasetemp``."""
    return SimpleNamespace(getbasetemp=lambda: base)


def _write_artifacts(outdir: Path) -> None:
    outdir.joinpath(_WHEEL_NAME).write_bytes(b"wheel-bytes")
    outdir.joinpath(_SDIST_NAME).write_bytes(b"sdist-bytes")


def test_worker_basetemp_parent_is_the_shared_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw3")
    worker_base = tmp_path / "run" / "popen-gw3"
    worker_base.mkdir(parents=True)
    assert run_scoped_shared_root(_fake_factory(worker_base)) == tmp_path / "run"


def test_serial_basetemp_is_already_the_shared_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    assert run_scoped_shared_root(_fake_factory(tmp_path / "run")) == tmp_path / "run"


def test_published_requires_a_complete_pair(tmp_path: Path) -> None:
    shared = tmp_path / _SHARED_DIR_NAME
    assert published_build_artifacts(shared) is None
    shared.mkdir()
    shared.joinpath(_WHEEL_NAME).write_bytes(b"w")
    assert published_build_artifacts(shared) is None
    shared.joinpath(_SDIST_NAME).write_bytes(b"s")
    published = published_build_artifacts(shared)
    assert published is not None
    assert published["wheel"].name == _WHEEL_NAME


def test_published_rejects_an_empty_artifact_file(tmp_path: Path) -> None:
    shared = tmp_path / _SHARED_DIR_NAME
    shared.mkdir()
    shared.joinpath(_WHEEL_NAME).write_bytes(b"")
    shared.joinpath(_SDIST_NAME).write_bytes(b"s")
    assert published_build_artifacts(shared) is None


def test_published_prefers_the_last_sorted_artifact(tmp_path: Path) -> None:
    shared = tmp_path / _SHARED_DIR_NAME
    shared.mkdir()
    shared.joinpath("spec_kitty_cli-1-py3-none-any.whl").write_bytes(b"a")
    shared.joinpath("spec_kitty_cli-9-py3-none-any.whl").write_bytes(b"b")
    shared.joinpath("spec_kitty_cli-1.tar.gz").write_bytes(b"c")
    shared.joinpath("spec_kitty_cli-9.tar.gz").write_bytes(b"d")
    published = published_build_artifacts(shared)
    assert published is not None
    assert published["wheel"].name == "spec_kitty_cli-9-py3-none-any.whl"
    assert published["sdist"].name == "spec_kitty_cli-9.tar.gz"


def test_ensure_reuses_a_publication_without_building(tmp_path: Path) -> None:
    shared = tmp_path / _SHARED_DIR_NAME
    shared.mkdir()
    _write_artifacts(shared)
    builds: list[Path] = []
    artifacts = ensure_shared_build_artifacts(tmp_path, builds.append)
    assert artifacts["wheel"] == shared / _WHEEL_NAME
    assert builds == []


def test_ensure_builds_once_then_later_callers_reuse(tmp_path: Path) -> None:
    builds: list[Path] = []

    def _building(outdir: Path) -> None:
        builds.append(outdir)
        _write_artifacts(outdir)

    first = ensure_shared_build_artifacts(tmp_path, _building)
    second = ensure_shared_build_artifacts(tmp_path, _building)
    assert first["wheel"] == tmp_path / _SHARED_DIR_NAME / _WHEEL_NAME
    assert second == first
    assert len(builds) == 1  # golden-count: cardinality-is-contract — exactly one build per run root
    assert not list(tmp_path.glob(f"{_SHARED_DIR_NAME}.staging-*"))


def test_ensure_surfaces_builder_failure_and_leaves_no_residue(tmp_path: Path) -> None:
    def _broken(outdir: Path) -> None:
        outdir.joinpath("junk.whl").write_bytes(b"x")
        raise SharedBuildError("Build failed: boom")

    with pytest.raises(SharedBuildError, match="boom"):
        ensure_shared_build_artifacts(tmp_path, _broken)
    assert not list(tmp_path.glob(f"{_SHARED_DIR_NAME}.staging-*"))
    assert not (tmp_path / _SHARED_DIR_NAME).exists()

    # The failed attempt must not poison later claims on the same run root.
    artifacts = ensure_shared_build_artifacts(tmp_path, _write_artifacts)
    assert artifacts["wheel"] == tmp_path / _SHARED_DIR_NAME / _WHEEL_NAME


def test_ensure_replaces_incomplete_published_residue(tmp_path: Path) -> None:
    residue = tmp_path / _SHARED_DIR_NAME
    residue.mkdir()
    residue.joinpath(_WHEEL_NAME).write_bytes(b"w")

    artifacts = ensure_shared_build_artifacts(tmp_path, _write_artifacts)
    assert artifacts["sdist"] == tmp_path / _SHARED_DIR_NAME / _SDIST_NAME


def test_conftest_build_artifacts_fixture_delegates_to_the_shared_protocol() -> None:
    """Pin the wiring itself: reverting the fixture to a private build must red here."""
    conftest = Path(__file__).resolve().parents[1] / "conftest.py"
    tree = ast.parse(conftest.read_text(encoding="utf-8"))
    fixture = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "build_artifacts"
    )
    referenced = {node.id for node in ast.walk(fixture) if isinstance(node, ast.Name)}
    assert {"ensure_shared_build_artifacts", "run_scoped_shared_root", "default_wheel_sdist_builder"} <= referenced


def test_default_builder_reports_stderr_and_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    class _FakeCompleted:
        returncode = 1
        stderr = "boom"

    def _fake_run(command, **kwargs: object) -> _FakeCompleted:
        seen["command"] = command
        seen.update(kwargs)
        return _FakeCompleted()

    monkeypatch.setattr("tests._support.shared_build_artifacts.subprocess.run", _fake_run)
    with pytest.raises(SharedBuildError, match="boom"):
        default_wheel_sdist_builder(Path("unused-outdir"))
    assert "--wheel" in str(seen["command"]) and "--sdist" in str(seen["command"])
    assert seen["cwd"] == Path(__file__).resolve().parents[2]
