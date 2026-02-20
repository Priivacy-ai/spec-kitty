"""Git State Detection Tests for pre-review validation."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.utils import run

pytestmark = [pytest.mark.adversarial]

FEATURE_SLUG = "024-git-state"
WP_ID = "WP01"


def _init_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    run(["git", "config", "user.name", "Test User"], cwd=repo)

    (repo / "README.md").write_text("init", encoding="utf-8")
    run(["git", "add", "README.md"], cwd=repo)
    run(["git", "commit", "-m", "init"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)

    feature_dir = repo / "kitty-specs" / FEATURE_SLUG
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text('{"mission": "software-dev"}\n', encoding="utf-8")
    run(["git", "add", "kitty-specs"], cwd=repo)
    run(["git", "commit", "-m", "add feature"], cwd=repo)

    worktree_dir = repo / ".worktrees" / f"{FEATURE_SLUG}-{WP_ID}"
    worktree_dir.parent.mkdir(exist_ok=True)
    run(
        ["git", "worktree", "add", str(worktree_dir), "-b", f"{FEATURE_SLUG}-{WP_ID}"],
        cwd=repo,
    )

    return repo, worktree_dir


def _commit_in_worktree(worktree: Path, filename: str, content: str, message: str) -> None:
    (worktree / filename).write_text(content, encoding="utf-8")
    run(["git", "add", filename], cwd=worktree)
    run(["git", "commit", "-m", message], cwd=worktree)


def _touch_git_state_marker(worktree: Path, marker: str) -> None:
    result = run(["git", "rev-parse", "--git-path", marker], cwd=worktree)
    marker_path = Path(result.stdout.strip())
    if not marker_path.is_absolute():
        marker_path = worktree / marker_path
    head_sha = run(["git", "rev-parse", "HEAD"], cwd=worktree).stdout.strip()
    marker_path.write_text(f"{head_sha}\n", encoding="utf-8")


@pytest.fixture()
def detached_head_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo, worktree = _init_repo(tmp_path)
    _commit_in_worktree(worktree, "work.txt", "work", "work")
    run(["git", "checkout", "--detach"], cwd=worktree)
    return repo, worktree


@pytest.fixture()
def merge_state_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo, worktree = _init_repo(tmp_path)
    _commit_in_worktree(worktree, "work.txt", "work", "work")
    return repo, worktree


@pytest.fixture()
def staged_uncommitted_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo, worktree = _init_repo(tmp_path)
    _commit_in_worktree(worktree, "work.txt", "work", "work")
    (worktree / "staged.txt").write_text("staged", encoding="utf-8")
    run(["git", "add", "staged.txt"], cwd=worktree)
    return repo, worktree


@pytest.fixture()
def diverged_main_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo, worktree = _init_repo(tmp_path)
    _commit_in_worktree(worktree, "work.txt", "work", "work")

    run(["git", "checkout", "main"], cwd=repo)
    (repo / "main.txt").write_text("main update", encoding="utf-8")
    run(["git", "add", "main.txt"], cwd=repo)
    run(["git", "commit", "-m", "main update"], cwd=repo)
    return repo, worktree


class TestDetachedHead:
    def test_detached_head_detected(self, detached_head_repo: tuple[Path, Path]) -> None:
        """Detached HEAD should be detected before review."""
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        _, worktree = detached_head_repo
        is_valid, guidance = _validate_ready_for_review(worktree, FEATURE_SLUG, WP_ID, force=False)

        assert is_valid is False
        guidance_text = "\n".join(guidance).lower()
        assert "detached head" in guidance_text

    def test_detached_head_with_changes(self, detached_head_repo: tuple[Path, Path]) -> None:
        """Detached HEAD with uncommitted changes should be caught."""
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        _, worktree = detached_head_repo
        (worktree / "dirty.txt").write_text("dirty", encoding="utf-8")
        is_valid, guidance = _validate_ready_for_review(worktree, FEATURE_SLUG, WP_ID, force=False)

        assert is_valid is False
        guidance_text = "\n".join(guidance).lower()
        assert "detached head" in guidance_text


class TestMergeState:
    def test_merge_head_detected(self, merge_state_repo: tuple[Path, Path]) -> None:
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        _, worktree = merge_state_repo
        _touch_git_state_marker(worktree, "MERGE_HEAD")

        is_valid, guidance = _validate_ready_for_review(worktree, FEATURE_SLUG, WP_ID, force=False)

        assert is_valid is False
        guidance_text = "\n".join(guidance).lower()
        assert "merge" in guidance_text

    def test_rebase_head_detected(self, merge_state_repo: tuple[Path, Path]) -> None:
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        _, worktree = merge_state_repo
        _touch_git_state_marker(worktree, "REBASE_HEAD")

        is_valid, guidance = _validate_ready_for_review(worktree, FEATURE_SLUG, WP_ID, force=False)

        assert is_valid is False
        guidance_text = "\n".join(guidance).lower()
        assert "rebase" in guidance_text

    def test_cherry_pick_head_detected(self, merge_state_repo: tuple[Path, Path]) -> None:
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        _, worktree = merge_state_repo
        _touch_git_state_marker(worktree, "CHERRY_PICK_HEAD")

        is_valid, guidance = _validate_ready_for_review(worktree, FEATURE_SLUG, WP_ID, force=False)

        assert is_valid is False
        guidance_text = "\n".join(guidance).lower()
        assert "cherry-pick" in guidance_text


class TestStagedUncommitted:
    def test_staged_uncommitted_detected(self, staged_uncommitted_repo: tuple[Path, Path]) -> None:
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        _, worktree = staged_uncommitted_repo
        is_valid, guidance = _validate_ready_for_review(worktree, FEATURE_SLUG, WP_ID, force=False)

        assert is_valid is False
        guidance_text = "\n".join(guidance).lower()
        assert "staged" in guidance_text
        assert "uncommitted" in guidance_text


class TestMainDivergence:
    def test_main_divergence_detected(self, diverged_main_repo: tuple[Path, Path]) -> None:
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        _, worktree = diverged_main_repo
        is_valid, guidance = _validate_ready_for_review(worktree, FEATURE_SLUG, WP_ID, force=False)

        assert is_valid is False
        guidance_text = "\n".join(guidance).lower()
        assert "main" in guidance_text
        assert "behind" in guidance_text or "rebase" in guidance_text

    def test_main_divergence_allowed_when_moving_to_done(
        self, diverged_main_repo: tuple[Path, Path]
    ) -> None:
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        _, worktree = diverged_main_repo
        is_valid, guidance = _validate_ready_for_review(
            worktree,
            FEATURE_SLUG,
            WP_ID,
            force=False,
            target_lane="done",
        )

        assert is_valid is True
        assert guidance == []


class TestNoCommitsOnBranch:
    def test_no_commits_on_branch_detected(self, tmp_path: Path) -> None:
        from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review

        _, worktree = _init_repo(tmp_path)
        is_valid, guidance = _validate_ready_for_review(worktree, FEATURE_SLUG, WP_ID, force=False)

        assert is_valid is False
        guidance_text = "\n".join(guidance).lower()
        assert "no implementation commits" in guidance_text
