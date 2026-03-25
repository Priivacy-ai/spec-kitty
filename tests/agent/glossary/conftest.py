"""Pytest fixtures for glossary tests."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from specify_cli.glossary.models import (
    TermSurface,
    TermSense,
    Provenance,
    SenseStatus,
    SemanticConflict,
    ConflictType,
    Severity,
    SenseRef,
)
from specify_cli.glossary.attachment import GlossaryAwarePrimitiveRunner
from kernel.glossary_runner import clear_registry, get_runner, register

_THIS_DIR = Path(__file__).parent


@pytest.fixture(autouse=True)
def _ensure_glossary_runner_registered():
    """Ensure GlossaryAwarePrimitiveRunner is registered for tests in this package.

    The kernel registry is cleared by tests/kernel/test_glossary_runner.py to
    prevent pollution between those unit tests. When those tests run before
    this package, the registry is left empty and production-hook tests fail
    because execute_with_glossary falls back to the no-runner path.

    This fixture re-registers the runner if the registry was cleared, and
    restores the original state after the test so the kernel unit tests
    remain unaffected when they run in the same session.
    """
    prior = get_runner()
    if prior is None:
        register(GlossaryAwarePrimitiveRunner)
    yield
    # Restore: if registry was empty before we entered, clear it again so
    # the test session is left in the same state we found it.
    if prior is None:
        clear_registry()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark all tests in this directory as fast."""
    for item in items:
        if _THIS_DIR in Path(item.fspath).parents:
            item.add_marker(pytest.mark.fast)


@pytest.fixture
def sample_term_surface():
    """Sample TermSurface for testing."""
    return TermSurface("workspace")


@pytest.fixture
def sample_provenance():
    """Sample Provenance for testing."""
    return Provenance(
        actor_id="user:alice",
        timestamp=datetime(2026, 2, 16, 12, 0, 0),
        source="user_clarification",
    )


@pytest.fixture
def sample_term_sense(sample_term_surface, sample_provenance):
    """Sample TermSense for testing."""
    return TermSense(
        surface=sample_term_surface,
        scope="team_domain",
        definition="Git worktree directory for a work package",
        provenance=sample_provenance,
        confidence=0.9,
        status=SenseStatus.ACTIVE,
    )


@pytest.fixture
def mock_primitive_context():
    """Mock PrimitiveExecutionContext for testing."""
    context = MagicMock()
    context.inputs = {"description": "The workspace contains files"}
    context.metadata = {
        "glossary_check": "enabled",
        "glossary_watch_terms": ["workspace", "mission"],
    }
    context.strictness = "medium"
    context.extracted_terms = []
    context.conflicts = []
    return context


@pytest.fixture
def mock_event_log(tmp_path):
    """Mock event log directory for testing."""
    event_log_path = tmp_path / "events"
    event_log_path.mkdir()
    return event_log_path


@pytest.fixture
def sample_seed_file(tmp_path):
    """Sample team_domain.yaml seed file for testing."""
    glossaries_path = tmp_path / ".kittify" / "glossaries"
    glossaries_path.mkdir(parents=True)

    seed_content = """terms:
  - surface: workspace
    definition: Git worktree directory for a work package
    confidence: 1.0
    status: active

  - surface: mission
    definition: Purpose-specific workflow machine
    confidence: 1.0
    status: active
"""
    seed_file = glossaries_path / "team_domain.yaml"
    seed_file.write_text(seed_content)
    return seed_file


def make_conflict(
    surface_text: str,
    conflict_type: ConflictType = ConflictType.AMBIGUOUS,
    severity: Severity = Severity.HIGH,
    candidates: list[SenseRef] = None,
) -> SemanticConflict:
    """Helper to create SemanticConflict for testing."""
    if candidates is None and conflict_type == ConflictType.AMBIGUOUS:
        # Default candidates for ambiguous conflicts
        candidates = [
            SenseRef(surface_text, "team_domain", f"Definition 1 of {surface_text}", 0.9),
            SenseRef(surface_text, "team_domain", f"Definition 2 of {surface_text}", 0.7),
        ]

    return SemanticConflict(
        term=TermSurface(surface_text),
        conflict_type=conflict_type,
        severity=severity,
        confidence=0.9,
        candidate_senses=candidates or [],
        context="test context",
    )
