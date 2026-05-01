"""Tests for the version-marker head-scan helper in m_2_1_4.

These tests pin down the contract that the migration's marker detection
helper recognizes spec-kitty-authored command files using the *new* layout
(YAML frontmatter on line 1, marker on line 4) as well as the legacy
layout (marker on line 1).  Without head scanning, the doctor and the
enforce-state migration would treat newly generated files as stale and
rewrite them on every upgrade.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.upgrade.migrations.m_2_1_4_enforce_command_file_state import (
    _VERSION_MARKER_HEAD_LINES,
    _expected_version_marker,
    _file_has_current_version_marker,
)

pytestmark = pytest.mark.fast


@pytest.fixture
def expected_marker() -> str:
    return _expected_version_marker()


def test_recognizes_marker_on_line_one(tmp_path: Path, expected_marker: str) -> None:
    """Legacy layout (marker on line 1) must still be detected."""
    target = tmp_path / "legacy.md"
    target.write_text(f"{expected_marker}\n# body\n", encoding="utf-8")
    assert _file_has_current_version_marker(target) is True


def test_recognizes_marker_after_yaml_frontmatter(tmp_path: Path, expected_marker: str) -> None:
    """New layout (frontmatter on line 1, marker on line 4) must be detected."""
    target = tmp_path / "new_layout.md"
    target.write_text(
        f"---\ndescription: Demo Command\n---\n{expected_marker}\nBody.\n",
        encoding="utf-8",
    )
    assert _file_has_current_version_marker(target) is True


def test_rejects_stale_version(tmp_path: Path) -> None:
    """A marker for a *different* version is treated as stale."""
    target = tmp_path / "stale.md"
    target.write_text(
        "---\ndescription: Demo Command\n---\n<!-- spec-kitty-command-version: 0.0.1-stale -->\nBody.\n",
        encoding="utf-8",
    )
    assert _file_has_current_version_marker(target) is False


def test_rejects_marker_buried_below_head_window(tmp_path: Path, expected_marker: str) -> None:
    """A marker beyond the head window is intentionally not detected."""
    filler = "\n".join(["filler line"] * (_VERSION_MARKER_HEAD_LINES + 5))
    target = tmp_path / "deep.md"
    target.write_text(f"{filler}\n{expected_marker}\n", encoding="utf-8")
    assert _file_has_current_version_marker(target) is False


def test_rejects_user_authored_file(tmp_path: Path) -> None:
    """No marker anywhere → not generated."""
    target = tmp_path / "user.md"
    target.write_text(
        "---\ndescription: A custom user command\n---\nDo my custom thing.\n",
        encoding="utf-8",
    )
    assert _file_has_current_version_marker(target) is False


def test_handles_oserror_gracefully(tmp_path: Path) -> None:
    """A read failure must return False rather than raising."""
    target = tmp_path / "blocked.md"
    target.write_text("doesn't matter\n", encoding="utf-8")

    with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
        assert _file_has_current_version_marker(target) is False
