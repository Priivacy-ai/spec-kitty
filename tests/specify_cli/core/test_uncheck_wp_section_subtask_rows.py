"""Unit tests for uncheck_wp_section_subtask_rows (#2513).

A rolled-back WP must have its subtask rows unchecked so the lane-transition
gate does not pass immediately without the work being re-done.
"""

from __future__ import annotations

import pytest

from specify_cli.core.subtask_rows import uncheck_wp_section_subtask_rows

pytestmark = [pytest.mark.unit, pytest.mark.fast]


TASKS_MD = """\
## WP01 — Build widget

- [x] T001 Design the API
- [x] T002 Implement the handler
- [ ] T003 Write tests

## WP02 — Ship widget

- [x] T004 Create release notes
- [x] T005 Tag the release
"""


def test_unchecks_checked_rows_in_target_wp() -> None:
    result = uncheck_wp_section_subtask_rows(TASKS_MD, "WP01")
    assert "- [ ] T001" in result
    assert "- [ ] T002" in result


def test_preserves_already_unchecked_rows() -> None:
    result = uncheck_wp_section_subtask_rows(TASKS_MD, "WP01")
    assert "- [ ] T003" in result


def test_does_not_touch_other_wp_sections() -> None:
    result = uncheck_wp_section_subtask_rows(TASKS_MD, "WP01")
    assert "- [x] T004" in result
    assert "- [x] T005" in result


def test_returns_original_when_no_checked_rows() -> None:
    tasks = "## WP03 — Empty\n\n- [ ] T006 Nothing done\n"
    result = uncheck_wp_section_subtask_rows(tasks, "WP03")
    assert result is tasks  # same object — no allocation


def test_returns_original_when_wp_section_absent() -> None:
    result = uncheck_wp_section_subtask_rows(TASKS_MD, "WP99")
    assert result is TASKS_MD


def test_ignores_rows_inside_code_fence() -> None:
    tasks = """\
## WP04 — Fenced example

```
- [x] T007 inside fence — must not be unchecked
```
- [x] T008 outside fence
"""
    result = uncheck_wp_section_subtask_rows(tasks, "WP04")
    assert "- [x] T007 inside fence" in result   # preserved
    assert "- [ ] T008 outside fence" in result  # unchecked


def test_heading_with_dependency_mention_does_not_reenter_dep_section() -> None:
    """WP03 heading mentioning WP01 must not re-enter WP01's section (#2346)."""
    tasks = """\
## WP01 — Base

- [x] T001 Done

## WP03 — Derived (depends: WP01)

- [x] T002 Also done
"""
    result = uncheck_wp_section_subtask_rows(tasks, "WP01")
    assert "- [ ] T001" in result   # WP01 row unchecked
    assert "- [x] T002" in result   # WP03 row left alone


def test_uppercase_x_also_unchecked() -> None:
    tasks = "## WP05 — Mixed case\n\n- [X] T009 Uppercase X\n"
    result = uncheck_wp_section_subtask_rows(tasks, "WP05")
    assert "- [ ] T009" in result


def test_heading_without_wp_token_does_not_end_section() -> None:
    """A sub-heading with no WP token inside a WP section must not close it."""
    tasks = """\
## WP06 — Work

### Details

- [x] T010 Under sub-heading
"""
    result = uncheck_wp_section_subtask_rows(tasks, "WP06")
    assert "- [ ] T010" in result
