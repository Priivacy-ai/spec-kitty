"""Helpers for deriving active project languages from charter inputs."""

from __future__ import annotations

from pathlib import Path
import re

from charter.interview import read_interview_answers
from doctrine.shared.scoping import normalize_languages


_LANGUAGE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("python", (r"\bpython\b", r"\bpytest\b", r"\bmypy\b", r"\bruff\b")),
    ("typescript", (r"\btypescript\b", r"\btsc\b")),
    ("javascript", (r"\bjavascript\b", r"\bjest\b", r"\bnode(?:\.js)?\b", r"\bnpm\b", r"\bpnpm\b", r"\byarn\b")),
    ("rust", (r"\brust\b", r"\bcargo\b", r"\brustc\b")),
    ("java", (r"\bjava\b", r"\bjunit\b", r"\bgradle\b", r"\bmaven\b")),
    ("swift", (r"\bswift\b", r"\bxctest\b")),
    ("ruby", (r"\bruby\b", r"\brspec\b", r"\brails\b")),
    ("php", (r"\bphp\b", r"\bphpunit\b")),
)


def extract_declared_languages(text: str) -> list[str]:
    """Return canonical language identifiers mentioned in free-form text."""
    haystack = text.lower()
    matches: list[str] = []
    for language, patterns in _LANGUAGE_PATTERNS:
        if any(re.search(pattern, haystack) for pattern in patterns):
            matches.append(language)
    return list(normalize_languages(matches))


def infer_repo_languages(repo_root: Path) -> list[str]:
    """Infer active project languages from interview answers or charter content."""
    interview_path = repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"
    interview = read_interview_answers(interview_path)
    if interview is not None:
        combined = "\n".join(str(value) for value in interview.answers.values())
        languages = extract_declared_languages(combined)
        if languages:
            return languages

    charter_path = repo_root / ".kittify" / "charter" / "charter.md"
    if charter_path.exists():
        return extract_declared_languages(charter_path.read_text(encoding="utf-8"))

    return []
