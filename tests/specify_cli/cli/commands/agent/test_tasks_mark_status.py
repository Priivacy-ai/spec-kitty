"""Regression tests for mark-status ID resolution strategies."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event, read_events

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


def _invoke_mark_status(repo: Path, slug: str, *ids: str) -> dict:
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
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _result_by_id(payload: dict, task_id: str) -> dict:
    return next(result for result in payload["results"] if result["id"] == task_id)


def _seed_done_event(mission_dir: Path, slug: str, wp_id: str) -> None:
    append_event(
        mission_dir,
        StatusEvent(
            event_id=f"01TEST{wp_id}DONE000000000000",
            mission_slug=slug,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,
            to_lane=Lane.DONE,
            at="2026-05-05T00:00:00+00:00",
            actor="test",
            force=True,
            reason="test seed",
            execution_mode="direct_repo",
        ),
    )


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


def test_wp_id_mark_done(tmp_path: Path) -> None:
    slug = "003-wp-mark-done"
    mission_dir = _write_mission(tmp_path, slug, "# Tasks\n\n## WP02\n", wp_ids=("WP02",))

    payload = _invoke_mark_status(tmp_path, slug, "WP02")

    result = _result_by_id(payload, "WP02")
    assert result["outcome"] == "updated"
    assert result["format"] == "wp_id"
    assert any(event.wp_id == "WP02" and event.to_lane == Lane.DONE for event in read_events(mission_dir))


def test_wp_id_already_done(tmp_path: Path) -> None:
    slug = "004-wp-already-done"
    mission_dir = _write_mission(tmp_path, slug, "# Tasks\n\n## WP02\n", wp_ids=("WP02",))
    _seed_done_event(mission_dir, slug, "WP02")

    payload = _invoke_mark_status(tmp_path, slug, "WP02")

    result = _result_by_id(payload, "WP02")
    assert result["outcome"] == "already_satisfied"
    assert result["format"] == "wp_id"


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
    content = (mission_dir / "tasks.md").read_text(encoding="utf-8")
    assert "- [x] T001" in content
    assert "- [x] T002" in content
    assert any(event.wp_id == "WP03" and event.to_lane == Lane.DONE for event in read_events(mission_dir))


def test_existing_checkbox_unchanged(tmp_path: Path) -> None:
    slug = "007-checkbox"
    mission_dir = _write_mission(tmp_path, slug, "# Tasks\n\n## WP01\n- [ ] T001 First task\n")

    payload = _invoke_mark_status(tmp_path, slug, "T001")

    result = _result_by_id(payload, "T001")
    assert result["outcome"] == "updated"
    assert result["format"] == "checkbox"
    assert "- [x] T001 First task" in (mission_dir / "tasks.md").read_text(encoding="utf-8")


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
