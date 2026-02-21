"""Integration tests for sparse-checkout cleanup after WP merge."""

import subprocess
from pathlib import Path

import pytest

from specify_cli.core.git_ops import run_command
from specify_cli.merge.executor import _cleanup_sparse_checkout_config


@pytest.fixture(name="_git_identity")
def git_identity_fixture(monkeypatch):
    """Ensure git commands can commit even if the user has no global config."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "spec@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "spec@example.com")


def _get_git_config(repo: Path, key: str) -> str | None:
    """Get a git config value, returning None if unset."""
    result = subprocess.run(
        ["git", "config", "--get", key],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


@pytest.mark.usefixtures("_git_identity")
def test_cleanup_removes_orphaned_sparse_checkout_config(tmp_path):
    """Verify cleanup removes sparse-checkout config when no worktrees remain."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)
    (repo / "file.txt").write_text("content")
    run_command(["git", "add", "."], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    # Simulate orphaned sparse-checkout config (left behind after worktree removal)
    run_command(["git", "config", "core.sparseCheckout", "true"], cwd=repo)
    run_command(["git", "config", "core.sparseCheckoutCone", "false"], cwd=repo)

    # Verify config is set
    assert _get_git_config(repo, "core.sparseCheckout") == "true"
    assert _get_git_config(repo, "core.sparseCheckoutCone") == "false"

    # Run cleanup — no worktrees remain, no sparse-checkout file exists
    _cleanup_sparse_checkout_config(repo)

    # Config should be unset
    assert _get_git_config(repo, "core.sparseCheckout") is None, (
        "core.sparseCheckout should be unset when no worktrees remain"
    )
    assert _get_git_config(repo, "core.sparseCheckoutCone") is None, (
        "core.sparseCheckoutCone should be unset when no worktrees remain"
    )


@pytest.mark.usefixtures("_git_identity")
def test_cleanup_preserves_config_when_worktrees_remain(tmp_path):
    """Verify sparse-checkout config is preserved when worktrees still exist."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)
    (repo / "file.txt").write_text("content")
    run_command(["git", "add", "."], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    # Create a worktree (simulating one that should stay)
    worktree = tmp_path / "wt"
    run_command(
        ["git", "worktree", "add", str(worktree), "-b", "remaining-branch"],
        cwd=repo,
    )

    # Enable sparse-checkout config
    run_command(["git", "config", "core.sparseCheckout", "true"], cwd=repo)

    # Cleanup should NOT remove config because worktree still exists
    _cleanup_sparse_checkout_config(repo)

    assert _get_git_config(repo, "core.sparseCheckout") == "true", (
        "core.sparseCheckout should be preserved when worktrees remain"
    )


@pytest.mark.usefixtures("_git_identity")
def test_cleanup_noop_when_config_not_set(tmp_path):
    """Verify cleanup is a no-op when sparse-checkout was never configured."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)
    (repo / "file.txt").write_text("content")
    run_command(["git", "add", "."], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    assert _get_git_config(repo, "core.sparseCheckout") is None

    # Cleanup should be a no-op (no error)
    _cleanup_sparse_checkout_config(repo)

    assert _get_git_config(repo, "core.sparseCheckout") is None


@pytest.mark.usefixtures("_git_identity")
def test_cleanup_preserves_config_when_sparse_checkout_file_exists(tmp_path):
    """Verify cleanup is skipped when a sparse-checkout file still exists."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init"], cwd=repo)
    (repo / "file.txt").write_text("content")
    run_command(["git", "add", "."], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)

    # Set sparse-checkout config and create the sparse-checkout file
    run_command(["git", "config", "core.sparseCheckout", "true"], cwd=repo)
    sparse_file = repo / ".git" / "info" / "sparse-checkout"
    sparse_file.parent.mkdir(parents=True, exist_ok=True)
    sparse_file.write_text("/*\n!/kitty-specs/\n")

    _cleanup_sparse_checkout_config(repo)

    # Config should remain because sparse-checkout file exists
    assert _get_git_config(repo, "core.sparseCheckout") == "true", (
        "core.sparseCheckout should be preserved when sparse-checkout file exists"
    )
