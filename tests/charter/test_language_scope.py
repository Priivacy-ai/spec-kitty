"""Tests for deriving active languages from charter inputs."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.interview import apply_answer_overrides, default_interview, write_interview_answers
from charter.language_scope import extract_declared_languages, infer_repo_languages

pytestmark = pytest.mark.fast


def _write_references_yaml(repo_root: Path, *, languages: list[str] | None) -> None:
    """Write a minimal ``references.yaml`` fixture, optionally with the T008 structured field.

    Passing ``languages=None`` omits the field entirely, simulating a charter
    compiled before this change existed (the FR-010 backward-compat shape).
    """
    references_path = repo_root / ".kittify" / "charter" / "references.yaml"
    references_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "generated_at": "2026-07-07T00:00:00Z",
        "mission": "software-dev",
        "template_set": "default",
        "references": [],
    }
    if languages is not None:
        payload["languages"] = languages

    yaml = YAML()
    yaml.default_flow_style = False
    with references_path.open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


def test_extract_declared_languages_deduplicates_alias_hits() -> None:
    languages = extract_declared_languages(
        "Python services with pytest and ruff. TypeScript frontend built with tsc."
    )

    assert languages == ["python", "typescript"]


def test_infer_repo_languages_prefers_compiled_charter_over_stale_interview(tmp_path: Path) -> None:
    """The compiled charter's structured field wins even when the interview transcript disagrees.

    This is the corrected (charter-authoritative) contract for the test that
    used to be named ``test_infer_repo_languages_prefers_interview_answers``
    and pinned the opposite (buggy) precedence. Confirmed red-first: this
    exact scenario (interview says "python", compiled charter says
    "typescript") passed with `infer_repo_languages(tmp_path) == ["python"]`
    against the pre-fix code — proof the old precedence was interview-first.
    """
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

    # Compiled charter disagrees with both the interview transcript ("python")
    # and the charter.md free text ("javascript") — it must win regardless.
    _write_references_yaml(tmp_path, languages=["typescript"])

    assert infer_repo_languages(tmp_path) == ["typescript"]


def test_infer_repo_languages_reads_structured_field_without_consulting_interview(tmp_path: Path) -> None:
    """The structured field is returned directly; no interview transcript exists at all."""
    _write_references_yaml(tmp_path, languages=["rust", "go"])

    # `go` is not in the recognized alias set and normalize_languages passes
    # unknown tokens through unchanged, so it round-trips as-is.
    assert infer_repo_languages(tmp_path) == ["rust", "go"]


def test_infer_repo_languages_empty_compiled_list_is_authoritative_not_absent(tmp_path: Path) -> None:
    """``languages: []`` in compiled charter is authoritative — must NOT fall back to interview/charter.md.

    Kills the mutation: replacing ``if compiled_languages is not None:`` with
    ``if compiled_languages:`` would cause this test to fall back to the charter.md
    fallback and return ``["java"]`` instead of ``[]``.
    """
    # Write a charter.md that would produce a non-empty result via the fallback path
    charter_path = tmp_path / ".kittify" / "charter" / "charter.md"
    charter_path.parent.mkdir(parents=True, exist_ok=True)
    charter_path.write_text("This repository uses Java and Maven.", encoding="utf-8")

    # Compiled charter says "no languages" — this must win over the charter.md fallback
    _write_references_yaml(tmp_path, languages=[])

    assert infer_repo_languages(tmp_path) == []


def test_infer_repo_languages_falls_back_to_charter_markdown(tmp_path: Path) -> None:
    charter_path = tmp_path / ".kittify" / "charter" / "charter.md"
    charter_path.parent.mkdir(parents=True, exist_ok=True)
    charter_path.write_text("This repository uses Java, Maven, and JUnit.", encoding="utf-8")

    assert infer_repo_languages(tmp_path) == ["java"]


def test_infer_repo_languages_returns_empty_without_inputs(tmp_path: Path) -> None:
    assert infer_repo_languages(tmp_path) == []


def test_infer_repo_languages_falls_back_when_compiled_charter_predates_structured_field(
    tmp_path: Path,
) -> None:
    """FR-010 backward compatibility: a references.yaml without the ``languages`` key.

    This is the compiled-charter shape produced before this change existed.
    Resolution must fall back to interview-transcript extraction exactly as
    it did prior to this fix (a regression guard, not a new-behavior proof).
    """
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

    # references.yaml exists (charter was compiled) but predates T008 — no
    # "languages" key at all.
    _write_references_yaml(tmp_path, languages=None)

    assert infer_repo_languages(tmp_path) == ["python"]


def test_infer_repo_languages_falls_back_when_no_compiled_charter_exists(tmp_path: Path) -> None:
    """No references.yaml at all (never compiled) also uses the pre-existing fallback."""
    charter_path = tmp_path / ".kittify" / "charter" / "charter.md"
    charter_path.parent.mkdir(parents=True, exist_ok=True)
    charter_path.write_text("This repository uses Java, Maven, and JUnit.", encoding="utf-8")

    assert infer_repo_languages(tmp_path) == ["java"]


def test_infer_repo_languages_falls_back_when_references_yaml_is_malformed(tmp_path: Path) -> None:
    """A malformed/unparseable references.yaml must degrade to the pre-existing
    fallback rather than hard-failing language resolution."""
    references_path = tmp_path / ".kittify" / "charter" / "references.yaml"
    references_path.parent.mkdir(parents=True, exist_ok=True)
    # Unterminated flow sequence — raises ruamel YAMLError on load.
    references_path.write_text("languages: [unterminated\n", encoding="utf-8")

    (tmp_path / ".kittify" / "charter" / "charter.md").write_text(
        "This repository uses Java, Maven, and JUnit.",
        encoding="utf-8",
    )

    assert infer_repo_languages(tmp_path) == ["java"]


def test_infer_repo_languages_falls_back_when_languages_field_is_not_a_list(tmp_path: Path) -> None:
    """A ``languages`` field that is present but not a list is treated as absent
    (fall back), never coerced — a malformed compiled field must not win."""
    references_path = tmp_path / ".kittify" / "charter" / "references.yaml"
    references_path.parent.mkdir(parents=True, exist_ok=True)
    references_path.write_text(
        "schema_version: '1.0.0'\nlanguages: python\n",
        encoding="utf-8",
    )

    (tmp_path / ".kittify" / "charter" / "charter.md").write_text(
        "This repository uses Java, Maven, and JUnit.",
        encoding="utf-8",
    )

    assert infer_repo_languages(tmp_path) == ["java"]
