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
