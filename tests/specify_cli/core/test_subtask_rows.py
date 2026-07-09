"""Tests for the canonical subtask-row patterns and progress counter (#2504)."""

from __future__ import annotations

import pytest

from specify_cli.core.subtask_rows import (
    CHECKED_SUBTASK_ROW,
    UNCHECKED_SUBTASK_ROW,
    count_subtask_rows,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_counts_checked_and_unchecked_rows() -> None:
    body = (
        "# Work Package Prompt: Demo\n"
        "- [x] T001 Build the thing\n"
        "- [X] T002 Build the other thing\n"
        "- [ ] T003 Verify the thing\n"
    )
    assert count_subtask_rows(body) == (2, 3)


def test_non_implementation_checkboxes_are_not_subtasks() -> None:
    """Command/validation rows and prose checkboxes don't count — mirrors the
    lane-transition guard's semantics."""
    body = (
        "- [ ] T004 Real subtask\n"
        "- [ ] swift test\n"
        "- [x] git status --short\n"
        "- [ ] remember to hydrate\n"
        "- [ ] T99 too-short id does not count\n"
    )
    assert count_subtask_rows(body) == (0, 1)


def test_fenced_code_blocks_are_ignored() -> None:
    body = (
        "- [x] T001 Done\n"
        "```\n"
        "- [ ] T002 example row inside a fence\n"
        "```\n"
        "~~~\n"
        "- [x] T003 another fenced example\n"
        "~~~\n"
        "- [ ] T004 Real remaining work\n"
    )
    assert count_subtask_rows(body) == (1, 2)


def test_no_checkbox_rows_is_zero_zero() -> None:
    assert count_subtask_rows("# Just prose\n\nNo checklists here.\n") == (0, 0)


def test_ids_past_t999_still_match() -> None:
    assert UNCHECKED_SUBTASK_ROW.match("- [ ] T1000 big mission")
    assert CHECKED_SUBTASK_ROW.match("- [x] T1000 big mission")


def test_guard_consumes_the_shared_unchecked_pattern() -> None:
    """The lane-transition guard and the dashboard must share ONE definition."""
    import inspect

    from specify_cli.cli.commands.agent import tasks_shared

    source = inspect.getsource(tasks_shared._check_unchecked_subtasks)
    assert "UNCHECKED_SUBTASK_ROW" in source
    assert 're.compile(r"^-' not in source
