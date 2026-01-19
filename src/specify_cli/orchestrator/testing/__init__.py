"""Testing infrastructure for orchestrator end-to-end tests.

This module provides:
    - Fixture data structures (FixtureCheckpoint, WorktreeMetadata, TestContext)
    - JSON schema validation for fixture files
    - Fixture loading and cleanup functions
    - Serialization/deserialization utilities
"""

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

__all__ = [
    # Data structures
    "FixtureCheckpoint",
    "WorktreeMetadata",
    "TestContext",
    # Exceptions
    "WorktreesFileError",
    "StateFileError",
    "GitError",
    # File I/O
    "load_worktrees_file",
    "save_worktrees_file",
    "load_state_file",
    "save_state_file",
    # Loader functions
    "copy_fixture_to_temp",
    "init_git_repo",
    "create_worktrees_from_metadata",
    "load_orchestration_state",
    "load_checkpoint",
    # Cleanup functions
    "cleanup_temp_dir",
    "cleanup_test_context",
    "register_for_cleanup",
]
