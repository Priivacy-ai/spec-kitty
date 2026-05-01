"""Tests for deriving active languages from charter inputs."""

from pathlib import Path

import pytest

from charter.interview import apply_answer_overrides, default_interview, write_interview_answers
from charter.language_scope import extract_declared_languages, infer_repo_languages

pytestmark = pytest.mark.fast


def test_extract_declared_languages_deduplicates_alias_hits() -> None:
    languages = extract_declared_languages(
        "Python services with pytest and ruff. TypeScript frontend built with tsc."
    )

    assert languages == ["python", "typescript"]


def test_infer_repo_languages_prefers_interview_answers(tmp_path: Path) -> None:
    answers_path = tmp_path / ".kittify" / "charter" / "interview" / "answers.yaml"
    answers_path.parent.mkdir(parents=True, exist_ok=True)

    interview = apply_answer_overrides(
        default_interview(mission="software-dev", profile="minimal"),
        answers={"languages_frameworks": "Python backend with pytest checks"},
    )
    write_interview_answers(answers_path, interview)

    (tmp_path / ".kittify" / "charter" / "charter.md").write_text(
        "JavaScript only",
        encoding="utf-8",
    )

    assert infer_repo_languages(tmp_path) == ["python"]


def test_infer_repo_languages_falls_back_to_charter_markdown(tmp_path: Path) -> None:
    charter_path = tmp_path / ".kittify" / "charter" / "charter.md"
    charter_path.parent.mkdir(parents=True, exist_ok=True)
    charter_path.write_text("This repository uses Java, Maven, and JUnit.", encoding="utf-8")

    assert infer_repo_languages(tmp_path) == ["java"]


def test_infer_repo_languages_returns_empty_without_inputs(tmp_path: Path) -> None:
    assert infer_repo_languages(tmp_path) == []
