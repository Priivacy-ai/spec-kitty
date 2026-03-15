"""Scope: utils unit tests — no real git or subprocesses."""

import sys

import pytest

from specify_cli.core import ensure_directory, format_path, get_platform, safe_remove

pytestmark = pytest.mark.fast


def test_ensure_directory_creates_path(tmp_path):
    """ensure_directory creates the full nested path and returns it."""
    # Arrange
    target = tmp_path / "nested" / "dir"

    # Assumption check
    assert not target.exists(), "target must not exist before the call"

    # Act
    returned = ensure_directory(target)

    # Assert
    assert target.is_dir()
    assert returned == target


def test_safe_remove_handles_files_and_dirs(tmp_path):
    """safe_remove deletes files and directories, returning False for already-absent paths."""
    # Arrange
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    dir_path = tmp_path / "dir"
    dir_path.mkdir()
    (dir_path / "child").write_text("child")

    # Assumption check
    assert file_path.exists() and dir_path.exists(), "both paths must exist before removal"

    # Act / Assert
    assert safe_remove(file_path) is True
    assert not file_path.exists()

    assert safe_remove(dir_path) is True
    assert not dir_path.exists()

    assert safe_remove(dir_path) is False  # already removed


def test_format_path_relative(tmp_path):
    """format_path returns a relative path when a base is given, absolute otherwise."""
    # Arrange
    base = tmp_path / "base"
    ensure_directory(base)
    target = base / "sub" / "file.txt"
    ensure_directory(target.parent)
    target.write_text("data")

    # Assumption check
    assert target.exists(), "target file must exist"

    # Act / Assert
    assert format_path(target, base) == "sub/file.txt"
    assert format_path(target) == str(target)


def test_get_platform_matches_sys_platform():
    """get_platform returns the same value as sys.platform."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act
    result = get_platform()

    # Assert
    assert result == sys.platform
