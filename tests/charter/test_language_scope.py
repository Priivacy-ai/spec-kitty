"""Tests for deriving active languages from charter inputs."""

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.interview import apply_answer_overrides, default_interview, write_interview_answers
from charter.language_scope import extract_declared_languages, infer_repo_languages

pytestmark = pytest.mark.fast


def _write_charter_yaml(repo_root: Path, *, languages: list[str] | None) -> None:
    """Write a minimal ``charter.yaml`` fixture, optionally with ``catalog.languages``.

    Passing ``languages=None`` omits the ``catalog`` section's ``languages``
    key entirely, simulating a charter compiled before this field existed
    (the FR-010 backward-compat shape).
    """
    charter_yaml_path = repo_root / ".kittify" / "charter" / "charter.yaml"
    charter_yaml_path.parent.mkdir(parents=True, exist_ok=True)
    catalog: dict[str, object] = {
        "mission": "software-dev",
        "template_set": "default",
        "references": [],
    }
    if languages is not None:
        catalog["languages"] = languages
    payload: dict[str, object] = {
        "schema_version": "2.0.0",
        "catalog": catalog,
    }

    yaml = YAML()
    yaml.default_flow_style = False
    with charter_yaml_path.open("w", encoding="utf-8") as handle:
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

    # A charter.md that disagrees with everything (WP08: must never be read
    # to resolve languages — its presence/content is irrelevant here).
    (tmp_path / ".kittify" / "charter" / "charter.md").write_text(
        "JavaScript only",
        encoding="utf-8",
    )

    # Compiled charter disagrees with both the interview transcript ("python")
    # and the never-read charter.md free text ("javascript") — it must win
    # regardless.
    _write_charter_yaml(tmp_path, languages=["typescript"])

    assert infer_repo_languages(tmp_path) == ["typescript"]


def test_infer_repo_languages_reads_structured_field_without_consulting_interview(tmp_path: Path) -> None:
    """The structured field is returned directly; no interview transcript exists at all."""
    _write_charter_yaml(tmp_path, languages=["rust", "go"])

    # `go` is not in the recognized alias set and normalize_languages passes
    # unknown tokens through unchanged, so it round-trips as-is.
    assert infer_repo_languages(tmp_path) == ["rust", "go"]


def test_infer_repo_languages_empty_compiled_list_is_authoritative_not_absent(tmp_path: Path) -> None:
    """``languages: []`` in compiled charter is authoritative — must NOT fall back to interview/charter.md.

    Kills the mutation: replacing ``if compiled_languages is not None:`` with
    ``if compiled_languages:`` would cause this test to fall back to a
    charter.md scan and return ``["java"]`` instead of ``[]``.
    """
    # Write a charter.md that would produce a non-empty result IF it were
    # ever read (WP08: it must not be — no fallback reaches it any more).
    charter_path = tmp_path / ".kittify" / "charter" / "charter.md"
    charter_path.parent.mkdir(parents=True, exist_ok=True)
    charter_path.write_text("This repository uses Java and Maven.", encoding="utf-8")

    # Compiled charter says "no languages" — this must win over any fallback.
    _write_charter_yaml(tmp_path, languages=[])

    assert infer_repo_languages(tmp_path) == []


def test_infer_repo_languages_returns_empty_without_inputs(tmp_path: Path) -> None:
    assert infer_repo_languages(tmp_path) == []


def test_infer_repo_languages_falls_back_when_compiled_charter_predates_structured_field(
    tmp_path: Path,
) -> None:
    """FR-010 backward compatibility: a charter.yaml without ``catalog.languages``.

    This is the compiled-charter shape produced before this field existed.
    Resolution must fall back to interview-transcript extraction (tier-2) —
    it must NOT fall back to a charter.md free-text read, which no longer
    exists as a resolution path (WP08 / FR-009).
    """
    answers_path = tmp_path / ".kittify" / "charter" / "interview" / "answers.yaml"
    answers_path.parent.mkdir(parents=True, exist_ok=True)

    interview = apply_answer_overrides(
        default_interview(mission="software-dev", profile="minimal"),
        answers={"languages_frameworks": "Python backend with pytest checks"},
    )
    write_interview_answers(answers_path, interview)

    # A charter.md that disagrees with the interview ("javascript" vs
    # "python") — proves it is never consulted, only the interview is.
    (tmp_path / ".kittify" / "charter" / "charter.md").write_text(
        "JavaScript only",
        encoding="utf-8",
    )

    # charter.yaml exists (charter was compiled) but predates the
    # catalog.languages field — no "languages" key under "catalog" at all.
    _write_charter_yaml(tmp_path, languages=None)

    assert infer_repo_languages(tmp_path) == ["python"]


def test_infer_repo_languages_returns_empty_when_no_compiled_charter_and_no_interview(
    tmp_path: Path,
) -> None:
    """No charter.yaml, no interview transcript: resolves to empty — NOT a charter.md scan.

    This is the INV-3 completeness assertion (reviewer guidance): a
    charter.md that would produce a non-empty result via free-text
    extraction must be proven irrelevant. Prior to WP08 this scenario fell
    back to scanning charter.md and returned ``["java"]``; now there is no
    tier-3 charter.md read at all, so it resolves to ``[]``.
    """
    charter_path = tmp_path / ".kittify" / "charter" / "charter.md"
    charter_path.parent.mkdir(parents=True, exist_ok=True)
    charter_path.write_text("This repository uses Java, Maven, and JUnit.", encoding="utf-8")

    assert infer_repo_languages(tmp_path) == []


def test_infer_repo_languages_falls_back_when_charter_yaml_is_malformed(tmp_path: Path) -> None:
    """A malformed/unparseable charter.yaml must degrade to the interview
    fallback rather than hard-failing language resolution, and must NOT
    reach a charter.md read (no such path exists any more)."""
    charter_yaml_path = tmp_path / ".kittify" / "charter" / "charter.yaml"
    charter_yaml_path.parent.mkdir(parents=True, exist_ok=True)
    # Unterminated flow sequence — raises ruamel YAMLError on load.
    charter_yaml_path.write_text("catalog:\n  languages: [unterminated\n", encoding="utf-8")

    answers_path = tmp_path / ".kittify" / "charter" / "interview" / "answers.yaml"
    answers_path.parent.mkdir(parents=True, exist_ok=True)
    interview = apply_answer_overrides(
        default_interview(mission="software-dev", profile="minimal"),
        answers={"languages_frameworks": "Python backend with pytest checks"},
    )
    write_interview_answers(answers_path, interview)

    (tmp_path / ".kittify" / "charter" / "charter.md").write_text(
        "This repository uses Java, Maven, and JUnit.",
        encoding="utf-8",
    )

    assert infer_repo_languages(tmp_path) == ["python"]


def test_infer_repo_languages_falls_back_when_languages_field_is_not_a_list(tmp_path: Path) -> None:
    """A ``languages`` field that is present but not a list is treated as absent
    (fall back), never coerced — a malformed compiled field must not win."""
    _write_charter_yaml(tmp_path, languages=[])
    charter_yaml_path = tmp_path / ".kittify" / "charter" / "charter.yaml"
    charter_yaml_path.write_text(
        "schema_version: '2.0.0'\ncatalog:\n  languages: python\n",
        encoding="utf-8",
    )

    answers_path = tmp_path / ".kittify" / "charter" / "interview" / "answers.yaml"
    answers_path.parent.mkdir(parents=True, exist_ok=True)
    interview = apply_answer_overrides(
        default_interview(mission="software-dev", profile="minimal"),
        answers={"languages_frameworks": "Python backend with pytest checks"},
    )
    write_interview_answers(answers_path, interview)

    assert infer_repo_languages(tmp_path) == ["python"]


def test_infer_repo_languages_ignores_charter_md_content_entirely(tmp_path: Path) -> None:
    """INV-3 completeness (reviewer guidance): no charter.md content, in any
    shape, ever changes the resolved language set — with or without a
    compiled charter.yaml or an interview transcript present."""
    charter_path = tmp_path / ".kittify" / "charter" / "charter.md"
    charter_path.parent.mkdir(parents=True, exist_ok=True)
    charter_path.write_text("Rust, Ruby, PHP, Swift — every language at once.", encoding="utf-8")

    _write_charter_yaml(tmp_path, languages=["python"])

    assert infer_repo_languages(tmp_path) == ["python"]
