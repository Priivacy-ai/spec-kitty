"""Windows acceptance tests for the confined coordination writer."""

from __future__ import annotations

import importlib
import os
import stat
from pathlib import Path

import pytest

from specify_cli.coordination import atomic_write as aw
from specify_cli.coordination import windows_confined_fs as wfs


pytestmark = [
    pytest.mark.windows_ci,
    pytest.mark.skipif(
        os.name != "nt",
        reason="Windows confined-writer contract",
    ),
]


def test_windows_confined_writer_pins_directories_against_rename(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "coord"
    parent = worktree / "mission"
    target = parent / "status.json"
    parent.mkdir(parents=True)

    with (
        wfs._locked_parent(worktree, target),
        pytest.raises(OSError) as exc_info,
    ):
        parent.rename(worktree / "moved")

    assert exc_info.value.winerror == 32
    assert parent.is_dir()
    assert not (worktree / "moved").exists()


def test_windows_confined_write_atomically_replaces_existing_file(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "kitty-specs" / "mission" / "analysis-report.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"before\n")

    written = aw._write_confined_artifact_bytes(
        worktree,
        target,
        b"after\n",
        resolve=aw._resolve_confined_artifact_path,
    )

    assert written == target.resolve()
    assert target.read_bytes() == b"after\n"
    assert list(target.parent.glob(".spec-kitty-*.tmp")) == []


def test_windows_confined_unlink_removes_regular_artifact(tmp_path: Path) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "kitty-specs" / "mission" / "status.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"{}\n")

    aw._unlink_confined_artifact_path(
        worktree,
        target,
        resolve=aw._resolve_confined_artifact_path,
    )

    assert not target.exists()


def test_windows_confined_unlink_missing_artifact_is_idempotent(tmp_path: Path) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "kitty-specs" / "mission" / "status.json"
    target.parent.mkdir(parents=True)

    aw._unlink_confined_artifact_path(
        worktree,
        target,
        resolve=aw._resolve_confined_artifact_path,
    )

    assert not target.exists()


def test_windows_confined_unlink_missing_parent_is_idempotent(tmp_path: Path) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "missing" / "nested" / "status.json"
    worktree.mkdir()

    aw._unlink_confined_artifact_path(
        worktree,
        target,
        resolve=aw._resolve_confined_artifact_path,
    )

    assert not target.exists()


def test_windows_confined_write_and_unlink_reject_directory_target(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "status.json"
    target.mkdir(parents=True)

    with pytest.raises(ValueError, match="unsafe path changed during write"):
        aw._write_confined_artifact_bytes(
            worktree,
            target,
            b"must-not-replace-directory",
            resolve=aw._resolve_confined_artifact_path,
        )
    with pytest.raises(ValueError, match="not a regular file"):
        aw._unlink_confined_artifact_path(
            worktree,
            target,
            resolve=aw._resolve_confined_artifact_path,
        )

    assert target.is_dir()


def test_windows_confined_writer_rejects_parent_reparse_point(tmp_path: Path) -> None:
    worktree = tmp_path / "coord"
    outside = tmp_path / "outside"
    worktree.mkdir()
    outside.mkdir()
    linked_parent = worktree / "linked"
    os.symlink(outside, linked_parent, target_is_directory=True)
    target = linked_parent / "escape.txt"

    with pytest.raises(ValueError, match="unsafe path changed during write"):
        aw._write_confined_artifact_bytes(
            worktree,
            target,
            b"must-not-escape",
            resolve=lambda _root, candidate: candidate,
        )

    assert not (outside / "escape.txt").exists()


def test_windows_confined_writer_rejects_parent_junction(tmp_path: Path) -> None:
    worktree = tmp_path / "coord"
    outside = tmp_path / "outside"
    worktree.mkdir()
    outside.mkdir()
    junction = worktree / "junction"
    winapi = importlib.import_module("_winapi")
    winapi.CreateJunction(str(outside), str(junction))

    with pytest.raises(ValueError, match="unsafe path changed during write"):
        aw._write_confined_artifact_bytes(
            worktree,
            junction / "escape.txt",
            b"must-not-escape",
            resolve=lambda _root, candidate: candidate,
        )

    assert not (outside / "escape.txt").exists()


def test_windows_confined_unlink_rejects_leaf_reparse_point(tmp_path: Path) -> None:
    worktree = tmp_path / "coord"
    outside = tmp_path / "outside.txt"
    worktree.mkdir()
    outside.write_bytes(b"outside")
    linked_artifact = worktree / "status.json"
    os.symlink(outside, linked_artifact)

    with pytest.raises(ValueError, match="reparse point"):
        aw._unlink_confined_artifact_path(
            worktree,
            linked_artifact,
            resolve=lambda _root, candidate: candidate,
        )

    assert outside.read_bytes() == b"outside"


@pytest.mark.parametrize(
    "unsafe_name",
    ["status.json:secret", "CON", "trailing. "],
)
def test_windows_confined_writer_rejects_unsafe_component(
    tmp_path: Path,
    unsafe_name: str,
) -> None:
    worktree = tmp_path / "coord"
    worktree.mkdir()

    with pytest.raises(ValueError, match="unsafe path changed during write"):
        aw._write_confined_artifact_bytes(
            worktree,
            worktree / unsafe_name,
            b"secret",
            resolve=lambda _root, candidate: candidate,
        )

    assert list(worktree.iterdir()) == []


def test_windows_confined_writer_creates_parents_relative_to_root_handle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "kitty-specs" / "mission" / "status.json"
    worktree.mkdir()
    path_opened: list[Path] = []
    relative_names: list[str] = []
    original_open_handle = wfs._open_handle
    original_open_relative_handle = wfs._open_relative_handle

    def record_path_open(path: Path, **kwargs: int) -> int:
        path_opened.append(path)
        return original_open_handle(path, **kwargs)

    def record_relative_open(
        parent_handle: int,
        name: str,
        path: Path,
        **kwargs: int,
    ) -> int:
        relative_names.append(name)
        return original_open_relative_handle(
            parent_handle,
            name,
            path,
            **kwargs,
        )

    monkeypatch.setattr(wfs, "_open_handle", record_path_open)
    monkeypatch.setattr(wfs, "_open_relative_handle", record_relative_open)

    aw._write_confined_artifact_bytes(
        worktree,
        target,
        b"{}\n",
        resolve=aw._resolve_confined_artifact_path,
    )

    assert target.read_bytes() == b"{}\n"
    assert path_opened and set(path_opened) == {worktree.resolve()}
    assert {"kitty-specs", "mission"}.issubset(relative_names)
    assert all("/" not in name and "\\" not in name for name in relative_names)


def test_windows_confined_writer_does_not_create_outside_after_junction_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = tmp_path / "coord"
    outside = tmp_path / "outside"
    anchor = worktree / "anchor"
    target = anchor / "nested" / "status.json"
    worktree.mkdir()
    outside.mkdir()
    original_ensure = wfs.ensure_confined_parent_windows
    winapi = importlib.import_module("_winapi")

    def swap_after_secure_parent_creation(root: Path, candidate: Path) -> None:
        original_ensure(root, candidate)
        candidate.parent.rmdir()
        anchor.rmdir()
        winapi.CreateJunction(str(outside), str(anchor))

    monkeypatch.setattr(
        wfs,
        "ensure_confined_parent_windows",
        swap_after_secure_parent_creation,
    )

    with pytest.raises(ValueError, match="outside worktree"):
        aw._write_confined_artifact_bytes(
            worktree,
            target,
            b"must-not-escape",
            resolve=aw._resolve_confined_artifact_path,
        )

    assert not (outside / "nested").exists()


def test_windows_confined_writer_cleans_temp_when_rename_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "status.json"
    worktree.mkdir()
    target.write_bytes(b"before")

    def fail_rename(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected rename failure")

    monkeypatch.setattr(wfs, "_rename_temp_handle", fail_rename)

    with pytest.raises(OSError, match="injected rename failure"):
        aw._write_confined_artifact_bytes(
            worktree,
            target,
            b"after",
            resolve=aw._resolve_confined_artifact_path,
        )

    assert target.read_bytes() == b"before"
    assert list(worktree.glob(".spec-kitty-*.tmp")) == []


def test_windows_confined_writer_does_not_use_path_based_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "status.json"
    worktree.mkdir()

    def reject_path_replace(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("path-based replace is not confined")

    monkeypatch.setattr(wfs.os, "replace", reject_path_replace)
    aw._write_confined_artifact_bytes(
        worktree,
        target,
        b"{}\n",
        resolve=aw._resolve_confined_artifact_path,
    )

    assert target.read_bytes() == b"{}\n"


def test_windows_confined_writer_readonly_failure_preserves_target(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "coord"
    target = worktree / "status.json"
    worktree.mkdir()
    target.write_bytes(b"before")
    os.chmod(target, stat.S_IREAD)
    try:
        with pytest.raises(OSError):
            aw._write_confined_artifact_bytes(
                worktree,
                target,
                b"after",
                resolve=aw._resolve_confined_artifact_path,
            )

        assert target.read_bytes() == b"before"
        assert list(worktree.glob(".spec-kitty-*.tmp")) == []
    finally:
        os.chmod(target, stat.S_IWRITE)
