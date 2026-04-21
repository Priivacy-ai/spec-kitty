"""Regression tests for the post-merge working-tree invariant helper.

Exercises _classify_porcelain_lines() to verify that:
- Untracked (??) lines never appear in offending_lines (T001/T002)
- Tracked modifications/deletions are offending (T003)
- Mixed lines produce the correct split (T004)
- expected_paths exemption works (T005)
"""

from __future__ import annotations

import pytest

from specify_cli.cli.commands.merge import _classify_porcelain_lines

pytestmark = pytest.mark.fast


def test_classify_untracked_lines_returns_empty_offending() -> None:
    """?? lines must not appear in offending_lines."""
    lines = ["?? .claude/", "?? .agents/", "?? .kittify/merge-state.json"]
    expected: set[str] = {
        "kitty-specs/test/status.events.jsonl",
        "kitty-specs/test/status.json",
    }
    offending, skipped = _classify_porcelain_lines(lines, expected)
    assert offending == []
    assert skipped == 3


def test_classify_tracked_modification_is_offending() -> None:
    """' M' lines for tracked files are offending."""
    lines = [" M src/specify_cli/some_module.py"]
    offending, skipped = _classify_porcelain_lines(lines, set())
    assert len(offending) == 1
    assert " M src/specify_cli/some_module.py" in offending
    assert skipped == 0


def test_classify_mixed_untracked_and_tracked() -> None:
    """Mix of ?? and ' M': tracked line is offending, untracked is not."""
    lines = ["?? .claude/", " M src/specify_cli/some_module.py"]
    offending, skipped = _classify_porcelain_lines(lines, set())
    assert len(offending) == 1
    assert " M src/specify_cli/some_module.py" in offending
    assert skipped == 1


def test_classify_deletion_is_offending() -> None:
    """' D' lines are offending."""
    lines = [" D src/specify_cli/old_module.py"]
    offending, skipped = _classify_porcelain_lines(lines, set())
    assert len(offending) == 1
    assert " D src/specify_cli/old_module.py" in offending
    assert skipped == 0


def test_classify_expected_path_not_offending() -> None:
    """Paths in expected_paths are not offending regardless of status code."""
    lines = [" M kitty-specs/feat/status.events.jsonl"]
    expected = {"kitty-specs/feat/status.events.jsonl"}
    offending, skipped = _classify_porcelain_lines(lines, expected)
    assert offending == []
    assert skipped == 0


def test_classify_empty_lines_ignored() -> None:
    """Empty and whitespace-only lines are silently dropped."""
    lines = ["", "   ", " M src/specify_cli/some_module.py"]
    offending, skipped = _classify_porcelain_lines(lines, set())
    assert len(offending) == 1


def test_classify_malformed_lines_ignored() -> None:
    """Lines that don't match porcelain v1 shape are silently skipped."""
    lines = ["M src/foo.py", "AB", "?? valid_untracked/"]
    offending, skipped = _classify_porcelain_lines(lines, set())
    # 'M src/foo.py' has no space at index 2 → skipped (malformed)
    # 'AB' is too short (len < 4) → skipped
    # '?? valid_untracked/' is untracked → skipped_untracked
    assert offending == []
    assert skipped == 1  # only the ?? line


def test_classify_multiple_untracked_directories() -> None:
    """Multiple untracked agent directories common in fresh checkouts are ignored."""
    lines = [
        "?? .amazonq/",
        "?? .augment/",
        "?? .claude/",
        "?? .cursor/",
        "?? .gemini/",
        "?? .kiro/",
        "?? .opencode/",
    ]
    offending, skipped = _classify_porcelain_lines(lines, set())
    assert offending == []
    assert skipped == 7
