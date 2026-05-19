"""Token budget enforcement and fetch substitution (WP05 T019, NFR-001).

The augmented WP prompt MUST stay under a configurable character budget
(default 32 000 chars, ~8 000 tokens at 4 chars/token).  When the rendered
governance payload exceeds the budget, the longest section bodies are
auto-substituted with the canonical fetch + when-doing stanza
(:func:`charter.context_renderers.fetch_stanza.fetch_stanza`) until the
budget is met.

Substitution algorithm (deterministic, order-independent):

1. Render the join of all sections; if ``len <= budget``, return as-is.
2. Sort substitutable sections by body length (longest first), breaking
   ties on ``section_id`` ascending so the same input always produces the
   same output (no dict-iteration assumption).
3. Pop the longest; replace its body with the canonical fetch stanza
   derived from the ``selector`` + ``when_doing_clause`` carried by the
   section descriptor.
4. Re-render; if still over budget, repeat with the next-longest.
5. When all substitutable bodies have been replaced, emit a single
   trailing warning line so the executing agent knows which surface to
   fetch:

       ``# Governance payload: <N> sections substituted with fetch
       commands (budget=<B>).``

Sections marked ``substitutable=False`` (e.g. the small authority-paths
block, core-doctrine sections) stay inline regardless of body length.

The returned tuple is ``(joined_text, substitution_notes)`` where
``substitution_notes`` is a list of human-readable strings describing
the swaps; callers may log this so operators can audit which sections
got swapped.
"""

from __future__ import annotations

from dataclasses import dataclass

from charter.context_renderers.fetch_stanza import (
    DEFAULT_WHEN_CLAUSE,
    fetch_stanza,
)

__all__ = [
    "BUDGET_DEFAULT",
    "RenderedSection",
    "apply_token_budget",
    "warning_line",
]


BUDGET_DEFAULT: int = 32_000
"""Default character budget — NFR-001 pin (~8000 tokens at 4 chars/token)."""


@dataclass(frozen=True)
class RenderedSection:
    """A single rendered section eligible for token-budget substitution.

    Attributes
    ----------
    section_id:
        Stable identifier used to break ties when sorting by body length
        and to surface in substitution notes.  Examples: ``"profile-cited-
        directives"``, ``"directive:DIRECTIVE_010"``, ``"section:
        terminology-canon"``.
    header:
        Optional leading line(s) emitted verbatim — the substitution
        algorithm never touches the header so anchors like ``Profile-Cited
        Directives (python-pedro):`` survive a swap.  Pass empty string
        for sections that have no separate header.
    body:
        The verbatim section body (potentially very long).  Substitution
        replaces this with the canonical fetch stanza when the section
        is selected.
    selector:
        Canonical ``<kind>:<identifier>`` selector for the fetch stanza
        (see :func:`charter.context_renderers.fetch_stanza.format_selector`).
        Empty selector implies the section has no fetch path — in that
        case the section is treated as non-substitutable regardless of
        the ``substitutable`` flag.
    when_doing_clause:
        Verb-phrase completing the ``When you <clause>, ...`` sentence
        in the fetch stanza.  Empty falls back to
        :data:`charter.context_renderers.fetch_stanza.DEFAULT_WHEN_CLAUSE`.
    substitutable:
        ``True`` when the section may be replaced with a fetch stanza
        under budget pressure.  Authority-paths and core-doctrine blocks
        carry ``False`` to keep them inline (they are small + critical).
    indent:
        Optional indentation applied to the fetch stanza lines when the
        section is substituted, so substituted output remains aligned
        with the surrounding list structure.
    """

    section_id: str
    header: str
    body: str
    selector: str = ""
    when_doing_clause: str = ""
    substitutable: bool = True
    indent: str = ""


def warning_line(count: int, budget: int) -> str:
    """Return the trailing warning line for *count* substitutions at *budget*."""

    return (
        f"# Governance payload: {count} sections substituted with fetch "
        f"commands (budget={budget})."
    )


def _join_sections(sections: list[RenderedSection]) -> str:
    """Combine sections into a single text block.

    Sections are joined with a single blank line between them when both
    header and body are non-empty, mirroring the existing renderer
    behaviour in :mod:`charter.context`.
    """

    blocks: list[str] = []
    for section in sections:
        pieces: list[str] = []
        if section.header:
            pieces.append(section.header)
        if section.body:
            pieces.append(section.body)
        if not pieces:
            continue
        blocks.append("\n".join(pieces))
    return "\n\n".join(blocks)


def _substituted_section(section: RenderedSection) -> RenderedSection:
    """Return a copy of *section* whose body is the canonical fetch stanza."""

    clause = section.when_doing_clause or DEFAULT_WHEN_CLAUSE
    if not section.selector:
        # No fetch path available — keep the original body so we don't
        # silently drop content with no recovery rail.  This is also
        # guarded by the ``substitutable`` flag in :func:`apply_token_budget`.
        return section
    stanza = fetch_stanza(section.selector, clause, indent=section.indent)
    return RenderedSection(
        section_id=section.section_id,
        header=section.header,
        body=stanza,
        selector=section.selector,
        when_doing_clause=clause,
        substitutable=False,  # Already substituted; never re-swap.
        indent=section.indent,
    )


def apply_token_budget(
    sections: list[RenderedSection],
    *,
    budget: int = BUDGET_DEFAULT,
) -> tuple[str, list[str]]:
    """Combine *sections* into a single text under *budget* characters.

    See module docstring for the substitution algorithm.

    Parameters
    ----------
    sections:
        Ordered list of :class:`RenderedSection` descriptors.  Section
        order is preserved in the output; only the bodies of selected
        sections are swapped for fetch stanzas.
    budget:
        Character budget cap.  Defaults to :data:`BUDGET_DEFAULT`.

    Returns
    -------
    tuple[str, list[str]]
        ``(joined_text, substitution_notes)``.  When no substitution is
        needed, ``substitution_notes`` is the empty list and the joined
        text does not carry the trailing warning line.

    Notes
    -----
    The algorithm is deterministic: same input always produces the same
    output.  Ties on body length are broken by ascending ``section_id``,
    which protects against ``dict``-iteration order changes across
    Python versions.
    """

    if budget <= 0:
        # Defensive: a non-positive budget is treated as no-op so we
        # never silently drop content on a misconfigured caller.
        return _join_sections(sections), []

    current = list(sections)
    notes: list[str] = []

    joined = _join_sections(current)
    if len(joined) <= budget:
        return joined, notes

    while len(joined) > budget:
        # Pick the longest substitutable section with a non-empty selector.
        candidates = [
            (idx, sec)
            for idx, sec in enumerate(current)
            if sec.substitutable and sec.selector and sec.body
        ]
        if not candidates:
            # Nothing left to swap — break out and let the caller see the
            # over-budget text rather than looping forever.
            break

        # Sort longest body first, ties broken on section_id ascending so
        # the swap order is deterministic regardless of input ordering.
        candidates.sort(key=lambda pair: (-len(pair[1].body), pair[1].section_id))
        target_index, target_section = candidates[0]
        replaced = _substituted_section(target_section)
        current[target_index] = replaced
        notes.append(
            f"{target_section.section_id} (body {len(target_section.body)} chars -> fetch stanza)"
        )
        joined = _join_sections(current)

    if notes:
        # Append the standardised warning line so operators see at a
        # glance which budget pressed and how many swaps happened.
        joined = f"{joined}\n\n{warning_line(len(notes), budget)}"

    return joined, notes
