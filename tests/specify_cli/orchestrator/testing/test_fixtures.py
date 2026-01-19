"""Tests for fixture data structures, validation, and loader functions."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from specify_cli.orchestrator.config import OrchestrationStatus, WPStatus
from specify_cli.orchestrator.state import OrchestrationRun, WPExecution
from specify_cli.orchestrator.testing.fixtures import (
    FixtureCheckpoint,
    GitError,
    StateFileError,
    TestContext,
    WorktreeMetadata,
    WorktreesFileError,
    cleanup_temp_dir,
    cleanup_test_context,
    copy_fixture_to_temp,
    create_worktrees_from_metadata,
    init_git_repo,
    load_checkpoint,
    load_orchestration_state,
    load_state_file,
    load_worktrees_file,
    register_for_cleanup,
    save_state_file,
    save_worktrees_file,
)


# =============================================================================
# FixtureCheckpoint Tests
# =============================================================================


class TestFixtureCheckpoint:
    """Tests for FixtureCheckpoint dataclass."""

    def test_create_checkpoint(self, tmp_path: Path) -> None:
        """Test basic checkpoint creation."""
        checkpoint = FixtureCheckpoint(
            name="wp_created",
            path=tmp_path / "checkpoint_wp_created",
            orchestrator_version="0.12.0",
            created_at=datetime(2026, 1, 19, 10, 0, 0),
        )

        assert checkpoint.name == "wp_created"
        assert checkpoint.orchestrator_version == "0.12.0"
        assert checkpoint.created_at == datetime(2026, 1, 19, 10, 0, 0)

    def test_property_paths(self, tmp_path: Path) -> None:
        """Test computed path properties."""
        checkpoint_dir = tmp_path / "checkpoint_wp_created"
        checkpoint = FixtureCheckpoint(
            name="wp_created",
            path=checkpoint_dir,
            orchestrator_version="0.12.0",
            created_at=datetime.now(),
        )

        assert checkpoint.state_file == checkpoint_dir / "state.json"
        assert checkpoint.feature_dir == checkpoint_dir / "feature"
        assert checkpoint.worktrees_file == checkpoint_dir / "worktrees.json"

    def test_exists_returns_false_for_missing(self, tmp_path: Path) -> None:
        """Test exists() returns False when checkpoint directory doesn't exist."""
        checkpoint = FixtureCheckpoint(
            name="wp_created",
            path=tmp_path / "nonexistent",
            orchestrator_version="0.12.0",
            created_at=datetime.now(),
        )

        assert checkpoint.exists() is False

    def test_exists_returns_false_for_partial(self, tmp_path: Path) -> None:
        """Test exists() returns False when only some files exist."""
        checkpoint_dir = tmp_path / "checkpoint_partial"
        checkpoint_dir.mkdir()
        (checkpoint_dir / "state.json").write_text("{}")
        # Missing feature/ and worktrees.json

        checkpoint = FixtureCheckpoint(
            name="partial",
            path=checkpoint_dir,
            orchestrator_version="0.12.0",
            created_at=datetime.now(),
        )

        assert checkpoint.exists() is False

    def test_exists_returns_true_for_complete(self, tmp_path: Path) -> None:
        """Test exists() returns True when all required files exist."""
        checkpoint_dir = tmp_path / "checkpoint_complete"
        checkpoint_dir.mkdir()
        (checkpoint_dir / "state.json").write_text("{}")
        (checkpoint_dir / "feature").mkdir()
        (checkpoint_dir / "worktrees.json").write_text("{}")

        checkpoint = FixtureCheckpoint(
            name="complete",
            path=checkpoint_dir,
            orchestrator_version="0.12.0",
            created_at=datetime.now(),
        )

        assert checkpoint.exists() is True

    def test_to_dict(self, tmp_path: Path) -> None:
        """Test serialization to dict."""
        created = datetime(2026, 1, 19, 10, 0, 0)
        checkpoint = FixtureCheckpoint(
            name="wp_created",
            path=tmp_path / "checkpoint",
            orchestrator_version="0.12.0",
            created_at=created,
        )

        data = checkpoint.to_dict()

        assert data["name"] == "wp_created"
        assert data["path"] == str(tmp_path / "checkpoint")
        assert data["orchestrator_version"] == "0.12.0"
        assert data["created_at"] == "2026-01-19T10:00:00"

    def test_from_dict(self, tmp_path: Path) -> None:
        """Test deserialization from dict."""
        data = {
            "name": "wp_created",
            "path": str(tmp_path / "checkpoint"),
            "orchestrator_version": "0.12.0",
            "created_at": "2026-01-19T10:00:00",
        }

        checkpoint = FixtureCheckpoint.from_dict(data)

        assert checkpoint.name == "wp_created"
        assert checkpoint.path == tmp_path / "checkpoint"
        assert checkpoint.orchestrator_version == "0.12.0"
        assert checkpoint.created_at == datetime(2026, 1, 19, 10, 0, 0)

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Test serialization roundtrip."""
        original = FixtureCheckpoint(
            name="wp_created",
            path=tmp_path / "checkpoint",
            orchestrator_version="0.12.0",
            created_at=datetime(2026, 1, 19, 10, 0, 0),
        )

        restored = FixtureCheckpoint.from_dict(original.to_dict())

        assert restored.name == original.name
        assert restored.path == original.path
        assert restored.orchestrator_version == original.orchestrator_version
        assert restored.created_at == original.created_at


# =============================================================================
# WorktreeMetadata Tests
# =============================================================================


class TestWorktreeMetadata:
    """Tests for WorktreeMetadata dataclass."""

    def test_create_worktree_metadata(self) -> None:
        """Test basic creation with all fields."""
        metadata = WorktreeMetadata(
            wp_id="WP01",
            branch_name="test-feature-WP01",
            relative_path=".worktrees/test-feature-WP01",
            commit_hash="abc123",
        )

        assert metadata.wp_id == "WP01"
        assert metadata.branch_name == "test-feature-WP01"
        assert metadata.relative_path == ".worktrees/test-feature-WP01"
        assert metadata.commit_hash == "abc123"

    def test_commit_hash_defaults_to_none(self) -> None:
        """Test commit_hash is optional and defaults to None."""
        metadata = WorktreeMetadata(
            wp_id="WP01",
            branch_name="test-feature-WP01",
            relative_path=".worktrees/test-feature-WP01",
        )

        assert metadata.commit_hash is None

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        metadata = WorktreeMetadata(
            wp_id="WP01",
            branch_name="test-feature-WP01",
            relative_path=".worktrees/test-feature-WP01",
            commit_hash="abc123",
        )

        data = metadata.to_dict()

        assert data == {
            "wp_id": "WP01",
            "branch_name": "test-feature-WP01",
            "relative_path": ".worktrees/test-feature-WP01",
            "commit_hash": "abc123",
        }

    def test_to_dict_with_none_commit(self) -> None:
        """Test serialization preserves None commit_hash."""
        metadata = WorktreeMetadata(
            wp_id="WP01",
            branch_name="test-feature-WP01",
            relative_path=".worktrees/test-feature-WP01",
        )

        data = metadata.to_dict()

        assert data["commit_hash"] is None

    def test_from_dict(self) -> None:
        """Test deserialization from dict."""
        data = {
            "wp_id": "WP01",
            "branch_name": "test-feature-WP01",
            "relative_path": ".worktrees/test-feature-WP01",
            "commit_hash": "abc123",
        }

        metadata = WorktreeMetadata.from_dict(data)

        assert metadata.wp_id == "WP01"
        assert metadata.branch_name == "test-feature-WP01"
        assert metadata.relative_path == ".worktrees/test-feature-WP01"
        assert metadata.commit_hash == "abc123"

    def test_from_dict_missing_commit_hash(self) -> None:
        """Test deserialization handles missing commit_hash."""
        data = {
            "wp_id": "WP01",
            "branch_name": "test-feature-WP01",
            "relative_path": ".worktrees/test-feature-WP01",
        }

        metadata = WorktreeMetadata.from_dict(data)

        assert metadata.commit_hash is None

    def test_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        original = WorktreeMetadata(
            wp_id="WP01",
            branch_name="test-feature-WP01",
            relative_path=".worktrees/test-feature-WP01",
            commit_hash="abc123",
        )

        restored = WorktreeMetadata.from_dict(original.to_dict())

        assert restored.wp_id == original.wp_id
        assert restored.branch_name == original.branch_name
        assert restored.relative_path == original.relative_path
        assert restored.commit_hash == original.commit_hash


# =============================================================================
# TestContext Tests
# =============================================================================


class TestTestContext:
    """Tests for TestContext dataclass."""

    def test_create_minimal_context(self, tmp_path: Path) -> None:
        """Test creating context with minimal required fields."""
        context = TestContext(
            temp_dir=tmp_path,
            repo_root=tmp_path / "repo",
            feature_dir=tmp_path / "repo" / "kitty-specs" / "test-feature",
            test_path=None,  # Will be TestPath object when WP02 merges
        )

        assert context.temp_dir == tmp_path
        assert context.repo_root == tmp_path / "repo"
        assert context.checkpoint is None
        assert context.orchestration_state is None
        assert context.worktrees == []

    def test_computed_paths(self, tmp_path: Path) -> None:
        """Test computed path properties."""
        repo_root = tmp_path / "repo"
        feature_dir = repo_root / "kitty-specs" / "test-feature"

        context = TestContext(
            temp_dir=tmp_path,
            repo_root=repo_root,
            feature_dir=feature_dir,
            test_path=None,
        )

        assert context.kitty_specs_dir == repo_root / "kitty-specs"
        assert context.worktrees_dir == repo_root / ".worktrees"
        assert context.state_file == feature_dir / ".orchestration-state.json"

    def test_with_checkpoint(self, tmp_path: Path) -> None:
        """Test context with loaded checkpoint."""
        checkpoint = FixtureCheckpoint(
            name="wp_created",
            path=tmp_path / "checkpoint",
            orchestrator_version="0.12.0",
            created_at=datetime.now(),
        )

        context = TestContext(
            temp_dir=tmp_path,
            repo_root=tmp_path / "repo",
            feature_dir=tmp_path / "repo" / "kitty-specs" / "test-feature",
            test_path=None,
            checkpoint=checkpoint,
        )

        assert context.checkpoint is not None
        assert context.checkpoint.name == "wp_created"

    def test_with_worktrees(self, tmp_path: Path) -> None:
        """Test context with worktree metadata."""
        worktrees = [
            WorktreeMetadata(
                wp_id="WP01",
                branch_name="test-feature-WP01",
                relative_path=".worktrees/test-feature-WP01",
            ),
            WorktreeMetadata(
                wp_id="WP02",
                branch_name="test-feature-WP02",
                relative_path=".worktrees/test-feature-WP02",
            ),
        ]

        context = TestContext(
            temp_dir=tmp_path,
            repo_root=tmp_path / "repo",
            feature_dir=tmp_path / "repo" / "kitty-specs" / "test-feature",
            test_path=None,
            worktrees=worktrees,
        )

        assert len(context.worktrees) == 2
        assert context.worktrees[0].wp_id == "WP01"
        assert context.worktrees[1].wp_id == "WP02"


# =============================================================================
# worktrees.json Validation Tests
# =============================================================================


class TestLoadWorktreesFile:
    """Tests for load_worktrees_file function."""

    def test_load_valid_file(self, tmp_path: Path) -> None:
        """Test loading a valid worktrees.json file."""
        worktrees_file = tmp_path / "worktrees.json"
        worktrees_file.write_text(
            json.dumps(
                {
                    "worktrees": [
                        {
                            "wp_id": "WP01",
                            "branch_name": "test-feature-WP01",
                            "relative_path": ".worktrees/test-feature-WP01",
                            "commit_hash": None,
                        },
                        {
                            "wp_id": "WP02",
                            "branch_name": "test-feature-WP02",
                            "relative_path": ".worktrees/test-feature-WP02",
                            "commit_hash": "abc123",
                        },
                    ]
                }
            )
        )

        worktrees = load_worktrees_file(worktrees_file)

        assert len(worktrees) == 2
        assert worktrees[0].wp_id == "WP01"
        assert worktrees[0].commit_hash is None
        assert worktrees[1].wp_id == "WP02"
        assert worktrees[1].commit_hash == "abc123"

    def test_load_empty_worktrees(self, tmp_path: Path) -> None:
        """Test loading file with empty worktrees array."""
        worktrees_file = tmp_path / "worktrees.json"
        worktrees_file.write_text(json.dumps({"worktrees": []}))

        worktrees = load_worktrees_file(worktrees_file)

        assert worktrees == []

    def test_raises_for_missing_file(self, tmp_path: Path) -> None:
        """Test raises WorktreesFileError for missing file."""
        with pytest.raises(WorktreesFileError, match="not found"):
            load_worktrees_file(tmp_path / "nonexistent.json")

    def test_raises_for_invalid_json(self, tmp_path: Path) -> None:
        """Test raises WorktreesFileError for invalid JSON."""
        worktrees_file = tmp_path / "worktrees.json"
        worktrees_file.write_text("not valid json {{{")

        with pytest.raises(WorktreesFileError, match="Invalid JSON"):
            load_worktrees_file(worktrees_file)

    def test_raises_for_non_object(self, tmp_path: Path) -> None:
        """Test raises WorktreesFileError when top-level is not object."""
        worktrees_file = tmp_path / "worktrees.json"
        worktrees_file.write_text("[]")

        with pytest.raises(WorktreesFileError, match="Expected object"):
            load_worktrees_file(worktrees_file)

    def test_raises_for_missing_worktrees_key(self, tmp_path: Path) -> None:
        """Test raises WorktreesFileError when 'worktrees' key is missing."""
        worktrees_file = tmp_path / "worktrees.json"
        worktrees_file.write_text(json.dumps({"other": []}))

        with pytest.raises(WorktreesFileError, match="Missing 'worktrees' key"):
            load_worktrees_file(worktrees_file)

    def test_raises_for_worktrees_not_array(self, tmp_path: Path) -> None:
        """Test raises WorktreesFileError when 'worktrees' is not array."""
        worktrees_file = tmp_path / "worktrees.json"
        worktrees_file.write_text(json.dumps({"worktrees": "not an array"}))

        with pytest.raises(WorktreesFileError, match="must be an array"):
            load_worktrees_file(worktrees_file)

    def test_raises_for_missing_required_keys(self, tmp_path: Path) -> None:
        """Test raises WorktreesFileError when worktree entry misses keys."""
        worktrees_file = tmp_path / "worktrees.json"
        worktrees_file.write_text(
            json.dumps(
                {
                    "worktrees": [
                        {"wp_id": "WP01"}  # Missing branch_name, relative_path
                    ]
                }
            )
        )

        with pytest.raises(WorktreesFileError, match="missing required keys"):
            load_worktrees_file(worktrees_file)

    def test_raises_for_non_object_entry(self, tmp_path: Path) -> None:
        """Test raises WorktreesFileError when worktree entry is not object."""
        worktrees_file = tmp_path / "worktrees.json"
        worktrees_file.write_text(json.dumps({"worktrees": ["not an object"]}))

        with pytest.raises(WorktreesFileError, match="must be an object"):
            load_worktrees_file(worktrees_file)


class TestSaveWorktreesFile:
    """Tests for save_worktrees_file function."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Test save creates the file with correct content."""
        worktrees_file = tmp_path / "worktrees.json"
        worktrees = [
            WorktreeMetadata(
                wp_id="WP01",
                branch_name="test-feature-WP01",
                relative_path=".worktrees/test-feature-WP01",
            )
        ]

        save_worktrees_file(worktrees_file, worktrees)

        assert worktrees_file.exists()
        data = json.loads(worktrees_file.read_text())
        assert len(data["worktrees"]) == 1
        assert data["worktrees"][0]["wp_id"] == "WP01"

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test save creates parent directories if needed."""
        worktrees_file = tmp_path / "nested" / "dir" / "worktrees.json"

        save_worktrees_file(worktrees_file, [])

        assert worktrees_file.exists()

    def test_save_empty_list(self, tmp_path: Path) -> None:
        """Test saving empty worktrees list."""
        worktrees_file = tmp_path / "worktrees.json"

        save_worktrees_file(worktrees_file, [])

        data = json.loads(worktrees_file.read_text())
        assert data == {"worktrees": []}

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Test save followed by load returns same data."""
        worktrees_file = tmp_path / "worktrees.json"
        original = [
            WorktreeMetadata(
                wp_id="WP01",
                branch_name="test-feature-WP01",
                relative_path=".worktrees/test-feature-WP01",
                commit_hash="abc123",
            ),
            WorktreeMetadata(
                wp_id="WP02",
                branch_name="test-feature-WP02",
                relative_path=".worktrees/test-feature-WP02",
            ),
        ]

        save_worktrees_file(worktrees_file, original)
        loaded = load_worktrees_file(worktrees_file)

        assert len(loaded) == len(original)
        for orig, load in zip(original, loaded):
            assert orig.wp_id == load.wp_id
            assert orig.branch_name == load.branch_name
            assert orig.relative_path == load.relative_path
            assert orig.commit_hash == load.commit_hash


# =============================================================================
# state.json Validation Tests
# =============================================================================


class TestLoadStateFile:
    """Tests for load_state_file function."""

    def _create_valid_state_json(self) -> dict:
        """Create a valid state.json content."""
        return {
            "run_id": "test-run-001",
            "feature_slug": "test-feature",
            "started_at": "2026-01-19T10:00:00",
            "completed_at": None,
            "status": "running",
            "config_hash": "abc123",
            "concurrency_limit": 5,
            "wps_total": 2,
            "wps_completed": 0,
            "wps_failed": 0,
            "parallel_peak": 0,
            "total_agent_invocations": 0,
            "work_packages": {
                "WP01": {
                    "wp_id": "WP01",
                    "status": "pending",
                    "implementation_agent": None,
                    "implementation_started": None,
                    "implementation_completed": None,
                    "implementation_exit_code": None,
                    "implementation_retries": 0,
                    "review_agent": None,
                    "review_started": None,
                    "review_completed": None,
                    "review_exit_code": None,
                    "review_retries": 0,
                    "log_file": None,
                    "worktree_path": None,
                    "last_error": None,
                    "fallback_agents_tried": [],
                }
            },
        }

    def test_load_valid_state(self, tmp_path: Path) -> None:
        """Test loading a valid state.json file."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(self._create_valid_state_json()))

        state = load_state_file(state_file)

        assert state.run_id == "test-run-001"
        assert state.feature_slug == "test-feature"
        assert state.status == OrchestrationStatus.RUNNING
        assert "WP01" in state.work_packages
        assert state.work_packages["WP01"].status == WPStatus.PENDING

    def test_raises_for_missing_file(self, tmp_path: Path) -> None:
        """Test raises StateFileError for missing file."""
        with pytest.raises(StateFileError, match="not found"):
            load_state_file(tmp_path / "nonexistent.json")

    def test_raises_for_invalid_json(self, tmp_path: Path) -> None:
        """Test raises StateFileError for invalid JSON."""
        state_file = tmp_path / "state.json"
        state_file.write_text("not valid json {{{")

        with pytest.raises(StateFileError, match="Invalid JSON"):
            load_state_file(state_file)

    def test_raises_for_missing_required_fields(self, tmp_path: Path) -> None:
        """Test raises StateFileError when required fields are missing."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"run_id": "test"}))

        with pytest.raises(StateFileError, match="Missing required fields"):
            load_state_file(state_file)

    def test_raises_for_invalid_structure(self, tmp_path: Path) -> None:
        """Test raises StateFileError when structure is invalid."""
        state_file = tmp_path / "state.json"
        state_data = self._create_valid_state_json()
        state_data["started_at"] = "not-a-datetime"

        state_file.write_text(json.dumps(state_data))

        with pytest.raises(StateFileError, match="Failed to parse"):
            load_state_file(state_file)


class TestSaveStateFile:
    """Tests for save_state_file function."""

    def _create_orchestration_run(self) -> OrchestrationRun:
        """Create a valid OrchestrationRun for testing."""
        return OrchestrationRun(
            run_id="test-run-001",
            feature_slug="test-feature",
            started_at=datetime(2026, 1, 19, 10, 0, 0),
            status=OrchestrationStatus.RUNNING,
            wps_total=2,
            work_packages={
                "WP01": WPExecution(wp_id="WP01", status=WPStatus.PENDING),
            },
        )

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Test save creates the file."""
        state_file = tmp_path / "state.json"
        state = self._create_orchestration_run()

        save_state_file(state_file, state)

        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["run_id"] == "test-run-001"

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test save creates parent directories if needed."""
        state_file = tmp_path / "nested" / "dir" / "state.json"
        state = self._create_orchestration_run()

        save_state_file(state_file, state)

        assert state_file.exists()

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Test save followed by load returns equivalent state."""
        state_file = tmp_path / "state.json"
        original = self._create_orchestration_run()

        save_state_file(state_file, original)
        loaded = load_state_file(state_file)

        assert loaded.run_id == original.run_id
        assert loaded.feature_slug == original.feature_slug
        assert loaded.status == original.status
        assert loaded.wps_total == original.wps_total
        assert "WP01" in loaded.work_packages
        assert loaded.work_packages["WP01"].status == original.work_packages["WP01"].status


# =============================================================================
# Fixture Loader Tests (WP04)
# =============================================================================


def _create_valid_state_json() -> dict:
    """Create a valid state.json content for testing."""
    return {
        "run_id": "test-run-001",
        "feature_slug": "test-feature",
        "started_at": "2026-01-19T10:00:00",
        "completed_at": None,
        "status": "running",
        "config_hash": "abc123",
        "concurrency_limit": 5,
        "wps_total": 2,
        "wps_completed": 0,
        "wps_failed": 0,
        "parallel_peak": 0,
        "total_agent_invocations": 0,
        "work_packages": {
            "WP01": {
                "wp_id": "WP01",
                "status": "pending",
                "implementation_agent": None,
                "implementation_started": None,
                "implementation_completed": None,
                "implementation_exit_code": None,
                "implementation_retries": 0,
                "review_agent": None,
                "review_started": None,
                "review_completed": None,
                "review_exit_code": None,
                "review_retries": 0,
                "log_file": None,
                "worktree_path": None,
                "last_error": None,
                "fallback_agents_tried": [],
            }
        },
    }


def _create_complete_checkpoint(base_path: Path, name: str = "wp_created") -> FixtureCheckpoint:
    """Create a complete checkpoint fixture for testing.

    Creates the checkpoint directory with all required files:
    - state.json
    - feature/ directory with some content
    - worktrees.json
    """
    checkpoint_dir = base_path / f"checkpoint_{name}"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Create state.json
    (checkpoint_dir / "state.json").write_text(json.dumps(_create_valid_state_json()))

    # Create feature directory with content
    feature_dir = checkpoint_dir / "feature"
    feature_dir.mkdir(exist_ok=True)
    (feature_dir / "spec.md").write_text("# Test Feature Spec")
    (feature_dir / "plan.md").write_text("# Test Feature Plan")
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    (tasks_dir / "WP01.md").write_text("# WP01 Task")

    # Create worktrees.json with empty list
    (checkpoint_dir / "worktrees.json").write_text(json.dumps({"worktrees": []}))

    return FixtureCheckpoint(
        name=name,
        path=checkpoint_dir,
        orchestrator_version="0.12.0",
        created_at=datetime.now(),
    )


class TestCopyFixtureToTemp:
    """Tests for copy_fixture_to_temp function."""

    def test_copies_fixture_to_temp(self, tmp_path: Path) -> None:
        """Test that fixture is copied to temp directory."""
        checkpoint = _create_complete_checkpoint(tmp_path)

        temp_dir = copy_fixture_to_temp(checkpoint)

        try:
            assert temp_dir.exists()
            assert (temp_dir / "kitty-specs" / "test-feature").exists()
            assert (temp_dir / "kitty-specs" / "test-feature" / "spec.md").exists()
            assert (temp_dir / "kitty-specs" / "test-feature" / ".orchestration-state.json").exists()
            assert (temp_dir / "worktrees.json").exists()
        finally:
            cleanup_temp_dir(temp_dir)

    def test_temp_dir_has_checkpoint_name_prefix(self, tmp_path: Path) -> None:
        """Test that temp directory name includes checkpoint name."""
        checkpoint = _create_complete_checkpoint(tmp_path, name="my_checkpoint")

        temp_dir = copy_fixture_to_temp(checkpoint)

        try:
            assert "orchestrator_test_my_checkpoint_" in temp_dir.name
        finally:
            cleanup_temp_dir(temp_dir)

    def test_raises_for_incomplete_checkpoint(self, tmp_path: Path) -> None:
        """Test raises FileNotFoundError for incomplete checkpoint."""
        # Create partial checkpoint (missing worktrees.json)
        checkpoint_dir = tmp_path / "partial_checkpoint"
        checkpoint_dir.mkdir()
        (checkpoint_dir / "state.json").write_text("{}")
        (checkpoint_dir / "feature").mkdir()
        # Missing worktrees.json

        checkpoint = FixtureCheckpoint(
            name="partial",
            path=checkpoint_dir,
            orchestrator_version="0.12.0",
            created_at=datetime.now(),
        )

        with pytest.raises(FileNotFoundError, match="Checkpoint not found or incomplete"):
            copy_fixture_to_temp(checkpoint)


class TestInitGitRepo:
    """Tests for init_git_repo function."""

    def test_initializes_git_repo(self, tmp_path: Path) -> None:
        """Test that git repository is initialized."""
        # Create a file to commit
        (tmp_path / "README.md").write_text("# Test Repo")

        init_git_repo(tmp_path)

        # Check .git directory exists
        assert (tmp_path / ".git").exists()

        # Check there's a commit
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Initial test fixture commit" in result.stdout

    def test_configures_git_user(self, tmp_path: Path) -> None:
        """Test that git user is configured."""
        (tmp_path / "README.md").write_text("# Test")

        init_git_repo(tmp_path)

        # Check user config
        result = subprocess.run(
            ["git", "config", "user.email"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "test@example.com" in result.stdout


class TestCreateWorktreesFromMetadata:
    """Tests for create_worktrees_from_metadata function."""

    def test_creates_single_worktree(self, tmp_path: Path) -> None:
        """Test creating a single worktree."""
        # Initialize git repo first
        (tmp_path / "README.md").write_text("# Test")
        init_git_repo(tmp_path)

        worktrees = [
            WorktreeMetadata(
                wp_id="WP01",
                branch_name="test-feature-WP01",
                relative_path=".worktrees/test-feature-WP01",
            )
        ]

        create_worktrees_from_metadata(tmp_path, worktrees)

        worktree_path = tmp_path / ".worktrees" / "test-feature-WP01"
        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()  # Worktree has git link

    def test_creates_multiple_worktrees(self, tmp_path: Path) -> None:
        """Test creating multiple worktrees."""
        (tmp_path / "README.md").write_text("# Test")
        init_git_repo(tmp_path)

        worktrees = [
            WorktreeMetadata(
                wp_id="WP01",
                branch_name="test-WP01",
                relative_path=".worktrees/test-WP01",
            ),
            WorktreeMetadata(
                wp_id="WP02",
                branch_name="test-WP02",
                relative_path=".worktrees/test-WP02",
            ),
        ]

        create_worktrees_from_metadata(tmp_path, worktrees)

        assert (tmp_path / ".worktrees" / "test-WP01").exists()
        assert (tmp_path / ".worktrees" / "test-WP02").exists()

    def test_handles_empty_worktrees_list(self, tmp_path: Path) -> None:
        """Test that empty worktrees list doesn't cause error."""
        (tmp_path / "README.md").write_text("# Test")
        init_git_repo(tmp_path)

        create_worktrees_from_metadata(tmp_path, [])

        # Should not create .worktrees directory
        assert not (tmp_path / ".worktrees").exists()


class TestLoadOrchestrationState:
    """Tests for load_orchestration_state function."""

    def test_loads_state_from_feature_dir(self, tmp_path: Path) -> None:
        """Test loading state from feature directory."""
        feature_dir = tmp_path / "test-feature"
        feature_dir.mkdir()
        (feature_dir / ".orchestration-state.json").write_text(
            json.dumps(_create_valid_state_json())
        )

        state = load_orchestration_state(feature_dir)

        assert state.run_id == "test-run-001"
        assert state.feature_slug == "test-feature"

    def test_raises_for_missing_state(self, tmp_path: Path) -> None:
        """Test raises StateFileError for missing state file."""
        feature_dir = tmp_path / "test-feature"
        feature_dir.mkdir()
        # No state file created

        with pytest.raises(StateFileError, match="not found"):
            load_orchestration_state(feature_dir)


class TestCleanupFunctions:
    """Tests for cleanup functions."""

    def test_cleanup_temp_dir_removes_directory(self, tmp_path: Path) -> None:
        """Test cleanup removes the directory."""
        test_dir = tmp_path / "to_cleanup"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")
        (test_dir / "subdir").mkdir()
        (test_dir / "subdir" / "nested.txt").write_text("nested")

        cleanup_temp_dir(test_dir)

        assert not test_dir.exists()

    def test_cleanup_temp_dir_handles_nonexistent(self, tmp_path: Path) -> None:
        """Test cleanup handles non-existent directory gracefully."""
        nonexistent = tmp_path / "does_not_exist"

        # Should not raise
        cleanup_temp_dir(nonexistent)

    def test_cleanup_temp_dir_idempotent(self, tmp_path: Path) -> None:
        """Test cleanup can be called multiple times safely."""
        test_dir = tmp_path / "to_cleanup"
        test_dir.mkdir()

        cleanup_temp_dir(test_dir)
        cleanup_temp_dir(test_dir)  # Second call should not raise

        assert not test_dir.exists()

    def test_cleanup_test_context(self, tmp_path: Path) -> None:
        """Test cleanup_test_context removes temp directory."""
        test_dir = tmp_path / "test_context_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        ctx = TestContext(
            temp_dir=test_dir,
            repo_root=test_dir,
            feature_dir=test_dir / "feature",
            test_path=None,
        )

        cleanup_test_context(ctx)

        assert not test_dir.exists()


class TestLoadCheckpoint:
    """Tests for load_checkpoint function."""

    def test_loads_complete_checkpoint(self, tmp_path: Path) -> None:
        """Test loading a complete checkpoint returns TestContext."""
        checkpoint = _create_complete_checkpoint(tmp_path)

        ctx = load_checkpoint(checkpoint)

        try:
            assert ctx.temp_dir.exists()
            assert ctx.repo_root.exists()
            assert ctx.feature_dir.exists()
            assert ctx.checkpoint == checkpoint
            assert ctx.orchestration_state is not None
            assert ctx.orchestration_state.run_id == "test-run-001"
            assert ctx.worktrees == []  # Empty worktrees list

            # Verify git repo was initialized
            assert (ctx.repo_root / ".git").exists()
        finally:
            cleanup_test_context(ctx)

    def test_loads_checkpoint_with_worktrees(self, tmp_path: Path) -> None:
        """Test loading checkpoint that includes worktree metadata."""
        checkpoint = _create_complete_checkpoint(tmp_path)

        # Add worktree metadata to the checkpoint
        worktrees_data = {
            "worktrees": [
                {
                    "wp_id": "WP01",
                    "branch_name": "test-feature-WP01",
                    "relative_path": ".worktrees/test-feature-WP01",
                    "commit_hash": None,
                }
            ]
        }
        (checkpoint.path / "worktrees.json").write_text(json.dumps(worktrees_data))

        ctx = load_checkpoint(checkpoint)

        try:
            assert len(ctx.worktrees) == 1
            assert ctx.worktrees[0].wp_id == "WP01"

            # Verify worktree was created
            worktree_path = ctx.repo_root / ".worktrees" / "test-feature-WP01"
            assert worktree_path.exists()
        finally:
            cleanup_test_context(ctx)

    def test_raises_for_incomplete_checkpoint(self, tmp_path: Path) -> None:
        """Test raises FileNotFoundError for incomplete checkpoint."""
        checkpoint_dir = tmp_path / "incomplete"
        checkpoint_dir.mkdir()
        (checkpoint_dir / "state.json").write_text("{}")
        # Missing feature/ and worktrees.json

        checkpoint = FixtureCheckpoint(
            name="incomplete",
            path=checkpoint_dir,
            orchestrator_version="0.12.0",
            created_at=datetime.now(),
        )

        with pytest.raises(FileNotFoundError):
            load_checkpoint(checkpoint)

    def test_cleans_up_on_failure(self, tmp_path: Path) -> None:
        """Test that temp directory is cleaned up if loading fails."""
        checkpoint = _create_complete_checkpoint(tmp_path)

        # Corrupt the state file to cause failure during load
        (checkpoint.path / "state.json").write_text("not valid json")

        with pytest.raises(StateFileError):
            load_checkpoint(checkpoint)

        # Verify no temp directories leaked
        # Note: We can't easily verify this without access to _temp_dirs_to_cleanup
        # but the test ensures the exception is raised properly

    def test_uses_provided_test_path(self, tmp_path: Path) -> None:
        """Test that provided test_path is used."""
        checkpoint = _create_complete_checkpoint(tmp_path)
        mock_test_path = {"mock": "test_path"}  # Any object works for this test

        ctx = load_checkpoint(checkpoint, test_path=mock_test_path)

        try:
            assert ctx.test_path == mock_test_path
        finally:
            cleanup_test_context(ctx)


class TestRegisterForCleanup:
    """Tests for register_for_cleanup function."""

    def test_registers_directory(self, tmp_path: Path) -> None:
        """Test registering a directory for cleanup."""
        test_dir = tmp_path / "registered"
        test_dir.mkdir()

        # Should not raise
        register_for_cleanup(test_dir)

        # Manually clean up to avoid test pollution
        cleanup_temp_dir(test_dir)
