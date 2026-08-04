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
    fetch_stanza_lines,
)

__all__ = [
    "BUDGET_DEFAULT",
    "RenderedSection",
    "_PROFILE_INLINE_BODY_LIMIT_CHARS",
    "_budget_estimate",
    "_enforce_token_budget",
    "apply_token_budget",
    "budget_without_warning_line",
    "warning_line",
]


BUDGET_DEFAULT: int = 32_000
"""Default character budget — NFR-001 pin (~8000 tokens at 4 chars/token)."""

_PROFILE_INLINE_BODY_LIMIT_CHARS = 2_400
"""Per-entry inline-body character ceiling (WP03/WP12): a profile-cited
artifact's verbatim body renders inline only when its estimated size (see
:func:`_budget_estimate`) is at or under this limit; otherwise the entry
renders as the canonical fetch + when-doing stanza instead."""


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


def budget_without_warning_line(count: int, budget: int) -> int:
    """Return pre-warning content budget after reserving warning-line space."""

    if count <= 0:
        return budget
    return budget - len(f"\n\n{warning_line(count, budget)}")


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

    while len(joined) > budget_without_warning_line(len(notes), budget):
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


def _budget_estimate(lines: list[str]) -> int:
    """Total character cost of *lines* including newlines."""
    return sum(len(line) + 1 for line in lines)


def _split_leading_header(text: str) -> tuple[str, str]:
    """Split *text* into its leading anchor-header line and the remainder.

    ``section_block`` / each per-kind chunk of ``profile_block`` (see
    :func:`_split_profile_blocks`) are pre-rendered strings whose own first
    line is the anchor header (e.g. ``Action-Critical Charter Sections
    (implement):`` or ``Profile-Cited Tactics (reviewer-renata):``). Per the
    :class:`RenderedSection` contract, the header must never be swapped away
    with the body — so it is split off here rather than embedded in the
    substitutable ``body``.

    A text with no embedded newline has no separate header line by design
    (e.g. a bare fixture body in a unit test): it is returned unchanged as
    the body with an empty header, so a substitution still replaces the
    whole thing verbatim (existing behaviour for header-less bodies is
    preserved byte-for-byte).
    """
    if "\n" not in text:
        return "", text
    header, _, remainder = text.partition("\n")
    return header, remainder


def _split_profile_blocks(text: str) -> list[tuple[str, str]]:
    """Split the joined profile-cited block into per-kind ``(header, body)`` parts.

    ``_render_profile_sections`` renders up to six kind-blocks (directives,
    tactics, styleguides, toolguides, procedures, suggested-doctrine) and
    joins them with a blank line (``"\\n\\n".join(blocks)``); each block's own
    first line is its anchor header. None of the per-kind renderers ever
    emit an internal blank line (entries are single lines or fixed-shape
    inline bodies), so splitting on the blank-line separator recovers
    exactly the top-level kind boundaries without disturbing any kind's
    content — this is what lets every populated kind's header (not just the
    first) survive a substitution below.

    A ``profile_block`` with no blank-line-separated structure (e.g. a bare
    single-line unit-test fixture) degrades to a single ``(header, body)``
    pair via :func:`_split_leading_header`, matching prior single-candidate
    behaviour exactly.
    """
    if not text:
        return []
    return [_split_leading_header(chunk) for chunk in text.split("\n\n") if chunk]


def _enforce_token_budget(
    text: str,
    *,
    action: str,
    profile_block: str,
    section_block: str,
    budget: int = BUDGET_DEFAULT,
) -> str:
    """Apply the NFR-001 token budget to *text* (WP05, consolidated WP04 T019).

    When ``len(text) <= budget`` the text is returned unchanged.  Over
    budget, the largest substitutable governance block is swapped for
    the canonical fetch + when-doing stanza, and the substitution loop
    iterates over the remaining blocks (longest first) until the budget
    holds or no swap candidates remain.

    Substitution preference (in order of preferred swap):
      1. action-critical section bodies (`section_block`) — largest
      2. profile-cited directives + tactics (`profile_block`)

    Authority paths and core action-doctrine sections stay inline (they
    are small + critical to the prompt's actionable surface, per
    WP05 NFR-001 spec).
    """

    if len(text) <= budget:
        return text

    # Decompose the rendered ``text`` into a fixed-section model and run
    # the substitution loop.  We do this by replacing whole blocks in
    # the original text rather than re-joining, so the surrounding
    # structure (Charter Context header, Policy Summary, Action
    # Doctrine, References) stays byte-identical.
    candidates: list[RenderedSection] = []
    if section_block:
        # The header (e.g. "Action-Critical Charter Sections (implement):")
        # is split off so a substitution below never removes it — see
        # _split_leading_header. A body-less section_block (no content past
        # its own header) has nothing left worth swapping, so it is left
        # inline rather than added as a candidate.
        header, body = _split_leading_header(section_block)
        if body:
            candidates.append(
                RenderedSection(
                    section_id="action-critical-sections",
                    header=header,
                    body=body,
                    selector=f"section:critical-{action}",
                    when_doing_clause=(
                        "need to consult the action-critical charter sections"
                    ),
                    substitutable=True,
                    indent="  ",
                )
            )
    if profile_block:
        # profile_block joins up to six kind-blocks (directives, tactics,
        # styleguides, toolguides, procedures, suggested-doctrine), each with
        # its own anchor header. Splitting it into one RenderedSection per
        # kind (rather than one opaque candidate for the whole block) means
        # EVERY populated kind's header survives a swap, not just the first
        # — see _split_profile_blocks.
        for index, (header, body) in enumerate(_split_profile_blocks(profile_block)):
            if not body:
                continue
            candidates.append(
                RenderedSection(
                    section_id=f"profile-cited-sections-{index}",
                    header=header,
                    body=body,
                    selector="section:profile-citations",
                    when_doing_clause=(
                        "need to consult the profile-cited directives and tactics"
                    ),
                    substitutable=True,
                    indent="  ",
                )
            )

    if not candidates:
        # Nothing safe to substitute — return the original text so we
        # don't silently drop content.  The caller (the WP prompt
        # builder) sees over-budget text rather than missing content;
        # operators will spot the regression via the measurement script.
        return text

    # Sort longest first, ties broken on section_id for determinism.
    candidates.sort(key=lambda sec: (-len(sec.body), sec.section_id))

    current_text = text
    swapped_ids: list[str] = []
    for section in candidates:
        if len(current_text) <= budget_without_warning_line(len(swapped_ids), budget):
            break
        stanza = "\n".join(
            fetch_stanza_lines(
                section.selector,
                section.when_doing_clause,
                indent=section.indent,
            )
        )
        # Replace only the first occurrence — the block is rendered
        # exactly once in the bootstrap text.
        new_text = current_text.replace(section.body, stanza, 1)
        if new_text == current_text:
            # Defensive: block not found (renderer drift).  Skip it.
            continue
        current_text = new_text
        swapped_ids.append(section.section_id)

    if swapped_ids:
        current_text = f"{current_text}\n\n{warning_line(len(swapped_ids), budget)}"

    return current_text
