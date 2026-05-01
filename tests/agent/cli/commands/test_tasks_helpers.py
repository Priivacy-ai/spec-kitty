"""Unit tests for agent/tasks.py helper functions.

Covers uncovered lines in the pure-logic and lightly-mocked helpers
without requiring a running git repo or full CLI invocation.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import specify_cli.cli.commands.agent.tasks as tasks_module
from specify_cli.cli.commands.agent.tasks import (
    _behind_commits_touch_only_planning_artifacts,
    _check_unchecked_subtasks,
    _collect_status_artifacts,
    _detect_reviewer_name,
    _is_pipe_table_task_row,
    _output_error,
    _output_result,
    _parse_pipe_table_header,
    _resolve_git_common_dir,
    _resolve_wp_slug,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# _collect_status_artifacts
# ---------------------------------------------------------------------------


def test_collect_status_artifacts_empty(tmp_path: Path) -> None:
    """Returns empty list when none of the status files exist."""
    result = _collect_status_artifacts(tmp_path)
    assert result == []


def test_collect_status_artifacts_partial(tmp_path: Path) -> None:
    """Returns only files that actually exist."""
    (tmp_path / "status.events.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    result = _collect_status_artifacts(tmp_path)
    names = {p.name for p in result}
    assert "status.events.jsonl" in names
    assert "tasks.md" in names
    assert "status.json" not in names


def test_collect_status_artifacts_all_present(tmp_path: Path) -> None:
    """Returns all three files when they all exist."""
    (tmp_path / "status.events.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "status.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    result = _collect_status_artifacts(tmp_path)
    assert len(result) == 3


# ---------------------------------------------------------------------------
# _output_result
# ---------------------------------------------------------------------------


def test_output_result_json_mode(capsys) -> None:
    """In JSON mode, prints JSON to stdout."""
    _output_result(True, {"result": "ok", "count": 3})
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data == {"result": "ok", "count": 3}


def test_output_result_human_with_message(capsys) -> None:
    """In human mode with a message, prints the message (not JSON)."""
    _output_result(False, {"result": "ok"}, success_message="Done!")
    captured = capsys.readouterr()
    assert "Done!" in captured.out
    # Verify it's not raw JSON
    assert "{" not in captured.out


def test_output_result_human_no_message(capsys) -> None:
    """In human mode with no message, produces no output."""
    _output_result(False, {"result": "ok"}, success_message=None)
    captured = capsys.readouterr()
    assert captured.out == ""


# ---------------------------------------------------------------------------
# _output_error
# ---------------------------------------------------------------------------


def test_output_error_json_mode(capsys) -> None:
    """In JSON mode, prints JSON error object."""
    _output_error(True, "something broke")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data == {"error": "something broke"}


def test_output_error_human_mode(capsys) -> None:
    """In human mode, prints Rich error text."""
    _output_error(False, "something broke")
    captured = capsys.readouterr()
    assert "something broke" in captured.out


# ---------------------------------------------------------------------------
# _detect_reviewer_name
# ---------------------------------------------------------------------------


def test_detect_reviewer_name_success() -> None:
    """Returns name from git config when successful."""
    mock_result = MagicMock()
    mock_result.stdout = "Alice Dev\n"
    with patch("subprocess.run", return_value=mock_result):
        name = _detect_reviewer_name()
    assert name == "Alice Dev"


def test_detect_reviewer_name_empty_output() -> None:
    """Returns 'unknown' when git config returns empty string."""
    mock_result = MagicMock()
    mock_result.stdout = "   \n"
    with patch("subprocess.run", return_value=mock_result):
        name = _detect_reviewer_name()
    assert name == "unknown"


def test_detect_reviewer_name_subprocess_error() -> None:
    """Returns 'unknown' when git command fails."""
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
        name = _detect_reviewer_name()
    assert name == "unknown"


def test_detect_reviewer_name_file_not_found() -> None:
    """Returns 'unknown' when git is not installed."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        name = _detect_reviewer_name()
    assert name == "unknown"


# ---------------------------------------------------------------------------
# _resolve_git_common_dir
# ---------------------------------------------------------------------------


def test_resolve_git_common_dir_relative(tmp_path: Path) -> None:
    """Resolves a relative path against main_repo_root."""
    mock_result = MagicMock()
    mock_result.stdout = ".git\n"
    with patch("subprocess.run", return_value=mock_result):
        result = _resolve_git_common_dir(tmp_path)
    assert result == (tmp_path / ".git").resolve()
    assert result.is_absolute()


def test_resolve_git_common_dir_absolute(tmp_path: Path) -> None:
    """Returns absolute path unchanged."""
    abs_path = str(tmp_path / ".git")
    mock_result = MagicMock()
    mock_result.stdout = abs_path + "\n"
    with patch("subprocess.run", return_value=mock_result):
        result = _resolve_git_common_dir(tmp_path)
    assert result == Path(abs_path)
    assert result.is_absolute()


def test_resolve_git_common_dir_empty_output(tmp_path: Path) -> None:
    """Raises RuntimeError when git returns empty string."""
    mock_result = MagicMock()
    mock_result.stdout = "  \n"
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="Unable to resolve git common directory"):
            _resolve_git_common_dir(tmp_path)


# ---------------------------------------------------------------------------
# _resolve_wp_slug
# ---------------------------------------------------------------------------


def test_resolve_wp_slug_finds_titled_file(tmp_path: Path) -> None:
    """Returns stem of matching WP file."""
    tasks_dir = tmp_path / "kitty-specs" / "010-test" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-agent-config-cleanup.md").write_text("", encoding="utf-8")

    result = _resolve_wp_slug(tmp_path, "010-test", "WP01")
    assert result == "WP01-agent-config-cleanup"


def test_resolve_wp_slug_exact_match(tmp_path: Path) -> None:
    """Returns stem when file stem exactly equals task_id."""
    tasks_dir = tmp_path / "kitty-specs" / "010-test" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01.md").write_text("", encoding="utf-8")

    result = _resolve_wp_slug(tmp_path, "010-test", "WP01")
    assert result == "WP01"


def test_resolve_wp_slug_no_tasks_dir(tmp_path: Path) -> None:
    """Falls back to bare task_id when tasks/ dir doesn't exist."""
    result = _resolve_wp_slug(tmp_path, "010-test", "WP01")
    assert result == "WP01"


def test_resolve_wp_slug_no_matching_file(tmp_path: Path) -> None:
    """Falls back to bare task_id when no matching file exists."""
    tasks_dir = tmp_path / "kitty-specs" / "010-test" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP02-something.md").write_text("", encoding="utf-8")

    result = _resolve_wp_slug(tmp_path, "010-test", "WP01")
    assert result == "WP01"


# ---------------------------------------------------------------------------
# _check_unchecked_subtasks
# ---------------------------------------------------------------------------

_TASKS_MD = """\
## Work Packages

### WP01 — Agent Config

- [x] T001 Remove AgentSelectionConfig (WP01)
- [ ] T002 Remove select_implementer (WP01)
- [ ] T003 Fix load_agent_config (WP01)

### WP02 — Init Surgery

- [ ] T004 Remove flags (WP02)
- [x] T005 Remove stages (WP02)
"""


def test_check_unchecked_subtasks_no_tasks_md(tmp_path: Path) -> None:
    """Returns empty list when tasks.md doesn't exist."""
    with patch(
        "specify_cli.cli.commands.agent.tasks.get_main_repo_root", return_value=tmp_path
    ):
        result = _check_unchecked_subtasks(tmp_path, "010-test", "WP01", False)
    assert result == []


def test_check_unchecked_subtasks_finds_unchecked(tmp_path: Path) -> None:
    """Returns unchecked task IDs in the target WP section."""
    feature_dir = tmp_path / "kitty-specs" / "010-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text(_TASKS_MD, encoding="utf-8")

    with patch(
        "specify_cli.cli.commands.agent.tasks.get_main_repo_root", return_value=tmp_path
    ):
        result = _check_unchecked_subtasks(tmp_path, "010-test", "WP01", False)

    assert "T002" in result
    assert "T003" in result
    assert "T001" not in result  # was checked


def test_check_unchecked_subtasks_all_checked(tmp_path: Path) -> None:
    """Returns empty list when all subtasks in the WP are checked."""
    content = "### WP01 — Config\n\n- [x] T001 Done (WP01)\n- [x] T002 Also done (WP01)\n"
    feature_dir = tmp_path / "kitty-specs" / "010-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text(content, encoding="utf-8")

    with patch(
        "specify_cli.cli.commands.agent.tasks.get_main_repo_root", return_value=tmp_path
    ):
        result = _check_unchecked_subtasks(tmp_path, "010-test", "WP01", False)
    assert result == []


def test_check_unchecked_subtasks_only_target_wp(tmp_path: Path) -> None:
    """Does not return unchecked tasks from a different WP section."""
    feature_dir = tmp_path / "kitty-specs" / "010-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text(_TASKS_MD, encoding="utf-8")

    with patch(
        "specify_cli.cli.commands.agent.tasks.get_main_repo_root", return_value=tmp_path
    ):
        result = _check_unchecked_subtasks(tmp_path, "010-test", "WP02", False)

    # WP02 has T004 unchecked and T005 checked
    assert "T004" in result
    assert "T005" not in result
    # WP01 tasks must not bleed in
    assert "T002" not in result


# ---------------------------------------------------------------------------
# _behind_commits_touch_only_planning_artifacts
# ---------------------------------------------------------------------------


def _make_subproc(returncode: int = 0, stdout: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


def test_behind_commits_merge_base_failure(tmp_path: Path) -> None:
    """Returns False when merge-base subprocess fails."""
    with patch("subprocess.run", return_value=_make_subproc(returncode=1)):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", "010-test")
    assert result is False


def test_behind_commits_empty_merge_base(tmp_path: Path) -> None:
    """Returns False when merge-base output is empty."""
    with patch("subprocess.run", return_value=_make_subproc(returncode=0, stdout="")):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", "010-test")
    assert result is False


def test_behind_commits_no_changed_files(tmp_path: Path) -> None:
    """Returns True when diff reports no changed files (fully up-to-date)."""
    responses = [
        _make_subproc(returncode=0, stdout="abc123\n"),  # merge-base
        _make_subproc(returncode=0, stdout=""),          # diff --name-only
    ]
    with patch("subprocess.run", side_effect=responses):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", "010-test")
    assert result is True


def test_behind_commits_only_planning_files(tmp_path: Path) -> None:
    """Returns True when all changed files are in kitty-specs/MISSION/."""
    responses = [
        _make_subproc(returncode=0, stdout="abc123\n"),
        _make_subproc(returncode=0, stdout="kitty-specs/010-test/tasks.md\nkitty-specs/010-test/status.json\n"),
    ]
    with patch("subprocess.run", side_effect=responses):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", "010-test")
    assert result is True


def test_behind_commits_mixed_files(tmp_path: Path) -> None:
    """Returns False when any changed file is outside allowed paths."""
    responses = [
        _make_subproc(returncode=0, stdout="abc123\n"),
        _make_subproc(returncode=0, stdout="kitty-specs/010-test/tasks.md\nsrc/foo.py\n"),
    ]
    with patch("subprocess.run", side_effect=responses):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", "010-test")
    assert result is False


def test_behind_commits_kittify_config_allowed(tmp_path: Path) -> None:
    """Allows .kittify/config.yaml as an exact-path exception."""
    responses = [
        _make_subproc(returncode=0, stdout="abc123\n"),
        _make_subproc(returncode=0, stdout=".kittify/config.yaml\n"),
    ]
    with patch("subprocess.run", side_effect=responses):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", "010-test")
    assert result is True


def test_behind_commits_diff_failure(tmp_path: Path) -> None:
    """Returns False when the diff subprocess fails."""
    responses = [
        _make_subproc(returncode=0, stdout="abc123\n"),
        _make_subproc(returncode=128, stdout=""),
    ]
    with patch("subprocess.run", side_effect=responses):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", "010-test")
    assert result is False


# ---------------------------------------------------------------------------
# _is_pipe_table_task_row
# ---------------------------------------------------------------------------


def test_is_pipe_table_task_row_match() -> None:
    assert _is_pipe_table_task_row("| T001 | description | WP01 | No |", "T001") is True


def test_is_pipe_table_task_row_padded() -> None:
    assert _is_pipe_table_task_row("|  T001  | desc |", "T001") is True


def test_is_pipe_table_task_row_no_match() -> None:
    assert _is_pipe_table_task_row("| T002 | description |", "T001") is False


def test_is_pipe_table_task_row_separator() -> None:
    assert _is_pipe_table_task_row("|------|------|", "T001") is False


def test_is_pipe_table_task_row_partial_id_not_matched() -> None:
    # T001 should not match T0012
    assert _is_pipe_table_task_row("| T0012 | desc |", "T001") is False


# ---------------------------------------------------------------------------
# _parse_pipe_table_header
# ---------------------------------------------------------------------------


def test_parse_pipe_table_header_found() -> None:
    lines = [
        "| ID | Description | WP | Parallel |",
        "|-----|-------------|----|----|",
        "| T001 | Do thing | WP01 | No |",
    ]
    result = _parse_pipe_table_header(lines, 2)
    assert result == {"id": 0, "description": 1, "wp": 2, "parallel": 3}


def test_parse_pipe_table_header_skips_separator() -> None:
    lines = [
        "| ID | Description |",
        "|---|---|",
        "| T001 | something |",
    ]
    result = _parse_pipe_table_header(lines, 2)
    assert "id" in result
    assert "description" in result


def test_parse_pipe_table_header_no_header() -> None:
    """Returns empty dict when there is no header row above the task row."""
    lines = ["Some prose line", "| T001 | desc |"]
    result = _parse_pipe_table_header(lines, 1)
    assert result == {}


def test_parse_pipe_table_header_at_top() -> None:
    """Returns empty dict when task row is the first line."""
    lines = ["| T001 | desc |"]
    result = _parse_pipe_table_header(lines, 0)
    assert result == {}
