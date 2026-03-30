"""Scope: mock-boundary tests for constitution interview persistence — no real git."""

import pytest
from pathlib import Path

from constitution.interview import (
    MINIMAL_QUESTION_ORDER,
    QUESTION_ORDER,
    apply_answer_overrides,
    default_interview,
    read_interview_answers,
    write_interview_answers,
)

pytestmark = pytest.mark.fast


def test_default_interview_minimal_uses_minimal_question_set() -> None:
    """Minimal profile populates exactly the MINIMAL_QUESTION_ORDER keys."""
    # Arrange / Act
    interview = default_interview(mission="software-dev", profile="minimal")
    # Assumption check
    assert len(MINIMAL_QUESTION_ORDER) > 0
    # Assert
    assert interview.mission == "software-dev"
    assert interview.profile == "minimal"
    assert set(interview.answers.keys()) == set(MINIMAL_QUESTION_ORDER)
    assert len(interview.selected_directives) >= 1


def test_default_interview_comprehensive_includes_full_questions() -> None:
    """Comprehensive profile includes all QUESTION_ORDER keys."""
    # Arrange / Act
    interview = default_interview(mission="software-dev", profile="comprehensive")
    # Assumption check
    assert len(QUESTION_ORDER) >= len(MINIMAL_QUESTION_ORDER)
    # Assert
    assert interview.profile == "comprehensive"
    assert set(QUESTION_ORDER).issubset(set(interview.answers.keys()))


def test_interview_roundtrip_yaml(tmp_path: Path) -> None:
    """Write then read preserves all interview fields."""
    # Arrange
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(interview, agent_profile="reviewer", agent_role="reviewer")
    path = tmp_path / "answers.yaml"
    # Assumption check
    assert not path.exists()
    # Act
    write_interview_answers(path, interview)
    loaded = read_interview_answers(path)
    # Assert
    assert loaded is not None
    assert loaded.mission == interview.mission
    assert loaded.profile == interview.profile
    assert loaded.answers == interview.answers
    assert loaded.selected_paradigms == interview.selected_paradigms
    assert loaded.agent_profile == "reviewer"
    assert loaded.agent_role == "reviewer"


def test_apply_answer_overrides_updates_answers_and_lists() -> None:
    """apply_answer_overrides replaces answers, paradigms, directives, and tools."""
    # Arrange
    base = default_interview(mission="software-dev", profile="minimal")
    # Assumption check
    assert base.answers.get("project_intent") != "Keep workflows deterministic."
    # Act
    updated = apply_answer_overrides(
        base,
        answers={"project_intent": "Keep workflows deterministic."},
        selected_paradigms=["test-first"],
        selected_directives=["TEST_FIRST"],
        available_tools=["git", "pytest"],
    )
    # Assert
    assert updated.answers["project_intent"] == "Keep workflows deterministic."
    assert updated.selected_paradigms == ["test-first"]
    assert updated.selected_directives == ["TEST_FIRST"]
    assert updated.available_tools == ["git", "pytest"]


def test_apply_answer_overrides_updates_agent_identity_fields() -> None:
    base = default_interview(mission="software-dev", profile="minimal")

    updated = apply_answer_overrides(
        base,
        agent_profile="architect",
        agent_role="reviewer",
    )

    assert updated.agent_profile == "architect"
    assert updated.agent_role == "reviewer"
