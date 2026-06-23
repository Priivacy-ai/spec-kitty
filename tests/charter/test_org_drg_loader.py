"""Unit coverage for the Slice F WP06 org-DRG loader + merge (T033).

Owner: ``src/charter/drg.py`` (Slice F WP06).

Covers loader edge cases (no config; multi-pack declaration order;
missing local_path → ``OrgPackMissingError``; ``source: url|package`` →
``NotImplementedError``); schema validation (8-kind C-009 enforcement);
merge edge cases (provenance threading; layer-rule hard-fail;
shipped-invariant hard-fail; backward-compat empty-org case).
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pydantic
import pytest

from charter.drg import (
    DRGEdge,
    DRGGraph,
    DRGNode,
    NodeKind,
    OrgDRGConflictError,
    OrgDRGFragment,
    OrgPackMissingError,
    Relation,
    UnknownRelationError,
    load_org_drg,
    merge_three_layers,
)


pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_built_in() -> DRGGraph:
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-05-18T00:00:00Z",
        generated_by="unit-test",
        nodes=[],
        edges=[],
    )


def _built_in_with_node(urn: str = "directive:caveman-comments") -> DRGGraph:
    return DRGGraph(
        schema_version="1.0",
        generated_at="2026-05-18T00:00:00Z",
        generated_by="unit-test",
        nodes=[DRGNode(urn=urn, kind=NodeKind.DIRECTIVE)],
        edges=[],
    )


def _make_pack(tmp_path: Path, name: str, *, fragment_yaml: str | None = None) -> Path:
    pack_dir = tmp_path / name
    drg_dir = pack_dir / "drg"
    drg_dir.mkdir(parents=True)
    payload = fragment_yaml if fragment_yaml is not None else dedent(
        f"""\
        pack_name: {name}
        source_kind: local_path
        source_ref: {pack_dir}
        layer_index: 1
        provenance_marker: org
        nodes:
          - id: pack-{name}-node
            kind: directives
            title: "Fixture directive for {name}"
        edges: []
        """
    )
    (drg_dir / "fragment.yaml").write_text(payload)
    return pack_dir


def _make_config(tmp_path: Path, body: str) -> None:
    kittify = tmp_path / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(body)


# ---------------------------------------------------------------------------
# OrgDRGFragment schema (C-009)
# ---------------------------------------------------------------------------


class TestOrgDRGFragmentSchema:
    """C-009 binding: the 8-kind plural universe is fully reused; unknown
    kinds raise ``pydantic.ValidationError`` (the FR-140 round-trip gate
    asserts this on the contract's invalid example)."""

    @pytest.mark.parametrize(
        "kind",
        [
            "directives",
            "tactics",
            "styleguides",
            "toolguides",
            "paradigms",
            "procedures",
            "agent_profiles",
            "mission_step_contracts",
        ],
    )
    def test_all_8_canonical_kinds_validate(self, kind: str) -> None:
        OrgDRGFragment.model_validate(
            {
                "pack_name": "acme",
                "source_kind": "local_path",
                "source_ref": "/tmp/acme",
                "layer_index": 1,
                "provenance_marker": "org",
                "nodes": [
                    {"id": f"x-{kind}", "kind": kind, "title": kind}
                ],
                "edges": [],
            }
        )

    def test_unknown_kind_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            OrgDRGFragment.model_validate(
                {
                    "pack_name": "acme",
                    "source_kind": "local_path",
                    "source_ref": "/tmp/acme",
                    "layer_index": 1,
                    "provenance_marker": "org",
                    "nodes": [
                        {"id": "x", "kind": "frobnications", "title": "X"}
                    ],
                    "edges": [],
                }
            )
        assert "unknown kind" in str(exc_info.value)

    def test_extra_top_level_field_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            OrgDRGFragment.model_validate(
                {
                    "pack_name": "acme",
                    "source_kind": "local_path",
                    "source_ref": "/tmp/acme",
                    "layer_index": 1,
                    "provenance_marker": "org",
                    "nodes": [],
                    "edges": [],
                    "rogue_field": "smuggle",
                }
            )

    def test_layer_index_must_be_positive(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            OrgDRGFragment.model_validate(
                {
                    "pack_name": "acme",
                    "source_kind": "local_path",
                    "source_ref": "/tmp/acme",
                    "layer_index": 0,
                    "provenance_marker": "org",
                    "nodes": [],
                    "edges": [],
                }
            )


# ---------------------------------------------------------------------------
# load_org_drg
# ---------------------------------------------------------------------------


class TestLoadOrgDrg:
    def test_no_config_returns_empty_list(self, tmp_path: Path) -> None:
        """NFR-001 backward compatibility — repos with no .kittify/config.yaml
        behave identically to today (no org layer)."""
        assert load_org_drg(tmp_path) == []

    def test_empty_organisation_packs_returns_empty_list(self, tmp_path: Path) -> None:
        _make_config(tmp_path, "organisation_packs: []\n")
        assert load_org_drg(tmp_path) == []

    def test_missing_organisation_packs_key_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        _make_config(tmp_path, "other_setting: value\n")
        assert load_org_drg(tmp_path) == []

    def test_one_fragment_per_configured_pack_in_declaration_order(
        self, tmp_path: Path
    ) -> None:
        pack_a = _make_pack(tmp_path, "alpha")
        pack_b = _make_pack(tmp_path, "bravo")
        _make_config(
            tmp_path,
            dedent(
                f"""\
                organisation_packs:
                  - name: alpha
                    source: local_path
                    path: {pack_a}
                  - name: bravo
                    source: local_path
                    path: {pack_b}
                """
            ),
        )
        fragments = load_org_drg(tmp_path)
        assert [f.pack_name for f in fragments] == ["alpha", "bravo"]
        assert [f.layer_index for f in fragments] == [1, 2]

    def test_missing_local_path_raises_named_error(self, tmp_path: Path) -> None:
        """FR-004: hard-fail on missing local_path with operator-actionable
        error naming pack + path."""
        _make_config(
            tmp_path,
            dedent(
                f"""\
                organisation_packs:
                  - name: vanished
                    source: local_path
                    path: {tmp_path}/no-such-dir
                """
            ),
        )
        with pytest.raises(OrgPackMissingError) as exc_info:
            load_org_drg(tmp_path)
        assert exc_info.value.pack_name == "vanished"
        assert "no-such-dir" in exc_info.value.configured_path
        assert "vanished" in str(exc_info.value)
        assert "no-such-dir" in str(exc_info.value)

    def test_missing_fragment_yaml_raises_named_error(self, tmp_path: Path) -> None:
        """Even when local_path exists, an empty pack (no drg/fragment.yaml)
        is treated as missing — the loader can't produce a fragment from
        nothing."""
        pack_dir = tmp_path / "empty-pack"
        pack_dir.mkdir()
        _make_config(
            tmp_path,
            dedent(
                f"""\
                organisation_packs:
                  - name: empty-pack
                    source: local_path
                    path: {pack_dir}
                """
            ),
        )
        with pytest.raises(OrgPackMissingError) as exc_info:
            load_org_drg(tmp_path)
        assert "empty-pack" in str(exc_info.value)
        assert "fragment.yaml" in str(exc_info.value)

    def test_source_url_not_yet_implemented(self, tmp_path: Path) -> None:
        """NEW-1 — only ``local_path`` ships in this mission."""
        _make_config(
            tmp_path,
            dedent(
                """\
                organisation_packs:
                  - name: remote-pack
                    source: url
                    path: https://example.org/pack
                """
            ),
        )
        with pytest.raises(NotImplementedError) as exc_info:
            load_org_drg(tmp_path)
        assert "url" in str(exc_info.value)

    def test_source_package_not_yet_implemented(self, tmp_path: Path) -> None:
        """NEW-1 — package sources are reserved."""
        _make_config(
            tmp_path,
            dedent(
                """\
                organisation_packs:
                  - name: pypi-pack
                    source: package
                    path: some-pypi-name
                """
            ),
        )
        with pytest.raises(NotImplementedError) as exc_info:
            load_org_drg(tmp_path)
        assert "package" in str(exc_info.value)

    def test_relative_path_resolved_against_repo_root(self, tmp_path: Path) -> None:
        _make_pack(tmp_path, "rel-pack")
        _make_config(
            tmp_path,
            dedent(
                """\
                organisation_packs:
                  - name: rel-pack
                    source: local_path
                    path: rel-pack
                """
            ),
        )
        fragments = load_org_drg(tmp_path)
        assert len(fragments) == 1
        assert "rel-pack" in fragments[0].source_ref

    def test_operator_config_wins_over_pack_side_fields(self, tmp_path: Path) -> None:
        """The loader overrides pack-side declared ``pack_name`` /
        ``layer_index`` / ``source_kind`` / ``source_ref`` with operator
        config values so a renamed/relocated pack stays consistent."""
        pack_dir = _make_pack(
            tmp_path,
            "alpha",
            fragment_yaml=dedent(
                """\
                pack_name: WRONG-NAME-FROM-PACK
                source_kind: local_path
                source_ref: /nonsense
                layer_index: 99
                provenance_marker: org
                nodes: []
                edges: []
                """
            ),
        )
        _make_config(
            tmp_path,
            dedent(
                f"""\
                organisation_packs:
                  - name: operator-name
                    source: local_path
                    path: {pack_dir}
                """
            ),
        )
        fragments = load_org_drg(tmp_path)
        assert fragments[0].pack_name == "operator-name"
        assert fragments[0].layer_index == 1
        assert fragments[0].source_kind == "local_path"


# ---------------------------------------------------------------------------
# merge_three_layers
# ---------------------------------------------------------------------------


class TestMergeThreeLayers:
    def test_empty_inputs_round_trip(self) -> None:
        built_in = _empty_built_in()
        merged = merge_three_layers(built_in=built_in, org_fragments=[], project=None)
        assert merged.nodes == []
        assert merged.edges == []

    def test_every_shipped_node_tagged_built_in(self) -> None:
        built_in = _built_in_with_node("directive:foo")
        merged = merge_three_layers(built_in=built_in, org_fragments=[], project=None)
        assert all(
            getattr(n, "provenance", None) == "built-in" for n in merged.nodes
        )

    def test_org_fragment_nodes_tagged_with_pack_name(self) -> None:
        built_in = _empty_built_in()
        fragment = OrgDRGFragment.model_validate(
            {
                "pack_name": "acme",
                "source_kind": "local_path",
                "source_ref": "/tmp/acme",
                "layer_index": 1,
                "provenance_marker": "org",
                "nodes": [
                    {"id": "policy", "kind": "directives", "title": "Policy"}
                ],
                "edges": [],
            }
        )
        merged = merge_three_layers(
            built_in=built_in, org_fragments=[fragment], project=None
        )
        assert any(
            getattr(n, "provenance", None) == "org:acme" for n in merged.nodes
        )

    def test_org_fragment_mission_step_contract_node_merges(self) -> None:
        built_in = _empty_built_in()
        fragment = OrgDRGFragment.model_validate(
            {
                "pack_name": "mission-pack",
                "source_kind": "local_path",
                "source_ref": "/tmp/mission-pack",
                "layer_index": 1,
                "provenance_marker": "org",
                "nodes": [
                    {
                        "id": "implement-step",
                        "kind": "mission_step_contracts",
                        "title": "Implement step",
                    }
                ],
                "edges": [],
            }
        )

        merged = merge_three_layers(
            built_in=built_in, org_fragments=[fragment], project=None
        )

        node = merged.get_node("mission_step_contract:implement-step")
        assert node is not None
        assert node.kind is NodeKind.MISSION_STEP_CONTRACT
        assert getattr(node, "provenance", None) == "org:mission-pack"

    def test_project_layer_nodes_tagged_project(self) -> None:
        built_in = _empty_built_in()
        project = DRGGraph(
            schema_version="1.0",
            generated_at="2026-05-18T00:00:00Z",
            generated_by="unit-test",
            nodes=[DRGNode(urn="tactic:project-only", kind=NodeKind.TACTIC)],
            edges=[],
        )
        merged = merge_three_layers(
            built_in=built_in, org_fragments=[], project=project
        )
        assert any(getattr(n, "provenance", None) == "project" for n in merged.nodes)

    def test_shipped_invariant_override_is_permitted_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An org pack overriding a shipped node URN is PERMITTED by the merge
        but surfaced as a WARNING (visible by design; a per-repo governance test
        decides sanction). Retired the prior hard-fail ``OrgDRGConflictError``
        expectation when the merge moved to warn-not-raise."""
        import logging  # noqa: PLC0415

        built_in = _built_in_with_node("directive:caveman-comments")
        fragment = OrgDRGFragment.model_validate(
            {
                "pack_name": "rogue",
                "source_kind": "local_path",
                "source_ref": "/tmp/rogue",
                "layer_index": 1,
                "provenance_marker": "org",
                "nodes": [
                    {
                        "id": "caveman-comments",
                        "kind": "directives",
                        "title": "Override",
                    }
                ],
                "edges": [],
            }
        )
        with caplog.at_level(logging.WARNING, logger="doctrine.drg.merge"):
            merged = merge_three_layers(
                built_in=built_in, org_fragments=[fragment], project=None
            )
        assert merged is not None
        override_warnings = [
            rec.getMessage()
            for rec in caplog.records
            if rec.levelno == logging.WARNING
            and "caveman-comments" in rec.getMessage()
            and "override" in rec.getMessage().lower()
        ]
        assert override_warnings, (
            "expected a same-kind-override WARNING naming 'caveman-comments', "
            f"got {[r.getMessage() for r in caplog.records]}"
        )

    def test_layer_rule_violation_hard_fails(self) -> None:
        """FR-005 / C-001: org node body_path into ``src/specify_cli/`` is
        a layer-rule violation regardless of any shipped collision."""
        built_in = _empty_built_in()
        fragment = OrgDRGFragment.model_validate(
            {
                "pack_name": "smuggler",
                "source_kind": "local_path",
                "source_ref": "/tmp/smuggler",
                "layer_index": 1,
                "provenance_marker": "org",
                "nodes": [
                    {
                        "id": "x",
                        "kind": "tactics",
                        "title": "X",
                        "body_path": "src/specify_cli/sneaky.py",
                    }
                ],
                "edges": [],
            }
        )
        with pytest.raises(OrgDRGConflictError) as exc_info:
            merge_three_layers(
                built_in=built_in, org_fragments=[fragment], project=None
            )
        assert any(
            c.kind == "layer_rule_violation" for c in exc_info.value.conflicts
        )

    def test_org_edge_tagged_with_pack_name(self) -> None:
        built_in = _empty_built_in()
        fragment = OrgDRGFragment.model_validate(
            {
                "pack_name": "edge-pack",
                "source_kind": "local_path",
                "source_ref": "/tmp/edge-pack",
                "layer_index": 1,
                "provenance_marker": "org",
                "nodes": [
                    {"id": "a", "kind": "directives", "title": "A"},
                    {"id": "b", "kind": "tactics", "title": "B"},
                ],
                "edges": [
                    {"source": "a", "target": "b", "relation": "requires"},
                ],
            }
        )
        merged = merge_three_layers(
            built_in=built_in, org_fragments=[fragment], project=None
        )
        org_edges = [
            e for e in merged.edges if getattr(e, "provenance", None) == "org:edge-pack"
        ]
        assert len(org_edges) == 1
        assert org_edges[0].relation == Relation.REQUIRES

    def test_org_to_shipped_edge_targets_synthesized_urn(self) -> None:
        """Edges from an org fragment may point at shipped artefacts; the
        merge synthesises a URN for the target so the edge isn't dropped."""
        built_in = _empty_built_in()
        fragment = OrgDRGFragment.model_validate(
            {
                "pack_name": "cross-pack",
                "source_kind": "local_path",
                "source_ref": "/tmp/cross-pack",
                "layer_index": 1,
                "provenance_marker": "org",
                "nodes": [
                    {"id": "policy", "kind": "directives", "title": "Policy"},
                ],
                "edges": [
                    # target 'caveman-comments' is not in this fragment;
                    # bridge synthesises 'directive:caveman-comments'
                    {
                        "source": "policy",
                        "target": "caveman-comments",
                        "relation": "applies",
                    },
                ],
            }
        )
        merged = merge_three_layers(
            built_in=built_in, org_fragments=[fragment], project=None
        )
        cross_edges = [
            e for e in merged.edges if e.target == "directive:caveman-comments"
        ]
        assert len(cross_edges) == 1

    def test_edge_with_unknown_relation_raises(self) -> None:
        """FR-003 / C0.3 (mission
        ``org-doctrine-profile-integrity-activation-closure-01KT1TV1`` WP03):
        an unknown relation label now fails closed with a structured
        :class:`UnknownRelationError` instead of being silently dropped.

        This supersedes the pre-WP03 ``..._dropped_silently`` contract: the
        org-fragment path previously returned ``None`` for an unrecognised
        relation, dropping the edge without trace, while the project-fragment
        Pydantic path rejected the same input loudly. WP03 normalises that
        asymmetry — shipped, org, and project fragments now reject an unknown
        relation identically. The raised error names the offending relation,
        the source fragment, and the valid token set.
        """
        built_in = _empty_built_in()
        fragment = OrgDRGFragment.model_validate(
            {
                "pack_name": "rel-pack",
                "source_kind": "local_path",
                "source_ref": "/tmp/rel-pack",
                "layer_index": 1,
                "provenance_marker": "org",
                "nodes": [
                    {"id": "a", "kind": "directives", "title": "A"},
                    {"id": "b", "kind": "tactics", "title": "B"},
                ],
                "edges": [
                    {"source": "a", "target": "b", "relation": "frobnicates"},
                ],
            }
        )
        with pytest.raises(UnknownRelationError) as exc_info:
            merge_three_layers(
                built_in=built_in, org_fragments=[fragment], project=None
            )
        assert exc_info.value.relation == "frobnicates"
        assert "rel-pack" in exc_info.value.source_marker
        assert "frobnicates" in str(exc_info.value)

    def test_multiple_conflict_kinds_reported_together(self) -> None:
        """``OrgDRGConflictError.conflicts`` lists every conflict so
        operators see the full picture in one hard-fail."""
        built_in = _built_in_with_node("directive:invariant-x")
        fragment = OrgDRGFragment.model_validate(
            {
                "pack_name": "bad-pack",
                "source_kind": "local_path",
                "source_ref": "/tmp/bad-pack",
                "layer_index": 1,
                "provenance_marker": "org",
                "nodes": [
                    {
                        "id": "invariant-x",
                        "kind": "directives",
                        "title": "shadow",
                    },
                    {
                        "id": "y",
                        "kind": "tactics",
                        "title": "Y",
                        "body_path": "src/specify_cli/y.py",
                    },
                ],
                "edges": [],
            }
        )
        with pytest.raises(OrgDRGConflictError) as exc_info:
            merge_three_layers(
                built_in=built_in, org_fragments=[fragment], project=None
            )
        kinds = {c.kind for c in exc_info.value.conflicts}
        assert {"node_override", "layer_rule_violation"} <= kinds


def test_drg_models_remain_re_exported() -> None:
    """Sanity: the facade still re-exports the legacy DRG models so
    pre-existing callers (calibration walker, glossary drg_builder,
    mission_step_contracts executor) keep working."""
    assert DRGEdge is not None
    assert DRGGraph is not None
    assert DRGNode is not None
    assert NodeKind is not None
    assert Relation is not None
