"""Multi-Parent Merge Tests for diamond dependencies."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.core.multi_parent_merge import (
    cleanup_merge_base_branch,
    create_multi_parent_base,
)
from tests.utils import run

pytestmark = [pytest.mark.adversarial]


def _init_repo(repo: Path) -> None:
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    run(["git", "config", "user.name", "Test User"], cwd=repo)
    (repo / "README.md").write_text("main\n", encoding="utf-8")
    run(["git", "add", "README.md"], cwd=repo)
    run(["git", "commit", "-m", "init"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)


def _create_branch(
    repo: Path,
    *,
    base_branch: str,
    branch: str,
    filename: str,
    content: str,
) -> None:
    run(["git", "checkout", base_branch], cwd=repo)
    run(["git", "checkout", "-b", branch], cwd=repo)
    (repo / filename).write_text(content, encoding="utf-8")
    run(["git", "add", filename], cwd=repo)
    run(["git", "commit", "-m", f"{branch} work"], cwd=repo)


@pytest.fixture
def diamond_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "diamond-repo"
    repo.mkdir()
    _init_repo(repo)

    feature_slug = "020-diamond"
    _create_branch(
        repo,
        base_branch="main",
        branch=f"{feature_slug}-WP01",
        filename="shared.txt",
        content="base\n",
    )
    _create_branch(
        repo,
        base_branch=f"{feature_slug}-WP01",
        branch=f"{feature_slug}-WP02",
        filename="feature-a.txt",
        content="feature-a\n",
    )
    _create_branch(
        repo,
        base_branch=f"{feature_slug}-WP01",
        branch=f"{feature_slug}-WP03",
        filename="feature-b.txt",
        content="feature-b\n",
    )
    run(["git", "checkout", "main"], cwd=repo)
    return repo, feature_slug


@pytest.fixture
def diamond_conflict_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "diamond-conflict-repo"
    repo.mkdir()
    _init_repo(repo)

    feature_slug = "021-diamond-conflict"
    _create_branch(
        repo,
        base_branch="main",
        branch=f"{feature_slug}-WP01",
        filename="shared.txt",
        content="base\n",
    )
    _create_branch(
        repo,
        base_branch=f"{feature_slug}-WP01",
        branch=f"{feature_slug}-WP02",
        filename="shared.txt",
        content="users\n",
    )
    _create_branch(
        repo,
        base_branch=f"{feature_slug}-WP01",
        branch=f"{feature_slug}-WP03",
        filename="shared.txt",
        content="auth\n",
    )
    run(["git", "checkout", "main"], cwd=repo)
    return repo, feature_slug


@pytest.fixture
def triple_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "triple-repo"
    repo.mkdir()
    _init_repo(repo)

    feature_slug = "022-triple"
    _create_branch(
        repo,
        base_branch="main",
        branch=f"{feature_slug}-WP01",
        filename="base.txt",
        content="base\n",
    )
    _create_branch(
        repo,
        base_branch=f"{feature_slug}-WP01",
        branch=f"{feature_slug}-WP02",
        filename="feature-a.txt",
        content="a\n",
    )
    _create_branch(
        repo,
        base_branch=f"{feature_slug}-WP01",
        branch=f"{feature_slug}-WP03",
        filename="feature-b.txt",
        content="b\n",
    )
    _create_branch(
        repo,
        base_branch=f"{feature_slug}-WP01",
        branch=f"{feature_slug}-WP04",
        filename="feature-c.txt",
        content="c\n",
    )
    run(["git", "checkout", "main"], cwd=repo)
    return repo, feature_slug


class TestMergeConflictDetection:
    def test_conflict_clearly_reported(self, diamond_conflict_repo: tuple[Path, str]) -> None:
        repo, feature_slug = diamond_conflict_repo

        result = create_multi_parent_base(
            feature_slug=feature_slug,
            wp_id="WP04",
            dependencies=["WP02", "WP03"],
            repo_root=repo,
        )

        assert result.success is False
        assert result.error is not None
        assert "merge conflict" in result.error.lower()
        assert "shared.txt" in result.conflicts

        result_check = subprocess.run(
            ["git", "rev-parse", "--verify", f"{feature_slug}-WP04-merge-base"],
            cwd=repo,
            capture_output=True,
            check=False,
        )
        assert result_check.returncode != 0


class TestDeterministicMergeOrder:
    def test_same_tree_hash_across_runs(self, diamond_repo: tuple[Path, str]) -> None:
        repo, feature_slug = diamond_repo

        result1 = create_multi_parent_base(
            feature_slug=feature_slug,
            wp_id="WP04",
            dependencies=["WP03", "WP02"],
            repo_root=repo,
        )
        assert result1.success is True

        tree1 = run(
            ["git", "rev-parse", f"{result1.commit_sha}^{{tree}}"],
            cwd=repo,
        ).stdout.strip()

        assert cleanup_merge_base_branch(feature_slug, "WP04", repo) is True

        result2 = create_multi_parent_base(
            feature_slug=feature_slug,
            wp_id="WP04",
            dependencies=["WP02", "WP03"],
            repo_root=repo,
        )
        assert result2.success is True

        tree2 = run(
            ["git", "rev-parse", f"{result2.commit_sha}^{{tree}}"],
            cwd=repo,
        ).stdout.strip()

        assert tree1 == tree2
        assert cleanup_merge_base_branch(feature_slug, "WP04", repo) is True


class TestOrphanedBranchCleanup:
    def test_merge_base_branch_removed(self, diamond_repo: tuple[Path, str]) -> None:
        repo, feature_slug = diamond_repo

        result = create_multi_parent_base(
            feature_slug=feature_slug,
            wp_id="WP04",
            dependencies=["WP02", "WP03"],
            repo_root=repo,
        )
        assert result.success is True

        assert cleanup_merge_base_branch(feature_slug, "WP04", repo) is True
        assert cleanup_merge_base_branch(feature_slug, "WP04", repo) is False


class TestThreeParentMerge:
    def test_three_parent_merge_includes_all_files(self, triple_repo: tuple[Path, str]) -> None:
        repo, feature_slug = triple_repo

        result = create_multi_parent_base(
            feature_slug=feature_slug,
            wp_id="WP05",
            dependencies=["WP02", "WP03", "WP04"],
            repo_root=repo,
        )

        assert result.success is True
        assert result.branch_name == f"{feature_slug}-WP05-merge-base"

        run(["git", "checkout", result.branch_name], cwd=repo)
        assert (repo / "base.txt").exists()
        assert (repo / "feature-a.txt").exists()
        assert (repo / "feature-b.txt").exists()
        assert (repo / "feature-c.txt").exists()

        run(["git", "checkout", "main"], cwd=repo)
        assert cleanup_merge_base_branch(feature_slug, "WP05", repo) is True
