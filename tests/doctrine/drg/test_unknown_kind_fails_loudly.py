"""No :class:`NodeKind` may vanish at a kind-dispatch boundary (WP03, FR-003/SC-002).

Two sites dispatch on :class:`~doctrine.drg.models.NodeKind` and drop what they
do not name:

===========================================  ==============  ============
Site                                         Shape           Kinds lost
===========================================  ==============  ============
``doctrine.drg.query.resolve_transitive_refs``  16 buckets filled, 10 read out   6
``charter.context._classify_artifact_urns``     4 branches, no ``else``          12
===========================================  ==============  ============

Both figures were re-derived by execution on this branch. **The two drops differ
in kind, and the distinction is load-bearing** — an earlier revision of this
docstring (and of the WP prompt) called both "live", which is wrong for the first
site:

* ``resolve_transitive_refs`` — **latent.** The shipped graph carries 35 nodes in
  unnameable kinds (``action`` 24, ``anti_pattern`` 6, ``mission_type`` 4,
  ``glossary_pack`` 1), but *carried is not reached*. All three production call
  sites pass ``{REQUIRES, SUGGESTS}`` with seeds limited to
  directive/tactic/paradigm plus ``_direct_root_urns``; the only edges into those
  kinds are ``mission_type --requires--> action`` (×21, and ``mission_type`` is
  never a seed) and ``paradigm --rejects--> anti_pattern`` (×8, and ``rejects`` is
  never passed). Zero unnamed kinds are reachable today.
* ``_classify_artifact_urns`` — **live.** Measured through the real path across
  all 24 shipped actions: **56** artifact-URN visits are discarded
  (``procedure`` 26, ``template`` 15, ``paradigm`` 12, ``agent_profile`` 3).

Latency is an argument *for* totality here, not against it: a raise would be a
timebomb the moment mission C authors anti-patterns, an org pack seeds a
``mission_type``, or any caller passes ``REJECTS``. Totality needs no edit then.

Why the two sites get *different* closures
------------------------------------------
They are not the same defect wearing two hats:

* ``resolve_transitive_refs`` is a **lossless bucketing wrapper**. Its job is to
  return what the walk found. Raising would be wrong even though nothing reaches
  those kinds today — it converts a latent gap into a future outage. So the
  closure is *totality*: a per-kind view seeded from
  ``NodeKind`` itself, so nothing can fall out and a kind added tomorrow is
  carried without anyone editing the wrapper. This also keeps the frozen
  contract at
  ``kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/contracts/resolve-transitive-refs.contract.md``
  intact — that contract says the function does **not** raise (:89, :204), and
  a total result never needs to.

* ``_classify_artifact_urns`` is a **deliberate 4-way projection** into an
  action bundle that has exactly four slots. Twelve kinds legitimately have no
  slot. The defect is not that they are excluded, it is that *exclusion and
  ignorance are indistinguishable*. The closure is an explicit, total
  kind→slot declaration: excluded kinds say so, and a kind nobody has ruled on
  is loud.

Pinned behaviourally, not by code shape (#2532)
-----------------------------------------------
`#2532 <https://github.com/Priivacy-ai/spec-kitty/issues/2532>`_ decomposes
``src/charter/context.py``, so the missing ``else`` lives inside a module about
to be split apart. Every assertion below is therefore written against
*observable outcomes* — "this kind survives the round trip", "an unruled kind
raises" — and never against the presence of a branch, a line number, or a
literal count of arms. A decomposition may move any of this code anywhere; it
cannot make these tests pass while reopening the drop.
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Mapping
from enum import StrEnum
from typing import cast

import pytest

from doctrine.drg.loader import load_graph_or_dir
from doctrine.drg.models import DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.query import ResolveTransitiveRefsResult, resolve_transitive_refs

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]

#: NFR-004 — the shipped graph's content must not move. Re-measured on this
#: branch. If it moves, that is a finding to ledger, never a number to bump.
#:
#: The single authority for every delta is the composition ledger in
#: ``tests/doctrine/drg/migration/test_extractor_projection.py``; this pin is the
#: shipped-graph (pure + hand-authored overlay) VIEW of that ledger. It is
#: ledgered, never bumped-to-green:
#:   (6)/(7) 2026-07-28 #3009 landing: rtk-search-tooling deleted (-1 node),
#:           eight activated-but-unreachable artefacts wired (+7 edges) -> 310/781
#:   (8)     WP09: one scope edge action:documentation/generate->DIRECTIVE_042 -> +1 edge
#:   (9)     #3063 family-A (DDD): +14 overlay edges
#:   (10)    #3063 family-B (REFACTORING): +1 node (directive) / +14 overlay edges
#:   (11)    #3063 family-C (ARCHITECTURE-DOCS): +1 node (directive) / +9 overlay edges
#:   (12)    #3063 family-D (TESTING/BDD/MUTATION): +5 nodes (1 directive, 2
#:           styleguides, 2 toolguides) / +54 overlay edges
#:   (13)    #3063 family-E (ANALYSIS/TERMINOLOGY/REASONS-CANVAS): +0 nodes /
#:           +9 overlay edges (all `suggests`, zero new artefacts) -> 317/882
#:   (14)    doctrine-delivery-activation-01KYQVQK WP02 (T007/T008/T009): +7
#:           anti_pattern nodes (the seven grounded refactoring code smells) /
#:           +10 overlay edges (3 action:documentation/design --instantiates-->
#:           template:c4-* topology edges + 7 tactic:refactoring-* --REJECTS-->
#:           anti_pattern:<smell> edges) -> 324/892. T006's Family-A `when`
#:           backfill is content-only (no count move). Full delta is
#:           projection-ledger entry (14).
#: Net: 324/892 = pure 311/764 plus the hand-authored overlay's 13 nodes / 128
#: edges. (WP09 and families A–D were ledgered in the projection module but this
#: shipped-graph mirror was left stale at 310/781 through those changes; corrected
#: with family D, whose full delta is projection-ledger entry (12); family E adds
#: +9 edges, projection-ledger entry (13); WP02 adds +7 nodes / +10 edges,
#: projection-ledger entry (14).)
_EXPECTED_NODE_COUNT = 324
_EXPECTED_EDGE_COUNT = 892

_DOCTRINE_ROOT = pathlib.Path(__file__).resolve().parents[3] / "src" / "doctrine"


class _FutureNodeKind(StrEnum):
    """Stands in for a :class:`NodeKind` member added after this test was written.

    The whole defect class is "somebody adds a kind and a dispatch site never
    hears about it". A test that can only use today's members cannot express
    that, so it is simulated with a value the production code has provably
    never been taught.
    """

    FUTURE = "future_kind"


def _shipped_graph() -> DRGGraph:
    return load_graph_or_dir(_DOCTRINE_ROOT)


def _every_id_readable_from(result: ResolveTransitiveRefsResult) -> set[str]:
    """Gather every artifact id the result exposes, whatever field carries it.

    Deliberately shape-agnostic. The property under test is "the walk's finding
    is still reachable by a caller", and pinning that to a named field would
    make the test a description of today's dataclass instead of a guard on the
    drop.
    """
    ids: set[str] = set()
    for spec in dataclasses.fields(result):
        value = getattr(result, spec.name)
        if isinstance(value, Mapping):
            for bucket in value.values():
                ids.update(bucket)
        elif isinstance(value, list):
            ids.update(item for item in value if isinstance(item, str))
    return ids


# ---------------------------------------------------------------------------
# Site 1 -- doctrine.drg.query.resolve_transitive_refs
# ---------------------------------------------------------------------------


def test_resolve_transitive_refs_loses_no_node_kind() -> None:
    """Every ``NodeKind`` the walk visits is readable back off the result.

    Enumerated from ``NodeKind`` at runtime, so the day a seventeenth member is
    added this test covers it without being edited — the property is
    "nothing is lost", not "these ten are kept".
    """
    nodes = [
        DRGNode(urn=f"{kind.value}:probe-{kind.value}", kind=kind) for kind in NodeKind
    ]
    graph = DRGGraph(
        schema_version="1.0",
        generated_at="2026-07-27T00:00:00Z",
        generated_by="test",
        nodes=nodes,
        edges=[],
    )

    result = resolve_transitive_refs(
        graph,
        start_urns={node.urn for node in nodes},
        relations=set(Relation),
    )

    assert result.unresolved == []
    readable = _every_id_readable_from(result)
    lost = sorted(
        kind.value for kind in NodeKind if f"probe-{kind.value}" not in readable
    )
    assert not lost, f"resolve_transitive_refs silently dropped kinds: {lost}"


def test_resolve_transitive_refs_per_kind_view_is_total() -> None:
    """The per-kind view carries an entry for *every* kind, not only hit ones.

    A view that only materialises the kinds it happened to see is still a
    hand-enumeration one refactor away from dropping something; totality is
    what makes the closure structural.
    """
    result = resolve_transitive_refs(
        _shipped_graph(),
        start_urns=set(),
        relations={Relation.REQUIRES},
    )

    assert set(result.by_kind) == set(NodeKind)


def test_named_buckets_and_per_kind_view_agree() -> None:
    """The legacy named fields and the per-kind view are one truth, not two.

    Callers still construct this result with named keyword arguments only
    (``charter.compiler``, ``charter.reference_resolver``). If the per-kind
    view did not reflect those, closing the drop here would open a fresh one
    for anyone who reads the new surface.
    """
    result = resolve_transitive_refs(
        _shipped_graph(),
        start_urns={"directive:DIRECTIVE_025"},
        relations={Relation.REQUIRES, Relation.SUGGESTS},
    )

    assert result.by_kind[NodeKind.DIRECTIVE] == result.directives
    assert result.by_kind[NodeKind.TACTIC] == result.tactics
    assert result.directives, "fixture must actually resolve something"


def test_anti_pattern_reachable_in_the_shipped_graph_survives() -> None:
    """A concrete, live kind — not a synthetic one — makes it out of the walk.

    ``rejects`` edges targeting ``anti_pattern`` nodes exist on the shipped
    graph today, so real graph data, on a relation set no production caller passes yet.
    """
    graph = _shipped_graph()
    rejects = [edge for edge in graph.edges if edge.relation is Relation.REJECTS]
    assert rejects, "shipped graph must carry `rejects` edges for this to be live"

    result = resolve_transitive_refs(
        graph,
        start_urns={edge.source for edge in rejects},
        relations={Relation.REJECTS},
    )

    expected = sorted(
        {edge.target.split(":", 1)[1] for edge in rejects}
    )
    assert result.by_kind[NodeKind.ANTI_PATTERN] == expected


# ---------------------------------------------------------------------------
# Site 2 -- charter.context._classify_artifact_urns
# ---------------------------------------------------------------------------


def test_action_bundle_rules_on_every_node_kind() -> None:
    """Every kind has a *recorded verdict*: projected into a slot, or excluded.

    Enumerated from ``NodeKind`` at runtime. A new member arrives with no
    verdict and this goes red — which is the only difference between an
    exclusion and an oversight.
    """
    from charter.context import action_bundle_bucket

    unruled = []
    for kind in NodeKind:
        try:
            action_bundle_bucket(kind)
        except LookupError:
            unruled.append(kind.value)

    assert not unruled, f"no recorded verdict for kinds: {unruled}"


def test_action_bundle_projects_exactly_the_delivered_slots() -> None:
    """The bundle projects exactly the *stated* delivered slots -- no more.

    WP03 of ``doctrine-silence-guards`` froze this at four slots ("state the
    exclusions, do not render them"). **WP10 (doctrine-delivery-reachability,
    FR-009/FR-011) reverses that verdict for PROCEDURE and ASSET**: a resolved
    procedure/asset is executing-agent context no other charter surface
    delivers on the action path (the criterion recorded at
    ``_ACTION_BUNDLE_SLOT_BY_KIND``). The guard's intent is unchanged -- the
    projected set must equal the *stated* set exactly, so a future kind cannot
    be smuggled in unstated; only the stated set grew from four to six.
    """
    from charter.context import action_bundle_bucket

    projected = {
        kind: action_bundle_bucket(kind)
        for kind in NodeKind
        if action_bundle_bucket(kind) is not None
    }

    assert projected == {
        NodeKind.DIRECTIVE: "directives",
        NodeKind.TACTIC: "tactics",
        NodeKind.STYLEGUIDE: "styleguides",
        NodeKind.TOOLGUIDE: "toolguides",
        NodeKind.PROCEDURE: "procedures",
        NodeKind.ASSET: "assets",
    }


def test_unruled_kind_is_loud_at_the_action_bundle_boundary() -> None:
    """A kind nobody has ruled on raises instead of evaporating.

    This is the non-vacuity half: without it, a declaration that happens to be
    total today would still pass ``test_action_bundle_rules_on_every_node_kind``
    while the runtime path silently swallowed anything outside it.
    """
    from charter.context import action_bundle_bucket

    with pytest.raises(LookupError, match="future_kind"):
        action_bundle_bucket(cast(NodeKind, _FutureNodeKind.FUTURE))


def test_classify_artifact_urns_propagates_the_loud_error() -> None:
    """The guard sits on the live classification path, not beside it.

    Asserted through ``_classify_artifact_urns`` itself so the protection is
    pinned to the behaviour of classifying a graph, not to where the
    declaration currently lives. ``#2532`` may relocate either; it cannot make
    this pass with the drop reopened.
    """
    from charter import context as context_module

    class _UnruledNode:
        kind = _FutureNodeKind.FUTURE

    class _StubGraph:
        @staticmethod
        def get_node(urn: str) -> object:
            return _UnruledNode() if urn == "future_kind:x" else None

    with pytest.raises(LookupError, match="future_kind"):
        context_module._classify_artifact_urns(
            {"future_kind:x"},
            cast(DRGGraph, _StubGraph()),
            set(),
        )


# ---------------------------------------------------------------------------
# T017 -- NFR-004 graph invariant
# ---------------------------------------------------------------------------


def test_shipped_graph_content_is_unchanged() -> None:
    """Closing the kind boundary must move the graph by exactly zero."""
    graph = _shipped_graph()

    assert (len(graph.nodes), len(graph.edges)) == (
        _EXPECTED_NODE_COUNT,
        _EXPECTED_EDGE_COUNT,
    )


def test_shipped_graph_carries_every_kind_the_drop_would_have_lost() -> None:
    """The six kinds ``resolve_transitive_refs`` dropped are real, present nodes.

    Guards the test above from going vacuous: if the shipped graph stopped
    carrying these, ``test_resolve_transitive_refs_loses_no_node_kind`` would
    still pass on synthetic nodes while the live exposure quietly disappeared —
    and nobody would learn that the mission's premise had changed.
    """
    graph = _shipped_graph()
    present = {node.kind for node in graph.nodes}

    for kind in (
        NodeKind.ACTION,
        NodeKind.ANTI_PATTERN,
        NodeKind.MISSION_TYPE,
        NodeKind.GLOSSARY_PACK,
    ):
        assert kind in present, f"{kind.value} nodes vanished from the shipped graph"


def test_the_legacy_field_table_covers_every_named_field() -> None:
    """`_KIND_BY_LEGACY_FIELD` is a new enumeration, and nothing else gates it.

    Review found this one line from being the next silent drop. `__post_init__`
    reconciles named fields against `by_kind` by iterating *this table*, and the
    table is deliberately `str`-keyed so `test_kind_mapping_totality` cannot
    discover it. Add an eleventh named field tomorrow and it is never reconciled:
    it sits populated beside an empty `by_kind` bucket — closing one silent drop
    by opening another, which is exactly the shape this WP exists to close.

    Derived from the dataclass rather than restated, so the two cannot drift.
    """
    from dataclasses import fields

    from doctrine.drg.query import _KIND_BY_LEGACY_FIELD, ResolveTransitiveRefsResult

    named = {f.name for f in fields(ResolveTransitiveRefsResult)} - {"unresolved", "by_kind"}

    assert set(_KIND_BY_LEGACY_FIELD) == named, (
        "every named kind field must be reconciled against by_kind. Unreconciled: "
        f"{sorted(named - set(_KIND_BY_LEGACY_FIELD))}; stale table entries: "
        f"{sorted(set(_KIND_BY_LEGACY_FIELD) - named)}"
    )
