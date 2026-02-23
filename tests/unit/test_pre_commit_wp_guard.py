"""Tests for WP branch protection in the manual pre-commit workflow hook."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _hook_script() -> Path:
    hook_script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "git-hooks"
        / "pre-commit-task-workflow.sh"
    )
    assert hook_script.exists()
    return hook_script


def test_wp_branch_hook_blocks_kitty_specs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    hook_path = _hook_script()

    subprocess.run(
        ["git", "checkout", "-b", "001-test-feature-WP01"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    blocked_file = repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test.md"
    blocked_file.parent.mkdir(parents=True)
    blocked_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "lane: \"doing\"\n"
        "shell_pid: \"123\"\n"
        "agent: \"tester\"\n"
        "---\n\n"
        "## Activity Log\n"
        "- 2026-01-01T00:00:00Z – tester – lane=doing – Started implementation\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", str(blocked_file)], cwd=repo, check=True, capture_output=True)

    result = subprocess.run(
        [str(hook_path)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "wp branches must not commit kitty-specs/" in result.stdout.lower()


def test_wp_branch_hook_allows_non_wp_branches(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    hook_path = _hook_script()

    allowed_file = repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test.md"
    allowed_file.parent.mkdir(parents=True)
    allowed_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "lane: \"doing\"\n"
        "shell_pid: \"123\"\n"
        "agent: \"tester\"\n"
        "---\n\n"
        "## Activity Log\n"
        "- 2026-01-01T00:00:00Z – tester – lane=doing – Started implementation\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", str(allowed_file)], cwd=repo, check=True, capture_output=True)

    result = subprocess.run(
        [str(hook_path)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
