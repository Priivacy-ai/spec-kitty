"""Tests for WP branch pre-commit protection in hook templates."""

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


def _install_hook(repo: Path) -> Path:
    hook_template = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "specify_cli"
        / "templates"
        / "git-hooks"
        / "pre-commit-agent-check"
    )
    hook_path = repo / ".git" / "hooks" / "pre-commit-agent-check"
    hook_path.write_text(hook_template.read_text(encoding="utf-8"), encoding="utf-8")
    hook_path.chmod(0o755)
    return hook_path


def test_wp_branch_hook_blocks_kitty_specs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    hook_path = _install_hook(repo)

    subprocess.run(
        ["git", "checkout", "-b", "001-test-feature-WP01"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    blocked_file = repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test.md"
    blocked_file.parent.mkdir(parents=True)
    blocked_file.write_text("test\n", encoding="utf-8")
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
    hook_path = _install_hook(repo)

    allowed_file = repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test.md"
    allowed_file.parent.mkdir(parents=True)
    allowed_file.write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", str(allowed_file)], cwd=repo, check=True, capture_output=True)

    result = subprocess.run(
        [str(hook_path)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
