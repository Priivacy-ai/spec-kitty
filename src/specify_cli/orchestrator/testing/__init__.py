"""Testing infrastructure for orchestrator end-to-end tests.

This module provides:
    - Fixture data structures (FixtureCheckpoint, WorktreeMetadata, TestContext)
    - JSON schema validation for fixture files
    - Serialization/deserialization utilities
"""

from specify_cli.orchestrator.testing.fixtures import (
    FixtureCheckpoint,
    StateFileError,
    TestContext,
    WorktreeMetadata,
    WorktreesFileError,
    load_state_file,
    load_worktrees_file,
    save_state_file,
    save_worktrees_file,
)

__all__ = [
    "FixtureCheckpoint",
    "WorktreeMetadata",
    "TestContext",
    "WorktreesFileError",
    "StateFileError",
    "load_worktrees_file",
    "save_worktrees_file",
    "load_state_file",
    "save_state_file",
]
