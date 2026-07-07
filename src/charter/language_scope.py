"""Helpers for deriving active project languages from charter inputs."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from charter.interview import read_interview_answers
from doctrine.shared.scoping import normalize_languages

__all__ = [
    "extract_declared_languages",
    "infer_repo_languages",
]



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


def _read_compiled_languages(repo_root: Path) -> list[str] | None:
    """Read the structured ``languages`` field persisted at compile time.

    Returns ``None`` when the compiled charter's ``references.yaml`` does not
    exist or does not carry the structured field yet (pre-existing charters
    compiled before this field was introduced) — the caller falls back to
    interview/charter.md extraction in that case. Returns an empty list
    (not ``None``) when the field is present but empty, since that is a
    legitimate compiled answer, not an absence signal.
    """
    references_path = repo_root / ".kittify" / "charter" / "references.yaml"
    if not references_path.exists():
        return None

    yaml = YAML(typ="safe")
    try:
        payload: Any = yaml.load(references_path.read_text(encoding="utf-8"))
    except (YAMLError, OSError, UnicodeDecodeError):
        # Malformed or unreadable references.yaml falls back to the
        # pre-existing resolution path rather than hard-failing charter
        # language resolution.
        return None

    if not isinstance(payload, dict) or "languages" not in payload:
        return None

    languages = payload["languages"]
    if not isinstance(languages, list):
        return None

    return list(normalize_languages(str(item) for item in languages))


def infer_repo_languages(repo_root: Path) -> list[str]:
    """Infer active project languages, preferring the compiled charter.

    Resolution precedence (FR-008/FR-009/FR-010):
      1. The structured ``languages`` field persisted on the compiled charter
         at ``charter generate``/``charter sync`` time. Once present, this is
         authoritative and unconditionally wins — the interview transcript is
         never consulted, even if it would produce a different answer.
      2. Otherwise (no compiled charter yet, or a charter compiled before this
         field existed): fall back to today's pre-existing logic — interview
         transcript first, then ``charter.md`` free-text extraction.
    """
    compiled_languages = _read_compiled_languages(repo_root)
    if compiled_languages is not None:
        return compiled_languages

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
