"""Shared dependency parser for finalize-tasks pipeline.

This module provides the canonical dependency parser used by both
``agent mission finalize-tasks`` (mission.py) and
``agent tasks finalize-tasks`` (tasks.py).

Recognises three declaration formats inside tasks.md WP sections:

1. Inline "Depends on":
   ``Depends on WP01, WP02``

2. Header-line colon:
   ``**Dependencies**: WP01, WP02``
   ``Dependencies: WP01``

3. Bullet-list under a Dependencies heading:
   ``### Dependencies``
   ``- WP01 (some note)``
   ``- WP02``

All three formats may coexist within a single WP section; results are
deduplicated and returned in declaration order via ``dict.fromkeys()``.

**Parser contract**: This parser matches only three explicit dependency
declaration formats. It does NOT perform prose inference. The common
false-positive (prose containing "Depends on WP##" being parsed as a
dependency) is addressed by section bounding, not by disabling the
patterns. The section-bound fix in ``_split_wp_sections`` prevents
trailing prose false-positives by stopping the final WP's section at
the first non-WP ``##`` heading rather than slurping to EOF.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Section splitter
# ---------------------------------------------------------------------------

_WP_SECTION_HEADER = re.compile(r"(?m)^(?:##|###)\s+(?P<title>.+)$")
_WP_ID_TITLE = re.compile(r"^(?:Work Package\s+)?(?P<wp_id>WP\d{2})(?:\b|:)")
_WP_NUMBER_TITLE = re.compile(r"^Work Package\s+(?P<wp_number>\d{1,2})(?:\b|\s*[—:-]|$)")

# Matches any top-level ## heading (exactly two #s).  Used by _split_wp_sections
# to find the stop boundary for the final WP section.  Sub-headings (### or
# deeper) are intentionally NOT matched — they must not trigger a stop.
_ANY_H2_HEADER = re.compile(r"^## ", re.MULTILINE)


def _match_wp_section_id(title: str) -> str | None:
    """Return canonical ``WP##`` when ``title`` is a work-package heading."""
    if explicit_id_match := _WP_ID_TITLE.match(title):
        return explicit_id_match.group("wp_id")
    if numeric_match := _WP_NUMBER_TITLE.match(title):
        return f"WP{int(numeric_match.group('wp_number')):02d}"
    return None


def _split_wp_sections(tasks_content: str) -> dict[str, str]:
    """Extract per-WP text sections from tasks.md.

    Args:
        tasks_content: Full text of tasks.md.

    Returns:
        Mapping of WP ID (e.g. ``"WP01"``) to the text of that section,
        from the character after the header line to the start of the next
        WP section header (or end of file).
    """
    sections: dict[str, str] = {}
    matches: list[tuple[str, re.Match[str]]] = []
    for match in _WP_SECTION_HEADER.finditer(tasks_content):
        wp_id = _match_wp_section_id(match.group("title"))
        if wp_id is not None:
            matches.append((wp_id, match))

    for idx, (wp_id, match) in enumerate(matches):
        start = match.end()
        if idx + 1 < len(matches):
            # There is a next WP header — use it as the end (existing behaviour).
            end = matches[idx + 1][1].start()
        else:
            # Final WP: stop at the first non-WP, non-Dependencies ## heading
            # after this WP header, or at EOF if no such heading exists.  This
            # prevents trailing prose sections (e.g. "## Notes", "## Appendix")
            # from being included in the final WP's body and producing
            # false-positive dependency matches (FR-304).
            #
            # Invariant: "## Dependencies" headings (Pattern 3) inside the
            # final WP's body must NOT be treated as stop boundaries — they
            # are valid dependency-declaration headers.  Sub-headings (###)
            # are also unaffected because _ANY_H2_HEADER only matches "^## ".
            end = len(tasks_content)
            for h2_match in _ANY_H2_HEADER.finditer(tasks_content, match.end()):
                # Skip WP ID headings — those would start the next WP section
                # (shouldn't happen in the final-WP branch, but be safe).
                line_end = tasks_content.find("\n", h2_match.start())
                heading_line = tasks_content[h2_match.start():line_end if line_end != -1 else None]
                if _match_wp_section_id(heading_line[3:].strip()) is not None:
                    continue
                # Skip "## Dependencies" headings — those are Pattern 3
                # dependency-declaration headers and belong to this WP.
                if _DEPS_HEADING.match(heading_line.strip()):
                    continue
                # Non-WP, non-Dependencies ## heading — this is a stop boundary.
                end = h2_match.start()
                break
        sections[wp_id] = tasks_content[start:end]

    return sections


# ---------------------------------------------------------------------------
# Per-section dependency patterns
# ---------------------------------------------------------------------------

# Explicit-declaration format only (not prose inference).
# Pattern 1: "Depends on WP01" / "Depend on WP01, WP02"
# Matches the literal phrase "Depends on" (or "Depend on") followed by WP IDs.
# No free-form sentence scanning; the phrase must start with the keyword.
_DEPENDS_ON = re.compile(
    r"Depends?\s+on\s+(WP\d{2}(?:\s*,\s*WP\d{2})*)",
    re.IGNORECASE,
)

# Explicit-declaration format only (not prose inference).
# Pattern 2: "**Dependencies**: WP01" / "Dependencies: WP01, WP02"
# Matches a header-colon line with one or more WP IDs on the same line.
_DEPS_COLON = re.compile(
    r"\*?\*?Dependencies\*?\*?\s*:\s*(.+)",
    re.IGNORECASE,
)

# Explicit-declaration format only (not prose inference).
# Pattern 3a: standalone Dependencies heading (matches the heading line itself)
# Followed by a bullet list (Pattern 3b) — the only structured list format.
_DEPS_HEADING = re.compile(
    r"^#{1,4}\s*\*?\*?Dependencies\*?\*?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Pattern 3b: bullet item containing a WP ID
_BULLET_WP = re.compile(r"^\s*[-*]\s*(WP\d{2})")

# Helper: any WP ID anywhere in a string
_WP_ID = re.compile(r"WP\d{2}")


def _parse_section_deps(section_content: str) -> list[str]:
    """Extract all dependency WP IDs declared within one WP section.

    Applies Patterns 1, 2, and 3 and deduplicates (preserving order).

    Args:
        section_content: Text of the WP section (everything after the
            header line and before the next WP header or EOF).

    Returns:
        Deduplicated list of WP IDs in declaration order.
    """
    explicit_deps: list[str] = []

    # Pattern 1 — "Depends on WP01, WP02"
    for match in _DEPENDS_ON.finditer(section_content):
        explicit_deps.extend(_WP_ID.findall(match.group(1)))

    # Pattern 2 — "**Dependencies**: WP01, WP02"
    # Skip lines that are *only* a heading (those are Pattern 3 territory).
    for match in _DEPS_COLON.finditer(section_content):
        line = match.group(0)
        # If the line also matches _DEPS_HEADING it is a bullet-list heading —
        # don't double-count it here.
        if _DEPS_HEADING.match(line.strip()):
            continue
        explicit_deps.extend(_WP_ID.findall(match.group(1)))

    # Pattern 3 — bullet list under a "### Dependencies" heading
    for heading_match in _DEPS_HEADING.finditer(section_content):
        after_heading = section_content[heading_match.end():]
        for line in after_heading.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                break  # Hit the next heading — stop collecting bullets
            bullet_match = _BULLET_WP.match(line)
            if bullet_match:
                explicit_deps.append(bullet_match.group(1))
            # Non-bullet, non-heading, non-empty line → stop collecting
            elif stripped:
                break

    return list(dict.fromkeys(explicit_deps))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_dependencies_from_tasks_md(tasks_content: str) -> dict[str, list[str]]:
    """Parse WP dependency declarations from tasks.md content.

    Recognises three formats:

    1. Inline: ``"Depends on WP01, WP02"``
    2. Header-line: ``"**Dependencies**: WP01, WP02"``
    3. Bullet-list::

           ### Dependencies
           - WP01 (some note)
           - WP02

    Args:
        tasks_content: Full text of a tasks.md file.

    Returns:
        Mapping of WP ID → list of dependency WP IDs.  WPs that appear in
        section headers but have no dependency declaration map to ``[]``.
    """
    result: dict[str, list[str]] = {}
    for wp_id, section in _split_wp_sections(tasks_content).items():
        result[wp_id] = _parse_section_deps(section)
    return result


__all__ = ["parse_dependencies_from_tasks_md"]
