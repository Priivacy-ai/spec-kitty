"""Per-channel reachability over the DRG, computed by *calling* the canonical
traversal primitives — never by a reimplemented walk.

There are two delivery channels (contract ``activation-delivery.md`` §3), each
with its own traversal and its own reachable set:

* **action channel** — :func:`action_channel_reachable` *calls*
  :func:`charter.offering.drg.query.resolve_context` for each action seed and unions the
  results. ``resolve_context`` owns the ``scope`` → ``requires`` → ``suggests``
  algorithm; this module never re-derives it. Every hand-rolled BFS in this
  mission's history produced a *different* wrong number (91 / 88 / 78 / 59 /
  103), which is exactly why R-1 forbids reimplementing the walk.

* **profile channel** — :func:`profile_channel_reachable` is a *distinct*
  :func:`charter.offering.drg.query.walk_edges` traversal over
  ``{requires, specializes_from, suggests}`` seeded from activated agent
  profiles. It is **not** a ``resolve_context`` seed set (R-3): ``agent_profile``
  nodes carry outbound ``requires``, ``specializes_from`` and ``suggests`` edges
  but **zero** outbound ``scope``, so ``resolve_context`` — whose step 1 walks
  ``scope`` only — returns nothing from a profile seed at any depth. Folding the
  profile channel into ``resolve_context`` would silently measure zero: the
  distinguishing fact is the *absence of* ``scope``, not the presence of
  ``suggests`` (both channels now follow ``suggests``, but only ``resolve_context``
  gates it behind a ``scope``-seeded first hop that profiles never satisfy).
  ``suggests`` joins this set in mission ``doctrine-delivery-activation-01KYQVQK``
  (WP01/FR-001), animating the #3063 A–E families that PR #3070 authored inert.

Both helpers return the reachable *artefact* URNs (the seed nodes themselves are
excluded), so a caller can compute ``activated − reachable`` for the
``activated-but-unreachable`` named sets the gate pins.
"""

from __future__ import annotations

from collections.abc import Iterable

from charter.offering.drg.models import DRGGraph, NodeKind, Relation
from charter.offering.drg.query import resolve_context, walk_edges

__all__ = [
    "PROFILE_CHANNEL_RELATIONS",
    "action_channel_reachable",
    "action_seed_urns",
    "agent_profile_seed_urns",
    "profile_channel_reachable",
]

#: The relations the profile entry-vector follows. A profile reaches the
#: doctrine it ``requires``, its lineage parents (``specializes_from``), and the
#: soft-recommended doctrine it ``suggests`` (WP01/FR-001, mission
#: ``doctrine-delivery-activation-01KYQVQK``). It is a three-relation
#: ``walk_edges`` set that deliberately **excludes** ``scope`` — the relation
#: ``resolve_context`` seeds on. That exclusion, not the relation list itself, is
#: why the two channels cannot be folded: profiles carry zero outbound ``scope``
#: (R-3), so a ``resolve_context`` seed measures zero at any depth. The consumer
#: layer surfaces each ``suggests`` edge's ``when`` as a link (see
#: ``charter.activation.progressive_disclosure.profile_channel_references``); this node-level
#: walk stays edge-agnostic.
PROFILE_CHANNEL_RELATIONS: frozenset[Relation] = frozenset(
    {Relation.REQUIRES, Relation.SPECIALIZES_FROM, Relation.SUGGESTS}
)


def action_seed_urns(graph: DRGGraph) -> frozenset[str]:
    """Every ``action`` node URN in *graph* — the action-channel seed set."""
    return frozenset(n.urn for n in graph.nodes if n.kind is NodeKind.ACTION)


def agent_profile_seed_urns(graph: DRGGraph) -> frozenset[str]:
    """Every ``agent_profile`` node URN in *graph*.

    The built-in pack activates all of these, so they are the profile-channel
    seed set for a project on the shipped pack. A caller with a narrower
    configuration (``profile: str | None``) passes its own seeds instead — see
    :func:`profile_channel_reachable`.
    """
    return frozenset(n.urn for n in graph.nodes if n.kind is NodeKind.AGENT_PROFILE)


def action_channel_reachable(
    graph: DRGGraph,
    seeds: Iterable[str],
    depth: int,
) -> frozenset[str]:
    """Artefact URNs reachable through the action channel at *depth*.

    Computed by **calling** :func:`charter.offering.drg.query.resolve_context` once per
    action seed and unioning the resolved ``artifact_urns``. There is no
    reimplemented traversal here: ``resolve_context`` is the single canonical
    walk (R-1), so its measured result cannot drift from the algorithm the
    runtime actually uses to deliver context.

    Args:
        graph: The merged DRG graph.
        seeds: Action-node URNs (e.g. from :func:`action_seed_urns`).
        depth: ``suggests`` depth handed to ``resolve_context`` — ``1`` is the
            compact steady state (the stricter measure) and ``2`` the bootstrap
            depth.

    Returns:
        The union of reachable artefact URNs (seed action nodes excluded, as
        ``resolve_context`` already drops the action node itself).
    """
    reached: set[str] = set()
    for seed in seeds:
        reached |= resolve_context(graph, seed, depth=depth).artifact_urns
    return frozenset(reached)


def profile_channel_reachable(
    graph: DRGGraph,
    seeds: Iterable[str],
) -> frozenset[str]:
    """Artefact URNs reachable through the profile channel.

    A *separate* :func:`charter.offering.drg.query.walk_edges` transitive closure over
    :data:`PROFILE_CHANNEL_RELATIONS` seeded from the activated agent profiles.
    This is intentionally not ``resolve_context`` (R-3).

    The channel is conditional on caller configuration (``profile: str | None``)
    and **fail-closed**: an empty seed set reaches nothing rather than falling
    open to the whole graph.

    Args:
        graph: The merged DRG graph.
        seeds: Activated ``agent_profile`` URNs. Empty ⇒ empty result.

    Returns:
        Reachable artefact URNs with the profile seeds themselves removed, so
        the result is the doctrine the profiles reach — not the profiles.
    """
    seed_set = set(seeds)
    if not seed_set:
        return frozenset()
    visited = walk_edges(graph, seed_set, set(PROFILE_CHANNEL_RELATIONS), max_depth=None)
    return frozenset(visited - seed_set)
