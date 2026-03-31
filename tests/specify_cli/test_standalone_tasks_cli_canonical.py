from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.reducer import materialize
from specify_cli.status.store import append_event
from tests.utils import REPO_ROOT, run_python_script

pytestmark = pytest.mark.fast

ROOT_TASKS_CLI = REPO_ROOT / "scripts" / "tasks" / "tasks_cli.py"
SRC_TASKS_CLI = REPO_ROOT / "src" / "specify_cli" / "scripts" / "tasks" / "tasks_cli.py"


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
            feature_slug=slug,
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


def test_src_tasks_cli_history_dry_run_omits_lane_segment(
    tmp_path: Path, isolated_env: dict[str, str]
) -> None:
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
