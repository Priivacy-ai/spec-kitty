"""Substantive-content gate for spec/plan auto-commit (issue #846).

Section-presence-only signal — there is no byte-length OR fallback.
A scaffold + arbitrary prose without the required structural rows
remains NON-substantive.

Used by ``mission create`` and ``setup-plan`` in
``specify_cli.cli.commands.agent.mission`` to decide whether
``spec.md`` / ``plan.md`` should be auto-committed.

See:
- ``kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/specify-plan-commit-boundary.md``
- ``research.md`` R7 (revised) and R8.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Final, Literal

Kind = Literal["spec", "plan"]

# Template placeholder patterns — content composed entirely of these is NOT
# substantive. Conservative on purpose: matches the scaffolds shipped by the
# spec/plan templates without snagging real prose that incidentally includes
# square-bracket text.
_PLACEHOLDER_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\[NEEDS CLARIFICATION[^\]]*\]"),
    re.compile(r"\[e\.g\.,[^\]]*\]"),
    re.compile(r"\[FEATURE\]"),
    re.compile(r"\[###-feature[^\]]*\]"),
    re.compile(r"\[Short title\]"),
    re.compile(r"\[Measurable threshold[^\]]*\]"),
    re.compile(r"\[role\]"),
    re.compile(r"\[goal\]"),
    re.compile(r"\[benefit\]"),
    re.compile(r"\[specific capability[^\]]*\]"),
    re.compile(r"\[key interaction[^\]]*\]"),
    re.compile(r"\[data requirement[^\]]*\]"),
    re.compile(r"\[behavior[^\]]*\]"),
    re.compile(r"\[domain-specific[^\]]*\]"),
    re.compile(r"\[if applicable[^\]]*\]"),
    re.compile(r"\[Project-specific[^\]]*\]"),
    re.compile(r"\[single/web/mobile[^\]]*\]"),
)


def _strip_placeholders(s: str) -> str:
    """Remove template placeholders so their text does not count as content."""
    for pattern in _PLACEHOLDER_PATTERNS:
        s = pattern.sub("", s)
    return s


# Functional Requirements rows can show up in two source-template shapes:
# - Markdown table:  | FR-001 | <title> | <description> | <priority> | <status> |
# - Bulleted list:   - **FR-001**: <description>
# Either qualifies as long as the description is non-empty after placeholder
# stripping AND is not the literal "As a [role], I want [goal]..." scaffold.
_FR_TABLE_ROW = re.compile(
    r"^\s*\|\s*\*{0,2}FR-\d{3}\*{0,2}\s*\|(?P<rest>[^\n]+)$",
    re.MULTILINE,
)
_FR_BULLET_PREFIXES: Final[tuple[str, ...]] = ("FR-", "**FR-")


def _has_substantive_fr_row(body: str) -> bool:
    """Return True iff the body contains at least one populated FR-### row.

    Substantive means: one of the descriptive columns (Title or Description in
    a Markdown table; the single description segment in a bullet) has
    non-placeholder content. Priority / Status columns (`High`, `Open`, etc.)
    do **not** qualify a row on their own — those values are present in the
    raw scaffold rows.
    """
    # Table-form rows: FR-### | <title> | <description> | <priority> | <status> |
    for m in _FR_TABLE_ROW.finditer(body):
        rest = m.group("rest").rstrip("|")
        columns = [c.strip() for c in rest.split("|")]
        # Only consider the first two columns (title, description). A scaffold
        # row carries real-looking values in priority/status (e.g. "High",
        # "Open"); those must not falsely qualify the row.
        descriptive_cols = columns[:2]
        for col in descriptive_cols:
            if _is_substantive_text(col):
                return True

    # Bullet-form rows: - **FR-###**: <description>
    return any(
        _is_substantive_text(desc)
        for line in body.splitlines()
        if (desc := _extract_fr_bullet_description(line)) is not None
    )


def _extract_fr_bullet_description(line: str) -> str | None:
    """Return a bullet FR description when ``line`` matches the scaffold shape."""
    stripped = line.lstrip()
    if not stripped or stripped[0] not in "-*":
        return None
    remainder = stripped[1:].lstrip()

    for prefix in _FR_BULLET_PREFIXES:
        if not remainder.startswith(prefix):
            continue
        if len(remainder) < len(prefix) + 3:
            return None
        digits = remainder[len(prefix) : len(prefix) + 3]
        if not digits.isdigit():
            return None
        suffix = remainder[len(prefix) + 3 :]
        if prefix.startswith("**"):
            if not suffix.startswith("**"):
                return None
            suffix = suffix[2:]
        suffix = suffix.lstrip()
        if not suffix or suffix[0] not in ":-":
            return None
        desc = suffix[1:].strip()
        return desc or None
    return None


# Recognises the empty user-story scaffold ("As a , I want  so that .") that
# remains after placeholder stripping. Permits the single-letter article and
# tolerates trailing punctuation/whitespace.
_EMPTY_USER_STORY_SCAFFOLDS: Final[frozenset[str]] = frozenset(
    {
        "as a i want so that",
        "as an i want so that",
    }
)


def _is_substantive_text(raw: str) -> bool:
    """Return True iff ``raw`` has real content after placeholder stripping."""
    cleaned = _strip_placeholders(raw).strip()
    if not cleaned:
        return False
    normalized = " ".join(cleaned.rstrip(".").replace(",", " ").split()).lower()
    return normalized not in _EMPTY_USER_STORY_SCAFFOLDS


def _is_real_technical_context_value(raw: str) -> bool:
    """Return True iff a Technical Context field value is non-placeholder."""
    value = _strip_placeholders(raw).strip()
    if not value:
        return False
    # Reject pure "NEEDS CLARIFICATION" residue and other obvious placeholders
    # that survived the strip pass (e.g. a bare "NEEDS CLARIFICATION").
    return not re.fullmatch(r"NEEDS CLARIFICATION\.?", value)


def _has_substantive_technical_context(body: str) -> bool:
    """Return True iff Technical Context has Language/Version plus a peer field."""
    section = re.search(
        r"##\s+Technical Context\s*\n(?P<body>.*?)(?=\n##\s+|\Z)",
        body,
        flags=re.DOTALL,
    )
    if section is None:
        return False
    sec_body = _strip_placeholders(section.group("body"))
    # NOTE: ``[ \t]*`` (not ``\s*``) so the value capture cannot leak across
    # newlines and pick up a sibling line's content when Language/Version is
    # blank after placeholder stripping.
    lang_match = re.search(
        r"\*\*Language/Version\*\*[ \t]*:[ \t]*(?P<val>[^\n]*)",
        sec_body,
    )
    if lang_match is None:
        return False
    if not _is_real_technical_context_value(lang_match.group("val")):
        return False

    peer_fields = re.finditer(
        r"^\s*\*\*(?P<label>[^*\n]+)\*\*[ \t]*:[ \t]*(?P<val>[^\n]*)",
        sec_body,
        flags=re.MULTILINE,
    )
    for field in peer_fields:
        if field.group("label").strip() == "Language/Version":
            continue
        if _is_real_technical_context_value(field.group("val")):
            return True
    return False


def is_substantive(file_path: Path, kind: Kind) -> bool:
    """Section-presence-only substantive-content gate.

    Args:
        file_path: Path to the artifact file (spec.md or plan.md).
        kind: ``"spec"`` or ``"plan"``.

    Returns:
        True iff the file contains at least one structurally-required,
        non-placeholder content row for the given artifact kind.

    Raises:
        ValueError: If ``kind`` is not one of ``{"spec", "plan"}``.
        OSError: If the file cannot be read.
    """
    body = file_path.read_text(encoding="utf-8")
    if kind == "spec":
        return _has_substantive_fr_row(body)
    if kind == "plan":
        return _has_substantive_technical_context(body)
    raise ValueError(f"Unknown kind: {kind!r}")


def is_committed(file_path: Path, repo_root: Path) -> bool:
    """Return True iff ``file_path`` is git-tracked AND present at HEAD.

    Both conditions must hold: a file freshly added to the index but not yet
    committed will return False. A previously-committed file that has since
    been deleted from the index also returns False.
    """
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return False
    rel_str = str(rel)
    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", rel_str],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "-e", f"HEAD:{rel_str}"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True


__all__ = ["Kind", "is_committed", "is_substantive"]
