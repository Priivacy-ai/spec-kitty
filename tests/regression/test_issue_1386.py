"""Regression coverage for issue #1386 protected-branch status writes."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app as tasks_app

pytestmark = [pytest.mark.regression, pytest.mark.git_repo]

runner = CliRunner()


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "issue1386@example.invalid")
    _git(repo, "config", "user.name", "Issue 1386")
    (repo / ".kittify").mkdir()


def _seed_mission(repo: Path) -> Path:
    mission_slug = "issue1386-protected"
    feature_dir = repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": mission_slug,
                "mission": "software-dev",
                "target_branch": "main",
                "friendly_name": "Issue 1386 protected branch",
                "created_at": "2026-05-29T00:00:00+00:00",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01\n- [ ] T001 First task\n",
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text(
        "# Spec\n\n## Functional Requirements\n\n- **FR-001**: First requirement.\n",
        encoding="utf-8",
    )
    (tasks_dir / "WP01-test.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "execution_mode: code_change\n"
        "agent: testbot\n"
        "owned_files:\n"
        "  - src/**\n"
        "authoritative_surface: src/\n"
        "---\n"
        "# WP01\n\n"
        "- [x] T001 First task\n\n"
        "## Activity Log\n",
        encoding="utf-8",
    )
    return feature_dir


def _commit_seed(repo: Path) -> None:
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed issue 1386 fixture")


def _status(repo: Path) -> str:
    return subprocess.run(
        ["git", "status", "--short"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_move_task_refuses_protected_branch_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _seed_mission(repo)
    _commit_seed(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "for_review",
            "--mission",
            "issue1386-protected",
            "--auto-commit",
        ],
    )

    assert result.exit_code == 1
    assert "Refusing to run `spec-kitty agent tasks move-task`" in result.output
    assert "protected branch 'main'" in result.output
    assert _status(repo) == ""


def test_mark_status_refuses_protected_branch_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _seed_mission(repo)
    _commit_seed(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(
        tasks_app,
        [
            "mark-status",
            "T001",
            "--status",
            "done",
            "--mission",
            "issue1386-protected",
            "--auto-commit",
        ],
    )

    assert result.exit_code == 1
    assert "Refusing to run `spec-kitty agent tasks mark-status`" in result.output
    assert "protected branch 'main'" in result.output
    assert _status(repo) == ""


def test_map_requirements_refuses_protected_branch_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _seed_mission(repo)
    _commit_seed(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(
        tasks_app,
        [
            "map-requirements",
            "--wp",
            "WP01",
            "--refs",
            "FR-001",
            "--mission",
            "issue1386-protected",
            "--auto-commit",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "Refusing to run `spec-kitty agent tasks map-requirements`" in payload["error"]
    assert "protected branch 'main'" in payload["error"]
    assert _status(repo) == ""
