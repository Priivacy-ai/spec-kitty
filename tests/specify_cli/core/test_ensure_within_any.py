"""Tests for ensure_within_any — the multi-root parameterised containment utility.

Squad-hardened test list (T011):
  - roots_accept: path under one root returns resolved path
  - roots_reject: path under no root raises ValueError
  - files_arm_accept: exact file in files= is accepted even if under no root
  - files_arm_default_empty: with files omitted, only root membership is consulted
  - files_arm_is_exact_not_prefix: path under allowed file's parent (but not equal) is REJECTED
  - strict_false_semantics: deeply non-existent nested path under a root is ACCEPTED (no FileNotFoundError)
  - symlink_outside_all_roots_is_rejected: symlink pointing outside all roots is rejected
  - symlink_resolving_inside_root_is_accepted: symlink pointing inside a root is accepted
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.core.utils import ensure_within_any

pytestmark = [pytest.mark.fast]


class TestRootsAccept:
    """A path under any of the listed roots is accepted and the resolved path is returned."""

    def test_path_under_sole_root_is_accepted(self, tmp_path: Path) -> None:
        root = tmp_path / "trusted"
        root.mkdir()
        target = root / "subdir" / "file.txt"
        target.parent.mkdir(parents=True)
        target.touch()

        result = ensure_within_any(target, roots=[root])

        assert result == target.resolve()

    def test_path_under_one_of_many_roots_is_accepted(self, tmp_path: Path) -> None:
        root_a = tmp_path / "alpha"
        root_b = tmp_path / "beta"
        root_c = tmp_path / "gamma"
        root_a.mkdir()
        root_b.mkdir()
        root_c.mkdir()
        target = root_b / "nested" / "thing.json"
        target.parent.mkdir(parents=True)
        target.touch()

        result = ensure_within_any(target, roots=[root_a, root_b, root_c])

        assert result == target.resolve()

    def test_returned_path_is_resolved(self, tmp_path: Path) -> None:
        root = tmp_path / "trusted"
        root.mkdir()
        target = root / "a" / ".." / "b.txt"
        (root / "b.txt").touch()

        result = ensure_within_any(target, roots=[root])

        assert result == (root / "b.txt").resolve()


class TestRootsReject:
    """A path under none of the listed roots raises ValueError."""

    def test_path_outside_sole_root_is_rejected(self, tmp_path: Path) -> None:
        trusted = tmp_path / "trusted"
        untrusted = tmp_path / "untrusted"
        trusted.mkdir()
        untrusted.mkdir()
        target = untrusted / "file.txt"
        target.touch()

        with pytest.raises(ValueError, match=str(target.resolve())):
            ensure_within_any(target, roots=[trusted])

    def test_path_outside_all_roots_is_rejected(self, tmp_path: Path) -> None:
        root_a = tmp_path / "alpha"
        root_b = tmp_path / "beta"
        outside = tmp_path / "outside"
        root_a.mkdir()
        root_b.mkdir()
        outside.mkdir()
        target = outside / "leaked.txt"
        target.touch()

        with pytest.raises(ValueError):
            ensure_within_any(target, roots=[root_a, root_b])

    def test_error_message_names_rejected_path(self, tmp_path: Path) -> None:
        trusted = tmp_path / "trusted"
        untrusted = tmp_path / "untrusted"
        trusted.mkdir()
        untrusted.mkdir()
        target = untrusted / "bad.txt"
        target.touch()

        with pytest.raises(ValueError, match=str(untrusted.resolve())):
            ensure_within_any(target, roots=[trusted])


class TestFilesArmAccept:
    """A path exactly equal to an allowed file in files= is accepted, even if under no root."""

    def test_exact_allowed_file_outside_roots_is_accepted(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        allowed_file = tmp_path / "special" / "merge-state.json"
        allowed_file.parent.mkdir(parents=True)
        allowed_file.touch()

        result = ensure_within_any(allowed_file, roots=[root], files=[allowed_file])

        assert result == allowed_file.resolve()

    def test_allowed_file_under_root_is_doubly_accepted(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        target = root / "state.json"
        target.touch()

        # Should be accepted by the roots arm — passing it in files= also should work
        result = ensure_within_any(target, roots=[root], files=[target])

        assert result == target.resolve()


class TestFilesArmDefaultEmpty:
    """With files= omitted, only root membership is consulted."""

    def test_files_default_is_empty_no_extra_allowances(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        outside = tmp_path / "outside"
        root.mkdir()
        outside.mkdir()
        target = outside / "some-file.txt"
        target.touch()

        # No files= kwarg — only root membership matters; should raise
        with pytest.raises(ValueError):
            ensure_within_any(target, roots=[root])


class TestFilesArmIsExactNotPrefix:
    """files= is exact-equality membership, NOT a root-prefix arm.

    A path under an allowed file's parent — but not equal to the file itself —
    and under no root must be REJECTED. This proves files= is membership, not
    a second roots arm (squad flag from T011).
    """

    def test_sibling_of_allowed_file_is_rejected(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        special_dir = tmp_path / "special"
        root.mkdir()
        special_dir.mkdir()
        allowed_file = special_dir / "merge-state.json"
        allowed_file.touch()
        sibling = special_dir / "other-file.txt"
        sibling.touch()

        # sibling shares parent dir with allowed_file, but is not equal — must be rejected
        with pytest.raises(ValueError):
            ensure_within_any(sibling, roots=[root], files=[allowed_file])

    def test_child_path_of_allowed_file_parent_is_rejected(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        special_dir = tmp_path / "special"
        root.mkdir()
        (special_dir / "subdir").mkdir(parents=True)
        allowed_file = special_dir / "merge-state.json"
        allowed_file.touch()
        child = special_dir / "subdir" / "nested.json"
        child.touch()

        # child is under the same parent as allowed_file but is NOT equal to it
        with pytest.raises(ValueError):
            ensure_within_any(child, roots=[root], files=[allowed_file])


class TestStrictFalseSemantics:
    """A deeply non-existent nested path under a root is ACCEPTED (strict=False).

    A strict=True resolve() would raise FileNotFoundError for non-existent paths.
    This test forces a strict=False implementation — it will fail if resolve()
    is called without strict=False.
    """

    def test_non_existent_nested_path_under_root_is_accepted(self, tmp_path: Path) -> None:
        root = tmp_path / "trusted"
        root.mkdir()
        # This path does not exist on disk — strict=True resolve() would raise
        deep_nonexistent = root / "a" / "b" / "c" / "does" / "not" / "exist.json"

        # Must not raise FileNotFoundError (strict=False behaviour)
        result = ensure_within_any(deep_nonexistent, roots=[root])

        assert result == deep_nonexistent.resolve(strict=False)
        assert str(root.resolve()) in str(result)

    def test_non_existent_file_in_files_arm_is_accepted(self, tmp_path: Path) -> None:
        root = tmp_path / "trusted"
        outside = tmp_path / "outside"
        root.mkdir()
        outside.mkdir()
        # This specific file does not exist on disk yet
        ghost_file = outside / "future-state.json"

        result = ensure_within_any(ghost_file, roots=[root], files=[ghost_file])

        assert result == ghost_file.resolve(strict=False)


class TestSymlinkBehavior:
    """Symlink resolution: ensure_within_any uses resolve(strict=False) on its own.

    A symlink pointing OUTSIDE all roots is rejected.
    A symlink resolving INSIDE a root is accepted.
    This tests ensure_within_any's OWN resolve-then-compare semantics;
    it does NOT assert parity with ensure_within_directory (which uses strict=True).
    """

    def test_symlink_pointing_outside_root_is_rejected(self, tmp_path: Path) -> None:
        root = tmp_path / "trusted"
        outside = tmp_path / "outside"
        root.mkdir()
        outside.mkdir()
        real_target = outside / "real-file.txt"
        real_target.touch()
        link = root / "evil-link"
        os.symlink(real_target, link)

        # The symlink lives under root but resolves to outside → rejected
        with pytest.raises(ValueError):
            ensure_within_any(link, roots=[root])

    def test_symlink_resolving_inside_root_is_accepted(self, tmp_path: Path) -> None:
        root = tmp_path / "trusted"
        root.mkdir()
        real_target = root / "real-file.txt"
        real_target.touch()
        link = root / "safe-link"
        os.symlink(real_target, link)

        result = ensure_within_any(link, roots=[root])

        assert result == real_target.resolve()
        assert str(root.resolve()) in str(result)
