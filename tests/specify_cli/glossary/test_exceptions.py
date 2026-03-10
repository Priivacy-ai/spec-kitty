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


def test_blocked_by_conflict():
    """BlockedByConflict stores conflicts and formats message."""
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

    exc = BlockedByConflict(conflicts)
    assert exc.conflicts == conflicts
    assert "1 semantic conflict" in str(exc)
    assert "--strictness off" in str(exc)


def test_deferred_to_async():
    """DeferredToAsync stores conflict_id."""
    exc = DeferredToAsync("uuid-1234-5678")
    assert exc.conflict_id == "uuid-1234-5678"
    assert "uuid-1234-5678" in str(exc)
    assert "deferred to async" in str(exc)


def test_abort_resume():
    """AbortResume stores reason."""
    exc = AbortResume("Input hash mismatch")
    assert exc.reason == "Input hash mismatch"
    assert "Input hash mismatch" in str(exc)


def test_exception_hierarchy():
    """All glossary exceptions inherit from GlossaryError."""
    assert issubclass(BlockedByConflict, GlossaryError)
    assert issubclass(DeferredToAsync, GlossaryError)
    assert issubclass(AbortResume, GlossaryError)
