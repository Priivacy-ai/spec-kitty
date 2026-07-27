"""Architectural gate: the shipped doctrine tree authors no ``applies`` edge.

WP09 of mission ``doctrine-silence-guards-01KYFV7Q`` (FR-012, NFR-001, NFR-002, SC-010).

What was measured, before anything was changed
----------------------------------------------
Exactly one ``applies`` edge existed in the shipped built-in graph::

    agent_profile:doctrine-daphne --applies--> procedure:onboard-external-agent-to-pack

and it was that procedure's **only** inbound edge. The consequence is the point of this
module: ``charter.cascade.cascade_activation_targets`` walks
:data:`~charter.cascade.REFERENCE_RELATIONS` (``requires`` / ``suggests`` / ``refines``),
so activating ``doctrine-daphne`` cascaded to 17 directives, 5 procedures, 39 tactics,
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

Absence claims in the relation registry are checked, not trusted
----------------------------------------------------------------
``RELATION_DESCRIPTIONS`` (``doctrine.drg.models``) is the canonical prose authority for
every relation, mirrored into ``docs/architecture/doctrine-relationships.md``. Five entries
state "zero edges exist in the built-in graph", and ``applies`` joins them in this change.
Nothing checked those claims: the ``applies`` entry read "1 edge in the built-in graph"
and stayed green after the edge count changed, and two positive counts had already drifted
(``requires`` said 255 against 259 measured, ``suggests`` said 330 against 332).
:class:`TestAbsenceClaimsAreTrue` closes the class this WP would otherwise create — a
canonical description asserting a relation is unemitted while it is emitted.

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

_DOCTRINE_ROOT = Path(__file__).resolve().parents[2] / "src" / "doctrine"

#: The relation this gate forbids in authored content.
_FORBIDDEN = Relation.APPLIES

#: Fragment paths (relative to ``src/doctrine/``) exempted from the rule. Deliberately
#: EMPTY: the one pre-existing ``applies`` edge was retyped to ``requires``, not frozen.
#: An entry here re-opens the unreachable-artefact class for that fragment.
_ALLOWLIST: frozenset[str] = frozenset()

_DAPHNE_URN = "agent_profile:doctrine-daphne"
_OPERATING_PROCEDURE_URN = "procedure:onboard-external-agent-to-pack"

#: Phrasing every registry entry uses to claim a relation is unemitted in the built-in
#: graph. One uniform sentence, so the check is a lookup rather than a five-pattern parser.
_ABSENCE_CLAIM = re.compile(r"zero edges exist in the built-in graph", re.IGNORECASE)


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

    Parsed as YAML and matched on the ``relation`` field, never grepped — several shipped
    fragments carry the English word "applies" inside an edge's ``when:`` prose, and a text
    match would red on correct content.
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

    def test_the_claim_scan_is_not_empty(self) -> None:
        """Floor: an entry-scan that matches nothing would pass the check above vacuously."""
        claimed = claimed_absent_relations()
        assert len(claimed) >= 5, (
            f"only {len(claimed)} absence claims parsed out of RELATION_DESCRIPTIONS"
        )

    def test_applies_is_documented_as_unemitted(self) -> None:
        """The registry entry this WP invalidates must state the new truth, not the old one.

        It previously read "1 edge in the built-in graph" — a claim nothing checked, which
        is why it survived unchanged while the edge it described was the mission's subject.
        """
        assert _FORBIDDEN in claimed_absent_relations()


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
        assert len(authored_applies_edges(tmp_path)) == 1

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
        """NFR-003-shaped discriminator: a text match would red on correct content.

        Two shipped fragments carry "applies" inside an edge's ``when:`` prose.
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
