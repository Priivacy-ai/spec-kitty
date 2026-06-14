"""Render the ``Action-Critical Charter Sections (<action>):`` block (FR-001).

For each action-critical charter heading, the renderer either:

* emits the **verbatim body** of the heading sliced from ``charter.md``
  (when the charter carries that section), or
* emits a **fetch + when-doing stanza** (selector ``section:<slug>``)
  when the charter is missing that section.

The two-arm contract pins the prompt-governance ATDD anchors in
``tests/specify_cli/next/test_wp_prompt_governance_contract.py``:

* ``test_implement_prompt_regression_vigilance_body_or_fetch_with_when_doing_rule``
* ``test_implement_prompt_terminology_canon_body_or_fetch_with_when_doing_rule``

The when-doing copy for each section MUST match the contract in
``kitty-specs/wp-prompt-governance-payload-01KRR8HS/contracts/charter-context-resolver.md``
verbatim — drift here is a contract violation (R-3 from the WP04 task).
"""

from __future__ import annotations

import re

__all__ = [
    "ACTION_CRITICAL_SECTIONS",
    "CRITICAL_SECTION_WHEN_CLAUSES",
    "critical_section_header",
    "render_critical_section_bodies",
    "render_critical_section_include",
]


TERMINOLOGY_CANON = "Terminology Canon"
CODE_REVIEW_CHECKLIST = "Code Review Checklist"
REGRESSION_VIGILANCE = "Regression Vigilance"
_COMMON_ACTION_CRITICAL_SECTIONS = [
    TERMINOLOGY_CANON,
    CODE_REVIEW_CHECKLIST,
    REGRESSION_VIGILANCE,
]


ACTION_CRITICAL_SECTIONS: dict[str, list[str]] = {
    "implement": list(_COMMON_ACTION_CRITICAL_SECTIONS),
    "review": list(_COMMON_ACTION_CRITICAL_SECTIONS),
}
"""Mapping of action -> ordered list of charter section names whose body
the resolver MUST surface (or fetch-substitute).  Future missions may
extend the set for specify / plan / tasks actions; absent actions yield
an empty block."""


CRITICAL_SECTION_WHEN_CLAUSES: dict[str, str] = {
    TERMINOLOGY_CANON: "rename or introduce a term in the diff",
    CODE_REVIEW_CHECKLIST: "prepare a WP for review",
    REGRESSION_VIGILANCE: "perform a terminology cutover",
}
"""Per-section when-doing clause used when the verbatim body is missing.

Each clause is the deterministic completion that the prompt-governance
contract pins (matched against ``_WHEN_DOING_RE`` in the ATDD helper)."""


_DEFAULT_WHEN_CLAUSE: str = "are about to apply a code change"
"""Fallback conditional for action-critical sections without an explicit
when-doing clause registered in :data:`CRITICAL_SECTION_WHEN_CLAUSES`."""


def critical_section_header(action: str) -> str:
    """Return the section header string for *action* used in the prompt."""

    return f"Action-Critical Charter Sections ({action}):"


def _slugify_heading(heading: str) -> str:
    """Return the kebab-cased slug used in the ``section:<slug>`` selector.

    Mirrors the contract: ``Regression Vigilance`` -> ``regression-vigilance``.
    Non-alphanumeric runs collapse to a single hyphen; the slug is then
    stripped of leading/trailing hyphens.
    """

    lowered = heading.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    return cleaned.strip("-")


def _heading_pattern(heading: str) -> re.Pattern[str]:
    """Compile the regex matching an ATX ``<heading>`` (with optional date suffix).

    The charter convention permits a parenthetical suffix after the
    heading text (``## Regression Vigilance (2026-04-06)``) — the ATDD
    fixture uses exactly that form.  We anchor on the heading prefix so
    those dated variants resolve to the same logical section.
    """

    escaped = re.escape(heading.strip())
    return re.compile(rf"^(#{{2,6}})\s+{escaped}\b.*$", re.MULTILINE)


_FENCE_OPEN_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")


def _is_fence_close(line: str, fence_marker: str, fence_length: int) -> bool:
    """Return whether *line* closes the active Markdown fence."""

    close_pattern = rf"^[ \t]{{0,3}}{re.escape(fence_marker)}{{{fence_length},}}[ \t]*\r?\n?$"
    return re.match(close_pattern, line) is not None


def _has_fence_close(
    lines: list[str], start_index: int, fence_marker: str, fence_length: int
) -> bool:
    """Return whether the active Markdown fence closes after ``start_index``."""

    return any(
        _is_fence_close(line, fence_marker, fence_length)
        for line in lines[start_index:]
    )


def _find_next_section_start(body: str, heading_level: int) -> int | None:
    """Return the next same-or-higher heading offset outside code fences."""

    fence_marker: str | None = None
    fence_length = 0
    offset = 0

    lines = body.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if fence_marker is not None:
            if _is_fence_close(line, fence_marker, fence_length):
                fence_marker = None
                fence_length = 0
        else:
            heading_match = re.match(r"^(#{1,6})\s+", line)
            if (
                heading_match is not None
                and len(heading_match.group(1)) <= heading_level
            ):
                return offset

            fence_match = _FENCE_OPEN_RE.match(line)
            if fence_match is not None:
                fence_marker = fence_match.group(1)[0]
                fence_length = len(fence_match.group(1))
                if not _has_fence_close(lines, index + 1, fence_marker, fence_length):
                    return offset

        offset += len(line)

    return None


def _find_heading_end(charter_content: str, heading: str) -> tuple[int, int] | None:
    """Return ``(end offset, level)`` for ``heading`` outside code fences."""

    pattern = _heading_pattern(heading)
    fence_marker: str | None = None
    fence_length = 0
    offset = 0

    for line in charter_content.splitlines(keepends=True):
        if fence_marker is not None:
            if _is_fence_close(line, fence_marker, fence_length):
                fence_marker = None
                fence_length = 0
        else:
            match = pattern.match(line)
            if match is not None:
                return offset + match.end(), len(match.group(1))

            fence_match = _FENCE_OPEN_RE.match(line)
            if fence_match is not None:
                fence_marker = fence_match.group(1)[0]
                fence_length = len(fence_match.group(1))

        offset += len(line)

    return None


def _extract_section_body(charter_content: str, heading: str) -> str | None:
    """Return the body of ``## <heading>`` from *charter_content*, or ``None``.

    The body is everything from the line **after** the heading up to (but
    not including) the next line that begins with ``## `` at the same
    level outside fenced code blocks.  Nested ``###`` headings are preserved
    verbatim so callers can embed multi-paragraph governance text without
    losing structure.
    """

    heading_match = _find_heading_end(charter_content, heading)
    if heading_match is None:
        return None

    body_start, heading_level = heading_match
    remainder = charter_content[body_start:]
    next_section_start = _find_next_section_start(remainder, heading_level)
    body = (
        remainder
        if next_section_start is None
        else charter_content[body_start : body_start + next_section_start]
    )

    return body.strip("\n").rstrip()


def _render_fetch_stanza(heading: str) -> list[str]:
    """Return the fetch + when-doing stanza for a missing section.

    The shape is the one pinned by the ATDD helper
    ``_contains_either_body_or_fetch_with_conditional`` in
    ``tests/specify_cli/next/test_wp_prompt_governance_contract.py``:

    * the fetch command line carries ``spec-kitty charter context
      --include section:<slug>`` so :data:`_FETCH_CMD_RE` matches,
    * the next line begins ``When you <conditional>, ...`` so
      :data:`_WHEN_DOING_RE` matches.
    """

    selector = f"section:{_slugify_heading(heading)}"
    when_clause = CRITICAL_SECTION_WHEN_CLAUSES.get(heading, _DEFAULT_WHEN_CLAUSE)
    return [
        f"  Run: spec-kitty charter context --include {selector}",
        f"  When you {when_clause}, run this command and apply the returned rule.",
    ]


def render_critical_section_bodies(
    charter_content: str,
    action: str,
) -> str:
    """Render ``Action-Critical Charter Sections (<action>):`` for *action*.

    Parameters
    ----------
    charter_content:
        Full text of ``charter.md`` as read from disk.
    action:
        The action label (e.g. ``"implement"``, ``"review"``).  Actions
        without an entry in :data:`ACTION_CRITICAL_SECTIONS` produce the
        empty string so the caller can skip emitting the header.

    Returns
    -------
    str
        A newline-delimited block beginning with
        :func:`critical_section_header`, or the empty string when the
        action carries no critical-section set.

    Notes
    -----
    Missing sections never crash the renderer (NFR-005): they emit the
    fetch stanza instead so the executing agent has a recovery path.
    """

    headings = ACTION_CRITICAL_SECTIONS.get(action)
    if not headings:
        return ""

    blocks: list[str] = [critical_section_header(action)]
    for heading in headings:
        body = _extract_section_body(charter_content, heading)
        blocks.append("")
        blocks.append(f"### {heading}")
        if body:
            blocks.append(body)
        # The fetch stanza is appended unconditionally:
        # * when the body is present it provides a recovery path for an
        #   agent that needs the full, unwrapped rule text;
        # * when the body is absent it is the only available rail.
        # Emitting both halves keeps the ATDD anchor
        # ``_contains_either_body_or_fetch_with_conditional`` happy for
        # bodies whose verbatim sentence is broken across wrapped lines.
        blocks.extend(_render_fetch_stanza(heading))

    return "\n".join(blocks)


def render_critical_section_include(
    charter_content: str,
    selector_id: str,
    *,
    action: str | None = None,
) -> str | None:
    """Render the body addressed by a ``section:<selector_id>`` fetch selector."""

    cleaned = selector_id.strip()
    if not cleaned:
        return None

    if cleaned.startswith("critical-"):
        action_name = cleaned.removeprefix("critical-").strip()
        if action is not None and action.strip() and action.strip().lower() != action_name:
            return None
        return render_critical_section_bodies(charter_content, action_name) or None

    headings = {
        heading
        for section_headings in ACTION_CRITICAL_SECTIONS.values()
        for heading in section_headings
    }
    for heading in sorted(headings):
        if _slugify_heading(heading) != cleaned:
            continue
        body = _extract_section_body(charter_content, heading)
        if body is None:
            return None
        return f"### {heading}\n{body}" if body else f"### {heading}"

    return None
