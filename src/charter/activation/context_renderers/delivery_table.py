"""The NodeKind delivery table -- which action-bundle slot each kind feeds.

Every :class:`~charter.offering.drg.models.NodeKind` the DRG can resolve must have a
recorded verdict: which :class:`_ActionDoctrineBundle` list (if any) it feeds,
and which reachability gate governs it. :func:`_classify_artifact_urns`
partitions a resolved action's artifact URNs into that slot-keyed mapping,
using :func:`action_bundle_bucket` / :func:`action_bundle_gate` as the total
(exception-on-unruled-kind) lookup surface over the table.

Design notes
------------

* ``gate`` is a column of the *same* table as ``slot`` (B-1), not a separate
  enumerated exception: an equality stated as ``activated ∩ reachable`` would
  make ``asset_ids = []`` the conforming implementation forever, because
  ``activated(asset)`` is ``∅`` by construction (assets are not
  activation-eligible). ``_Gate.ALL`` names that case instead of leaving it
  implicit.
* WP03 of ``doctrine-silence-guards`` froze the bundle at four slots ("state
  the exclusions, do NOT render them"). WP10 (FR-009/FR-011) reversed that
  for ``PROCEDURE`` and ``ASSET``: the criterion is *delivery obligation* -- a
  resolved procedure/asset is executing-agent context no other charter
  surface delivers on this path. The ten still-excluded kinds each have a
  delivery home elsewhere or are not bundle artefacts.
* Totality is enforced, not trusted: ``tests/charter/test_action_bundle_delivery.py``
  and ``tests/doctrine/drg/test_unknown_kind_fails_loudly.py`` redden on any
  ``NodeKind``-keyed dict that omits a member, and on a kind whose delivery
  row is missing raising anything other than the stated ``LookupError``.

WP04 (mission doctrine-delivery-activation): relocated verbatim from
``charter.activation.context`` (single-owner, no-net-growth for that file). Three test
modules import these names directly from ``charter.activation.context``
(``tests/charter/test_action_bundle_delivery.py``,
``tests/charter/test_context_display_charter_md.py``,
``tests/doctrine/drg/test_unknown_kind_fails_loudly.py``) -- ``charter.activation.context``
re-exports the full public surface (including ``_Gate``, accessed there as
``context._Gate``) so those import paths keep resolving unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import NamedTuple, TYPE_CHECKING

from charter.offering.drg.models import NodeKind

if TYPE_CHECKING:
    from charter.offering.drg.models import DRGGraph

# ``_ACTION_BUNDLE_DELIVERY_BY_KIND`` / ``_KindDelivery`` / ``_kind_delivery`` de-exported
# after the context.py re-export shim retirement (doctrine-built-in-seam-consolidation
# WP06): no external ``src/`` importer remains. They stay module-internal, used by the
# functions below.
__all__ = [
    "_Gate",
    "_classify_artifact_urns",
    "action_bundle_bucket",
    "action_bundle_gate",
]


class _Gate(Enum):
    """How a delivered kind is gated (``delivered = gate ∩ reachable``).

    ``ACTIVATED`` -> ``activated(kind) ∩ reachable`` (the kinds
    ``charter.activation.drg_activation._SINGULAR_TO_PLURAL`` gates on). ``ALL`` -> ``reachable``
    alone; ``activated(kind)`` is ``∅`` by construction for these, so gating an
    asset on ``activated ∩ reachable`` would ship ``asset_ids = []`` forever.
    """

    ACTIVATED = "activated"
    ALL = "all"


class _KindDelivery(NamedTuple):
    """One row of the NodeKind delivery table: the ``slot`` and ``gate`` columns.

    ``slot`` is the :class:`_ActionDoctrineBundle` list the kind feeds (``None``
    = not delivered, with a stated reason). ``gate`` is total over ``NodeKind``
    so ``TEMPLATE``'s exclusion carries a reason rather than being ASSET's
    untreated twin (B-1a).
    """

    slot: str | None
    gate: _Gate


#: The NodeKind delivery table -- ``slot`` and ``gate`` as two columns of ONE
#: total table (B-1: ``gate`` is a column of the same table as the slot).
#:
#: WP03 of ``doctrine-silence-guards`` froze the bundle at four slots ("state
#: the exclusions, do NOT render them"). **WP10 (FR-009/FR-011) reverses that
#: for PROCEDURE and ASSET**: the criterion is *delivery obligation* -- a
#: resolved procedure/asset is executing-agent context no other charter surface
#: delivers on this path (13/18 activated procedures are graph-reachable; assets
#: arrive only through inbound requires/suggests edges, D4). The ten still
#: excluded each have a delivery home elsewhere or are not bundle artefacts.
#:
#: Totality is enforced, not trusted: ``test_kind_mapping_totality.py`` reddens
#: on any NodeKind-keyed dict that omits a member.
_ACTION_BUNDLE_DELIVERY_BY_KIND: dict[NodeKind, _KindDelivery] = {
    NodeKind.DIRECTIVE: _KindDelivery("directives", _Gate.ACTIVATED),
    NodeKind.TACTIC: _KindDelivery("tactics", _Gate.ACTIVATED),
    NodeKind.STYLEGUIDE: _KindDelivery("styleguides", _Gate.ACTIVATED),
    NodeKind.TOOLGUIDE: _KindDelivery("toolguides", _Gate.ACTIVATED),
    NodeKind.PROCEDURE: _KindDelivery("procedures", _Gate.ACTIVATED),  # WP10: flipped
    NodeKind.ASSET: _KindDelivery("assets", _Gate.ALL),  # WP10: flipped, ungated (D4)
    # WP01 (deliver-loaded-doctrine, FR-001/FR-002): a glossary pack activated
    # and graph-reachable is executing-agent context no other charter surface
    # delivers on this path -- flipped into its own slot, activation-gated.
    NodeKind.GLOSSARY_PACK: _KindDelivery("glossary_packs", _Gate.ACTIVATED),
    # Excluded (slot=None) -- each carries a stated reason in
    # ``_DELIVERY_REASON_BY_KIND`` below (the machine-checkable authority), NOT
    # ASSET's untreated twin (B-1a):
    NodeKind.PARADIGM: _KindDelivery(None, _Gate.ACTIVATED),  # charter selection block
    NodeKind.AGENT_PROFILE: _KindDelivery(None, _Gate.ACTIVATED),  # profile channel (FR-020)
    NodeKind.MISSION_STEP_CONTRACT: _KindDelivery(None, _Gate.ACTIVATED),  # step executor
    NodeKind.ANTI_PATTERN: _KindDelivery(None, _Gate.ACTIVATED),  # validation-tier topology only
    NodeKind.TEMPLATE: _KindDelivery(None, _Gate.ALL),  # template-file selection (C-004)
    # Not artefacts this bundle carries:
    NodeKind.ACTION: _KindDelivery(None, _Gate.ALL),
    NodeKind.MISSION_TYPE: _KindDelivery(None, _Gate.ALL),
    NodeKind.GLOSSARY: _KindDelivery(None, _Gate.ALL),
    NodeKind.GLOSSARY_SCOPE: _KindDelivery(None, _Gate.ALL),
}


#: The stated reason each ``slot=None`` kind is excluded from the bundle -- the
#: machine-checkable half of "state the exclusions" (B-1a): exclusion and
#: ignorance must be distinguishable, so every excluded kind says WHY here.
#: Keyed by exactly the ``slot=None`` kinds of ``_ACTION_BUNDLE_DELIVERY_BY_KIND``
#: -- a partial NodeKind map by construction (delivered kinds have no exclusion
#: reason). ``tests/charter/test_action_bundle_delivery.py`` asserts this covers
#: every ``None``-slot kind (and only those), so a future ``None`` row added
#: without a reason reddens rather than passing as an unexplained blank. It is a
#: documented, intentional partial (an audit sidecar, never read via ``[kind]``
#: on a delivered kind); the totality guard exempts it in
#: ``tests/doctrine/drg/test_kind_mapping_totality.py::_EXEMPT_GET_PARTIALS``.
_DELIVERY_REASON_BY_KIND: dict[NodeKind, str] = {
    NodeKind.PARADIGM: "delivered via the charter selection block, not the action bundle",
    NodeKind.AGENT_PROFILE: "delivered through the profile channel (FR-020), not the action bundle",
    NodeKind.MISSION_STEP_CONTRACT: "consumed by the step executor, not a bundle artefact",
    NodeKind.ANTI_PATTERN: (
        "validation-tier topology only (rejects edges) -- never a delivered bundle artefact"
    ),
    NodeKind.TEMPLATE: "template-file selection (C-004), not a doctrine bundle artefact",
    NodeKind.ACTION: "an action node is the resolution root, not a delivered artefact",
    NodeKind.MISSION_TYPE: "a mission-type node is graph structure, not a delivered artefact",
    NodeKind.GLOSSARY: "a glossary namespace node is graph structure, not a delivered artefact",
    NodeKind.GLOSSARY_SCOPE: "a glossary-scope node is graph structure, not a delivered artefact",
}


def _kind_delivery(kind: NodeKind) -> _KindDelivery:
    """Look up *kind*'s delivery row, loud on an unruled (new) member."""
    try:
        return _ACTION_BUNDLE_DELIVERY_BY_KIND[kind]
    except KeyError as exc:
        raise LookupError(
            f"NodeKind {kind!r} has no delivery row. Add it to "
            "_ACTION_BUNDLE_DELIVERY_BY_KIND (slot + gate)."
        ) from exc


def action_bundle_bucket(kind: NodeKind) -> str | None:
    """Return the action-bundle list *kind* feeds, or ``None`` if excluded.

    Raises ``LookupError`` for a kind with no recorded verdict (a new
    ``NodeKind`` nobody ruled on) -- the defect class this closes.
    """
    return _kind_delivery(kind).slot


def action_bundle_gate(kind: NodeKind) -> _Gate:
    """Return the delivery gate for *kind* (``ACTIVATED`` or ``ALL``); total (B-1)."""
    return _kind_delivery(kind).gate


def _empty_slot_map() -> dict[str, list[str]]:
    """A fresh accumulator with one empty list per delivered slot.

    Derived from the delivery table so a kind flipped into a slot grows an
    accumulator automatically -- totality and delivery are one statement.
    """
    return {
        row.slot: []
        for row in _ACTION_BUNDLE_DELIVERY_BY_KIND.values()
        if row.slot is not None
    }


def _classify_artifact_urns(
    artifact_urns: frozenset[str] | set[str],
    merged: DRGGraph,
    project_directives: set[str] | None,
    selected_tactics: set[str] | None = None,
    selected_paradigms: set[str] | None = None,
    action_urn: str | None = None,
) -> Mapping[str, tuple[str, ...]]:
    """Partition resolved artifact URNs into a slot-keyed mapping.

    Returns ``{slot: (id, ...)}`` for every delivered slot in the delivery
    table. The mapping is *not* destroyed into a positional tuple: that shape
    spawned five parallel per-kind projections that drifted apart, and every
    drift was a delivery defect (WP10/T053). A kind with no recorded verdict
    raises via :func:`action_bundle_bucket` rather than falling out unnoticed.

    WP02 (Decision Record 2, FR-014): ``project_directives`` is three-state
    (``None`` / ``frozenset()`` / non-empty) at THIS boundary too, mirroring
    :func:`~charter.activation.action_doctrine_bundle._load_action_doctrine_bundle`'s
    own three-state handling of its caller-facing fields. The production
    caller never passes ``None`` here -- it converts once, at assignment,
    before calling in -- but this function stays correct standing alone
    (defense-in-depth, not the load-bearing fix) because
    ``tests/charter/test_action_bundle_delivery.py`` calls it directly with
    ``None`` to mean "no project-directive scoping applied" (PLAN-GOV-001).
    ``None`` seeds no directive start URNs below (same as an empty set would
    -- the seeding step is orthogonal to the exclusion guard's own
    ``is not None`` semantics further down) and never crashes on iteration.

    Follow-on fix (operator ruling, ``reviews/wp02.ruling.md``):
    ``project_directives``/``selected_tactics``/``selected_paradigms`` serve
    TWO different jobs here -- the exclusion-guard allowlist just below
    (correctly ``None -> all built-ins``: an unconfigured project permits
    everything) and the SEED set for the ``requires``/``suggests`` closure
    walk (``selected_closure``). Those jobs must not share one unscoped
    result: a seed URN is unconditionally "visited" by
    :func:`~charter.offering.drg.query.walk_edges` (it is a start node), so
    unioning the closure's raw output into ``artifact_urns`` with no
    reachability check let an activated-but-unscoped directive leak into
    every action's delivered set regardless of whether that action's own DRG
    resolution ever reaches it -- the FR-005 (``DIRECTIVE_003`` onto
    ``implement``) and #883 (cross-mission-type) leaks. *``action_urn``* (new,
    optional, trailing) lets the caller identify the resolving action so the
    closure's result can be bounded to what is actually reachable within
    THAT action's own scope, reusing
    :func:`~charter.offering.drg.query.resolve_context`'s own
    ``Relation.SCOPE``-then-``{REQUIRES, SUGGESTS}`` definition of "scope"
    (:func:`~charter.offering.drg.query.walk_edges`) rather than inventing a
    second one. Callers that supply no ``action_urn`` (this module's own
    direct-call test fixtures) get the conservative fallback: the closure
    widens no further than the caller's already-resolved ``artifact_urns`` --
    fail closed, never fail open.
    """
    from charter.offering.drg.models import Relation
    from charter.offering.drg.query import resolve_transitive_refs, walk_edges

    # selected_tactics / selected_paradigms have no three-state exclusion
    # guard anywhere in this function (only project_directives does, below) --
    # these two lines are therefore defense-in-depth / a documented no-op
    # guard against a caller passing None, not load-bearing after WP02 (the
    # real caller, _load_action_doctrine_bundle, converts None to a concrete
    # catalog-default set once, before calling in).
    selected_tactics = selected_tactics or set()
    selected_paradigms = selected_paradigms or set()
    start_urns = {f"directive:{directive_id}" for directive_id in (project_directives or ())}
    start_urns.update(f"tactic:{tactic_id}" for tactic_id in selected_tactics)
    start_urns.update(f"paradigm:{paradigm_id}" for paradigm_id in selected_paradigms)
    selected_closure = resolve_transitive_refs(
        merged,
        start_urns=start_urns,
        relations={Relation.REQUIRES, Relation.SUGGESTS},
    )
    artifact_urns = set(artifact_urns)

    # Scope gate: bound the closure's result to what is actually reachable
    # within the resolving action's own scope -- see the docstring above.
    # Mirrors resolve_context's OWN two SEPARATE walks (one REQUIRES-only,
    # one SUGGESTS-only) rather than a single walk over both relations at
    # once: a combined walk lets a path cross from a `suggests` hop onto a
    # `requires` hop (e.g. a scoped directive SUGGESTS a paradigm that itself
    # REQUIRES an unrelated, unscoped directive) and call that "in scope" --
    # a relation-mixing leak `resolve_context` itself never allows, since
    # each of its own two walks follows only its own relation end to end.
    if action_urn is not None:
        scoped_artifacts = walk_edges(merged, {action_urn}, {Relation.SCOPE}, max_depth=1)
        scoped_artifacts.discard(action_urn)
        in_scope_urns = (
            scoped_artifacts
            | walk_edges(merged, scoped_artifacts, {Relation.REQUIRES})
            | walk_edges(merged, scoped_artifacts, {Relation.SUGGESTS})
        )
    else:
        in_scope_urns = set(artifact_urns)

    closure_urns: set[str] = set()
    closure_urns.update(f"directive:{directive_id}" for directive_id in selected_closure.directives)
    closure_urns.update(f"tactic:{tactic_id}" for tactic_id in selected_closure.tactics)
    closure_urns.update(f"styleguide:{styleguide_id}" for styleguide_id in selected_closure.styleguides)
    closure_urns.update(f"toolguide:{toolguide_id}" for toolguide_id in selected_closure.toolguides)
    artifact_urns.update(closure_urns & in_scope_urns)

    slots = _empty_slot_map()
    for urn in sorted(artifact_urns):
        node = merged.get_node(urn)
        if node is None:
            continue
        # Raises LookupError for a kind nobody has ruled on -- the `else` the
        # old elif-chain never had.
        slot = action_bundle_bucket(node.kind)
        if slot is None:
            continue
        artifact_id = urn.split(":", 1)[1] if ":" in urn else urn
        if (
            node.kind is NodeKind.DIRECTIVE
            and project_directives is not None
            and artifact_id not in project_directives
        ):
            continue
        slots[slot].append(artifact_id)
    return {slot: tuple(ids) for slot, ids in slots.items()}
