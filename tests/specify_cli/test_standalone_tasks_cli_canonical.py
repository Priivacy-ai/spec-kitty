from __future__ import annotations

import argparse
import importlib.util
import io
import subprocess
import sys
from contextlib import redirect_stderr
from pathlib import Path

import pytest

from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.reducer import materialize
from specify_cli.status.store import append_event, read_events
from tests.utils import REPO_ROOT, run_python_script

pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]  # non_sandbox: subprocess CLI invocation
ROOT_TASKS_CLI = REPO_ROOT / "scripts" / "tasks" / "tasks_cli.py"
SRC_TASKS_CLI = REPO_ROOT / "src" / "specify_cli" / "scripts" / "tasks" / "tasks_cli.py"
SRC_TASK_HELPERS = REPO_ROOT / "src" / "specify_cli" / "scripts" / "tasks" / "task_helpers.py"


def _load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)
    (repo / ".kittify").mkdir()


def _build_feature(repo: Path, slug: str = "060-standalone-test", *, with_events: bool = True) -> Path:
    feature_dir = repo / "kitty-specs" / slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-test.md").write_text(
        "---\n"
        'work_package_id: "WP01"\n'
        'title: "Test WP01"\n'
        'agent: "tester"\n'
        'shell_pid: "123"\n'
        "---\n\n"
        "# WP01\n\n"
        "## Activity Log\n"
        "- 2026-03-31T09:00:00Z -- tester -- Prompt created\n",
        encoding="utf-8",
    )

    if with_events:
        event = StatusEvent(
            event_id="01TESTSTANDALONEDONE",
            mission_slug=slug,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.DONE,
            at="2026-03-31T09:00:00+00:00",
            actor="tester",
            force=True,
            execution_mode="direct_repo",
        )
        append_event(feature_dir, event)
        materialize(feature_dir)

    return feature_dir


def test_repo_root_tasks_cli_list_uses_canonical_status(tmp_path: Path, isolated_env: dict[str, str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo)

    result = run_python_script(ROOT_TASKS_CLI, ["list", feature_dir.name], cwd=repo, env=isolated_env)

    assert result.returncode == 0, result.stderr
    assert "done" in result.stdout
    assert "planned  WP01" not in result.stdout


def test_src_tasks_cli_history_dry_run_omits_lane_segment(tmp_path: Path, isolated_env: dict[str, str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo)

    result = run_python_script(
        SRC_TASKS_CLI,
        ["history", feature_dir.name, "WP01", "--note", "probe", "--dry-run"],
        cwd=repo,
        env=isolated_env,
    )

    assert result.returncode == 0, result.stderr
    assert "lane=" not in result.stdout
    assert "probe" in result.stdout


def test_src_task_helpers_require_canonical_status_for_lane(
    tmp_path: Path,
    isolated_env: dict[str, str],
) -> None:
    del isolated_env
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, with_events=False)
    task_helpers = _load_module("standalone_task_helpers_missing", SRC_TASK_HELPERS)

    with pytest.raises(task_helpers.TaskCliError, match="Canonical status not found"):
        task_helpers.get_lane_from_frontmatter(feature_dir / "tasks" / "WP01-test.md")


def test_src_task_helpers_work_package_lane_reads_canonical_status(
    tmp_path: Path,
    isolated_env: dict[str, str],
) -> None:
    del isolated_env
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, with_events=True)
    task_helpers = _load_module("standalone_task_helpers_lane", SRC_TASK_HELPERS)
    wp_path = feature_dir / "tasks" / "WP01-test.md"
    frontmatter, body, padding = task_helpers.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    wp = task_helpers.WorkPackage(
        feature=feature_dir.name,
        path=wp_path,
        current_lane="done",
        relative_subpath=Path("WP01-test.md"),
        frontmatter=frontmatter,
        body=body,
        padding=padding,
    )

    assert wp.lane == "done"


def test_src_tasks_cli_derive_current_lane_defaults_to_planned_without_events(
    tmp_path: Path,
    isolated_env: dict[str, str],
) -> None:
    del isolated_env
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, with_events=False)
    tasks_cli = _load_module("standalone_tasks_cli_derive", SRC_TASKS_CLI)

    assert tasks_cli._derive_current_lane(feature_dir, "WP01") == "planned"


def test_src_tasks_cli_stage_update_writes_status_artifacts(
    tmp_path: Path,
    isolated_env: dict[str, str],
) -> None:
    del isolated_env
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, with_events=False)
    task_helpers = _load_module("standalone_task_helpers_stage", SRC_TASK_HELPERS)
    tasks_cli = _load_module("standalone_tasks_cli_stage", SRC_TASKS_CLI)
    wp_path = feature_dir / "tasks" / "WP01-test.md"
    frontmatter, body, padding = task_helpers.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    wp = task_helpers.WorkPackage(
        feature=feature_dir.name,
        path=wp_path,
        current_lane="planned",
        relative_subpath=Path("WP01-test.md"),
        frontmatter=frontmatter,
        body=body,
        padding=padding,
    )

    updated_path = tasks_cli.stage_update(
        repo_root=repo,
        wp=wp,
        target_lane="doing",
        agent="tester",
        shell_pid="42",
        note="claim work",
        timestamp="2026-03-31T10:00:00Z",
    )

    assert updated_path == wp_path
    assert "lane=" not in wp_path.read_text(encoding="utf-8")
    assert (feature_dir / "status.json").exists()
    events = read_events(feature_dir)
    assert str(events[-1].to_lane) == "in_progress"


def test_src_tasks_cli_check_legacy_format_warns_once(
    tmp_path: Path,
    isolated_env: dict[str, str],
) -> None:
    del isolated_env
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = repo / "kitty-specs" / "060-legacy-test"
    (feature_dir / "tasks" / "planned").mkdir(parents=True)
    (feature_dir / "tasks" / "planned" / "WP01.md").write_text("# WP01\n", encoding="utf-8")
    tasks_cli = _load_module("standalone_tasks_cli_legacy", SRC_TASKS_CLI)
    tasks_cli._legacy_warning_shown = False

    stderr = io.StringIO()
    with redirect_stderr(stderr):
        assert tasks_cli._check_legacy_format(feature_dir.name, repo) is True
        assert tasks_cli._check_legacy_format(feature_dir.name, repo) is True

    output = stderr.getvalue()
    assert output.count("Legacy directory-based lanes detected.") == 1
    assert "status.events.jsonl" in output


def test_src_tasks_cli_rollback_uses_canonical_event_history(
    tmp_path: Path,
    isolated_env: dict[str, str],
) -> None:
    del isolated_env
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, with_events=False)
    tasks_cli = _load_module("standalone_tasks_cli_rollback", SRC_TASKS_CLI)
    append_event(
        feature_dir,
        StatusEvent(
            event_id="01TESTROLLBACKPLANNED000001",
            mission_slug=feature_dir.name,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.PLANNED,
            at="2026-03-31T09:00:00+00:00",
            actor="planner",
            force=True,
            execution_mode="direct_repo",
        ),
    )
    append_event(
        feature_dir,
        StatusEvent(
            event_id="01TESTROLLBACKREVIEW00001",
            mission_slug=feature_dir.name,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.FOR_REVIEW,
            at="2026-03-31T10:00:00+00:00",
            actor="reviewer",
            force=True,
            execution_mode="direct_repo",
        ),
    )
    materialize(feature_dir)

    captured: dict[str, object] = {}

    def fake_update_command(args: argparse.Namespace) -> None:
        captured["args"] = args

    tasks_cli.update_command = fake_update_command
    tasks_cli.find_repo_root = lambda: repo
    args = argparse.Namespace(
        feature=feature_dir.name,
        work_package="WP01",
        note=None,
        agent=None,
        assignee=None,
        shell_pid=None,
        timestamp=None,
        dry_run=True,
        force=False,
    )

    tasks_cli.rollback_command(args)

    update_args = captured["args"]
    assert update_args.lane == "planned"
    assert update_args.agent == "reviewer"
    assert update_args.note == "Rolled back to planned"


@pytest.mark.parametrize("script_path", [ROOT_TASKS_CLI, SRC_TASKS_CLI])
def test_standalone_tasks_cli_requires_canonical_status(
    script_path: Path,
    tmp_path: Path,
    isolated_env: dict[str, str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    feature_dir = _build_feature(repo, with_events=False)

    result = run_python_script(
        script_path,
        ["list", feature_dir.name],
        cwd=repo,
        env=isolated_env,
    )

    assert result.returncode == 1
    assert "Canonical status not found" in result.stderr
    assert "finalize-tasks" in result.stderr
