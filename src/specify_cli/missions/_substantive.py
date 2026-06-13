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
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from mission_runtime import CommitTarget

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
        r"##\s+Technical Context\s*\n(?P<body>(?:[^\n]|\n(?!##))*)",
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

    # FR-013 (#1896): Technical Context fields may be written as Markdown
    # bullets (``- **Field**: value`` / ``* **Field**: value``). The peer-field
    # scan must tolerate an optional leading bullet marker before the bolded
    # label; a bullet-intolerant ``^\s*\*\*`` anchor rejected a fully-populated
    # bulleted section as non-substantive.
    peer_fields = re.finditer(
        r"^[ \t]*(?:[-*][ \t]+)?\*\*(?P<label>[^*\n]+)\*\*[ \t]*:[ \t]*(?P<val>[^\n]*)",
        sec_body,
        flags=re.MULTILINE,
    )
    for field in peer_fields:
        if field.group("label").strip() == "Language/Version":
            continue
        if _is_real_technical_context_value(field.group("val")):
            return True
    return False


def describe_technical_context_gap(body: str) -> str | None:
    """Return a human reason when Technical Context fails the substantive gate.

    FR-013 (#1896): when ``_has_substantive_technical_context`` returns False
    the caller's ``blocked_reason`` should *name the offending format* rather
    than emit a generic verdict. This returns ``None`` when the section is
    substantive (no gap), or a specific diagnostic string otherwise:

    * the section is absent;
    * ``Language/Version`` is missing or placeholder-only;
    * peer fields exist (incl. bulleted ``- **Field**: value``) but every
      value parsed as a template placeholder.
    """
    section = re.search(
        r"##\s+Technical Context\s*\n(?P<body>(?:[^\n]|\n(?!##))*)",
        body,
        flags=re.DOTALL,
    )
    if section is None:
        return "Technical Context section is missing from plan.md."
    sec_body = _strip_placeholders(section.group("body"))
    lang_match = re.search(
        r"\*\*Language/Version\*\*[ \t]*:[ \t]*(?P<val>[^\n]*)",
        sec_body,
    )
    if lang_match is None or not _is_real_technical_context_value(
        lang_match.group("val")
    ):
        return (
            "Technical Context **Language/Version** is missing or carries only "
            "placeholder content."
        )
    if _has_substantive_technical_context(body):
        return None
    return (
        "Technical Context has **Language/Version** but no peer field with "
        "non-placeholder content (bulleted '- **Field**: value' fields are "
        "accepted — populate at least one peer field)."
    )


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


def is_committed(
    file_path: Path,
    repo_root: Path,
    placement: CommitTarget | None = None,
) -> bool:
    """Return True iff ``file_path`` is git-tracked AND present at HEAD.

    Both conditions must hold: a file freshly added to the index but not yet
    committed will return False. A previously-committed file that has since
    been deleted from the index also returns False.

    Args:
        file_path: The file to check for commit presence.
        repo_root: The repository root used for git operations.
        placement: Optional :class:`~mission_runtime.CommitTarget` that
            carries coordination-topology information.  When provided and
            the target's ``kind`` is ``COORDINATION``, the coordination
            branch ref is checked first (``git cat-file -e <ref>:<rel>``).
            If the file is found there, ``True`` is returned immediately
            without falling back to HEAD.  Flat-topology callers that pass
            no ``placement`` receive the original HEAD-only behaviour.

    Returns:
        ``True`` iff the file is committed to the coordination branch (when
        applicable) or to ``HEAD``.
    """
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return False
    rel_str = str(rel)

    # Coord-topology fast path: check the coordination branch before HEAD.
    # OR logic: committed to *either* branch counts as committed.
    if placement is not None:
        # Avoid importing CommitTargetKind at module-level (circular-import
        # risk); the attribute read is safe because CommitTarget is a frozen
        # dataclass with a guaranteed ``kind`` field.
        from mission_runtime import CommitTargetKind

        try:
            coord_ref = placement.ref if placement.kind is CommitTargetKind.COORDINATION else None
        except AttributeError:
            coord_ref = None

        if coord_ref is not None:
            try:
                subprocess.run(
                    ["git", "-C", str(repo_root), "cat-file", "-e", f"{coord_ref}:{rel_str}"],
                    check=True,
                    capture_output=True,
                )
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass  # fall through to HEAD check

    # Primary HEAD check (flat topology or coord-branch miss).
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


__all__ = ["Kind", "describe_technical_context_gap", "is_committed", "is_substantive"]
