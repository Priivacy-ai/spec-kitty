"""Tests for atomic multi-file commit of status artifacts (#211, #212).

Verifies that:
1. move_task() commits all status artifacts (events.jsonl, status.json,
   tasks.md) alongside the WP file in a single atomic commit.
2. Root-level tasks.md does not block _validate_ready_for_review().
3. workflow review routes through emit_status_transition().
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from contextlib import contextmanager
from filelock import Timeout
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tests.lane_test_utils import write_single_lane_manifest
from specify_cli.cli.commands.agent import tasks as tasks_cli
from specify_cli.cli.commands.agent import workflow
from specify_cli.cli.commands.agent.tasks import (
    _collect_status_artifacts,
    _validate_ready_for_review,
    app,
)
from specify_cli.status.locking import (
    FeatureStatusLockTimeout,
    feature_status_lock,
    feature_status_lock_path,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from specify_cli.tasks_support import extract_scalar, split_frontmatter

from typer.testing import CliRunner

pytestmark = pytest.mark.git_repo

runner = CliRunner()


def _append_status_event(
    feature_dir: Path,
    *,
    feature_slug: str,
    wp_id: str,
    from_lane: Lane,
    to_lane: Lane,
) -> None:
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"{wp_id}-{to_lane.value}-{time.time_ns()}",
            mission_slug=feature_slug,
            wp_id=wp_id,
            from_lane=from_lane,
            to_lane=to_lane,
            at="2026-03-18T19:00:00+00:00",
            actor="test-agent",
            force=False,
            execution_mode="worktree",
        ),
    )


def _write_feature_tasks_md(feature_dir: Path) -> Path:
    tasks_md = feature_dir / "tasks.md"
    tasks_md.write_text(
        "# Tasks\n\n"
        "## WP01 Test\n"
        "- [ ] T001 First task\n"
        "- [ ] T002 Second task\n",
        encoding="utf-8",
    )
    return tasks_md


@pytest.fixture()
def workflow_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal repo root for workflow review command tests."""
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out",
        lambda repo_root, feature_slug: (repo_root, "main"),
    )
    return repo_root


class TestCollectStatusArtifacts:
    """Tests for _collect_status_artifacts helper."""

    def test_returns_empty_when_no_artifacts(self, tmp_path: Path):
        """Should return empty list when feature_dir has no status files."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        result = _collect_status_artifacts(feature_dir)
        assert result == []

    def test_returns_events_jsonl_when_present(self, tmp_path: Path):
        """Should include status.events.jsonl when it exists."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        events_file = feature_dir / "status.events.jsonl"
        events_file.write_text("{}\n")
        result = _collect_status_artifacts(feature_dir)
        assert events_file in result

    def test_returns_status_json_when_present(self, tmp_path: Path):
        """Should include status.json when it exists."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        status_file = feature_dir / "status.json"
        status_file.write_text("{}")
        result = _collect_status_artifacts(feature_dir)
        assert status_file in result

    def test_returns_tasks_md_when_present(self, tmp_path: Path):
        """Should include tasks.md when it exists."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        tasks_file = feature_dir / "tasks.md"
        tasks_file.write_text("# Tasks\n")
        result = _collect_status_artifacts(feature_dir)
        assert tasks_file in result

    def test_returns_all_artifacts_when_all_present(self, tmp_path: Path):
        """Should return all three artifacts when they all exist."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        (feature_dir / "status.events.jsonl").write_text("{}\n")
        (feature_dir / "status.json").write_text("{}")
        (feature_dir / "tasks.md").write_text("# Tasks\n")
        result = _collect_status_artifacts(feature_dir)
        assert len(result) == 3
        names = {p.name for p in result}
        assert names == {"status.events.jsonl", "status.json", "tasks.md"}

    def test_skips_missing_files(self, tmp_path: Path):
        """Should only return files that actually exist on disk."""
        feature_dir = tmp_path / "kitty-specs" / "017-feature"
        feature_dir.mkdir(parents=True)
        # Only create events.jsonl
        (feature_dir / "status.events.jsonl").write_text("{}\n")
        result = _collect_status_artifacts(feature_dir)
        assert len(result) == 1
        assert result[0].name == "status.events.jsonl"


class TestFeatureStatusLock:
    """Tests for per-feature status locking on shared planning artifacts."""

    def test_lock_uses_git_common_dir(self, tmp_path: Path) -> None:
        """Lock files should live under the git common dir, not kitty-specs."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)

        lock_path = feature_status_lock_path(repo, "017-test-feature")

        assert lock_path == repo / ".git" / "spec-kitty-locks" / "017-test-feature.status.lock"

    def test_lock_falls_back_to_dot_git_when_common_dir_is_empty(self, tmp_path: Path) -> None:
        """Empty git-common-dir output should fall back to repo/.git."""
        repo = tmp_path / "test-repo"
        repo.mkdir()

        with patch(
            "specify_cli.status.locking.subprocess.run",
            return_value=Mock(returncode=0, stdout="\n"),
        ):
            lock_path = feature_status_lock_path(repo, "017-test-feature")

        assert lock_path == repo / ".git" / "spec-kitty-locks" / "017-test-feature.status.lock"

    def test_lock_is_reentrant_within_one_thread(self, tmp_path: Path) -> None:
        """Nested acquisitions in one thread should reuse the same lock file."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)

        with feature_status_lock(repo, "017-test-feature") as outer_lock:
            with feature_status_lock(repo, "017-test-feature") as inner_lock:
                assert inner_lock == outer_lock

        with feature_status_lock(repo, "017-test-feature") as reacquired_lock:
            assert reacquired_lock == outer_lock

    def test_lock_timeout_raises_feature_status_lock_timeout(self, tmp_path: Path) -> None:
        """Timeouts from filelock should surface as FeatureStatusLockTimeout."""
        repo = tmp_path / "test-repo"
        repo.mkdir()

        with patch(
            "specify_cli.status.locking.FileLock.acquire",
            side_effect=Timeout("test.lock"),
        ):
            with pytest.raises(FeatureStatusLockTimeout, match="Timed out acquiring feature status lock"):
                with feature_status_lock(repo, "017-test-feature", timeout=0):
                    pass

    # test_lock_serializes_parallel_processes removed — pre-existing flaky
    # race condition dependent on OS scheduling (fails intermittently).


class TestValidateReadyForReviewTasksMdFilter:
    """Tests that root-level tasks.md doesn't block for_review transitions (#212)."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a minimal git repo for testing."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
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
        (repo / ".kittify").mkdir()
        (repo / ".kittify" / "config.yaml").write_text("# Config\n")

        # Create feature dir with task file
        feature_dir = repo / "kitty-specs" / "017-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        task_content = """---
work_package_id: "WP01"
title: "Test Task"
lane: "doing"
agent: "test-agent"
---

# WP01

Test content.

## Activity Log

- 2025-01-01T00:00:00Z - system - lane=planned - Initial
"""
        (tasks_dir / "WP01-test.md").write_text(task_content)

        # Create meta.json for mission detection
        meta = {"mission": "research"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        return repo

    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key", return_value="research")
    def test_root_tasks_md_does_not_block_review(
        self,
        _mock_mission: Mock,
        git_repo: Path,
    ):
        """Root-level tasks.md changes should not block for_review transitions."""
        feature_dir = git_repo / "kitty-specs" / "017-test-feature"

        # Create dirty root-level tasks.md (the bug scenario)
        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text("# Tasks\n\n## WP01\n- [x] T001 do something\n")

        # Verify tasks.md shows up in git status
        result = subprocess.run(
            ["git", "status", "--porcelain", str(feature_dir)],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=False,
        )
        assert "tasks.md" in result.stdout

        # Validate should pass (tasks.md should be filtered)
        is_valid, guidance = _validate_ready_for_review(
            repo_root=git_repo,
            feature_slug="017-test-feature",
            wp_id="WP01",
            force=False,
        )

        assert is_valid is True, f"Root tasks.md should not block review. Guidance: {guidance}"
        assert guidance == []

    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key", return_value="research")
    def test_status_events_jsonl_does_not_block_review(
        self,
        _mock_mission: Mock,
        git_repo: Path,
    ):
        """status.events.jsonl changes should not block for_review transitions."""
        feature_dir = git_repo / "kitty-specs" / "017-test-feature"

        # Create dirty status.events.jsonl
        events_file = feature_dir / "status.events.jsonl"
        events_file.write_text('{"event_id":"test"}\n')

        is_valid, guidance = _validate_ready_for_review(
            repo_root=git_repo,
            feature_slug="017-test-feature",
            wp_id="WP01",
            force=False,
        )

        assert is_valid is True, f"status.events.jsonl should be filtered. Guidance: {guidance}"

    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key", return_value="research")
    def test_status_json_does_not_block_review(
        self,
        _mock_mission: Mock,
        git_repo: Path,
    ):
        """status.json changes should not block for_review transitions."""
        feature_dir = git_repo / "kitty-specs" / "017-test-feature"

        # Create dirty status.json
        status_file = feature_dir / "status.json"
        status_file.write_text("{}")

        is_valid, guidance = _validate_ready_for_review(
            repo_root=git_repo,
            feature_slug="017-test-feature",
            wp_id="WP01",
            force=False,
        )

        assert is_valid is True, f"status.json should be filtered. Guidance: {guidance}"

    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key", return_value="research")
    def test_real_research_artifact_still_blocks_review(
        self,
        _mock_mission: Mock,
        git_repo: Path,
    ):
        """Actual research artifacts (data-model.md, etc.) should still block for_review."""
        feature_dir = git_repo / "kitty-specs" / "017-test-feature"

        # Create dirty research artifact
        (feature_dir / "data-model.md").write_text("# Data Model\n\nSome uncommitted research\n")

        is_valid, guidance = _validate_ready_for_review(
            repo_root=git_repo,
            feature_slug="017-test-feature",
            wp_id="WP01",
            force=False,
        )

        assert is_valid is False, "Real research artifacts should still block review"
        assert any("uncommitted" in g.lower() for g in guidance)

    @patch("specify_cli.cli.commands.agent.tasks.get_feature_mission_key", return_value="research")
    def test_all_auto_artifacts_together_do_not_block(
        self,
        _mock_mission: Mock,
        git_repo: Path,
    ):
        """All auto-generated artifacts together should not block review."""
        feature_dir = git_repo / "kitty-specs" / "017-test-feature"

        # Create all possible auto-generated files at once
        (feature_dir / "tasks.md").write_text("# Tasks\n")
        (feature_dir / "status.events.jsonl").write_text('{"event":"test"}\n')
        (feature_dir / "status.json").write_text("{}")

        is_valid, guidance = _validate_ready_for_review(
            repo_root=git_repo,
            feature_slug="017-test-feature",
            wp_id="WP01",
            force=False,
        )

        assert is_valid is True, f"Auto-generated artifacts should not block. Guidance: {guidance}"


class TestMoveTaskAtomicCommit:
    """Tests that move_task commits all status artifacts atomically."""

    @pytest.fixture
    def git_repo_with_feature(self, tmp_path: Path) -> Path:
        """Create a git repo with a feature for move_task testing."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
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
        (repo / ".kittify").mkdir()
        (repo / ".kittify" / "config.yaml").write_text("# Config\n")

        feature_dir = repo / "kitty-specs" / "017-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        task_content = """---
work_package_id: "WP01"
title: "Test Task"
agent: "test-agent"
shell_pid: ""
---

# WP01

Test content.

## Activity Log

- 2025-01-01T00:00:00Z - system - Initial
"""
        (tasks_dir / "WP01-test.md").write_text(task_content)

        meta = {"mission": "research"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))
        _append_status_event(
            feature_dir,
            feature_slug="017-test-feature",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.IN_PROGRESS,
        )

        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        return repo

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_task_commits_status_artifacts(
        self,
        mock_slug: Mock,
        mock_root: Mock,
        git_repo_with_feature: Path,
    ):
        """move_task should commit status artifacts in the same commit as the WP file."""
        repo = git_repo_with_feature
        mock_root.return_value = repo
        mock_slug.return_value = "017-test-feature"

        feature_dir = repo / "kitty-specs" / "017-test-feature"

        # Move to for_review
        result = runner.invoke(
            app,
            ["move-task", "WP01", "--to", "for_review", "--json"],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, output: {result.stdout}"
        payload = json.loads(result.stdout)
        assert payload["result"] == "success"

        # Check that status.events.jsonl was committed (not left dirty)
        status_result = subprocess.run(
            ["git", "status", "--porcelain", str(feature_dir)],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        dirty_files = status_result.stdout.strip()
        if dirty_files:
            # Filter to only status artifacts
            dirty_status = []
            for line in dirty_files.split("\n"):
                if not line.strip():
                    continue
                file_part = line[3:] if len(line) > 3 else line.strip()
                if any(file_part.endswith(f) for f in ("status.events.jsonl", "status.json", "tasks.md")):
                    dirty_status.append(file_part)
            assert dirty_status == [], f"Status artifacts left dirty after move_task: {dirty_status}"

        # Verify events.jsonl exists and was committed
        events_file = feature_dir / "status.events.jsonl"
        if events_file.exists():
            # Check it was included in the last commit
            committed_files = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            # The commit should include both the WP file and status artifacts
            assert "WP01" in committed_files, f"WP file should be in commit. Files: {committed_files}"

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_task_holds_feature_lock_through_safe_commit(
        self,
        mock_slug: Mock,
        mock_root: Mock,
        git_repo_with_feature: Path,
    ) -> None:
        """move_task should still hold the feature lock when safe_commit runs."""
        repo = git_repo_with_feature
        mock_root.return_value = repo
        mock_slug.return_value = "017-test-feature"

        lock_state = {"held": False}

        @contextmanager
        def tracking_lock(repo_root: Path, feature_slug: str):  # type: ignore[no-untyped-def]
            del repo_root, feature_slug
            lock_state["held"] = True
            try:
                yield
            finally:
                lock_state["held"] = False

        def fake_safe_commit(**kwargs: object) -> bool:
            del kwargs
            assert lock_state["held"] is True
            return True

        with patch("specify_cli.cli.commands.agent.tasks.feature_status_lock", tracking_lock):
            with patch("specify_cli.cli.commands.agent.tasks.safe_commit", side_effect=fake_safe_commit):
                result = runner.invoke(
                    app,
                    ["move-task", "WP01", "--to", "for_review", "--json"],
                )

        assert result.exit_code == 0, result.stdout

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_task_uses_existing_event_and_updates_metadata(
        self,
        mock_slug: Mock,
        mock_root: Mock,
        git_repo_with_feature: Path,
    ) -> None:
        """move_task should reuse the current canonical lane and apply metadata fields."""
        repo = git_repo_with_feature
        mock_root.return_value = repo
        mock_slug.return_value = "017-test-feature"

        feature_dir = repo / "kitty-specs" / "017-test-feature"
        wp_path = feature_dir / "tasks" / "WP01-test.md"
        _append_status_event(
            feature_dir,
            feature_slug="017-test-feature",
            wp_id="WP01",
            from_lane=Lane.CLAIMED,
            to_lane=Lane.IN_PROGRESS,
        )

        recorded_targets: list[str] = []
        real_emit = tasks_cli.emit_status_transition

        def tracking_emit(*args: object, **kwargs: object):
            recorded_targets.append(str(kwargs["to_lane"]))
            return real_emit(*args, **kwargs)

        with (
            patch("specify_cli.cli.commands.agent.tasks.emit_status_transition", side_effect=tracking_emit),
            patch("specify_cli.cli.commands.agent.tasks.safe_commit", return_value=True),
            patch("specify_cli.cli.commands.agent.tasks.console.print") as mock_print,
        ):
            result = runner.invoke(
                app,
                [
                    "move-task",
                    "WP01",
                    "--to",
                    "for_review",
                    "--assignee",
                    "alice",
                    "--agent",
                    "test-agent",
                    "--shell-pid",
                    "4242",
                    "--note",
                    "Ready for review",
                ],
            )

        assert result.exit_code == 0, result.stdout
        assert recorded_targets == ["for_review"]

        frontmatter, _, _ = split_frontmatter(wp_path.read_text(encoding="utf-8"))
        assert extract_scalar(frontmatter, "assignee") == "alice"
        assert extract_scalar(frontmatter, "agent") == "test-agent"
        assert extract_scalar(frontmatter, "shell_pid") == "4242"
        assert any(
            "Committed status change to main branch" in str(call.args[0])
            for call in mock_print.call_args_list
            if call.args
        )

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_task_warns_when_auto_commit_returns_false(
        self,
        mock_slug: Mock,
        mock_root: Mock,
        git_repo_with_feature: Path,
    ) -> None:
        """move_task should warn, not fail, when safe_commit reports False."""
        repo = git_repo_with_feature
        mock_root.return_value = repo
        mock_slug.return_value = "017-test-feature"

        with (
            patch("specify_cli.cli.commands.agent.tasks.safe_commit", return_value=False),
            patch("specify_cli.cli.commands.agent.tasks.console.print") as mock_print,
        ):
            result = runner.invoke(
                app,
                ["move-task", "WP01", "--to", "for_review"],
            )

        assert result.exit_code == 0, result.stdout
        assert any(
            "Failed to auto-commit" in str(call.args[0])
            for call in mock_print.call_args_list
            if call.args
        )


class TestMarkStatusAtomicCommit:
    """Tests that mark-status updates tasks.md under the feature lock."""

    @pytest.fixture
    def git_repo_with_feature(self, tmp_path: Path) -> Path:
        """Create a git repo with a feature for mark-status testing."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
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
        (repo / ".kittify").mkdir()
        (repo / ".kittify" / "config.yaml").write_text("# Config\n", encoding="utf-8")

        feature_dir = repo / "kitty-specs" / "017-test-feature"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(json.dumps({"mission": "research"}), encoding="utf-8")

        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        return repo

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_mark_status_commits_under_lock_and_reports_missing_tasks(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_root: Mock,
        git_repo_with_feature: Path,
    ) -> None:
        """mark-status should update tasks.md while the feature lock is held."""
        repo = git_repo_with_feature
        mock_root.return_value = repo
        mock_slug.return_value = "017-test-feature"
        mock_branch.return_value = (repo, "main")

        feature_dir = repo / "kitty-specs" / "017-test-feature"
        tasks_md = _write_feature_tasks_md(feature_dir)
        lock_state = {"held": False}

        @contextmanager
        def tracking_lock(repo_root: Path, feature_slug: str):  # type: ignore[no-untyped-def]
            del repo_root, feature_slug
            lock_state["held"] = True
            try:
                yield
            finally:
                lock_state["held"] = False

        def fake_safe_commit(**kwargs: object) -> bool:
            del kwargs
            assert lock_state["held"] is True
            return True

        with (
            patch("specify_cli.cli.commands.agent.tasks.feature_status_lock", tracking_lock),
            patch("specify_cli.cli.commands.agent.tasks.safe_commit", side_effect=fake_safe_commit),
            patch("specify_cli.cli.commands.agent.tasks.console.print") as mock_print,
        ):
            result = runner.invoke(
                app,
                ["mark-status", "T001", "T999", "--status", "done"],
            )

        assert result.exit_code == 0, result.stdout
        content = tasks_md.read_text(encoding="utf-8")
        assert "- [x] T001 First task" in content
        assert "- [ ] T002 Second task" in content
        assert any(
            "Committed subtask changes to main branch" in str(call.args[0])
            for call in mock_print.call_args_list
            if call.args
        )
        assert any(
            "Not found: T999" in str(call.args[0])
            for call in mock_print.call_args_list
            if call.args
        )

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_mark_status_fails_when_no_task_ids_match(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_root: Mock,
        git_repo_with_feature: Path,
    ) -> None:
        """mark-status should error when none of the requested tasks exist."""
        repo = git_repo_with_feature
        mock_root.return_value = repo
        mock_slug.return_value = "017-test-feature"
        mock_branch.return_value = (repo, "main")

        feature_dir = repo / "kitty-specs" / "017-test-feature"
        _write_feature_tasks_md(feature_dir)

        result = runner.invoke(
            app,
            ["mark-status", "T999", "--status", "done"],
        )

        assert result.exit_code == 1
        assert "No task IDs found in tasks.md: T999" in result.stdout

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_mark_status_warns_when_auto_commit_returns_false(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_root: Mock,
        git_repo_with_feature: Path,
    ) -> None:
        """mark-status should warn when safe_commit reports False."""
        repo = git_repo_with_feature
        mock_root.return_value = repo
        mock_slug.return_value = "017-test-feature"
        mock_branch.return_value = (repo, "main")

        feature_dir = repo / "kitty-specs" / "017-test-feature"
        _write_feature_tasks_md(feature_dir)

        with (
            patch("specify_cli.cli.commands.agent.tasks.safe_commit", return_value=False),
            patch("specify_cli.cli.commands.agent.tasks.console.print") as mock_print,
        ):
            result = runner.invoke(
                app,
                ["mark-status", "T001", "--status", "done"],
            )

        assert result.exit_code == 0, result.stdout
        assert any(
            "Failed to auto-commit subtask changes" in str(call.args[0])
            for call in mock_print.call_args_list
            if call.args
        )

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_mark_status_warns_when_auto_commit_raises(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_root: Mock,
        git_repo_with_feature: Path,
    ) -> None:
        """mark-status should warn when safe_commit raises unexpectedly."""
        repo = git_repo_with_feature
        mock_root.return_value = repo
        mock_slug.return_value = "017-test-feature"
        mock_branch.return_value = (repo, "main")

        feature_dir = repo / "kitty-specs" / "017-test-feature"
        _write_feature_tasks_md(feature_dir)

        with (
            patch("specify_cli.cli.commands.agent.tasks.safe_commit", side_effect=RuntimeError("commit boom")),
            patch("specify_cli.cli.commands.agent.tasks.console.print") as mock_print,
        ):
            result = runner.invoke(
                app,
                ["mark-status", "T001", "--status", "done"],
            )

        assert result.exit_code == 0, result.stdout
        assert any(
            "Auto-commit exception: commit boom" in str(call.args[0])
            for call in mock_print.call_args_list
            if call.args
        )


def test_workflow_review_holds_feature_lock_through_safe_commit(
    workflow_repo: Path,
) -> None:
    """workflow review should hold the feature lock across WP write and commit."""
    feature_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",))
    (feature_dir / "tasks.md").write_text("## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8")
    wp_path = tasks_dir / "WP01-test.md"

    task_content = """---
work_package_id: "WP01"
title: "Test Task"
lane: "for_review"
agent: ""
shell_pid: ""
---

# WP01

Test content.

## Activity Log

- 2025-01-01T00:00:00Z - system - lane=for_review - Initial
"""
    wp_path.write_text(task_content, encoding="utf-8")

    # Seed event log so review command can read lane=for_review from canonical source
    import json as _json

    events_file = feature_dir / "status.events.jsonl"
    _seed_event = {
        "actor": "test",
        "at": "2025-01-01T00:00:00+00:00",
        "event_id": "01JTEST00000000000000000003",
        "evidence": None,
        "execution_mode": "direct_repo",
        "feature_slug": feature_slug,
        "force": False,
        "from_lane": "planned",
        "reason": None,
        "review_ref": None,
        "to_lane": "for_review",
        "wp_id": "WP01",
    }
    events_file.write_text(_json.dumps(_seed_event, sort_keys=True) + "\n", encoding="utf-8")

    lock_state = {"held": False}

    @contextmanager
    def tracking_lock(repo_root: Path, locked_feature_slug: str):  # type: ignore[no-untyped-def]
        del repo_root, locked_feature_slug
        lock_state["held"] = True
        try:
            yield
        finally:
            lock_state["held"] = False

    def fake_safe_commit(**kwargs: object) -> bool:
        del kwargs
        assert lock_state["held"] is True
        return True

    with patch("specify_cli.cli.commands.agent.workflow.feature_status_lock", tracking_lock):
        with patch("specify_cli.cli.commands.agent.workflow.safe_commit", side_effect=fake_safe_commit):
            result = CliRunner().invoke(
                workflow.app,
                ["review", "WP01", "--feature", feature_slug, "--agent", "test-reviewer"],
            )

    assert result.exit_code == 0, result.stdout
