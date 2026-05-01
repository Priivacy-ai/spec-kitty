"""Tests for pipe-table row detection and mutation in mark-status (WP04 / T025).

Covers:
- Pipe-table rows with a "Status" column get the status cell updated.
- Pipe-table rows with a "Parallel" column do NOT get [P] corrupted; a new status cell is appended.
- Pipe-table rows with no recognisable status-like cell get a new status cell appended.
- Checkbox format still works (regression).
- Mixed-format files (both checkbox and pipe-table) work correctly.
- Separator rows are not matched as task rows.
- Multi-task mark in one file.
- Template does not instruct use of pipe-table for task tracking.
"""

from __future__ import annotations

import re
from pathlib import Path


from specify_cli.cli.commands.agent.tasks import (
    _is_pipe_table_task_row,
    _parse_pipe_table_header,
    _update_pipe_table_status,
)

# ---------------------------------------------------------------------------
# Unit tests for helper functions (no git / IO needed)
# ---------------------------------------------------------------------------


class TestIsPipeTableTaskRow:
    """Unit tests for _is_pipe_table_task_row()."""

    def test_matches_task_id_in_first_data_column(self):
        line = "| T001 | description | WP01 | [P] |"
        assert _is_pipe_table_task_row(line, "T001") is True

    def test_matches_task_id_with_whitespace_padding(self):
        line = "|  T022  | some desc | WP04 | [D] |"
        assert _is_pipe_table_task_row(line, "T022") is True

    def test_matches_task_id_in_non_first_column(self):
        line = "| description | T005 | WP01 |"
        assert _is_pipe_table_task_row(line, "T005") is True

    def test_does_not_match_separator_row(self):
        line = "|---|---|---|---|"
        assert _is_pipe_table_task_row(line, "T001") is False

    def test_does_not_match_separator_row_with_colons(self):
        line = "|:---|:---:|---:|"
        assert _is_pipe_table_task_row(line, "T001") is False

    def test_does_not_match_header_row_if_task_id_absent(self):
        line = "| ID | Description | WP | Parallel |"
        assert _is_pipe_table_task_row(line, "T001") is False

    def test_does_not_match_task_id_as_substring(self):
        # "T001" must not match a cell containing "T0012" or "XT001"
        line = "| T0012 | desc | WP01 |"
        assert _is_pipe_table_task_row(line, "T001") is False

    def test_does_not_match_plain_checkbox_row(self):
        line = "- [ ] T001 Some task"
        assert _is_pipe_table_task_row(line, "T001") is False

    def test_matches_done_marker_row(self):
        line = "| T003 | rename module | WP02 | [D] |"
        assert _is_pipe_table_task_row(line, "T003") is True


class TestParsePipeTableHeader:
    """Unit tests for _parse_pipe_table_header()."""

    def test_finds_header_above_task_row(self):
        lines = [
            "| ID | Description | WP | Parallel |",
            "|----|-------------|-----|----------|",
            "| T001 | do thing | WP01 | [P] |",
        ]
        header_map = _parse_pipe_table_header(lines, task_row_idx=2)
        assert "id" in header_map
        assert "parallel" in header_map

    def test_finds_status_column(self):
        lines = [
            "| ID | Description | Status |",
            "|----|-------------|--------|",
            "| T001 | do thing | [ ] |",
        ]
        header_map = _parse_pipe_table_header(lines, task_row_idx=2)
        assert "status" in header_map

    def test_returns_empty_dict_when_no_header_found(self):
        lines = [
            "| T001 | do thing | WP01 |",
        ]
        header_map = _parse_pipe_table_header(lines, task_row_idx=0)
        assert header_map == {}

    def test_skips_separator_between_header_and_task(self):
        lines = [
            "| Task | Desc | WP | Parallel |",
            "|------|------|-----|----------|",
            "| T001 | something | WP01 | [P] |",
        ]
        header_map = _parse_pipe_table_header(lines, task_row_idx=2)
        assert "parallel" in header_map

    def test_column_indices_are_zero_based(self):
        lines = [
            "| ID | Description | WP | Status |",
            "|----|-------------|-----|--------|",
            "| T001 | thing | WP01 | [ ] |",
        ]
        header_map = _parse_pipe_table_header(lines, task_row_idx=2)
        # "ID" is column 0, "Description" is 1, "WP" is 2, "Status" is 3
        assert header_map["status"] == 3


class TestUpdatePipeTableStatus:
    """Unit tests for _update_pipe_table_status()."""

    def test_updates_status_column_when_present(self):
        line = "| T001 | do thing | WP01 | [ ] |"
        # header_map: status is at index 3 (0=id, 1=desc, 2=wp, 3=status)
        header_map = {"id": 0, "description": 1, "wp": 2, "status": 3}
        result = _update_pipe_table_status(line, "done", header_map)
        assert "[D]" in result
        # The WP column cell should be unchanged
        assert "WP01" in result

    def test_does_not_touch_parallel_column(self):
        line = "| T001 | do thing | WP01 | [P] |"
        # header_map has "parallel" at index 3
        header_map = {"id": 0, "description": 1, "wp": 2, "parallel": 3}
        result = _update_pipe_table_status(line, "done", header_map)
        # The parallel [P] must be preserved
        assert "[P]" in result
        # A done status should have been appended
        assert "[D]" in result

    def test_appends_status_when_no_header_map(self):
        line = "| T001 | do thing | WP01 |"
        header_map: dict[str, int] = {}
        result = _update_pipe_table_status(line, "done", header_map)
        assert "[D]" in result

    def test_updates_pending_status(self):
        line = "| T001 | do thing | WP01 | [D] |"
        header_map = {"id": 0, "description": 1, "wp": 2, "status": 3}
        result = _update_pipe_table_status(line, "pending", header_map)
        assert "[ ]" in result
        assert "[D]" not in result

    def test_returns_pipe_table_line(self):
        line = "| T001 | do thing | WP01 | [P] |"
        header_map = {"id": 0, "description": 1, "wp": 2, "parallel": 3}
        result = _update_pipe_table_status(line, "done", header_map)
        assert result.startswith("|")
        assert result.endswith("|")


# ---------------------------------------------------------------------------
# Integration-style tests: operate on tasks.md content strings
# ---------------------------------------------------------------------------
# These tests drive the helpers in a more end-to-end fashion without touching
# git or the filesystem, to stay fast and deterministic.
# ---------------------------------------------------------------------------


def _apply_mark_status_to_content(content: str, task_ids: list[str], status: str) -> tuple[str, list[str], list[str]]:
    """Replicate the core mark-status loop from tasks.py in a pure function.

    Returns (updated_content, updated_tasks, not_found_tasks).
    """
    from specify_cli.cli.commands.agent.tasks import (
        _is_pipe_table_task_row,
        _parse_pipe_table_header,
        _update_pipe_table_status,
    )

    lines = content.split("\n")
    new_checkbox = "[x]" if status == "done" else "[ ]"
    updated_tasks: list[str] = []
    not_found_tasks: list[str] = []

    for task_id in task_ids:
        task_found = False
        for i, line in enumerate(lines):
            # Strategy 1: Checkbox format (canonical)
            if re.search(rf"-\s*\[[ x]\]\s*{re.escape(task_id)}\b", line):
                lines[i] = re.sub(r"-\s*\[[ x]\]", f"- {new_checkbox}", line)
                task_found = True
            # Strategy 2: Pipe-table format (backward compatibility)
            elif _is_pipe_table_task_row(line, task_id):
                header_map = _parse_pipe_table_header(lines, i)
                lines[i] = _update_pipe_table_status(line, status, header_map)
                task_found = True
        if task_found:
            updated_tasks.append(task_id)
        if not task_found:
            not_found_tasks.append(task_id)

    return "\n".join(lines), updated_tasks, not_found_tasks


class TestMarkStatusPipeTableIntegration:
    """Integration-level tests exercising the full mark-status logic."""

    def test_pipe_table_mark_done(self):
        """Marking a pending pipe-table task as done sets [D] in the row."""
        content = (
            "# Tasks\n\n"
            "## Subtask Index\n\n"
            "| ID | Description | WP | Parallel |\n"
            "|----|-------------|-----|-----------|\n"
            "| T001 | rename module | WP01 | [P] |\n"
            "| T002 | update imports | WP01 | |\n"
        )
        result, updated, not_found = _apply_mark_status_to_content(content, ["T001"], "done")
        assert "T001" in updated
        assert not not_found
        # The Parallel [P] for T001 must NOT be touched
        t001_line = [ln for ln in result.split("\n") if "T001" in ln][0]
        assert "[P]" in t001_line, "Parallel marker must be preserved"
        # A done marker must have been appended
        assert "[D]" in t001_line

    def test_pipe_table_mark_pending(self):
        """A done pipe-table task can be reset to pending."""
        # Re-run with no header knowledge (no Status column) — the [D] in last cell
        # should be replaced by pending marker because _update_pipe_table_status
        # recognises it as a status-like cell when there is no header map.
        content_status_col = "# Tasks\n\n| ID | Description | Status |\n|----|-------------|--------|\n| T001 | rename module | [D] |\n"
        result, updated, not_found = _apply_mark_status_to_content(content_status_col, ["T001"], "pending")
        assert "T001" in updated
        t001_line = [ln for ln in result.split("\n") if "T001" in ln][0]
        assert "[ ]" in t001_line
        assert "[D]" not in t001_line

    def test_pipe_table_with_status_column(self):
        """When a Status column exists, only that column is updated."""
        content = "# Tasks\n\n| ID | Description | WP | Status |\n|----|-------------|-----|--------|\n| T001 | do thing | WP01 | [ ] |\n"
        result, updated, not_found = _apply_mark_status_to_content(content, ["T001"], "done")
        assert "T001" in updated
        assert not not_found
        t001_line = [ln for ln in result.split("\n") if "T001" in ln][0]
        assert "[D]" in t001_line

    def test_pipe_table_no_status_like_cell_appends(self):
        """Pipe-table row with no recognisable status marker gets one appended."""
        content = "# Tasks\n\n| ID | Description | WP |\n|----|-------------|-----|\n| T001 | build feature | WP01 |\n"
        result, updated, not_found = _apply_mark_status_to_content(content, ["T001"], "done")
        assert "T001" in updated
        t001_line = [ln for ln in result.split("\n") if "T001" in ln][0]
        assert "[D]" in t001_line

    def test_separator_row_not_matched_as_task(self):
        """Separator rows must never be treated as task rows."""
        # _is_pipe_table_task_row should return False for the separator line
        separator = "|----|-------------|"
        assert _is_pipe_table_task_row(separator, "T001") is False
        assert _is_pipe_table_task_row(separator, "ID") is False

    def test_checkbox_format_still_works(self):
        """Existing checkbox detection is unaffected (regression)."""
        content = "## WP01\n- [ ] T001 First task\n- [ ] T002 Second task\n"
        result, updated, not_found = _apply_mark_status_to_content(content, ["T001"], "done")
        assert "T001" in updated
        assert not not_found
        assert "- [x] T001" in result

    def test_mixed_format_file_both_updated(self):
        """A file with both checkbox rows and a pipe-table index — both are handled.

        The Subtask Index pipe-table appears at the top of tasks.md.  The per-WP
        checkbox rows appear lower down. Both representations must be updated so
        the summary index and canonical checklist stay in sync.

        T003 exists only as a checkbox row and is matched via the checkbox path.
        """
        content = (
            "# Tasks\n\n"
            "## Subtask Index\n\n"
            "| ID | Description | WP | Parallel |\n"
            "|----|-------------|-----|-----------|\n"
            "| T001 | pipe-table task | WP01 | [P] |\n"
            "| T002 | pipe-table task 2 | WP01 | |\n\n"
            "## WP01 Work Package\n\n"
            "- [ ] T001 pipe-table task (WP01)\n"
            "- [ ] T002 pipe-table task 2 (WP01)\n"
            "- [ ] T003 checkbox-only task\n"
        )
        result, updated, not_found = _apply_mark_status_to_content(content, ["T001", "T003"], "done")
        assert set(updated) == {"T001", "T003"}
        assert not not_found
        # T001's pipe-table row gets the done marker
        t001_pipe_line = next(ln for ln in result.split("\n") if ln.startswith("| T001"))
        assert "[D]" in t001_pipe_line
        assert "- [x] T001" in result
        # T003 has no pipe-table entry, so the checkbox row is matched
        assert "- [x] T003" in result

    def test_pipe_table_multiple_tasks(self):
        """Mark multiple pipe-table tasks done in one operation."""
        content = (
            "| ID | Description | WP | Parallel |\n"
            "|----|-------------|-----|-----------|\n"
            "| T001 | task a | WP01 | [P] |\n"
            "| T002 | task b | WP01 | |\n"
            "| T003 | task c | WP01 | [P] |\n"
        )
        result, updated, not_found = _apply_mark_status_to_content(content, ["T001", "T003"], "done")
        assert set(updated) == {"T001", "T003"}
        assert not not_found
        lines = result.split("\n")
        t001_line = next(ln for ln in lines if "T001" in ln)
        t003_line = next(ln for ln in lines if "T003" in ln)
        assert "[D]" in t001_line
        assert "[D]" in t003_line
        # T002 must be untouched
        t002_line = next(ln for ln in lines if "T002" in ln)
        assert "[D]" not in t002_line

    def test_not_found_task_reported(self):
        """Tasks that don't match any line are reported in not_found."""
        content = "| ID | Description | WP |\n|----|-------------|-----|\n| T001 | thing | WP01 |\n"
        _, updated, not_found = _apply_mark_status_to_content(content, ["T001", "T999"], "done")
        assert "T001" in updated
        assert "T999" in not_found


# ---------------------------------------------------------------------------
# Template validation test
# ---------------------------------------------------------------------------


class TestTasksTemplateCheckboxFormat:
    """Verify the tasks command template directs agents to use checkbox format."""

    def _get_template_path(self) -> Path:
        # Walk up from this file to repo root, then find the template.
        here = Path(__file__).resolve()
        # tests/git_ops/test_mark_status_pipe_table.py → tests/ → repo_root
        repo_root = here.parent.parent.parent
        return repo_root / "src" / "specify_cli" / "missions" / "software-dev" / "command-templates" / "tasks.md"

    def test_template_mentions_checkbox_format(self):
        """tasks.md template must reference checkbox format for task rows."""
        template = self._get_template_path()
        assert template.exists(), f"Template not found: {template}"
        content = template.read_text(encoding="utf-8")
        # The template should mention checkbox style explicitly
        assert "- [ ]" in content or "checkbox" in content.lower(), "tasks.md template must mention checkbox format for tracking rows"

    def test_template_distinguishes_index_table_from_tracking(self):
        """tasks.md template must note that the index table is a reference, not a tracking surface."""
        template = self._get_template_path()
        content = template.read_text(encoding="utf-8")
        # Should contain some guidance that distinguishes index/reference table
        # from the per-WP tracking rows
        assert "mark-status" in content or "reference" in content.lower() or "index" in content.lower(), (
            "tasks.md template should clarify the role of the Subtask Index table"
        )
