"""Helpers for deriving active project languages from charter inputs."""

from __future__ import annotations

from pathlib import Path
import re

from ruamel.yaml.error import YAMLError

from charter.bundle import CHARTER_YAML
from charter.charter_yaml_io import load_charter_yaml
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

    Returns ``None`` when ``charter.yaml`` does not exist, or its ``catalog``
    section does not carry the structured ``languages`` field yet (a charter
    compiled before this field existed) — the caller falls back to interview
    extraction in that case. Returns an empty list (not ``None``) when the
    field is present but empty, since that is a legitimate compiled answer,
    not an absence signal.

    Tier-1, authoritative post-inversion (WP08): reads ``charter.yaml``'s
    ``catalog.languages`` rather than the retired ``references.yaml``.
    """
    charter_yaml_path = repo_root / CHARTER_YAML
    if not charter_yaml_path.exists():
        return None

    try:
        document = load_charter_yaml(charter_yaml_path)
    except (YAMLError, OSError, UnicodeDecodeError):
        # Malformed or unreadable charter.yaml falls back to the
        # pre-existing resolution path rather than hard-failing charter
        # language resolution.
        return None

    catalog = document.get("catalog") if isinstance(document, dict) else None
    if not isinstance(catalog, dict) or "languages" not in catalog:
        return None

    languages = catalog["languages"]
    if not isinstance(languages, list):
        return None

    return list(normalize_languages(str(item) for item in languages))


def infer_repo_languages(repo_root: Path) -> list[str] | None:
    """Infer active project languages, preferring the compiled charter.

    Resolution precedence (FR-008/FR-009/FR-010):
      1. The structured ``languages`` field persisted in ``charter.yaml``'s
         ``catalog`` section at ``charter generate``/``charter sync`` time.
         Once present, this is authoritative and unconditionally wins — the
         interview transcript is never consulted, even if it would produce
         a different answer. An empty compiled list (``catalog.languages:
         []``) is a legitimate, deliberate answer — a configured project
         whose interview transcript named no recognized language — and is
         returned as ``[]``, not promoted to ``None``.
      2. Otherwise (no compiled charter yet, or a ``charter.yaml`` compiled
         before this field existed): fall back to the interview transcript,
         if one exists. Its extraction result is returned as-is, including
         ``[]`` when the transcript exists but names no recognized language
         — an interview transcript is itself a completed signal, not an
         absence of one, so it is never promoted to ``None`` either.
      3. Only when NEITHER a compiled charter NOR an interview transcript
         exists is there truly no active-language signal at all. That bare/
         unconfigured-project case resolves to ``None`` — explicitly
         distinct from the deliberate ``[]`` results above.

    The ``None`` vs. ``[]`` distinction is load-bearing for callers, not
    cosmetic (regression fix, charter-sole-door-bypass-closure-01KZ3WAA
    landing fold): ``doctrine.shared.scoping.applies_to_languages_match``
    treats ``active_languages=None`` as "admit every scoped artifact" and an
    explicitly empty active set as "admit none". Collapsing "no signal yet"
    into ``[]`` silently drops every language-scoped built-in profile
    (``python-pedro``, ``frontend-freddy``, ``java-jenny``, ``node-norris``,
    …) from an otherwise-unconfigured project's catalog — this happened on
    PR #3175 and was caught by two independent adversarial review lenses.

    There is no further ``charter.md`` prose fallback (WP08 / FR-009):
    ``charter.md`` is a curated narrative document, not a decision input, and
    ``catalog.languages`` is populated from the same interview signal at
    compile time — so a free-text re-scan of the prose would be redundant
    with tier-2, never additive.
    """
    compiled_languages = _read_compiled_languages(repo_root)
    if compiled_languages is not None:
        return compiled_languages

    interview_path = repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"
    interview = read_interview_answers(interview_path)
    if interview is not None:
        combined = "\n".join(str(value) for value in interview.answers.values())
        return extract_declared_languages(combined)

    return None
