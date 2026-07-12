"""Characterization + direct coverage for the WP04 checkbox-parser canonicalization (#2567).

FR-008/FR-009, plan.md D5: ``acceptance/gates_core.py::_find_unchecked_tasks``
used to flag ANY ``- [ ] ...`` row via a stray whole-file regex
(``re.match(r"^\\s*-\\s*\\[ \\]", line)``) -- prose checkboxes, fenced-code
example rows, and rows without a ``T###`` id all got flagged. WP04 migrates it
onto the canonical, fence-aware, T###-scoped
``core.subtask_rows.iter_unchecked_subtask_rows``. This is an intentional
TIGHTENING of what counts as an unchecked subtask, not a mechanical fold --
this module captures the old->new flagging delta on a single mixed fixture so
the semantics change is ratified, not silently absorbed, and adds direct
branch coverage for the new iterator plus a pin on the untouched
terminal-mission normalization (``_normalized_unchecked_tasks``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specify_cli.acceptance.gates_core import _find_unchecked_tasks, _normalized_unchecked_tasks
from specify_cli.core.subtask_rows import iter_unchecked_subtask_rows

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# The stray regex `_find_unchecked_tasks` used PRIOR to WP04 (#2567). Kept
# here, in the test only, purely to characterize the old->new flagging delta
# below -- it must never reappear in production code (C-003 / dead-code gate).
_OLD_STRAY_UNCHECKED_REGEX = re.compile(r"^\s*-\s*\[ \]")

_MIXED_FIXTURE = (
    "# Tasks\n"
    "## WP01 — Demo section\n"
    "- [ ] T001 Real canonical subtask\n"
    "- [ ] remember to circle back on caching\n"
    "```\n"
    "- [ ] T002 example row shown inside a fenced code block\n"
    "```\n"
    "- [x] T003 already done, checked\n"
    "  - [ ] T004 indented but still T###-scoped\n"
)


def test_old_regex_flagged_prose_and_fenced_rows_new_iterator_does_not() -> None:
    """Ratifies the FR-009 tightening: the OLD stray regex flagged the prose
    row and the fenced example row (whole-file, no T### requirement, no fence
    awareness); the NEW canonical iterator narrows to T###-scoped, fence-aware
    rows only, so both drop out of the new result."""
    old_flagged = [
        line.strip() for line in _MIXED_FIXTURE.splitlines() if _OLD_STRAY_UNCHECKED_REGEX.match(line)
    ]
    new_flagged = list(iter_unchecked_subtask_rows(_MIXED_FIXTURE))

    # OLD: whole-file, no T-id or fence awareness -- flags all 4 unchecked dash-checkbox rows.
    assert old_flagged == [
        "- [ ] T001 Real canonical subtask",
        "- [ ] remember to circle back on caching",
        "- [ ] T002 example row shown inside a fenced code block",
        "- [ ] T004 indented but still T###-scoped",
    ]

    # NEW: T###-scoped + fence-aware -- drops the prose row and the fenced row.
    assert new_flagged == [
        "- [ ] T001 Real canonical subtask",
        "- [ ] T004 indented but still T###-scoped",
    ]

    # The delta this WP ratifies: prose (no T###) and fenced rows no longer flagged.
    dropped = set(old_flagged) - set(new_flagged)
    assert dropped == {
        "- [ ] remember to circle back on caching",
        "- [ ] T002 example row shown inside a fenced code block",
    }


def test_find_unchecked_tasks_end_to_end_matches_new_iterator(tmp_path: Path) -> None:
    """``_find_unchecked_tasks`` (the gate's production entry point) must
    return exactly the canonical iterator's output for a real ``tasks.md``
    file -- no extra whole-file regex behind it anymore."""
    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text(_MIXED_FIXTURE, encoding="utf-8")

    assert _find_unchecked_tasks(tasks_file) == list(iter_unchecked_subtask_rows(_MIXED_FIXTURE))


def test_find_unchecked_tasks_missing_file_sentinel(tmp_path: Path) -> None:
    """Preserves the pre-existing ``tasks.md missing`` sentinel behaviour."""
    missing = tmp_path / "tasks.md"
    assert _find_unchecked_tasks(missing) == ["tasks.md missing"]


class TestIterUncheckedSubtaskRowsDirectBranches:
    """Direct unit coverage of ``iter_unchecked_subtask_rows``'s branches --
    not exercised directly by the gate-level characterization tests above nor
    by the terminal-mission normalization tests below."""

    def test_t_id_unchecked_row_is_yielded(self) -> None:
        assert list(iter_unchecked_subtask_rows("- [ ] T001 real subtask\n")) == [
            "- [ ] T001 real subtask"
        ]

    def test_prose_checkbox_without_t_id_is_rejected(self) -> None:
        assert list(iter_unchecked_subtask_rows("- [ ] remember to hydrate\n")) == []

    def test_short_t_id_below_three_digits_is_rejected(self) -> None:
        assert list(iter_unchecked_subtask_rows("- [ ] T99 too-short id\n")) == []

    def test_row_inside_backtick_fence_is_rejected(self) -> None:
        body = "```\n- [ ] T001 fenced example\n```\n"
        assert list(iter_unchecked_subtask_rows(body)) == []

    def test_row_inside_tilde_fence_is_rejected(self) -> None:
        body = "~~~\n- [ ] T001 fenced example\n~~~\n"
        assert list(iter_unchecked_subtask_rows(body)) == []

    def test_checked_row_is_not_yielded_by_the_unchecked_iterator(self) -> None:
        assert list(iter_unchecked_subtask_rows("- [x] T001 already done\n")) == []

    def test_indented_row_with_t_id_is_still_yielded(self) -> None:
        """Anchoring is on the STRIPPED line -- leading indentation alone
        does not exclude a row, mirroring ``count_subtask_rows``'s existing
        fence-loop semantics."""
        assert list(iter_unchecked_subtask_rows("  - [ ] T001 indented\n")) == [
            "- [ ] T001 indented"
        ]

    def test_mixed_fence_and_real_rows_yields_only_unfenced(self) -> None:
        body = (
            "- [ ] T001 before the fence\n"
            "```\n"
            "- [ ] T002 inside fence\n"
            "```\n"
            "- [ ] T003 after the fence\n"
        )
        assert list(iter_unchecked_subtask_rows(body)) == [
            "- [ ] T001 before the fence",
            "- [ ] T003 after the fence",
        ]


class TestNormalizedUncheckedTasksPreserved:
    """T027: pins ``_normalized_unchecked_tasks`` (gates_core.py) unchanged by
    the WP04 migration -- FR-009's WP-terminal-status normalization is a
    distinct concern from the checkbox-row parser and must not drift."""

    def test_tasks_md_missing_sentinel_is_dropped(self) -> None:
        assert _normalized_unchecked_tasks(["tasks.md missing"], {"planned": ["WP01"]}) == []

    def test_all_terminal_wps_clears_unchecked_tasks(self) -> None:
        unchecked = ["- [ ] T001 leftover checkbox"]
        lanes = {"approved": ["WP01"], "done": ["WP02"]}
        assert _normalized_unchecked_tasks(unchecked, lanes) == []

    def test_non_terminal_wp_still_reports_unchecked_tasks(self) -> None:
        unchecked = ["- [ ] T001 leftover checkbox"]
        lanes = {"approved": ["WP01"], "in_review": ["WP02"]}
        assert _normalized_unchecked_tasks(unchecked, lanes) == unchecked

    def test_no_tracked_wps_returns_unchecked_tasks_unchanged(self) -> None:
        unchecked = ["- [ ] T001 leftover checkbox"]
        assert _normalized_unchecked_tasks(unchecked, {"planned": []}) == unchecked
