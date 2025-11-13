import sys
from pathlib import Path

from specify_cli.core import ensure_directory, format_path, get_platform, safe_remove


def test_ensure_directory_creates_path(tmp_path):
    target = tmp_path / "nested" / "dir"
    returned = ensure_directory(target)
    assert target.is_dir()
    assert returned == target


def test_safe_remove_handles_files_and_dirs(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    dir_path = tmp_path / "dir"
    dir_path.mkdir()
    (dir_path / "child").write_text("child")

    assert safe_remove(file_path) is True
    assert not file_path.exists()

    assert safe_remove(dir_path) is True
    assert not dir_path.exists()

    assert safe_remove(dir_path) is False  # already removed


def test_format_path_relative(tmp_path):
    base = tmp_path / "base"
    ensure_directory(base)
    target = base / "sub" / "file.txt"
    ensure_directory(target.parent)
    target.write_text("data")

    assert format_path(target, base) == "sub/file.txt"
    assert format_path(target) == str(target)


def test_get_platform_matches_sys_platform():
    assert get_platform() == sys.platform
