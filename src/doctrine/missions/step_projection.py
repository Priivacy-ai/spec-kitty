"""Projection seam: derive ``MissionType.action_sequence`` / ``template_set``.

Single canonical, doctrine-layer seam (S-B, WP02). **Both** the DRG
extractor (WP04) and the charter/runtime consumer switch (WP06) import
*this* module -- never a second copy, never independently re-derived
downstream (C-003, "one ordering authority: every consumer switches").
Layering: this module lives in ``doctrine`` and is imported *by* the
charter layer, never the reverse -- no layering inversion.

The two functions here are pure and deterministic: given the same
``MissionStep`` collection, both always return byte-identical output. The
DRG freshness gate (NFR-002) and the software-dev parity scaffold
(NFR-001a) both depend on that determinism, so neither function may read
the filesystem, mutate its input, or depend on iteration/dict ordering
beyond what is explicitly sorted below.

Scope fence (C-008, "whack-a-field"): this module projects **only**
``MissionType.template_set`` -- the ``dict[artifact_key, template_file]``
derived from ``MissionStep.template``. The unrelated charter/project
``doctrine.template_set`` **scalar** (``charter/resolver.py``,
``compiler.py``, ``compact.py``, ``generator.py``, ``catalog.py``,
``prompt_builder.py``, ``scope_router.py``, ``governance-profile.yaml``) is
a different domain object entirely. This module must never import from, or
reference, that scalar surface.
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import MissionStep, MissionStepTemplateRef, validate_action_sequence

__all__ = [
    "project_action_sequence",
    "project_template_set",
]

#: Sentinel sort weight for a sequence member with no ``sequence_index``.
#: Sorts after every real (non-negative) index so the total order stays
#: deterministic even for data that should not occur in practice (an
#: ``in_action_sequence: true`` step is expected to always carry an index --
#: WP03 author discipline).
_UNINDEXED = 2**31


def _sequence_sort_key(step: MissionStep) -> tuple[int, str]:
    """Sort key: ``sequence_index`` first, ``id`` as a deterministic tiebreak."""
    index = step.sequence_index if step.sequence_index is not None else _UNINDEXED
    return (index, step.id)


def project_action_sequence(steps: Iterable[MissionStep]) -> list[str]:
    """Project the ordered action-sequence step ids from *steps*.

    Returns the ``id`` of every step with ``in_action_sequence is True``,
    sorted ascending by ``sequence_index`` (stable, deterministic -- the DRG
    freshness gate needs byte-identical regeneration across runs). Steps
    with ``in_action_sequence is False`` (e.g. ``retrospect``,
    software-dev's 7 non-sequence steps) are excluded entirely -- they mint
    no entry and, downstream, no DRG edge (WP04).

    Returns an empty list when no step is a sequence member. That is a
    valid **transitional** state: before a mission type's steps are
    annotated with ``sequence_index``/``in_action_sequence`` (pending
    WP03/WP05), every step in that type projects to nothing. Callers that
    require a non-empty sequence (e.g. the ``MissionTypeRepository`` cached
    accessor, see ``mission_type_repository._inject_projected_fields``) are
    responsible for falling back to the still-authored YAML value during
    this transition -- this function itself never fabricates or fails on
    an honestly-empty projection.

    When the projection *is* non-empty, the WP01->WP02 contract invariant
    (non-empty + unique ids) is re-asserted here via
    :func:`~doctrine.missions.models.validate_action_sequence` -- the same
    check :class:`~doctrine.missions.models.MissionType` applies to the raw
    YAML-authored field -- so direct consumers of this pure function (the
    DRG extractor, WP04; the runtime seam, WP06) get the same guarantee
    without needing to construct a ``MissionType`` first.
    """
    members = [step for step in steps if step.in_action_sequence]
    members.sort(key=_sequence_sort_key)
    sequence = [step.id for step in members]
    if sequence:
        validate_action_sequence(sequence)
    return sequence


def project_template_set(steps: Iterable[MissionStep]) -> dict[str, str] | None:
    """Project the ``template_set`` mapping from *steps*.

    Keyed on ``MissionStepTemplateRef.artifact_key`` -- **not** the step
    id. A step's id need not match its template's artifact key (e.g.
    software-dev's ``specify`` step projects ``template_set["spec"]``,
    because ``artifact_key="spec"``); the resolver reads
    ``template_set["spec"]``, so keying on step id would silently break it.

    Steps without a ``template`` ref are dropped. Returns ``None`` when no
    step in *steps* carries a template -- matching the 3 built-in mission
    types (``documentation``, ``research``, ``plan``) whose ``template_set``
    is explicitly ``null`` today.
    """
    template_set: dict[str, str] = {}
    for step in steps:
        template_ref = _step_template_ref(step)
        if template_ref is None:
            continue
        template_set[template_ref.artifact_key] = template_ref.template_file
    return template_set or None


def _step_template_ref(step: MissionStep) -> MissionStepTemplateRef | None:
    """Return *step*'s template reference, explicitly typed as :class:`MissionStepTemplateRef`."""
    return step.template
