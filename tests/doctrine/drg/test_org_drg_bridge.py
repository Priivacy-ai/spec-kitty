"""org->DRG bridge integrity (WP08, FR-010/FR-011, SC-009).

The bridge between an organisation pack's fragment shape (bare ids + plural
kinds) and the canonical DRG (URNs + :class:`NodeKind`) had five measured
integrity defects, each an instance of the mission's root finding — *the
doctrine layer's failure mode is silence, not error*. Measured on
``remediation/doctrine-silence-guards`` @ ``13464fea7`` before this file
existed:

===  ===================================================  =====================
D    Shape                                                Behaviour before WP08
===  ===================================================  =====================
D1   built-in-source -> pack-target edge                  dropped: ``None``,
                                                          0 warnings,
                                                          0 conflict records
D2   bare target naming a non-directive built-in          re-kinded to
                                                          ``directive:<id>`` —
                                                          a phantom node
D3   URN-shaped target (``agent_profile:ryan``)           raw
                                                          ``pydantic_core``
                                                          ``ValidationError``
D4   ``mission_types`` / ``glossary_packs`` node          raw ``KeyError`` —
                                                          2 of 12 canonical
                                                          plural kinds unmapped
D5   field-projection auto-emitted edge                   dropped: 100% of the
     (URN-shaped **source**)                              legacy projection
                                                          path never landed
===  ===================================================  =====================

ADR ``2026-07-26-3`` makes this file's fixes a precondition for mission B1:
adding ``Relation.IMPACTS`` to a bridge with a silent-drop path ships a
relation that works for built-ins and silently fails for external packs.

Every test here drives the **real** transport
(:func:`doctrine.drg.merge.merge_three_layers`) — no reimplementation of the
resolution rules under test.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from doctrine.drg.merge import (
    OrgDRGConflictError,
    _bridge_org_edge_to_drg_edge,
    merge_three_layers,
)
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.org_pack_loader import OrgDRGFragment, load_org_pack

pytestmark = [pytest.mark.unit]

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _minter() -> dict[str, str]:
    """The bridge's plural -> singular URN-kind map.

    Imported lazily so this module still *collects* before WP08 lands the
    symbol — a collection error would collapse the whole red map into one
    ``ImportError`` and hide which behaviours are actually broken.
    """
    from doctrine.drg.org_pack_loader import ORG_PLURAL_TO_SINGULAR_KIND

    return ORG_PLURAL_TO_SINGULAR_KIND


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _graph(*nodes: DRGNode, edges: list[DRGEdge] | None = None) -> DRGGraph:
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-07-26T00:00:00Z",
        generated_by="test_org_drg_bridge",
        nodes=list(nodes),
        edges=list(edges or []),
    )


def _fragment(
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
    *,
    pack_name: str = "probe-pack",
) -> OrgDRGFragment:
    return OrgDRGFragment.model_validate(
        {
            "pack_name": pack_name,
            "source_kind": "local_path",
            "source_ref": f"/tmp/{pack_name}",
            "layer_index": 1,
            "nodes": nodes,
            "edges": edges,
        }
    )


def _built_in() -> DRGGraph:
    """A small built-in layer carrying one node of three distinct kinds.

    ``caveman-comments`` is deliberately a **styleguide** — it is the shape the
    in-repo ``tests/architectural/_fixtures/org_packs/example_org`` fixture
    references, and the one D2 mistranslated into ``directive:caveman-comments``.
    """
    return _graph(
        DRGNode(urn="directive:builtin-alpha", kind=NodeKind.DIRECTIVE),
        DRGNode(urn="styleguide:caveman-comments", kind=NodeKind.STYLEGUIDE),
        DRGNode(urn="agent_profile:researcher-ryan", kind=NodeKind.AGENT_PROFILE),
    )


def _org_edges(merged: DRGGraph, built_in: DRGGraph) -> list[tuple[str, str, str]]:
    """Return the ``(source, target, relation)`` triples the org layer added."""
    before = {(e.source, e.target, str(e.relation)) for e in built_in.edges}
    return [(e.source, e.target, str(e.relation)) for e in merged.edges if (e.source, e.target, str(e.relation)) not in before]


# ---------------------------------------------------------------------------
# D1 — the silent cross-layer drop (FR-010, SC-009, US3 scenario 1)
# ---------------------------------------------------------------------------


class TestUnresolvableEndpointIsNeverSilent:
    def test_builtin_source_to_pack_target_edge_raises_with_a_conflict_record(
        self,
    ) -> None:
        """A source the fragment does not declare must not vanish.

        Before WP08 :func:`_bridge_org_edge_to_drg_edge` returned ``None`` for
        any source missing from the fragment-local index and
        :func:`_merge_org_fragment` dropped it — no warning, no conflict
        record, no trace. This is the exact shape ADR 2026-07-26-3 names.
        """
        fragment = _fragment(
            [{"id": "pack-thing", "kind": "directives", "title": "Pack Thing"}],
            [
                {
                    "source": "no-such-artefact-anywhere",
                    "target": "pack-thing",
                    "relation": "requires",
                }
            ],
        )

        with pytest.raises(OrgDRGConflictError) as excinfo:
            merge_three_layers(_built_in(), [fragment], None)

        conflict_kinds = {c.kind for c in excinfo.value.conflicts}
        assert "unresolved_edge_endpoint" in conflict_kinds, f"expected an unresolved_edge_endpoint conflict record, got {sorted(conflict_kinds)}"
        offending = [c for c in excinfo.value.conflicts if c.kind == "unresolved_edge_endpoint"]
        assert offending[0].target_id == "no-such-artefact-anywhere", (
            f"the conflict must name the offending endpoint token so the pack author can find it; got {offending[0].target_id!r}"
        )
        assert offending[0].resolution_applied == "hard_fail"
        assert "org:probe-pack" in offending[0].conflicting_layers
        # The edge dict must be recoverable from the record — kind says *why*,
        # target_id says *which token*, org_value says *which edge*.
        assert offending[0].org_value["relation"] == "requires"

    def test_ambiguous_bare_endpoint_is_a_conflict_not_a_coin_flip(self) -> None:
        """A bare id matching two kinds must not resolve to an arbitrary one.

        Before WP08 the bridge answered this by construction: every unresolved
        bare target became ``directive:<id>``, so the directive interpretation
        always silently won.
        """
        built_in = _graph(
            DRGNode(urn="directive:shared-id", kind=NodeKind.DIRECTIVE),
            DRGNode(urn="tactic:shared-id", kind=NodeKind.TACTIC),
        )
        fragment = _fragment(
            [{"id": "pack-thing", "kind": "directives", "title": "Pack Thing"}],
            [
                {
                    "source": "pack-thing",
                    "target": "shared-id",
                    "relation": "requires",
                }
            ],
        )

        with pytest.raises(OrgDRGConflictError) as excinfo:
            merge_three_layers(built_in, [fragment], None)

        ambiguous = [c for c in excinfo.value.conflicts if c.kind == "ambiguous_edge_endpoint"]
        assert ambiguous, f"an id resolvable to two kinds must be reported ambiguous, not silently bound to one; got {[c.kind for c in excinfo.value.conflicts]}"
        assert ambiguous[0].target_id == "shared-id"

    def test_the_conflict_message_names_the_offending_token(self) -> None:
        """``OrgDRGConflictError``'s message must be operator-actionable."""
        fragment = _fragment(
            [{"id": "pack-thing", "kind": "directives"}],
            [
                {
                    "source": "pack-thing",
                    "target": "urn:profile:researcher-ryan",
                    "relation": "specializes_from",
                }
            ],
        )
        with pytest.raises(OrgDRGConflictError) as excinfo:
            merge_three_layers(_built_in(), [fragment], None)
        message = str(excinfo.value)
        assert "urn:profile:researcher-ryan" in message
        # ...and the remediation must address the endpoint, not tell the
        # author to "remove the override" of a thing they never overrode.
        assert "Remediation (endpoint)" in message
        assert "Remediation (override)" not in message
        assert "agent_profile:researcher-ryan" in message, "the guidance must show the shape that does resolve"

    def test_every_conflict_class_carries_a_remediation_line(self) -> None:
        """C-009 coverage gate for the remediation table.

        A conflict class with no remediation entry is a slot with no producer:
        the operator gets a class name and no way to act on it.
        """
        import typing

        from doctrine.drg.merge import _CONFLICT_REMEDIATIONS, OrgDRGConflict

        # ``from __future__ import annotations`` makes __annotations__ strings;
        # resolve them so the gate reads the real Literal members.
        hints = typing.get_type_hints(OrgDRGConflict)
        declared = set(typing.get_args(hints["kind"]))
        assert len(declared) >= 7, (
            f"floor: OrgDRGConflict.kind declares >= 7 classes, saw {declared}"
        )
        assert declared == set(_CONFLICT_REMEDIATIONS), (
            "conflict classes without operator remediation: "
            f"{sorted(declared - set(_CONFLICT_REMEDIATIONS))}; "
            "remediation entries for no conflict class: "
            f"{sorted(set(_CONFLICT_REMEDIATIONS) - declared)}"
        )


# ---------------------------------------------------------------------------
# D2 — blind re-kinding (FR-010, US3)
# ---------------------------------------------------------------------------


class TestBareTargetsAreResolvedByKindNotInvented:
    def test_bare_target_naming_a_styleguide_does_not_become_a_directive(self) -> None:
        """The in-repo ``example_org`` shape: ``sox-controls --refines--> caveman-comments``.

        ``caveman-comments`` is a styleguide. Before WP08 the bridge minted
        ``directive:caveman-comments`` — a node that exists nowhere in the
        merged graph, producing a dangling edge that every downstream traversal
        silently fails to follow.
        """
        built_in = _built_in()
        fragment = _fragment(
            [{"id": "sox-controls", "kind": "directives", "title": "SOX"}],
            [
                {
                    "source": "sox-controls",
                    "target": "caveman-comments",
                    "relation": "refines",
                }
            ],
        )

        merged = merge_three_layers(built_in, [fragment], None)

        assert _org_edges(merged, built_in) == [("directive:sox-controls", "styleguide:caveman-comments", "refines")]

    def test_no_merged_edge_endpoint_is_a_phantom_node(self) -> None:
        """Every endpoint the bridge mints must exist in the merged node set."""
        built_in = _built_in()
        fragment = _fragment(
            [{"id": "sox-controls", "kind": "directives"}],
            [
                {
                    "source": "sox-controls",
                    "target": "caveman-comments",
                    "relation": "refines",
                },
                {
                    "source": "sox-controls",
                    "target": "builtin-alpha",
                    "relation": "requires",
                },
            ],
        )

        merged = merge_three_layers(built_in, [fragment], None)

        urns = {n.urn for n in merged.nodes}
        dangling = [(e.source, e.target) for e in merged.edges if e.source not in urns or e.target not in urns]
        assert dangling == [], f"bridge minted phantom endpoints: {dangling}"


# ---------------------------------------------------------------------------
# D3 — URN-shaped endpoints (FR-010, US3 scenario 3)
# ---------------------------------------------------------------------------


class TestUrnShapedEndpoints:
    def test_urn_shaped_target_resolves_verbatim(self) -> None:
        """A fully-qualified target is unambiguous — accept it as authored.

        Before WP08 it was re-kinded to ``directive:agent_profile:researcher-ryan``,
        which fails ``DRGEdge``'s URN regex and escaped as a raw
        ``pydantic_core.ValidationError`` from deep inside the merge.
        """
        built_in = _built_in()
        fragment = _fragment(
            [{"id": "my-analyst", "kind": "agent_profiles", "title": "Analyst"}],
            [
                {
                    "source": "my-analyst",
                    "target": "agent_profile:researcher-ryan",
                    "relation": "specializes_from",
                }
            ],
        )

        merged = merge_three_layers(built_in, [fragment], None)

        assert _org_edges(merged, built_in) == [
            (
                "agent_profile:my-analyst",
                "agent_profile:researcher-ryan",
                "specializes_from",
            )
        ]

    def test_urn_shaped_source_resolves_verbatim(self) -> None:
        """Symmetry: source and target obey one resolution policy, not two.

        The asymmetry (source = fragment-local-only, target = fragment-local
        or invented) is the structural cause of D1 and D5.
        """
        built_in = _built_in()
        fragment = _fragment(
            [{"id": "my-analyst", "kind": "agent_profiles"}],
            [
                {
                    "source": "agent_profile:my-analyst",
                    "target": "agent_profile:researcher-ryan",
                    "relation": "specializes_from",
                }
            ],
        )

        merged = merge_three_layers(built_in, [fragment], None)

        assert _org_edges(merged, built_in) == [
            (
                "agent_profile:my-analyst",
                "agent_profile:researcher-ryan",
                "specializes_from",
            )
        ]

    @pytest.mark.parametrize(
        ("target", "expected_kind"),
        [
            # Illegal character in the id half: URN-shaped, valid kind prefix,
            # unparseable => malformed, not "not found".
            ("agent_profile:has space", "malformed_urn"),
            # A kind prefix that is not a NodeKind member: the author used a
            # vocabulary that does not exist (this is the CLAUDE.md shape).
            ("urn:profile:researcher-ryan", "unresolved_edge_endpoint"),
            ("nosuchkind:whatever", "unresolved_edge_endpoint"),
        ],
    )
    def test_unresolvable_urn_shaped_target_raises_a_typed_pack_error(self, target: str, expected_kind: str) -> None:
        """US3 scenario 3 — a typed pack error, never a raw pydantic error."""
        fragment = _fragment(
            [{"id": "my-analyst", "kind": "agent_profiles"}],
            [
                {
                    "source": "my-analyst",
                    "target": target,
                    "relation": "specializes_from",
                }
            ],
        )

        with pytest.raises(OrgDRGConflictError) as excinfo:
            merge_three_layers(_built_in(), [fragment], None)

        matching = [c for c in excinfo.value.conflicts if c.target_id == target]
        assert matching, f"no conflict record named {target!r}"
        assert matching[0].kind == expected_kind

    def test_a_node_id_that_cannot_form_a_urn_is_a_typed_pack_error(self) -> None:
        """The same guarantee on the node side of the bridge.

        ``_OrgDRGNode.id`` is a free-form ``str``, so a pack could always mint
        an unparseable URN. Before WP08 that escaped as a raw
        ``pydantic_core.ValidationError`` from ``_bridge_org_node_to_drg_node``.
        """
        fragment = _fragment([{"id": "has space", "kind": "directives"}], [])

        with pytest.raises(OrgDRGConflictError) as excinfo:
            merge_three_layers(_built_in(), [fragment], None)

        assert [c.kind for c in excinfo.value.conflicts] == ["malformed_urn"]
        assert excinfo.value.conflicts[0].target_id == "directive:has space"


# ---------------------------------------------------------------------------
# D4 — plural-kind coverage is derived, not hand-restated (FR-010, C-009)
# ---------------------------------------------------------------------------


class TestPluralKindCoverageIsTotal:
    """The bridge's URN minter is the **fourth** hand-restated DRG writer.

    ``merge._PLURAL_TO_SINGULAR`` restated the org-pack plural universe by
    hand and had drifted 2 kinds behind ``_ORG_DRG_KIND_ALIASES``. WP04 fixed
    the same class in the extractor by deriving from ``NodeKind``; this does
    it for the bridge by deriving from the loader's own alias table.
    """

    def test_every_accepted_org_pack_plural_kind_mints_a_urn(self) -> None:
        """The coverage gate (C-009). Concrete floor: all 12 canonical kinds.

        Drives the real merge per kind, so the gate fails on a *behavioural*
        gap, not merely a missing dict key.
        """
        from doctrine.drg.org_pack_loader import _ORG_DRG_KIND_ALIASES

        accepted = sorted(_ORG_DRG_KIND_ALIASES)
        assert len(accepted) >= 12, "floor: the loader accepts >= 12 input forms"

        failures: dict[str, str] = {}
        for plural in accepted:
            fragment = _fragment([{"id": "probe-node", "kind": plural}], [])
            try:
                merged = merge_three_layers(_graph(), [fragment], None)
            except Exception as exc:  # noqa: BLE001 - the gate reports the class
                failures[plural] = f"{type(exc).__name__}: {exc}"
                continue
            if len(merged.nodes) != 1:
                failures[plural] = f"minted {len(merged.nodes)} nodes"
        assert failures == {}, f"org-pack plural kinds the bridge cannot mint a URN for (hand-restated map drifted behind the loader universe): {failures}"

    def test_the_minter_is_derived_from_the_loader_universe(self) -> None:
        """Totality by construction — the property that keeps the gate honest.

        Equality (not containment) in both directions: a canonical kind
        added to the loader but not the minter fails, and a minter entry that
        no canonical kind resolves to fails too — no dead map entries.
        """
        from doctrine.drg.org_pack_loader import _ORG_DRG_KIND_ALIASES

        assert set(_minter()) == set(_ORG_DRG_KIND_ALIASES.values())

    def test_every_minted_singular_is_a_real_nodekind(self) -> None:
        """A singular with no ``NodeKind`` member would fail at ``NodeKind(...)``."""
        node_kinds = {k.value for k in NodeKind}
        assert set(_minter().values()) <= node_kinds

    def test_the_coverage_gate_would_catch_a_reintroduced_gap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Self-mutation (standing order 5): prove the gate can fail.

        Delete one kind from the derived minter and assert the merge for that
        kind now fails — i.e. the gate above is load-bearing, not decorative.
        """
        mutated = dict(_minter())
        removed = mutated.pop("mission_types")
        assert removed == "mission_type"
        monkeypatch.setattr("doctrine.drg.merge.ORG_PLURAL_TO_SINGULAR_KIND", mutated, raising=True)

        fragment = _fragment([{"id": "probe-node", "kind": "mission_types"}], [])
        with pytest.raises(OrgDRGConflictError) as excinfo:
            merge_three_layers(_graph(), [fragment], None)
        assert [c.kind for c in excinfo.value.conflicts] == ["kind_mismatch"]

    def test_an_unmappable_plural_kind_is_a_typed_conflict_not_a_keyerror(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Even the impossible branch fails typed. D4's raw ``KeyError`` is gone."""
        monkeypatch.setattr("doctrine.drg.merge.ORG_PLURAL_TO_SINGULAR_KIND", {})
        fragment = _fragment([{"id": "probe-node", "kind": "directives"}], [])
        with pytest.raises(OrgDRGConflictError):
            merge_three_layers(_graph(), [fragment], None)


# ---------------------------------------------------------------------------
# D5 — the field-projection producer whose output never landed
# ---------------------------------------------------------------------------


class TestFieldProjectionEdgesReachTheGraph:
    """``_collect_augmentation_edges`` emits ``<kind>:<id>`` on **both**
    endpoints. The bridge's source lookup was keyed on bare fragment-local ids
    only, so 100% of that producer's output was discarded at the bridge — a
    zero-effect producer, the mission's own defect class one layer up.
    """

    def test_auto_emitted_projection_edge_survives_the_bridge(self, tmp_path: Path) -> None:
        pack = tmp_path / "proj-pack"
        (pack / "drg").mkdir(parents=True)
        (pack / "agent_profiles").mkdir()
        (pack / "drg" / "fragment.yaml").write_text(
            "pack_name: proj-pack\n"
            "source_kind: local_path\n"
            "source_ref: proj-pack\n"
            "layer_index: 1\n"
            "provenance_marker: org\n"
            "nodes:\n"
            "  - id: my-analyst\n"
            "    kind: agent_profiles\n"
            "    title: My Analyst\n"
            "edges: []\n",
            encoding="utf-8",
        )
        (pack / "agent_profiles" / "my-analyst.agent.yaml").write_text("id: my-analyst\nspecializes_from: researcher-ryan\n", encoding="utf-8")

        fragment = load_org_pack("proj-pack", pack, 1)
        assert [(e.source, e.target) for e in fragment.edges] == [("agent_profile:my-analyst", "agent_profile:researcher-ryan")], (
            "precondition: the projection path emits URN-shaped endpoints"
        )

        built_in = _built_in()
        merged = merge_three_layers(built_in, [fragment], None)

        assert _org_edges(merged, built_in) == [
            (
                "agent_profile:my-analyst",
                "agent_profile:researcher-ryan",
                "specializes_from",
            )
        ]


# ---------------------------------------------------------------------------
# FR-011 — the documented snippet must produce an edge
# ---------------------------------------------------------------------------


def _claude_md_lineage_snippet() -> dict[str, Any]:
    """Extract the ``specializes_from`` YAML block from ``CLAUDE.md``.

    Reading the doc (rather than restating it) is what makes this test a
    guard: the snippet cannot drift back to an inert shape without going red.
    """
    text = (_REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    heading = "### `specializes_from` DRG Lineage"
    assert heading in text, "the documented lineage section moved or was renamed"
    after = text.split(heading, 1)[1]
    match = re.search(r"```yaml\n(.*?)```", after, re.DOTALL)
    assert match is not None, "no YAML snippet follows the lineage heading"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict) and parsed.get("edges"), f"the documented snippet is not an edges: block: {parsed!r}"
    return parsed


class TestDocumentedLineageSnippet:
    def test_the_claude_md_snippet_produces_an_edge(self) -> None:
        """US3 scenario 2 / SC-009 — a reader who follows the doc gets an edge.

        The shipped ``urn:profile:`` shape appears nowhere in the DRG
        vocabulary: ``urn`` is not a ``NodeKind``, so both endpoints failed to
        resolve and the edge was dropped in silence. Documentation that yields
        an inert declaration.
        """
        snippet = _claude_md_lineage_snippet()
        fragment = _fragment(
            [{"id": "my-analyst", "kind": "agent_profiles", "title": "My Analyst"}],
            snippet["edges"],
            pack_name="documented-pack",
        )

        built_in = _built_in()
        merged = merge_three_layers(built_in, [fragment], None)

        emitted = _org_edges(merged, built_in)
        assert len(emitted) == 1, f"the documented snippet must yield exactly one edge, got {emitted}"
        source, target, relation = emitted[0]
        assert relation == Relation.SPECIALIZES_FROM.value
        assert source.startswith("agent_profile:")
        assert target == "agent_profile:researcher-ryan"

    def test_the_documented_endpoints_use_a_real_nodekind_prefix(self) -> None:
        """The narrow, fast guard against the exact retired shape."""
        snippet = _claude_md_lineage_snippet()
        kinds = {k.value for k in NodeKind}
        for edge in snippet["edges"]:
            for endpoint in (edge["source"], edge["target"]):
                prefix = endpoint.split(":", 1)[0]
                assert prefix in kinds, f"documented endpoint {endpoint!r} uses prefix {prefix!r}, which is not a NodeKind — the bridge cannot resolve it"


# ---------------------------------------------------------------------------
# Regression floor for the resolution policy itself
# ---------------------------------------------------------------------------


class TestResolutionPrecedence:
    def test_fragment_local_id_wins_over_a_same_named_builtin(self) -> None:
        """A pack's own node is the nearest scope for a bare id it declared."""
        built_in = _graph(DRGNode(urn="tactic:shared", kind=NodeKind.TACTIC))
        fragment = _fragment(
            [
                {"id": "shared", "kind": "directives"},
                {"id": "other", "kind": "directives"},
            ],
            [{"source": "other", "target": "shared", "relation": "requires"}],
        )

        merged = merge_three_layers(built_in, [fragment], None)

        assert _org_edges(merged, built_in) == [("directive:other", "directive:shared", "requires")]

    def test_the_bridge_helper_reports_the_unresolved_endpoint_directly(self) -> None:
        """Unit-level floor on the helper the merge delegates to."""
        resolved, conflict = _bridge_org_edge_to_drg_edge(
            _fragment(
                [{"id": "a", "kind": "directives"}],
                [{"source": "a", "target": "ghost", "relation": "requires"}],
            ).edges[0],
            {"a": "directive:a"},
            {"directive:a"},
            "org:probe-pack",
        )
        assert resolved is None
        assert conflict is not None
        assert conflict.kind == "unresolved_edge_endpoint"
        assert conflict.target_id == "ghost"
