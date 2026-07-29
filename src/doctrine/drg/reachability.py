"""Per-channel reachability over the DRG, computed by *calling* the canonical
traversal primitives — never by a reimplemented walk.

There are two delivery channels (contract ``activation-delivery.md`` §3), each
with its own traversal and its own reachable set:

* **action channel** — :func:`action_channel_reachable` *calls*
  :func:`doctrine.drg.query.resolve_context` for each action seed and unions the
  results. ``resolve_context`` owns the ``scope`` → ``requires`` → ``suggests``
  algorithm; this module never re-derives it. Every hand-rolled BFS in this
  mission's history produced a *different* wrong number (91 / 88 / 78 / 59 /
  103), which is exactly why R-1 forbids reimplementing the walk.

* **profile channel** — :func:`profile_channel_reachable` is a *distinct*
  :func:`doctrine.drg.query.walk_edges` traversal over
  ``{requires, specializes_from}`` seeded from activated agent profiles. It is
  **not** a ``resolve_context`` seed set (R-3): ``agent_profile`` nodes carry 97
  outbound ``requires``, 4 ``specializes_from`` and **zero** outbound ``scope``,
  so ``resolve_context`` — whose step 1 walks ``scope`` only — returns nothing
  from a profile seed at any depth. Folding the profile channel into
  ``resolve_context`` would silently measure zero.

Both helpers return the reachable *artefact* URNs (the seed nodes themselves are
excluded), so a caller can compute ``activated − reachable`` for the
``activated-but-unreachable`` named sets the gate pins.
"""

from __future__ import annotations

from collections.abc import Iterable

from doctrine.drg.models import DRGGraph, NodeKind, Relation
from doctrine.drg.query import resolve_context, walk_edges

__all__ = [
    "PROFILE_CHANNEL_RELATIONS",
    "action_channel_reachable",
    "action_seed_urns",
    "agent_profile_seed_urns",
    "profile_channel_reachable",
]

#: The relations the profile entry-vector follows. A profile reaches the
#: doctrine it ``requires`` and its lineage parents (``specializes_from``). It is
#: deliberately a two-relation ``walk_edges`` set and **not** the
#: ``scope``/``requires``/``suggests`` shape of ``resolve_context`` — see the
#: module docstring (R-3).
PROFILE_CHANNEL_RELATIONS: frozenset[Relation] = frozenset(
    {Relation.REQUIRES, Relation.SPECIALIZES_FROM}
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

    Computed by **calling** :func:`doctrine.drg.query.resolve_context` once per
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

    A *separate* :func:`doctrine.drg.query.walk_edges` transitive closure over
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
