"""Tests for constitution interview persistence."""

from pathlib import Path

from specify_cli.constitution.interview import (
    MINIMAL_QUESTION_ORDER,
    QUESTION_ORDER,
    apply_answer_overrides,
    default_interview,
    read_interview_answers,
    write_interview_answers,
)


def test_default_interview_minimal_uses_minimal_question_set() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")

    assert interview.mission == "software-dev"
    assert interview.profile == "minimal"
    assert set(interview.answers.keys()) == set(MINIMAL_QUESTION_ORDER)
    assert len(interview.selected_paradigms) >= 1
    assert len(interview.selected_directives) >= 1


def test_default_interview_comprehensive_includes_full_questions() -> None:
    interview = default_interview(mission="software-dev", profile="comprehensive")

    assert interview.profile == "comprehensive"
    assert set(QUESTION_ORDER).issubset(set(interview.answers.keys()))


def test_interview_roundtrip_yaml(tmp_path: Path) -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    path = tmp_path / "answers.yaml"

    write_interview_answers(path, interview)
    loaded = read_interview_answers(path)

    assert loaded is not None
    assert loaded.mission == interview.mission
    assert loaded.profile == interview.profile
    assert loaded.answers == interview.answers
    assert loaded.selected_paradigms == interview.selected_paradigms


def test_apply_answer_overrides_updates_answers_and_lists() -> None:
    base = default_interview(mission="software-dev", profile="minimal")

    updated = apply_answer_overrides(
        base,
        answers={"project_intent": "Keep workflows deterministic."},
        selected_paradigms=["test-first"],
        selected_directives=["TEST_FIRST"],
        available_tools=["git", "pytest"],
    )

    assert updated.answers["project_intent"] == "Keep workflows deterministic."
    assert updated.selected_paradigms == ["test-first"]
    assert updated.selected_directives == ["TEST_FIRST"]
    assert updated.available_tools == ["git", "pytest"]
