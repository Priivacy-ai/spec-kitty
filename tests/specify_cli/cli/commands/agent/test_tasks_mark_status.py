"""Regression tests for mark-status ID resolution strategies."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app
from specify_cli.core.wps_manifest import (
    WorkPackageEntry,
    WpsManifest,
    generate_tasks_md_from_manifest,
)

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]
runner = CliRunner()


def _write_mission(repo: Path, slug: str, tasks_content: str, wp_ids: tuple[str, ...] = ()) -> Path:
    mission_dir = repo / "kitty-specs" / slug
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(json.dumps({"mission_id": "01TESTMISSION"}), encoding="utf-8")
    (mission_dir / "tasks.md").write_text(tasks_content, encoding="utf-8")
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir()
    for wp_id in wp_ids:
        (tasks_dir / f"{wp_id}-test.md").write_text(
            f"---\nwork_package_id: {wp_id}\n---\n\n# {wp_id}\n",
            encoding="utf-8",
        )
    return mission_dir


@contextmanager
def _null_lock(repo_root: Path, mission_slug: str):  # type: ignore[no-untyped-def]
    del repo_root, mission_slug
    yield


def _invoke_mark_status(repo: Path, slug: str, *ids: str, expected_exit_code: int = 0) -> dict:
    with (
        patch("specify_cli.cli.commands.agent.tasks.locate_project_root", return_value=repo),
        patch("specify_cli.cli.commands.agent.tasks._find_mission_slug", return_value=slug),
        patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out", return_value=(repo, "main")),
        patch("specify_cli.cli.commands.agent.tasks._emit_sparse_session_warning"),
        patch("specify_cli.cli.commands.agent.tasks.feature_status_lock", _null_lock),
        patch("specify_cli.cli.commands.agent.tasks.emit_history_added"),
    ):
        result = runner.invoke(
            app,
            [
                "mark-status",
                *ids,
                "--status",
                "done",
                "--mission",
                slug,
                "--json",
                "--no-auto-commit",
            ],
        )
    assert result.exit_code == expected_exit_code, result.output
    return json.loads(result.stdout)


def _result_by_id(payload: dict, task_id: str) -> dict:
    return next(result for result in payload["results"] if result["id"] == task_id)


def test_inline_subtasks_single(tmp_path: Path) -> None:
    slug = "001-inline-single"
    mission_dir = _write_mission(tmp_path, slug, "# Tasks\n\n## WP01\nSubtasks: T001\n")

    payload = _invoke_mark_status(tmp_path, slug, "T001")

    result = _result_by_id(payload, "T001")
    assert result["outcome"] == "updated"
    assert result["format"] == "inline_subtasks"
    assert "- [x] T001" in (mission_dir / "tasks.md").read_text(encoding="utf-8")


def test_inline_subtasks_multiple(tmp_path: Path) -> None:
    slug = "002-inline-multiple"
    mission_dir = _write_mission(tmp_path, slug, "# Tasks\n\n## WP01\nSubtasks: T001, T002, T003\n")

    payload = _invoke_mark_status(tmp_path, slug, "T001", "T002", "T003")

    assert payload["summary"] == {"updated": 3, "already_satisfied": 0, "not_found": 0}
    content = (mission_dir / "tasks.md").read_text(encoding="utf-8")
    for task_id in ("T001", "T002", "T003"):
        result = _result_by_id(payload, task_id)
        assert result["outcome"] == "updated"
        assert result["format"] == "inline_subtasks"
        assert f"- [x] {task_id}" in content


def test_generated_bold_inline_subtasks_are_markable(tmp_path: Path) -> None:
    slug = "003-generated-bold-inline"
    tasks_md = generate_tasks_md_from_manifest(
        WpsManifest(
            work_packages=[
                WorkPackageEntry(
                    id="WP01",
                    title="Generated",
                    subtasks=["T014", "T015", "T016", "T017"],
                )
            ]
        ),
        "Generated Feature",
    )
    assert "**Subtasks**: T014, T015, T016, T017" in tasks_md
    mission_dir = _write_mission(tmp_path, slug, tasks_md)

    payload = _invoke_mark_status(tmp_path, slug, "T014")

    result = _result_by_id(payload, "T014")
    assert result["outcome"] == "updated"
    assert result["format"] == "inline_subtasks"
    assert "- [x] T014" in (mission_dir / "tasks.md").read_text(encoding="utf-8")


def test_wp_id_rejected_with_move_task_guidance(tmp_path: Path) -> None:
    slug = "003-wp-mark-done"
    _write_mission(tmp_path, slug, "# Tasks\n\n## WP02\n", wp_ids=("WP02",))

    with patch("specify_cli.cli.commands.agent.tasks.emit_status_transition_transactional") as emit_mock:
        payload = _invoke_mark_status(tmp_path, slug, "WP02", expected_exit_code=1)

    result = _result_by_id(payload, "WP02")
    assert result["outcome"] == "not_found"
    assert result["format"] == "wp_id"
    assert "mark-status does not change work-package lanes" in result["message"]
    assert "move-task" in result["message"]
    emit_mock.assert_not_called()


def test_wp_id_rejection_is_actionable_in_human_output(tmp_path: Path) -> None:
    slug = "003-wp-mark-done-human"
    _write_mission(tmp_path, slug, "# Tasks\n\n## WP05\n", wp_ids=("WP05",))

    with (
        patch("specify_cli.cli.commands.agent.tasks.locate_project_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.agent.tasks._find_mission_slug", return_value=slug),
        patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out", return_value=(tmp_path, "main")),
        patch("specify_cli.cli.commands.agent.tasks._emit_sparse_session_warning"),
        patch("specify_cli.cli.commands.agent.tasks.feature_status_lock", _null_lock),
        patch("specify_cli.cli.commands.agent.tasks.emit_history_added"),
        patch("specify_cli.cli.commands.agent.tasks.emit_status_transition_transactional") as emit_mock,
    ):
        result = runner.invoke(
            app,
            [
                "mark-status",
                "WP05",
                "--status",
                "done",
                "--mission",
                slug,
                "--no-auto-commit",
            ],
        )

    assert result.exit_code == 1
    assert "mark-status does not change work-package lanes" in result.output
    normalized_output = " ".join(result.output.split())
    assert "spec-kitty agent tasks move-task <WP_ID> --to <lane>" in normalized_output
    emit_mock.assert_not_called()


def test_wp_id_rejection_does_not_consult_lane_state(tmp_path: Path) -> None:
    slug = "004-wp-already-done"
    _write_mission(tmp_path, slug, "# Tasks\n\n## WP02\n", wp_ids=("WP02",))

    payload = _invoke_mark_status(tmp_path, slug, "WP02", expected_exit_code=1)

    result = _result_by_id(payload, "WP02")
    assert result["outcome"] == "not_found"
    assert result["format"] == "wp_id"
    assert "move-task" in result["message"]


def test_unknown_id_not_found(tmp_path: Path) -> None:
    slug = "005-unknown-id"
    _write_mission(tmp_path, slug, "# Tasks\n\n## WP01\n- [ ] T001 First task\n")

    payload = _invoke_mark_status(tmp_path, slug, "T001", "T999")

    assert _result_by_id(payload, "T001")["outcome"] == "updated"
    assert _result_by_id(payload, "T999")["outcome"] == "not_found"
    assert payload["summary"] == {"updated": 1, "already_satisfied": 0, "not_found": 1}


def test_mixed_formats(tmp_path: Path) -> None:
    slug = "006-mixed-formats"
    mission_dir = _write_mission(
        tmp_path,
        slug,
        "# Tasks\n\n## WP01\n- [ ] T001 Checkbox\nSubtasks: T002\n\n## WP03\n",
        wp_ids=("WP03",),
    )

    payload = _invoke_mark_status(tmp_path, slug, "T001", "T002", "WP03")

    assert _result_by_id(payload, "T001")["format"] == "checkbox"
    assert _result_by_id(payload, "T002")["format"] == "inline_subtasks"
    assert _result_by_id(payload, "WP03")["format"] == "wp_id"
    assert _result_by_id(payload, "WP03")["outcome"] == "not_found"
    assert "move-task" in _result_by_id(payload, "WP03")["message"]
    content = (mission_dir / "tasks.md").read_text(encoding="utf-8")
    assert "- [x] T001" in content
    assert "- [x] T002" in content


def test_existing_checkbox_unchanged(tmp_path: Path) -> None:
    slug = "007-checkbox"
    mission_dir = _write_mission(tmp_path, slug, "# Tasks\n\n## WP01\n- [ ] T001 First task\n")

    payload = _invoke_mark_status(tmp_path, slug, "T001")

    result = _result_by_id(payload, "T001")
    assert result["outcome"] == "updated"
    assert result["format"] == "checkbox"
    assert "- [x] T001 First task" in (mission_dir / "tasks.md").read_text(encoding="utf-8")


def test_history_added_uses_owning_wp_for_checkbox_task(tmp_path: Path) -> None:
    slug = "007-history-checkbox"
    _write_mission(tmp_path, slug, "# Tasks\n\n## WP01 Build\n- [ ] T001 First task\n")

    with (
        patch("specify_cli.cli.commands.agent.tasks.locate_project_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.agent.tasks._find_mission_slug", return_value=slug),
        patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out", return_value=(tmp_path, "main")),
        patch("specify_cli.cli.commands.agent.tasks._emit_sparse_session_warning"),
        patch("specify_cli.cli.commands.agent.tasks.feature_status_lock", _null_lock),
        patch("specify_cli.cli.commands.agent.tasks.emit_history_added") as emit_history,
    ):
        result = runner.invoke(
            app,
            [
                "mark-status",
                "T001",
                "--status",
                "done",
                "--mission",
                slug,
                "--json",
                "--no-auto-commit",
            ],
        )

    assert result.exit_code == 0, result.output
    emit_history.assert_called_once()
    assert emit_history.call_args.kwargs["wp_id"] == "WP01"


def test_history_added_uses_work_package_heading_for_checkbox_task(tmp_path: Path) -> None:
    slug = "007-history-work-package-heading"
    _write_mission(tmp_path, slug, "# Tasks\n\n## Work Package WP01: Build\n- [ ] T001 First task\n")

    with (
        patch("specify_cli.cli.commands.agent.tasks.locate_project_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.agent.tasks._find_mission_slug", return_value=slug),
        patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out", return_value=(tmp_path, "main")),
        patch("specify_cli.cli.commands.agent.tasks._emit_sparse_session_warning"),
        patch("specify_cli.cli.commands.agent.tasks.feature_status_lock", _null_lock),
        patch("specify_cli.cli.commands.agent.tasks.emit_history_added") as emit_history,
    ):
        result = runner.invoke(
            app,
            [
                "mark-status",
                "T001",
                "--status",
                "done",
                "--mission",
                slug,
                "--json",
                "--no-auto-commit",
            ],
        )

    assert result.exit_code == 0, result.output
    emit_history.assert_called_once()
    assert emit_history.call_args.kwargs["wp_id"] == "WP01"


def test_history_added_uses_explicit_wp_column_for_non_derivable_task_id(tmp_path: Path) -> None:
    slug = "007-history-pipe-table"
    _write_mission(
        tmp_path,
        slug,
        (
            "# Tasks\n\n"
            "| ID | Description | WP | Parallel |\n"
            "|----|-------------|----|----------|\n"
            "| T010 | Tenth task | WP02 | [P] |\n"
        ),
    )

    with (
        patch("specify_cli.cli.commands.agent.tasks.locate_project_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.agent.tasks._find_mission_slug", return_value=slug),
        patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out", return_value=(tmp_path, "main")),
        patch("specify_cli.cli.commands.agent.tasks._emit_sparse_session_warning"),
        patch("specify_cli.cli.commands.agent.tasks.feature_status_lock", _null_lock),
        patch("specify_cli.cli.commands.agent.tasks.emit_history_added") as emit_history,
    ):
        result = runner.invoke(
            app,
            [
                "mark-status",
                "T010",
                "--status",
                "done",
                "--mission",
                slug,
                "--json",
                "--no-auto-commit",
            ],
        )

    assert result.exit_code == 0, result.output
    emit_history.assert_called_once()
    assert emit_history.call_args.kwargs["wp_id"] == "WP02"


def test_history_added_groups_multi_wp_updates_by_owning_wp(tmp_path: Path) -> None:
    slug = "007-history-multi-wp"
    _write_mission(
        tmp_path,
        slug,
        "# Tasks\n\n## WP01 Build\n- [ ] T001 First task\n\n## WP02 Ship\n- [ ] T010 Tenth task\n",
    )

    with (
        patch("specify_cli.cli.commands.agent.tasks.locate_project_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.agent.tasks._find_mission_slug", return_value=slug),
        patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out", return_value=(tmp_path, "main")),
        patch("specify_cli.cli.commands.agent.tasks._emit_sparse_session_warning"),
        patch("specify_cli.cli.commands.agent.tasks.feature_status_lock", _null_lock),
        patch("specify_cli.cli.commands.agent.tasks.emit_history_added") as emit_history,
    ):
        result = runner.invoke(
            app,
            [
                "mark-status",
                "T001",
                "T010",
                "--status",
                "done",
                "--mission",
                slug,
                "--json",
                "--no-auto-commit",
            ],
        )

    assert result.exit_code == 0, result.output
    assert [
        (call.kwargs["wp_id"], call.kwargs["entry_content"])
        for call in emit_history.call_args_list
    ] == [
        ("WP01", "Subtask(s) T001 marked as done"),
        ("WP02", "Subtask(s) T010 marked as done"),
    ]


def test_existing_pipe_table_unchanged(tmp_path: Path) -> None:
    slug = "008-pipe-table"
    mission_dir = _write_mission(
        tmp_path,
        slug,
        "# Tasks\n\n| ID | Description | Status |\n|----|-------------|--------|\n| T001 | First task | [ ] |\n",
    )

    payload = _invoke_mark_status(tmp_path, slug, "T001")

    result = _result_by_id(payload, "T001")
    assert result["outcome"] == "updated"
    assert result["format"] == "pipe_table"
    assert "| T001 | First task | [D] |" in (mission_dir / "tasks.md").read_text(encoding="utf-8")
