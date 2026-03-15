"""Scope: exceptions unit tests — no real git or subprocesses."""

import pytest
from specify_cli.glossary.exceptions import (
    GlossaryError,
    BlockedByConflict,
    DeferredToAsync,
    AbortResume,
)
from specify_cli.glossary.models import (
    SemanticConflict,
    TermSurface,
    ConflictType,
    Severity,
    SenseRef,
)

pytestmark = pytest.mark.fast


def test_blocked_by_conflict():
    """BlockedByConflict stores conflicts and formats message."""
    # Arrange
    conflicts = [
        SemanticConflict(
            term=TermSurface("workspace"),
            conflict_type=ConflictType.AMBIGUOUS,
            severity=Severity.HIGH,
            confidence=0.9,
            candidate_senses=[
                SenseRef("workspace", "team_domain", "Git worktree", 0.9),
                SenseRef("workspace", "team_domain", "VS Code workspace", 0.7),
            ],
        ),
    ]

    # Assumption check
    assert len(conflicts) == 1, "must have exactly one conflict for message check"

    # Act
    exc = BlockedByConflict(conflicts)

    # Assert
    assert exc.conflicts == conflicts
    assert "1 semantic conflict" in str(exc)
    assert "--strictness off" in str(exc)


def test_deferred_to_async():
    """DeferredToAsync stores conflict_id."""
    # Arrange
    conflict_id = "uuid-1234-5678"

    # Assumption check
    # (no precondition)

    # Act
    exc = DeferredToAsync(conflict_id)

    # Assert
    assert exc.conflict_id == conflict_id
    assert conflict_id in str(exc)
    assert "deferred to async" in str(exc)


def test_abort_resume():
    """AbortResume stores reason."""
    # Arrange
    reason = "Input hash mismatch"

    # Assumption check
    # (no precondition)

    # Act
    exc = AbortResume(reason)

    # Assert
    assert exc.reason == reason
    assert reason in str(exc)


def test_exception_hierarchy():
    """All glossary exceptions inherit from GlossaryError."""
    # Arrange
    # (no precondition)

    # Assumption check
    # (no precondition)

    # Act / Assert
    assert issubclass(BlockedByConflict, GlossaryError)
    assert issubclass(DeferredToAsync, GlossaryError)
    assert issubclass(AbortResume, GlossaryError)
