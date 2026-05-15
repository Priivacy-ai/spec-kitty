"""Interview section → synthesis target mapping.

INVARIANT (R-9): The mappings in this module use **shipped-only DRG** for any
resolution during the interview phase. The project-layer DRG (if any) is NOT
merged in during interview-time target selection. This prevents stale or
circular project-layer entries from skewing interview defaults.

This invariant is enforced by ``resolve_sections()`` and locked by
``tests/charter/synthesizer/test_interview_mapping.py::test_r9_shipped_only_drg``.

---

The ``INTERVIEW_MAPPINGS`` table is the single source of truth for
interview-section → artifact-kind correspondence. WP04's
``test_context_reflects_synthesis`` reads this table to verify that the
synthesized artifact set matches the charter context output.

Mapping semantics
-----------------
Each ``InterviewSectionMapping`` entry describes one interview section and the
artifact kinds it drives. The ``requires_nonempty`` flag gates target emission
on a non-empty, non-whitespace answer for that section.

Special-case sections
---------------------
- ``selected_directives``: each selected directive URN drives a distinct tactic
  artifact (``how-we-apply-<directive-id>``) for each item in the selection
  list. Handled by ``resolve_sections()`` using a per-item expansion.
- ``language_scope``: each selected language drives a distinct styleguide
  artifact (``<lang>-style-guide``). Handled by per-item expansion.

These expansions are intentionally kept inside ``resolve_sections()`` rather
than inside the table so the table remains declarative and inspectable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

ArtifactKind = Literal["directive", "tactic", "styleguide"]


@dataclass(frozen=True)
class InterviewSectionMapping:
    """Maps one interview section to a fixed set of artifact kinds.

    Parameters
    ----------
    section_label:
        The canonical interview section / question key (matches keys in
        ``CharterInterview.answers``, ``selected_directives``, etc.).
    kinds:
        Artifact kinds this section drives.
    requires_nonempty:
        When True, emit targets only when the section has a non-blank answer.
        When False, always emit (even for absent / blank answers).
    """

    section_label: str
    kinds: tuple[ArtifactKind, ...]
    requires_nonempty: bool = True


# ---------------------------------------------------------------------------
# The canonical mapping table (T009)
# ---------------------------------------------------------------------------

#: Public, explicitly-enumerated mapping table.
#: WP04's ``test_context_reflects_synthesis`` reads this to validate context.
INTERVIEW_MAPPINGS: tuple[InterviewSectionMapping, ...] = (
    # mission_type → directive describing the project's primary mission scope
    InterviewSectionMapping(
        "mission_type",
        ("directive",),
        requires_nonempty=False,  # always synthesize a mission-scope directive
    ),
    # testing_philosophy → tactic (how to test) + styleguide (testing conventions)
    InterviewSectionMapping(
        "testing_philosophy",
        ("tactic", "styleguide"),
        requires_nonempty=True,
    ),
    # neutrality_posture → directive constraining agent neutrality behaviour
    InterviewSectionMapping(
        "neutrality_posture",
        ("directive",),
        requires_nonempty=True,
    ),
    # risk_appetite → directive bounding acceptable risk
    InterviewSectionMapping(
        "risk_appetite",
        ("directive",),
        requires_nonempty=True,
    ),
    # quality_gates → styleguide for merge/review quality gates
    InterviewSectionMapping(
        "quality_gates",
        ("styleguide",),
        requires_nonempty=True,
    ),
    # review_policy → tactic for the review/approval workflow
    InterviewSectionMapping(
        "review_policy",
        ("tactic",),
        requires_nonempty=True,
    ),
    # documentation_policy → styleguide for docs standards
    InterviewSectionMapping(
        "documentation_policy",
        ("styleguide",),
        requires_nonempty=True,
    ),
)

# Interview sections that receive special per-item expansion in resolve_sections().
# These are NOT rows in INTERVIEW_MAPPINGS because each item in the list drives
# a distinct artifact, not a single fixed artifact per section.
_EXPANDED_SECTIONS: frozenset[str] = frozenset(
    {
        "selected_directives",  # each directive → tactic:how-we-apply-<directive-id>
        "language_scope",  # each language → styleguide:<lang>-style-guide
    }
)


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


def _section_answer(snapshot: dict[str, Any], section_label: str) -> str:
    """Extract a scalar answer string from the interview snapshot.

    Returns an empty string when the section is absent or not a string.
    """
    value = snapshot.get(section_label, "")
    if isinstance(value, str):
        return value.strip()
    return ""


def _section_is_nonempty(snapshot: dict[str, Any], section_label: str) -> bool:
    """Return True if the section has a non-blank scalar answer."""
    return bool(_section_answer(snapshot, section_label))


def _append_table_driven_results(
    results: list[tuple[str, dict[str, Any]]],
    interview_snapshot: dict[str, Any],
) -> None:
    """Append the standard fixed-cardinality section mappings."""
    for mapping in INTERVIEW_MAPPINGS:
        label = mapping.section_label
        answer = _section_answer(interview_snapshot, label)

        if mapping.requires_nonempty and not answer:
            continue

        results.append(
            (
                label,
                {
                    "answer": answer,
                    "kinds": list(mapping.kinds),
                    "source_section": label,
                },
            )
        )


def _iter_clean_strings(raw_values: object) -> tuple[str, ...]:
    """Return stripped non-empty strings from a scalar or sequence input."""
    if isinstance(raw_values, str):
        cleaned = raw_values.strip()
        return (cleaned,) if cleaned else ()
    if isinstance(raw_values, (list, tuple)):
        return tuple(
            item.strip()
            for item in raw_values
            if isinstance(item, str) and item.strip()
        )
    return ()


def _append_selected_directives(
    results: list[tuple[str, dict[str, Any]]],
    interview_snapshot: dict[str, Any],
) -> None:
    """Append one tactic entry per selected directive."""
    for directive_id in _iter_clean_strings(
        interview_snapshot.get("selected_directives", [])
    ):
        results.append(
            (
                "selected_directives",
                {
                    "answer": directive_id,
                    "kinds": ["tactic"],
                    "source_section": "selected_directives",
                    "source_urns": (f"directive:{directive_id}",),
                    "directive_id": directive_id,
                },
            )
        )


def _append_language_scope_results(
    results: list[tuple[str, dict[str, Any]]],
    interview_snapshot: dict[str, Any],
) -> None:
    """Append one styleguide entry per declared language."""
    for language in _iter_clean_strings(interview_snapshot.get("language_scope", [])):
        normalized_language = language.lower()
        results.append(
            (
                "language_scope",
                {
                    "answer": normalized_language,
                    "kinds": ["styleguide"],
                    "source_section": "language_scope",
                    "language": normalized_language,
                },
            )
        )


def resolve_sections(
    interview_snapshot: dict[str, Any],
    *,
    _use_shipped_only_drg: bool = True,  # R-9 invariant — always True at interview time
) -> list[tuple[str, dict[str, Any]]]:
    """Map interview answers to a list of (section_label, answer_context) pairs.

    Each pair represents one target-generation context. For most sections this
    is a 1-to-1 mapping. For expanded sections (``language_scope``,
    ``selected_directives``), one list item is emitted per selection.

    Parameters
    ----------
    interview_snapshot:
        The frozen interview answers dict from ``SynthesisRequest.interview_snapshot``.
    _use_shipped_only_drg:
        Internal sentinel documenting the R-9 invariant. Must never be set to
        ``False`` during interview-time resolution. Tests assert on this.

    Returns
    -------
    list[tuple[str, dict[str, Any]]]
        Each element is ``(section_label, answer_context)`` where
        ``answer_context`` carries the section's answer(s) and any
        DRG URN references relevant to the target.
    """
    # R-9: this function must never read from a merged (project + shipped) DRG.
    # The _use_shipped_only_drg sentinel documents and enforces this invariant.
    if not _use_shipped_only_drg:
        raise ValueError(
            "resolve_sections() requires _use_shipped_only_drg=True (R-9 invariant). "
            "Do not merge the project-layer DRG during interview-time resolution."
        )

    results: list[tuple[str, dict[str, Any]]] = []

    _append_table_driven_results(results, interview_snapshot)
    _append_selected_directives(results, interview_snapshot)
    _append_language_scope_results(results, interview_snapshot)

    return results
