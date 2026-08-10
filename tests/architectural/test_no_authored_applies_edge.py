"""Architectural gate: the shipped doctrine tree authors no ``applies`` edge.

WP09 of mission ``doctrine-silence-guards-01KYFV7Q`` (FR-012, NFR-001, NFR-002, SC-010).

What was measured, before anything was changed
----------------------------------------------
Exactly one ``applies`` edge existed in the shipped built-in graph::

    agent_profile:doctrine-daphne --applies--> procedure:onboard-external-agent-to-pack

and it was that procedure's **only** inbound edge. The consequence is the point of this
module: ``charter.cascade.cascade_activation_targets`` walks
:data:`~charter.cascade.REFERENCE_RELATIONS` (``requires`` / ``suggests`` / ``refines``),
so activating ``doctrine-daphne`` cascaded to 17 directives, 5 procedures, 40 tactics,
5 styleguides, 6 templates, 3 toolguides and a paradigm — and **not** to her own operating
procedure. The one artefact the profile's initialization declaration says she runs was the
one artefact her activation could not reach.

``applies`` is not a dead sink, and this gate is deliberately NOT built on the claim that
it is
--------------------------------------------------------------------------------------
``src/doctrine/drg/merge.py`` carries a comment asserting that "no traversal reads
``APPLIES``". Taken literally that is false, and a gate resting on it would be resting on
a wrong premise. Measured instead:

* ``specify_cli.charter_runtime.lint.checks.orphan`` **does** read ``applies`` — but only
  in the ``directive`` orphan rule, i.e. only for an inbound edge onto a ``directive``
  node. The retyped edge targets a ``procedure``, so no shipped reader ever saw it.
* ``charter.synthesizer.project_drg`` **produces** ``applies`` at project-tier synthesis
  time. That producer is live and out of scope here.

So the property this gate enforces is narrow and measurable: **no ``applies`` edge is
*authored* into the shipped doctrine tree.** It says nothing about the relation existing,
nothing about a runtime synthesiser emitting one, and nothing about the enum member. It
is exactly NFR-002.

Two authoring surfaces, both measured by their output
-----------------------------------------------------
1. The checked-in per-kind fragments ``src/doctrine/**/*.graph.yaml`` — parsed as YAML by
   :func:`authored_applies_edges`, never grepped, so prose containing the word "applies"
   cannot false-red it.
2. The generator that produces those fragments
   (``spec-kitty doctrine regenerate-graph`` →
   ``doctrine.drg.migration.hand_authored_overlay.generate_reference_graph_with_overlay``).
   An ``applies`` edge added to its curated tables but not yet regenerated is not visible
   in surface 1, so the generated graph is checked by :func:`applies_edges_in` too.

When mission ``drg-edge-migration-extractor-retirement-01KYFV8C`` retires the generator,
surface 2 disappears and its assertion should be **deleted**, not weakened — the import
will fail loudly, which is the intended behaviour.

Edge-count claims in the relation registry are checked, not trusted
-------------------------------------------------------------------
``RELATION_DESCRIPTIONS`` (``doctrine.drg.models``) is the canonical prose authority for
every relation, mirrored into ``docs/architecture/doctrine-relationships.md``. **Six**
entries state "zero edges exist in the built-in graph" on ``upstream/main``
(``delegates_to``, ``enhances``, ``overrides``, ``refines``, ``replaces``, ``vocabulary``),
and ``applies`` joins them in this change, making **seven**.
Nothing checked those claims: the ``applies`` entry read "1 edge in the built-in graph"
and stayed green after the edge count changed, and two positive counts had already drifted
(``requires`` said 255 against 259 measured, ``suggests`` said 330 against 332).

An earlier revision of this paragraph said "Five entries", and the floor below read
``>= 5``. Both were wrong, and wrong in the direction that matters: a floor two below the
live figure would have stayed green while two entries were deleted. Correcting the prose
alone would only reset the clock, so the count is no longer written down at all —
:meth:`TestAbsenceClaimsAreTrue.test_absence_claims_are_exactly_the_unemitted_relations`
derives it from the shipped graph, and seven is now a consequence rather than a claim.
That this module — whose stated purpose is checking that absence claims are true — shipped
a false count of its own is the reason the derivation replaced the number instead of
correcting it.

Both halves of the claim are now measured against the shipped graph, because gating only
the absence half would fix the instance and leave the class — the five re-pinned positive
counts would drift again on the next edge addition, silently, exactly as before:

* :class:`TestAbsenceClaimsAreTrue` — "zero edges exist" must be true.
* :class:`TestPositiveCountClaimsAreTrue` — "N edges" must be the right N.

The positive counts use **two** phrasings, not the five the deferral note assumed:
``(260 edges)`` and ``Emitted 8 times``. One alternation
(:data:`_POSITIVE_CLAIM`) reads both, so no cross-registry normalisation is needed.
:func:`unattributed_numbers` closes the remaining hole in that approach — a count written
in a *third* phrasing would parse to nothing and be verified by nothing, so any number the
patterns do not account for is red rather than skipped.

Note the residual, deliberately out of scope here: ``in_tension_with`` (2 edges),
``reconciles_tension`` (3) and ``rejects`` (8) are emitted but state no count at all.
A claim that is never made cannot drift, so nothing is unchecked — but a count added to
those entries later must go through :data:`_POSITIVE_CLAIM`, which
:func:`unattributed_numbers` now forces.

Non-vacuity (NFR-001)
---------------------
:class:`TestGateNonVacuity` plants each real violation shape and calls **the same public
checker callable** the shipped-tree assertions call, differing only in the tree/graph it
points at. A gate that re-implements its check inline in the mutation test stays green
forever while the production checker rots, so every mutation below routes through
:func:`authored_applies_edges`, :func:`applies_edges_in`, or
:func:`operating_procedure_is_cascade_reachable`. :data:`_ALLOWLIST` is empty and asserted
empty: the single pre-existing edge was retyped, not grandfathered.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from charter.cascade import REFERENCE_RELATIONS, CascadeScope, cascade_activation_targets
from doctrine.drg.loader import load_graph_or_dir
from doctrine.drg.migration.hand_authored_overlay import (
    generate_reference_graph_with_overlay,
)
from doctrine.drg.models import (
    RELATION_DESCRIPTIONS,
    DRGEdge,
    DRGGraph,
    DRGNode,
    NodeKind,
    Relation,
)

pytestmark = pytest.mark.architectural

# Relocated built-in pack root (mission relocate-builtin-doctrine-packs-01KYT87F):
# the checked-in per-kind ``*.graph.yaml`` fragments now live under
# ``packs/built-in/``, no longer under ``src/doctrine/``.
_DOCTRINE_ROOT = Path(__file__).resolve().parents[2] / "packs" / "built-in"

#: The relation this gate forbids in authored content.
_FORBIDDEN = Relation.APPLIES

#: Fragment paths (relative to ``packs/built-in/``) exempted from the rule. Deliberately
#: EMPTY: the one pre-existing ``applies`` edge was retyped to ``requires``, not frozen.
#: An entry here re-opens the unreachable-artefact class for that fragment.
_ALLOWLIST: frozenset[str] = frozenset()

_DAPHNE_URN = "agent_profile:doctrine-daphne"
_OPERATING_PROCEDURE_URN = "procedure:onboard-external-agent-to-pack"

#: Phrasing every registry entry uses to claim a relation is unemitted in the built-in
#: graph. One uniform sentence, so the check is a lookup rather than a five-pattern parser.
_ABSENCE_CLAIM = re.compile(r"zero edges exist in the built-in graph", re.IGNORECASE)

#: Phrasings the registry uses to state a *positive* edge count. There are two, not the
#: five the deferral note assumed: ``(260 edges)`` (``requires``/``suggests``/``scope``)
#: and ``Emitted 8 times`` (``instantiates``/``specializes_from``). No cross-registry
#: normalisation is needed -- one alternation reads both.
_POSITIVE_CLAIM = re.compile(r"\((\d+) edges?\)|emitted (\d+) times", re.IGNORECASE)

#: Numbers in the registry prose that are not edge counts (``walked at depth 1``).
#: A fail-closed lexicon, NOT a violation allowlist: :func:`unattributed_numbers`
#: reds on any number matched by neither pattern, so a *third* count phrasing cannot
#: enter the registry ungated -- which is the class this check exists to close.
_NON_COUNT_NUMBER = re.compile(r"depth (\d+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Checkers -- the public surface both the shipped assertions and the mutation
# proofs call. Nothing below re-implements them.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthoredAppliesEdge:
    """One ``applies`` edge found authored in a checked-in DRG fragment."""

    fragment: str
    source: str
    target: str

    def __str__(self) -> str:
        return f"{self.fragment}: {self.source} --applies--> {self.target}"


def _load_fragment(path: Path) -> dict[str, Any]:
    data: Any = YAML(typ="safe").load(path)
    return data if isinstance(data, dict) else {}


def iter_fragments(root: Path) -> list[Path]:
    """Return every checked-in DRG fragment under *root*.

    ``rglob``, not ``glob``: the loader only reads fragments at the top level, so a
    fragment nested in a subdirectory is already invisible to it. Scanning wider means a
    forbidden edge cannot hide in the one place nobody would look for it.
    """
    return sorted(p for p in root.rglob("*.graph.yaml") if "__pycache__" not in p.parts)


def authored_applies_edges(root: Path) -> tuple[AuthoredAppliesEdge, ...]:
    """Return every ``applies`` edge authored into a DRG fragment under *root*.

    Parsed as YAML and matched on the ``relation`` field, never grepped — two shipped edges
    carry the English word "applies" inside their ``when:`` prose
    (``tactic.graph.yaml:415`` and ``:1175``), and a text match would red on correct content.
    """
    found: list[AuthoredAppliesEdge] = []
    for path in iter_fragments(root):
        relative = path.relative_to(root).as_posix()
        if relative in _ALLOWLIST:
            continue
        edges = _load_fragment(path).get("edges") or []
        if not isinstance(edges, list):
            continue
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            if str(edge.get("relation", "")) == _FORBIDDEN.value:
                found.append(
                    AuthoredAppliesEdge(
                        fragment=relative,
                        source=str(edge.get("source", "?")),
                        target=str(edge.get("target", "?")),
                    )
                )
    return tuple(found)


def relations_authored_in(root: Path) -> set[str]:
    """Return every distinct ``relation`` token the fragment scan actually read.

    The floor for :func:`authored_applies_edges`. An empty result from a checker whose
    parser is broken looks exactly like an empty result from a compliant tree.
    """
    seen: set[str] = set()
    for path in iter_fragments(root):
        edges = _load_fragment(path).get("edges") or []
        if not isinstance(edges, list):
            continue
        for edge in edges:
            if isinstance(edge, dict) and "relation" in edge:
                seen.add(str(edge["relation"]))
    return seen


def applies_edges_in(graph: DRGGraph) -> tuple[str, ...]:
    """Return ``"<source> --applies--> <target>"`` for every ``applies`` edge in *graph*."""
    return tuple(
        f"{edge.source} --{_FORBIDDEN.value}--> {edge.target}"
        for edge in graph.edges
        if edge.relation is _FORBIDDEN
    )


def operating_procedure_is_cascade_reachable(graph: DRGGraph) -> bool:
    """Return whether activating Daphne cascades to her declared operating procedure.

    The behavioural form of "has a traversable inbound edge". Asserting the edge's
    *relation* literal would pass the day someone renames the relation and breaks the walk;
    asserting the walk's outcome cannot.
    """
    result = cascade_activation_targets(graph, _DAPHNE_URN, CascadeScope.all())
    kind, _, bare_id = _OPERATING_PROCEDURE_URN.partition(":")
    return bare_id in result.activated.get(kind, [])


def inbound_relations(graph: DRGGraph, urn: str) -> set[Relation]:
    """Return the relations of every edge pointing at *urn*."""
    return {edge.relation for edge in graph.edges if edge.target == urn}


def claimed_absent_relations() -> frozenset[Relation]:
    """Return every relation whose canonical description claims it is unemitted.

    Read off :data:`~doctrine.drg.models.RELATION_DESCRIPTIONS`, the single authority for
    that prose. The mirrored copy in ``docs/architecture/doctrine-relationships.md`` is
    already pinned to it, character for character, by
    ``tests/doctrine/test_relation_doc_parity.py`` — so checking the registry checks both,
    and re-reading the markdown here would only create a second, driftable authority.
    """
    return frozenset(
        relation
        for relation, text in RELATION_DESCRIPTIONS.items()
        if _ABSENCE_CLAIM.search(text)
    )


def claimed_edge_counts(
    descriptions: dict[Relation, str] | None = None,
) -> dict[Relation, int]:
    """Return the edge count each canonical description *claims* for its relation.

    *descriptions* defaults to :data:`~doctrine.drg.models.RELATION_DESCRIPTIONS`; the
    parameter exists so the mutation proofs can plant a wrong count and route through
    this exact callable rather than re-implementing the parse.
    """
    source = RELATION_DESCRIPTIONS if descriptions is None else descriptions
    claims: dict[Relation, int] = {}
    for relation, text in source.items():
        match = _POSITIVE_CLAIM.search(text)
        if match is not None:
            claims[relation] = int(match.group(1) or match.group(2))
    return claims


def measured_edge_counts(graph: DRGGraph) -> dict[Relation, int]:
    """Return the number of edges of each relation actually present in *graph*."""
    counts: dict[Relation, int] = {}
    for edge in graph.edges:
        counts[edge.relation] = counts.get(edge.relation, 0) + 1
    return counts


def unattributed_numbers(
    descriptions: dict[Relation, str] | None = None,
) -> dict[Relation, list[str]]:
    """Return, per relation, every number in its description no pattern accounts for.

    The completeness half of the count gate. Verifying the five *recognised* claims
    leaves the class open: a sixth claim written in a third phrasing would parse to
    nothing and be checked by nothing, which is exactly how ``requires`` reached 255
    against 259 measured. Anything numeric that is neither a count claim
    (:data:`_POSITIVE_CLAIM`, :data:`_ABSENCE_CLAIM`) nor a known non-count phrase
    (:data:`_NON_COUNT_NUMBER`) is surfaced here so the parser must be widened
    deliberately instead of silently under-reading.
    """
    source = RELATION_DESCRIPTIONS if descriptions is None else descriptions
    leftovers: dict[Relation, list[str]] = {}
    for relation, text in source.items():
        stripped = _POSITIVE_CLAIM.sub(" ", text)
        stripped = _ABSENCE_CLAIM.sub(" ", stripped)
        stripped = _NON_COUNT_NUMBER.sub(" ", stripped)
        remaining = re.findall(r"\S*\d+\S*", stripped)
        if remaining:
            leftovers[relation] = remaining
    return leftovers


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def shipped_graph() -> DRGGraph:
    return load_graph_or_dir(_DOCTRINE_ROOT)


def _fragment_text(*edges: str) -> str:
    body = "\n".join(edges)
    return (
        "schema_version: '1.0'\n"
        "generated_at: STATIC\n"
        "generated_by: test\n"
        "nodes:\n"
        "- urn: agent_profile:planted\n"
        "  kind: agent_profile\n"
        "edges:\n" + body + "\n"
    )


def _edge_block(relation: str) -> str:
    return (
        "- source: agent_profile:planted\n"
        "  target: procedure:planted-procedure\n"
        f"  relation: {relation}\n"
    )


def _graph_with(relation: Relation) -> DRGGraph:
    """A minimal valid graph carrying one edge of *relation*."""
    return DRGGraph(
        schema_version="1.0",
        generated_at="STATIC",
        generated_by="test",
        nodes=[
            DRGNode(urn=_DAPHNE_URN, kind=NodeKind.AGENT_PROFILE),
            DRGNode(urn=_OPERATING_PROCEDURE_URN, kind=NodeKind.PROCEDURE),
        ],
        edges=[
            DRGEdge(
                source=_DAPHNE_URN,
                target=_OPERATING_PROCEDURE_URN,
                relation=relation,
            )
        ],
    )


# ---------------------------------------------------------------------------
# The shipped tree
# ---------------------------------------------------------------------------


class TestShippedTreeAuthorsNoAppliesEdge:
    def test_no_fragment_authors_an_applies_edge(self) -> None:
        offenders = authored_applies_edges(_DOCTRINE_ROOT)
        assert not offenders, (
            "an `applies` edge is authored in the shipped doctrine tree. No context "
            "resolution, charter cascade or reference walk follows `applies`, so the "
            "relationship it names is inert and its target may be unreachable:\n"
            + "\n".join(f"  - {o}" for o in offenders)
            + "\nUse the relation the traversal actually reads (`requires` for a hard "
            "dependency, `suggests` for an advisory one)."
        )

    def test_loaded_shipped_graph_carries_no_applies_edge(
        self, shipped_graph: DRGGraph
    ) -> None:
        """Semantic half: catches an edge that reaches the graph by any route."""
        assert applies_edges_in(shipped_graph) == ()

    def test_the_generator_emits_no_applies_edge(self) -> None:
        """Authoring-surface half: an edge in the curated tables, not yet regenerated.

        Surface 1 only sees committed YAML. A curated-table entry awaiting a
        ``regenerate-graph`` run is authored but invisible there.
        """
        regenerated = generate_reference_graph_with_overlay(_DOCTRINE_ROOT)
        assert applies_edges_in(regenerated) == ()

    def test_allowlist_is_empty(self) -> None:
        """The one pre-existing edge was retyped, not grandfathered. Keep it that way."""
        assert len(_ALLOWLIST) == 0


class TestScannerFloor:
    """A compliant tree and a broken parser produce the same empty result. Separate them."""

    def test_every_fragment_on_disk_is_scanned(self) -> None:
        on_disk = set(_DOCTRINE_ROOT.rglob("*.graph.yaml"))
        assert on_disk, "no DRG fragments found -- the gate is pointed at the wrong tree"
        assert set(iter_fragments(_DOCTRINE_ROOT)) == on_disk

    def test_the_parser_actually_reads_relations(self) -> None:
        """Proves the empty ``applies`` result comes from content, not from a dead read."""
        seen = relations_authored_in(_DOCTRINE_ROOT)
        assert {"requires", "suggests", "scope"} <= seen, (
            f"fragment parser read only {sorted(seen)} -- it is not reading edges"
        )
        assert _FORBIDDEN.value not in seen


# ---------------------------------------------------------------------------
# The reachability half (SC-010)
# ---------------------------------------------------------------------------


class TestOperatingProcedureIsReachable:
    def test_the_procedure_has_an_inbound_edge_a_traversal_follows(
        self, shipped_graph: DRGGraph
    ) -> None:
        """Derived from ``REFERENCE_RELATIONS``, not from a restated relation list."""
        followed = inbound_relations(shipped_graph, _OPERATING_PROCEDURE_URN) & set(
            REFERENCE_RELATIONS
        )
        assert followed, (
            f"{_OPERATING_PROCEDURE_URN} has no inbound edge any traversal follows; "
            f"inbound relations are "
            f"{sorted(r.value for r in inbound_relations(shipped_graph, _OPERATING_PROCEDURE_URN))}"
        )

    def test_activating_daphne_cascades_to_her_operating_procedure(
        self, shipped_graph: DRGGraph
    ) -> None:
        assert operating_procedure_is_cascade_reachable(shipped_graph), (
            "`charter activate agent-profile doctrine-daphne --cascade all` does not "
            "pull in the procedure the profile declares it runs"
        )

    def test_cascade_probe_is_not_trivially_true(self, shipped_graph: DRGGraph) -> None:
        """Floor: the probe must be capable of reporting absence.

        Same callable, a graph whose only edge is the pre-fix ``applies`` shape.
        """
        assert not operating_procedure_is_cascade_reachable(
            _graph_with(Relation.APPLIES)
        )
        assert operating_procedure_is_cascade_reachable(_graph_with(Relation.REQUIRES))


# ---------------------------------------------------------------------------
# Absence claims in the canonical relation registry
# ---------------------------------------------------------------------------


class TestAbsenceClaimsAreTrue:
    """A registry entry claiming "zero edges exist" must be true of the shipped graph."""

    def test_every_absence_claim_matches_the_measured_graph(
        self, shipped_graph: DRGGraph
    ) -> None:
        liars = sorted(
            relation.value
            for relation in claimed_absent_relations()
            if any(edge.relation is relation for edge in shipped_graph.edges)
        )
        assert not liars, (
            "these relations are documented as unemitted in the built-in graph but are "
            f"emitted: {liars}"
        )

    def test_absence_claims_are_exactly_the_unemitted_relations(
        self, shipped_graph: DRGGraph
    ) -> None:
        """Both directions, derived — replacing the floor that used to read ``>= 5``.

        That floor was doubly wrong. It was loose (two entries could be deleted in
        silence), and the figure it approximated was itself misread: six on
        ``upstream/main``, seven here. Re-pinning it at 7 would fix today's number and
        keep the shape that produced the error.

        So no number is written down. A relation claims "zero edges exist" **iff** the
        shipped graph emits none of it:

        * left-to-right catches a claim that has become false — the ``applies`` case,
          where retyping the last edge silently invalidated the prose;
        * right-to-left catches a relation that fell to zero edges without anyone saying
          so — the same defect discovered from the other end, which the old one-way check
          could not see at any floor value.

        It is also self-flooring, and strictly stronger than the floor it replaces.
        ``>= 5`` did catch a *totally* dead :data:`_ABSENCE_CLAIM` (0 claims fails the
        floor). What it could not catch is a *partially* dead one: a parser that dropped
        a single entry left six claims, cleared the floor, and left the one-way check
        above green, because the six it still read were all genuinely absent. Verified by
        mutation — dropping ``vocabulary`` from the parse is invisible to ``>= 5`` and
        reds here by name.
        """
        emitted = {edge.relation for edge in shipped_graph.edges}
        unemitted = {
            relation for relation in RELATION_DESCRIPTIONS if relation not in emitted
        }
        claimed = claimed_absent_relations()

        assert unemitted, "no relation is unemitted -- the graph read is broken"
        assert claimed == unemitted, (
            "the set of relations documented as unemitted must equal the set the shipped "
            "graph actually leaves unemitted.\n"
            "  claimed absent but ARE emitted: "
            f"{sorted(r.value for r in claimed - unemitted)}\n"
            "  emitted zero times but NOT documented as absent: "
            f"{sorted(r.value for r in unemitted - claimed)}\n"
            "Update RELATION_DESCRIPTIONS -- and its mirror in "
            "docs/architecture/doctrine-relationships.md, which "
            "tests/doctrine/test_relation_doc_parity.py pins to it."
        )

    def test_no_relation_claims_both_absence_and_a_positive_count(self) -> None:
        """The two claim shapes are mutually exclusive; an entry asserting both lies once."""
        both = sorted(
            r.value for r in claimed_absent_relations() & set(claimed_edge_counts())
        )
        assert not both, f"these entries claim both zero and a positive count: {both}"

    def test_applies_is_documented_as_unemitted(self) -> None:
        """The registry entry this WP invalidates must state the new truth, not the old one.

        It previously read "1 edge in the built-in graph" — a claim nothing checked, which
        is why it survived unchanged while the edge it described was the mission's subject.
        """
        assert _FORBIDDEN in claimed_absent_relations()


class TestPositiveCountClaimsAreTrue:
    """A registry entry claiming *N* edges must be right about *N*, same as a zero claim.

    Gating only the absence claims left the five positive counts free to drift again on
    the next edge addition -- the shape they had already drifted in twice before this
    module existed. Both claim shapes are now measured against the same shipped graph.
    """

    def test_every_positive_count_matches_the_measured_graph(
        self, shipped_graph: DRGGraph
    ) -> None:
        measured = measured_edge_counts(shipped_graph)
        wrong = {
            relation.value: (claimed, measured.get(relation, 0))
            for relation, claimed in claimed_edge_counts().items()
            if measured.get(relation, 0) != claimed
        }
        assert not wrong, (
            "RELATION_DESCRIPTIONS states an edge count the built-in graph does not "
            f"have (relation: claimed vs measured): {wrong}. Update the registry entry "
            "-- and its mirror in docs/architecture/doctrine-relationships.md, which "
            "tests/doctrine/test_relation_doc_parity.py pins to it."
        )

    def test_the_two_number_patterns_partition_the_registry(self) -> None:
        """Replaces a ``len(claims) >= 5`` floor. The number is gone; nothing replaced it.

        **Why not set equality, as the absence half uses.** There the ground truth is
        derivable — a relation is claimed-absent *iff* the shipped graph emits none of
        it — so equating the two sets removes the number and adds the reverse direction.
        Here there is no such set. Three relations are emitted and state no count at all
        (``rejects`` 8, ``reconciles_tension`` 3, ``in_tension_with`` 2), legitimately:
        stating a count is a prose choice, not an obligation, so "the relations that
        should carry a count" is not derivable from the graph and equating against the
        emitted set would red on correct content. Applying set equality by symmetry would
        manufacture a false invariant, which is worse than the floor it replaced.

        **What the floor was actually wrong about.** Not slack — at 5 against a live 5 it
        was exact, unlike the absence half's 5 against a live 7. It was wrong by being a
        hand-maintained number at all: it had to be edited whenever a registry entry
        gained or lost a count sentence, and a legitimate *removal* would have reddened
        it while nothing was broken.

        **What replaces it.** The partition, which is derivable: every number in the
        registry is read by exactly one of the two patterns, and neither can absorb the
        other's shape. Together with
        :meth:`test_no_number_in_the_registry_escapes_attribution` this is strictly
        stronger than any floor value. A dead :data:`_POSITIVE_CLAIM` leaves its numbers
        unattributed and reds there; the one hole that check cannot see on its own is
        :data:`_NON_COUNT_NUMBER` being widened until it swallows counts — attribution
        would stay complete while verification quietly stopped. That is what the
        cross-discrimination probes below close.
        """
        for relation, text in RELATION_DESCRIPTIONS.items():
            count_spans = [m.span() for m in _POSITIVE_CLAIM.finditer(text)]
            prose_spans = [m.span() for m in _NON_COUNT_NUMBER.finditer(text)]
            overlaps = [
                (text[c[0] : c[1]], text[p[0] : p[1]])
                for c in count_spans
                for p in prose_spans
                if c[0] < p[1] and p[0] < c[1]
            ]
            assert not overlaps, (
                f"{relation.value}: the same text is matched by both _POSITIVE_CLAIM "
                f"and _NON_COUNT_NUMBER ({overlaps}) — one pattern shadows the other, "
                "so which of them 'owns' that number depends on evaluation order"
            )

        # Cross-discrimination: neither pattern may take the other's shape. Without
        # this, widening _NON_COUNT_NUMBER (say, to a bare `\\d+`) would empty
        # `unattributed_numbers()` AND `claimed_edge_counts()` in one edit, and every
        # check above would pass with nothing verified.
        for count_phrasing in ("(260 edges)", "Emitted 8 times", "emitted 332 times"):
            assert _POSITIVE_CLAIM.search(count_phrasing), (
                f"_POSITIVE_CLAIM no longer reads {count_phrasing!r} — counts written "
                "that way are now unverified"
            )
            assert not _NON_COUNT_NUMBER.search(count_phrasing), (
                f"_NON_COUNT_NUMBER swallows {count_phrasing!r}, which excuses a real "
                "count from verification instead of excusing prose"
            )
        assert not _POSITIVE_CLAIM.search("walked at depth 1")
        assert _NON_COUNT_NUMBER.search("walked at depth 1")

    def test_no_number_in_the_registry_escapes_attribution(self) -> None:
        """Completeness: a count written in a third phrasing must not slip through.

        Checking only the phrasings the parser already knows re-creates the original
        defect one rewording later.
        """
        leftovers = {r.value: nums for r, nums in unattributed_numbers().items()}
        assert not leftovers, (
            "these numbers in RELATION_DESCRIPTIONS are matched by no known pattern, so "
            f"nothing checks them: {leftovers}. If a number is an edge count, add its "
            "phrasing to _POSITIVE_CLAIM so it is verified; if it is not, add it to "
            "_NON_COUNT_NUMBER."
        )


# ---------------------------------------------------------------------------
# Non-vacuity (NFR-001) -- every mutation routes through a checker above
# ---------------------------------------------------------------------------


class TestGateNonVacuity:
    def test_a_planted_applies_edge_in_a_fragment_is_flagged(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "planted.graph.yaml").write_text(
            _fragment_text(_edge_block("applies")), encoding="utf-8"
        )
        offenders = authored_applies_edges(tmp_path)
        assert [str(o) for o in offenders] == [
            "planted.graph.yaml: agent_profile:planted "
            "--applies--> procedure:planted-procedure"
        ]

    def test_a_planted_applies_edge_in_a_subdirectory_is_flagged(
        self, tmp_path: Path
    ) -> None:
        """The loader would not read it; the gate still must, or it becomes a hiding place."""
        nested = tmp_path / "overlays"
        nested.mkdir()
        (nested / "planted.graph.yaml").write_text(
            _fragment_text(_edge_block("applies")), encoding="utf-8"
        )
        offenders = authored_applies_edges(tmp_path)
        assert [str(o) for o in offenders] == [
            "overlays/planted.graph.yaml: agent_profile:planted "
            "--applies--> procedure:planted-procedure"
        ]

    def test_a_fragment_without_an_applies_edge_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """Negative control: the checker discriminates, it does not flag every edge."""
        (tmp_path / "clean.graph.yaml").write_text(
            _fragment_text(_edge_block("requires"), _edge_block("suggests")),
            encoding="utf-8",
        )
        assert authored_applies_edges(tmp_path) == ()

    def test_the_word_applies_in_prose_is_not_flagged(self, tmp_path: Path) -> None:
        """Discriminator proof: a text match would red on correct content.

        ``tactic.graph.yaml`` carries "applies" inside two edges' ``when:`` prose
        (lines 415 and 1175). A grep-based gate would flag both.
        """
        (tmp_path / "prose.graph.yaml").write_text(
            _fragment_text(
                _edge_block("requires")
                + "  when: The tactic applies extraction before interpretation\n"
            ),
            encoding="utf-8",
        )
        assert authored_applies_edges(tmp_path) == ()

    def test_a_planted_applies_edge_in_a_graph_is_flagged(self) -> None:
        """Same callable the generator-surface assertion uses."""
        assert applies_edges_in(_graph_with(Relation.APPLIES)) == (
            f"{_DAPHNE_URN} --applies--> {_OPERATING_PROCEDURE_URN}",
        )

    def test_the_graph_checker_ignores_other_relations(self) -> None:
        for relation in (Relation.REQUIRES, Relation.SUGGESTS, Relation.SCOPE):
            assert applies_edges_in(_graph_with(relation)) == ()

    def test_a_false_absence_claim_is_caught(self, shipped_graph: DRGGraph) -> None:
        """Plant the real shape: a relation documented as unemitted that is emitted.

        Routes through the same ``claimed_absent_relations()`` read the shipped assertion
        uses, against a graph mutated to emit one of the claimed-absent relations.
        """
        claimed = sorted(claimed_absent_relations(), key=lambda r: r.value)
        assert claimed, "no absence claims to mutate against"
        victim = claimed[0]
        mutated = _graph_with(victim)
        liars = [
            relation.value
            for relation in claimed_absent_relations()
            if any(edge.relation is relation for edge in mutated.edges)
        ]
        assert liars == [victim.value]

    def test_a_drifted_positive_count_is_caught(self, shipped_graph: DRGGraph) -> None:
        """Plant the historical shape: ``requires`` reading 255 against 259 measured.

        Same :func:`claimed_edge_counts` read the shipped assertion uses, against a
        registry copy carrying the pre-WP09 wrong number.
        """
        drifted = dict(RELATION_DESCRIPTIONS)
        drifted[Relation.REQUIRES] = drifted[Relation.REQUIRES].replace(
            "(321 edges)", "(265 edges)"
        )
        assert drifted != RELATION_DESCRIPTIONS, "the mutation did not apply"

        measured = measured_edge_counts(shipped_graph)
        claims = claimed_edge_counts(drifted)
        assert claims[Relation.REQUIRES] == 265
        wrong = {
            relation.value
            for relation, claimed in claims.items()
            if measured.get(relation, 0) != claimed
        }
        assert wrong == {"requires"}

    def test_both_positive_phrasings_are_read(self) -> None:
        """Discriminator: the parser is an alternation, not a single ``(N edges)`` regex.

        ``instantiates``/``specializes_from`` state their counts as ``Emitted N times``.
        A gate built on ``(\\d+) edges?`` alone would silently skip them -- present as a
        checked claim, actually unchecked.
        """
        claims = claimed_edge_counts()
        assert claims[Relation.REQUIRES] == 321  # "(321 edges)"
        assert claims[Relation.INSTANTIATES] == 11  # "Emitted 11 times"

    def test_an_unrecognised_count_phrasing_is_flagged(self) -> None:
        """A third phrasing must red the sweep rather than parse to nothing."""
        rephrased = dict(RELATION_DESCRIPTIONS)
        rephrased[Relation.REJECTS] += " It carries 8 such links in the built-in graph."
        assert Relation.REJECTS not in claimed_edge_counts(rephrased)
        assert unattributed_numbers(rephrased) == {Relation.REJECTS: ["8"]}

    def test_known_non_count_numbers_are_not_flagged(self) -> None:
        """Negative control: ``walked at depth 1`` is prose, not a drifting claim."""
        assert Relation.SCOPE not in unattributed_numbers()
        assert Relation.VOCABULARY not in unattributed_numbers()
