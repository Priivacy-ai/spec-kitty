"""Canonical artifact <-> event verdict vocabulary bridge (FR-005).

Before this module, the equivalence between a review-cycle **artifact**
verdict (what a rejected/approved ``.md`` review-cycle record spells) and the
**event**-side ``review_result`` verdict a :class:`~specify_cli.status.
models.StatusEvent` carries was re-inlined independently in nine modules
(paula finding). This module is the single canonical surface for that
mapping -- every other module routes through it instead of re-spelling the
``rejected`` <-> ``changes_requested`` equivalence.

## Vocabulary

Artifact-side (:data:`ArtifactVerdict`, four values a review-cycle ``.md``
record or an arbiter action may carry):

- ``"approved"``
- ``"rejected"``
- ``"arbiter_override"``
- ``"approved_after_orchestrator_fix"``

Event-side (:data:`EventVerdict`, the two values a ``review_result`` slot on a
:class:`~specify_cli.status.models.StatusEvent` may carry):

- ``"approved"``
- ``"changes_requested"``

## D-PLAN-14 -- emission scope

``arbiter_override`` and ``approved_after_orchestrator_fix`` are **not**
valid inputs to an *emitted* ``review_result`` event. An arbiter override
resolves via a separate :class:`~specify_cli.status.models.ReviewOverride`
record (see ``reducer.py``'s ``_apply_annotation_delta``, the ``review`` slot
vs. the ``review_result`` slot -- two different facts, never collapsed). A
synthesized ``approved`` ``review_result`` for an override would silently
erase that distinction, so :func:`emission_event_verdict` -- the ONLY
function callers may use when constructing an emitted event -- refuses
(raises :class:`ValueError`) on either override value. Use
:func:`to_event_verdict` only for prose/render or non-emission bookkeeping
that legitimately needs the full four-value domain.

## Guarantees (contracts/vocabulary-bridge.md)

- **G1 (total)**: :func:`to_event_verdict` is defined over all four inbound
  :data:`ArtifactVerdict` values -- no value falls through to "damaged".
- **G2 (no drift surface)**: enforced by
  ``tests/architectural/test_verdict_vocab_single_source.py`` -- no module
  other than this one spells the ``rejected`` <-> ``changes_requested``
  equivalence inline.
"""

from __future__ import annotations

from typing import Final, Literal

#: The four verdict values a review-cycle artifact (or an arbiter action) may
#: carry.
ArtifactVerdict = Literal[
    "approved", "rejected", "arbiter_override", "approved_after_orchestrator_fix"
]

#: The subset of :data:`ArtifactVerdict` that is a legal input to an *emitted*
#: ``review_result`` event (D-PLAN-14). ``arbiter_override`` and
#: ``approved_after_orchestrator_fix`` resolve via ``ReviewOverride`` instead.
EmissionArtifactVerdict = Literal["approved", "rejected"]

#: The two verdict values a ``review_result`` event slot may carry.
EventVerdict = Literal["approved", "changes_requested"]

APPROVED: Final = "approved"
REJECTED: Final = "rejected"
ARBITER_OVERRIDE: Final = "arbiter_override"
APPROVED_AFTER_ORCHESTRATOR_FIX: Final = "approved_after_orchestrator_fix"
CHANGES_REQUESTED: Final = "changes_requested"

#: Total artifact -> event mapping (G1). Every :data:`ArtifactVerdict` value
#: has an entry; nothing falls through.
_ARTIFACT_TO_EVENT: Final[dict[str, str]] = {
    APPROVED: APPROVED,
    REJECTED: CHANGES_REQUESTED,
    ARBITER_OVERRIDE: APPROVED,
    APPROVED_AFTER_ORCHESTRATOR_FIX: APPROVED,
}

#: Inverse mapping, for prose/render only (2 -> 2). An event verdict never
#: reconstructs the override/orchestrator-fix distinction -- that provenance
#: lives in ``ReviewOverride``, not in this bridge.
_EVENT_TO_ARTIFACT: Final[dict[str, str]] = {
    APPROVED: APPROVED,
    CHANGES_REQUESTED: REJECTED,
}


def artifact_verdicts() -> frozenset[str]:
    """The full four-value :data:`ArtifactVerdict` domain."""
    return frozenset(_ARTIFACT_TO_EVENT)


def event_verdicts() -> frozenset[str]:
    """The two-value :data:`EventVerdict` domain."""
    return frozenset(_EVENT_TO_ARTIFACT)


def emission_artifact_verdicts() -> frozenset[str]:
    """The two-value :data:`EmissionArtifactVerdict` domain (D-PLAN-14)."""
    return frozenset(_EVENT_TO_ARTIFACT.values())


def to_event_verdict(artifact_verdict: str) -> str:
    """Total mapping (G1): every one of the four :data:`ArtifactVerdict`
    values maps to an :data:`EventVerdict`. Use this for prose/render or
    non-emission bookkeeping that needs the full four-value domain; use
    :func:`emission_event_verdict` when the result feeds an *emitted*
    ``review_result`` event (D-PLAN-14 scopes that to two values only).

    Raises :class:`ValueError` on an unrecognized input -- never falls
    through to a fabricated verdict.
    """
    try:
        return _ARTIFACT_TO_EVENT[artifact_verdict]
    except KeyError:
        raise ValueError(f"unknown artifact verdict: {artifact_verdict!r}") from None


def to_artifact_verdict(event_verdict: str) -> str:
    """Inverse of :func:`to_event_verdict`, for prose/render only (2 -> 2).

    Never reconstructs ``arbiter_override`` / ``approved_after_orchestrator_fix``
    -- an event verdict alone cannot distinguish those from a plain
    ``"approved"``; that provenance lives in ``ReviewOverride``, not here.
    """
    try:
        return _EVENT_TO_ARTIFACT[event_verdict]
    except KeyError:
        raise ValueError(f"unknown event verdict: {event_verdict!r}") from None


def emission_event_verdict(artifact_verdict: str) -> str:
    """D-PLAN-14 emission-scoped bridge: the ONLY conversion callers may use
    when the result feeds an *emitted* ``review_result`` event.

    Scoped to :data:`EmissionArtifactVerdict` (``{"approved", "rejected"}``).
    ``arbiter_override`` and ``approved_after_orchestrator_fix`` are refused
    here -- they are not verdict-bridge inputs to a ``review_result`` event;
    they resolve via a separate ``ReviewOverride`` record. Passing either
    raises :class:`ValueError` rather than silently synthesizing an approval.
    """
    if artifact_verdict not in _EVENT_TO_ARTIFACT.values():
        raise ValueError(
            f"{artifact_verdict!r} is not a valid emission-scoped verdict "
            "(D-PLAN-14): 'arbiter_override' and "
            "'approved_after_orchestrator_fix' resolve via a ReviewOverride "
            "record, never a synthesized review_result event"
        )
    return to_event_verdict(artifact_verdict)


def is_changes_requested(value: object) -> bool:
    """True when ``value`` is the rejection-shaped event verdict.

    A single-value helper for call sites that only ever check the
    ``changes_requested`` side of the equivalence (never construct or branch
    on ``rejected``/``approved`` together) -- routes even that one-directional
    check through the canonical bridge instead of re-inlining the literal.
    """
    return value == CHANGES_REQUESTED


def is_approved(value: object) -> bool:
    """True when ``value`` is the approval-shaped event verdict."""
    return value == APPROVED
