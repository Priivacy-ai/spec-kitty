"""Fixture data structures for orchestrator e2e testing.

This module defines the core data structures for managing test fixtures:
    - FixtureCheckpoint: A restorable snapshot of orchestration state
    - WorktreeMetadata: Information needed to recreate a git worktree
    - TestContext: Complete runtime context for an e2e test

It also provides JSON schema validation for:
    - worktrees.json: List of worktree metadata
    - state.json: Serialized OrchestrationRun
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from specify_cli.orchestrator.state import OrchestrationRun


# =============================================================================
# Exceptions
# =============================================================================


class WorktreesFileError(Exception):
    """Error loading or validating worktrees.json."""

    pass


class StateFileError(Exception):
    """Error loading or validating state.json."""

    pass


class GitError(Exception):
    """Error executing git command."""

    pass


# =============================================================================
# FixtureCheckpoint Dataclass (T010)
# =============================================================================


@dataclass
class FixtureCheckpoint:
    """A restorable snapshot of orchestration state.

    Represents a checkpoint directory containing:
    - state.json: Serialized OrchestrationRun
    - feature/: Copy of the feature directory
    - worktrees.json: Worktree metadata for recreation
    """

    name: str
    """Checkpoint identifier (e.g., 'wp_created', 'review_pending')."""

    path: Path
    """Absolute path to the checkpoint directory."""

    orchestrator_version: str
    """Version of spec-kitty that created this checkpoint."""

    created_at: datetime
    """When this checkpoint was created."""

    @property
    def state_file(self) -> Path:
        """Path to state.json within checkpoint."""
        return self.path / "state.json"

    @property
    def feature_dir(self) -> Path:
        """Path to feature/ directory within checkpoint."""
        return self.path / "feature"

    @property
    def worktrees_file(self) -> Path:
        """Path to worktrees.json within checkpoint."""
        return self.path / "worktrees.json"

    def exists(self) -> bool:
        """Check if all required checkpoint files exist."""
        return (
            self.path.exists()
            and self.state_file.exists()
            and self.feature_dir.exists()
            and self.worktrees_file.exists()
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "path": str(self.path),
            "orchestrator_version": self.orchestrator_version,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FixtureCheckpoint:
        """Create from JSON dict."""
        return cls(
            name=data["name"],
            path=Path(data["path"]),
            orchestrator_version=data["orchestrator_version"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


# =============================================================================
# WorktreeMetadata Dataclass (T011)
# =============================================================================


@dataclass
class WorktreeMetadata:
    """Information needed to recreate a git worktree.

    Used in worktrees.json to track which worktrees exist in a fixture
    and how to recreate them when restoring from checkpoint.
    """

    wp_id: str
    """Work package identifier (e.g., 'WP01')."""

    branch_name: str
    """Git branch name for this worktree."""

    relative_path: str
    """Path relative to repo root (e.g., '.worktrees/test-feature-WP01')."""

    commit_hash: str | None = None
    """Optional commit hash to checkout (None = branch HEAD)."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "wp_id": self.wp_id,
            "branch_name": self.branch_name,
            "relative_path": self.relative_path,
            "commit_hash": self.commit_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorktreeMetadata:
        """Create from JSON dict."""
        return cls(
            wp_id=data["wp_id"],
            branch_name=data["branch_name"],
            relative_path=data["relative_path"],
            commit_hash=data.get("commit_hash"),
        )


# =============================================================================
# TestContext Dataclass (T012)
# =============================================================================


@dataclass
class TestContext:
    """Complete context for running an e2e orchestrator test.

    Combines:
    - Temporary test environment paths
    - Test path selection (which agents to use)
    - Loaded checkpoint state (if starting from snapshot)
    - Worktree metadata
    """

    temp_dir: Path
    """Temporary directory containing the test environment."""

    repo_root: Path
    """Root of the test git repository."""

    feature_dir: Path
    """Path to the test feature directory."""

    test_path: Any  # TestPath from paths.py - forward reference until WP02 merges
    """Selected test path with agent assignments."""

    checkpoint: FixtureCheckpoint | None = None
    """Loaded checkpoint if test started from snapshot."""

    orchestration_state: OrchestrationRun | None = None
    """Loaded state from checkpoint (None if fresh start)."""

    worktrees: list[WorktreeMetadata] = field(default_factory=list)
    """Worktree metadata for this test context."""

    @property
    def kitty_specs_dir(self) -> Path:
        """Path to kitty-specs directory in test repo."""
        return self.repo_root / "kitty-specs"

    @property
    def worktrees_dir(self) -> Path:
        """Path to .worktrees directory in test repo."""
        return self.repo_root / ".worktrees"

    @property
    def state_file(self) -> Path:
        """Path to orchestration state file."""
        return self.feature_dir / ".orchestration-state.json"


# =============================================================================
# worktrees.json Schema Validation (T013)
# =============================================================================


def load_worktrees_file(path: Path) -> list[WorktreeMetadata]:
    """Load and validate worktrees.json file.

    Expected format:
    {
        "worktrees": [
            {
                "wp_id": "WP01",
                "branch_name": "test-feature-WP01",
                "relative_path": ".worktrees/test-feature-WP01",
                "commit_hash": null
            }
        ]
    }

    Args:
        path: Path to worktrees.json

    Returns:
        List of WorktreeMetadata objects

    Raises:
        WorktreesFileError: If file is invalid or missing required fields
    """
    if not path.exists():
        raise WorktreesFileError(f"Worktrees file not found: {path}")

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise WorktreesFileError(f"Invalid JSON in {path}: {e}")

    # Validate top-level structure
    if not isinstance(data, dict):
        raise WorktreesFileError(f"Expected object, got {type(data).__name__}")

    if "worktrees" not in data:
        raise WorktreesFileError("Missing 'worktrees' key")

    worktrees_list = data["worktrees"]
    if not isinstance(worktrees_list, list):
        raise WorktreesFileError("'worktrees' must be an array")

    # Parse and validate each worktree entry
    result: list[WorktreeMetadata] = []
    required_keys = {"wp_id", "branch_name", "relative_path"}

    for i, item in enumerate(worktrees_list):
        if not isinstance(item, dict):
            raise WorktreesFileError(f"Worktree entry {i} must be an object")

        missing = required_keys - set(item.keys())
        if missing:
            raise WorktreesFileError(f"Worktree entry {i} missing required keys: {missing}")

        result.append(WorktreeMetadata.from_dict(item))

    return result


def save_worktrees_file(path: Path, worktrees: list[WorktreeMetadata]) -> None:
    """Save worktrees to JSON file.

    Args:
        path: Path to write to
        worktrees: List of worktree metadata
    """
    data = {"worktrees": [w.to_dict() for w in worktrees]}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# =============================================================================
# state.json Schema Validation (T014)
# =============================================================================


def load_state_file(path: Path) -> OrchestrationRun:
    """Load and validate state.json file.

    Args:
        path: Path to state.json

    Returns:
        OrchestrationRun object

    Raises:
        StateFileError: If file is invalid or cannot be parsed
    """
    # Import here to avoid circular imports
    from specify_cli.orchestrator.state import OrchestrationRun

    if not path.exists():
        raise StateFileError(f"State file not found: {path}")

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise StateFileError(f"Invalid JSON in {path}: {e}")

    # Validate required fields per OrchestrationRun schema
    required_fields = {
        "run_id",
        "feature_slug",
        "started_at",
        "status",
        "wps_total",
        "wps_completed",
        "wps_failed",
        "work_packages",
    }
    missing = required_fields - set(data.keys())
    if missing:
        raise StateFileError(f"Missing required fields: {missing}")

    # Use OrchestrationRun's deserialization
    try:
        return OrchestrationRun.from_dict(data)
    except Exception as e:
        raise StateFileError(f"Failed to parse OrchestrationRun: {e}")


def save_state_file(path: Path, state: OrchestrationRun) -> None:
    """Save OrchestrationRun to JSON file.

    Args:
        path: Path to write to
        state: Orchestration state
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state.to_dict(), f, indent=2)


# =============================================================================
# Test Helper Functions
# =============================================================================


_cleanup_registry: list[Path] = []


def register_for_cleanup(path: Path) -> None:
    """Register a path for cleanup.

    Args:
        path: Path to register
    """
    _cleanup_registry.append(path)


def cleanup_temp_dir(path: Path) -> None:
    """Clean up a temporary directory.

    Args:
        path: Directory to remove
    """
    import shutil

    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def cleanup_test_context(ctx: TestContext) -> None:
    """Clean up a test context.

    Args:
        ctx: Context to clean up
    """
    cleanup_temp_dir(ctx.temp_dir)


def copy_fixture_to_temp(checkpoint: FixtureCheckpoint) -> Path:
    """Copy a fixture checkpoint to a temp directory.

    Creates directory structure:
        temp_dir/
            kitty-specs/test-feature/  (copied from checkpoint.feature_dir)
                .orchestration-state.json  (copied from checkpoint.state_file)
            worktrees.json

    Args:
        checkpoint: Checkpoint to copy

    Returns:
        Path to temporary directory

    Raises:
        FileNotFoundError: If checkpoint is incomplete (missing required files)
    """
    import shutil
    import tempfile

    # Validate checkpoint has required files
    if not checkpoint.worktrees_file.exists():
        raise FileNotFoundError(
            f"Checkpoint not found or incomplete: missing {checkpoint.worktrees_file}"
        )

    temp_dir = Path(tempfile.mkdtemp(prefix=f"orchestrator_test_{checkpoint.name}_"))

    # Create kitty-specs/test-feature directory structure
    feature_dest = temp_dir / "kitty-specs" / "test-feature"
    feature_dest.parent.mkdir(parents=True, exist_ok=True)

    # Copy feature directory if it exists
    if checkpoint.feature_dir.exists():
        shutil.copytree(checkpoint.feature_dir, feature_dest)

    # Copy state file into the feature directory as .orchestration-state.json
    if checkpoint.state_file.exists():
        shutil.copy(checkpoint.state_file, feature_dest / ".orchestration-state.json")

    # Copy worktrees file to temp dir root
    shutil.copy(checkpoint.worktrees_file, temp_dir / "worktrees.json")

    register_for_cleanup(temp_dir)
    return temp_dir


def init_git_repo(path: Path) -> None:
    """Initialize a git repository at path with initial commit.

    Creates a git repo, configures user, and makes an initial commit.
    If no files exist, creates a .gitkeep file.

    Args:
        path: Directory to initialize

    Raises:
        GitError: If git command fails
    """
    import subprocess

    path.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            ["git", "init"],
            cwd=path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=path,
            capture_output=True,
            check=True,
        )

        # Create a .gitkeep if no files exist (to ensure we can make a commit)
        gitkeep = path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("")

        # Add all files and make initial commit
        subprocess.run(
            ["git", "add", "."],
            cwd=path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial test fixture commit"],
            cwd=path,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to init git repo: {e}")


def create_worktrees_from_metadata(
    repo_root: Path, worktrees: list[WorktreeMetadata]
) -> None:
    """Create git worktrees from metadata.

    Args:
        repo_root: Root of the main repository
        worktrees: List of worktree metadata

    Raises:
        GitError: If worktree creation fails
    """
    import subprocess

    for wt in worktrees:
        # Use relative_path from metadata to determine worktree location
        worktree_path = repo_root / wt.relative_path
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # First create the branch
            subprocess.run(
                ["git", "branch", wt.branch_name],
                cwd=repo_root,
                capture_output=True,
            )
            # Then create the worktree
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), wt.branch_name],
                cwd=repo_root,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to create worktree for {wt.wp_id}: {e}")


def load_orchestration_state(path: Path) -> "OrchestrationRun":
    """Load orchestration state from a feature directory or state file.

    Args:
        path: Path to feature directory or state.json file.
              If a directory, looks for .orchestration-state.json inside.

    Returns:
        OrchestrationRun instance

    Raises:
        StateFileError: If loading fails or state file not found
    """
    if path.is_dir():
        # Assume it's a feature directory, look for state file inside
        state_file = path / ".orchestration-state.json"
    else:
        state_file = path

    return load_state_file(state_file)


def load_checkpoint(
    checkpoint: FixtureCheckpoint,
    test_path: Any | None = None,
) -> TestContext:
    """Load a checkpoint into a TestContext.

    Args:
        checkpoint: Checkpoint to load from
        test_path: Optional TestPath to use (creates mock if None)

    Returns:
        TestContext with checkpoint loaded

    Raises:
        FileNotFoundError: If checkpoint files are missing
        StateFileError: If state.json is invalid
    """
    import shutil
    import tempfile

    # Validate checkpoint has required files
    if not checkpoint.feature_dir.exists():
        raise FileNotFoundError(f"Checkpoint feature directory missing: {checkpoint.feature_dir}")

    # Create temp directory for test
    temp_dir = Path(tempfile.mkdtemp(prefix=f"orchestrator_test_{checkpoint.name}_"))
    register_for_cleanup(temp_dir)

    # Copy files to temp_dir
    state_file = temp_dir / "state.json"
    feature_dir = temp_dir / "feature"
    repo_root = temp_dir / "repo"

    if checkpoint.state_file.exists():
        shutil.copy(checkpoint.state_file, state_file)

    if checkpoint.feature_dir.exists():
        shutil.copytree(checkpoint.feature_dir, feature_dir)

    # Also copy state.json to where TestContext.state_file property expects it
    expected_state_file = feature_dir / ".orchestration-state.json"
    if checkpoint.state_file.exists():
        shutil.copy(checkpoint.state_file, expected_state_file)

    # Initialize git repo
    init_git_repo(repo_root)

    # Load worktrees metadata if present
    worktrees: list[WorktreeMetadata] = []
    if checkpoint.worktrees_file.exists():
        worktrees = load_worktrees_file(checkpoint.worktrees_file)
        # Create the worktrees in the repo
        if worktrees:
            create_worktrees_from_metadata(repo_root, worktrees)

    # Load state if it exists
    orchestration_state = None
    if state_file.exists():
        orchestration_state = load_state_file(state_file)

    # Use provided test_path or create a mock one
    if test_path is None:
        from specify_cli.orchestrator.testing.paths import TestPath

        test_path = TestPath(
            path_type="1-agent",
            implementation_agent="mock",
            review_agent="mock",
            available_agents=["mock"],
            fallback_agent=None,
        )

    return TestContext(
        temp_dir=temp_dir,
        repo_root=repo_root,
        feature_dir=feature_dir,
        test_path=test_path,
        checkpoint=checkpoint,
        orchestration_state=orchestration_state,
        worktrees=worktrees,
    )


def setup_test_repo(tmp_path: Path, feature_slug: str = "test-feature") -> TestContext:
    """Set up a test repository with basic structure.

    Args:
        tmp_path: pytest tmp_path
        feature_slug: Name for the test feature

    Returns:
        TestContext for the test
    """
    repo_root = tmp_path / "repo"
    init_git_repo(repo_root)

    # Create feature directory
    feature_dir = repo_root / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()

    # Create basic files
    (feature_dir / "spec.md").write_text("# Test Spec\n")
    (feature_dir / "plan.md").write_text("# Test Plan\n")

    # Create a mock test_path
    from specify_cli.orchestrator.testing.paths import TestPath

    mock_path = TestPath(
        path_type="1-agent",
        implementation_agent="mock",
        review_agent="mock",
        available_agents=["mock"],
        fallback_agent=None,
    )

    return TestContext(
        temp_dir=tmp_path,
        repo_root=repo_root,
        feature_dir=feature_dir,
        test_path=mock_path,
    )
