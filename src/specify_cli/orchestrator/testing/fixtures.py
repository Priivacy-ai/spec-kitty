"""Fixture data structures and loader for orchestrator e2e testing.

This module defines the core data structures for managing test fixtures:
    - FixtureCheckpoint: A restorable snapshot of orchestration state
    - WorktreeMetadata: Information needed to recreate a git worktree
    - TestContext: Complete runtime context for an e2e test

It also provides:
    - JSON schema validation for worktrees.json and state.json
    - Fixture loading functions to restore checkpoints to usable test state
    - Cleanup functions for temporary test directories
"""

from __future__ import annotations

import atexit
import json
import shutil
import subprocess
import tempfile
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
    """Error during git operations."""

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
# Fixture Loader Functions (WP04: T015-T020)
# =============================================================================

# Track temp directories for cleanup at exit
_temp_dirs_to_cleanup: set[Path] = set()


def copy_fixture_to_temp(checkpoint: FixtureCheckpoint) -> Path:
    """Copy checkpoint fixture to a temporary directory.

    Creates an isolated copy of the checkpoint fixture in a temporary
    directory for use in testing. The copy includes:
    - feature/ directory copied to kitty-specs/test-feature/
    - state.json copied to the feature directory
    - worktrees.json copied to the temp root

    Args:
        checkpoint: The checkpoint to copy

    Returns:
        Path to the temporary directory

    Raises:
        FileNotFoundError: If checkpoint doesn't exist or is incomplete
    """
    if not checkpoint.exists():
        raise FileNotFoundError(
            f"Checkpoint not found or incomplete: {checkpoint.path}"
        )

    # Create temp directory with descriptive prefix
    temp_dir = Path(tempfile.mkdtemp(prefix=f"orchestrator_test_{checkpoint.name}_"))

    # Copy feature directory
    feature_dest = temp_dir / "kitty-specs" / "test-feature"
    shutil.copytree(
        checkpoint.feature_dir,
        feature_dest,
        dirs_exist_ok=True,
    )

    # Copy state file to feature dir
    shutil.copy2(
        checkpoint.state_file,
        feature_dest / ".orchestration-state.json",
    )

    # Copy worktrees.json for reference
    shutil.copy2(
        checkpoint.worktrees_file,
        temp_dir / "worktrees.json",
    )

    return temp_dir


def init_git_repo(repo_path: Path) -> None:
    """Initialize a git repository with initial commit.

    Creates a new git repository, configures a test user, adds all files,
    and creates an initial commit.

    Args:
        repo_path: Path to initialize as git repo

    Raises:
        GitError: If git commands fail
    """
    try:
        # Initialize repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Configure git user for commits
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Add all files
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Initial commit
        subprocess.run(
            ["git", "commit", "-m", "Initial test fixture commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

    except subprocess.CalledProcessError as e:
        raise GitError(
            f"Git command failed: {e.cmd}\n"
            f"stdout: {e.stdout.decode() if e.stdout else ''}\n"
            f"stderr: {e.stderr.decode() if e.stderr else ''}"
        )


def create_worktrees_from_metadata(
    repo_path: Path,
    worktrees: list[WorktreeMetadata],
) -> None:
    """Create git worktrees from metadata.

    For each worktree in the metadata list, creates the corresponding
    branch and git worktree.

    Args:
        repo_path: Path to the git repository
        worktrees: List of worktree metadata

    Raises:
        GitError: If worktree creation fails
    """
    for wt in worktrees:
        worktree_path = repo_path / wt.relative_path

        # Ensure parent directory exists
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create branch if it doesn't exist
            subprocess.run(
                ["git", "branch", wt.branch_name],
                cwd=repo_path,
                check=False,  # Branch may already exist
                capture_output=True,
            )

            # Create worktree
            cmd = ["git", "worktree", "add", str(worktree_path), wt.branch_name]
            subprocess.run(
                cmd,
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Checkout specific commit if specified
            if wt.commit_hash:
                subprocess.run(
                    ["git", "checkout", wt.commit_hash],
                    cwd=worktree_path,
                    check=True,
                    capture_output=True,
                )

        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to create worktree {wt.wp_id}: {e.cmd}\n"
                f"stdout: {e.stdout.decode() if e.stdout else ''}\n"
                f"stderr: {e.stderr.decode() if e.stderr else ''}"
            )


def load_orchestration_state(feature_dir: Path) -> OrchestrationRun:
    """Load orchestration state from feature directory.

    Args:
        feature_dir: Path to feature directory containing state file

    Returns:
        Loaded OrchestrationRun

    Raises:
        StateFileError: If state file is invalid or missing
    """
    state_path = feature_dir / ".orchestration-state.json"
    return load_state_file(state_path)


def cleanup_temp_dir(temp_dir: Path) -> None:
    """Remove a temporary directory and its contents.

    Handles git worktrees by pruning before removal. Safe to call
    multiple times (idempotent).

    Args:
        temp_dir: Path to remove
    """
    if temp_dir.exists():
        # Remove worktrees first (git requirement)
        worktrees_dir = temp_dir / ".worktrees"
        if worktrees_dir.exists():
            try:
                subprocess.run(
                    ["git", "worktree", "prune"],
                    cwd=temp_dir,
                    check=False,
                    capture_output=True,
                )
            except Exception:
                pass  # Best effort

        # Remove directory tree
        shutil.rmtree(temp_dir, ignore_errors=True)

    _temp_dirs_to_cleanup.discard(temp_dir)


def cleanup_test_context(ctx: TestContext) -> None:
    """Clean up a test context.

    Removes the temporary directory and any git worktrees.

    Args:
        ctx: The test context to clean up
    """
    cleanup_temp_dir(ctx.temp_dir)


def register_for_cleanup(temp_dir: Path) -> None:
    """Register a temp directory for cleanup at exit.

    Directories registered here will be cleaned up when the process
    exits, ensuring no leaked temp directories.

    Args:
        temp_dir: Path to register
    """
    _temp_dirs_to_cleanup.add(temp_dir)


def _cleanup_all_temp_dirs() -> None:
    """Cleanup handler for atexit."""
    for temp_dir in list(_temp_dirs_to_cleanup):
        cleanup_temp_dir(temp_dir)


# Register cleanup handler
atexit.register(_cleanup_all_temp_dirs)


def load_checkpoint(
    checkpoint: FixtureCheckpoint,
    test_path: Any | None = None,
) -> TestContext:
    """Load a checkpoint fixture into a usable test context.

    This is the main entry point for loading test fixtures. It:
    1. Copies the checkpoint to a temp directory
    2. Initializes a git repository
    3. Loads worktree metadata and creates worktrees
    4. Loads the orchestration state
    5. Assembles a TestContext

    Args:
        checkpoint: The checkpoint to load
        test_path: Optional pre-selected test path. If None, a placeholder
            is used (tests should provide this when WP02 is merged).

    Returns:
        Complete TestContext ready for testing

    Raises:
        FileNotFoundError: If checkpoint doesn't exist
        GitError: If git operations fail
        StateFileError: If state file is invalid
        WorktreesFileError: If worktrees.json is invalid
    """
    # Copy fixture to temp
    temp_dir = copy_fixture_to_temp(checkpoint)
    register_for_cleanup(temp_dir)

    repo_root = temp_dir
    feature_dir = temp_dir / "kitty-specs" / "test-feature"

    try:
        # Initialize git repo
        init_git_repo(repo_root)

        # Load worktrees metadata
        worktrees_path = temp_dir / "worktrees.json"
        worktrees = load_worktrees_file(worktrees_path)

        # Create worktrees
        if worktrees:
            create_worktrees_from_metadata(repo_root, worktrees)

        # Load orchestration state
        state = load_orchestration_state(feature_dir)

        # Use provided test_path or placeholder
        # Note: When WP02 is merged, this can import and call select_test_path_sync()
        if test_path is None:
            test_path = None  # Placeholder until WP02 provides TestPath

        return TestContext(
            temp_dir=temp_dir,
            repo_root=repo_root,
            feature_dir=feature_dir,
            test_path=test_path,
            checkpoint=checkpoint,
            orchestration_state=state,
            worktrees=worktrees,
        )

    except Exception:
        # Cleanup on failure
        cleanup_temp_dir(temp_dir)
        raise
