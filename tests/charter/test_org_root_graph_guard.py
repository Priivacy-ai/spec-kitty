"""Org pack DRG root-graph guard regression tests (#3384, mission
``org-pack-drg-root-graph-guard-01KZY0QT``).

Issue #3384: declaring an org doctrine pack whose only DRG content lives at
``<org_root>/drg/*.graph.yaml`` -- the **only** layout the shipped authoring
guide (``docs/guides/how-to/governance/create-an-org-doctrine-pack.md``)
documents -- silently zeroed every action-scoped
directive/tactic/styleguide/toolguide/procedure count the moment the pack
was declared, because ``_drg_helpers.py``'s ``load_validated_graph`` called
``load_graph_or_dir(org_root)`` unconditionally whenever ``org_root.exists()``,
with no check for whether ``org_root`` (or its ``drg/`` subdirectory) actually
contained a loadable graph. ``load_graph_or_dir`` raises ``DRGLoadError`` on a
directory with no root-level graph file, and the caller's wide
``except DRGLoadError`` in ``_load_action_doctrine_bundle`` collapsed the
*entire* resolved action bundle to empty, logging only a WARNING.

``--json`` procedure-count carve-out (spec ruling SPEC-FRESH4-001, binding):
``charter context --action <a> --json`` exposes typed arrays for
``directives``/``tactics``/``styleguides``/``toolguides`` only -- never a
``procedures`` array. Every assertion about a procedure count in this module
goes through the **plain-text render** (``charter.context.build_charter_context``
/ ``result.text``, whose Procedures section is emitted by
``src/charter/context_renderers/bootstrap_text.py``), never the ``--json``
payload.

Fixtures are built inline with ``tmp_path`` (no committed fixture files under
``tests/charter/fixtures/``), mirroring the conventions already used by
``test_merged_graph_on_live_path.py`` (patch ``charter._drg_helpers.
load_built_in_graph`` to inject a small fixture built-in graph) and
``test_context_org_governance.py`` (declare an org pack via
``.kittify/config.yaml``'s ``doctrine.org.packs`` list, resolved through
``charter.drg.resolve_org_roots``).
"""

from __future__ import annotations

import json
import textwrap
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from doctrine.drg.models import DRGGraph

pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_MISSION_TYPE = "software-dev"
_ACTION = "implement"
_ACTION_URN = f"action:{_MISSION_TYPE}/{_ACTION}"

_CHARTER_MD = textwrap.dedent(
    """\
    # Test Charter

    ## Policy Summary

    - Intent: deterministic delivery
    """
)

_GOVERNANCE_YAML = textwrap.dedent(
    """\
    doctrine:
      template_set: software-dev-default
      selected_paradigms: []
      selected_directives: []
      available_tools: []
    """
)

#: Small fixture built-in graph -- patched in for ``load_built_in_graph`` so
#: every test is isolated from the ~600-node shipped built-in graph. Carries
#: exactly one baseline directive AND one baseline procedure, each scoped
#: from the resolved action, so the no-pack baseline is non-zero for BOTH
#: the four ``--json``-typed kinds and the plain-text-only procedure count
#: (a non-vacuous floor for the ">=" assertions below -- an all-zero
#: baseline would let a still-broken fix pass by accident; PR-TESTS-001, R3
#: confirmed -- this fixture previously declared zero procedure nodes, so
#: every procedure "with-pack >= baseline" comparison was ">= 0", vacuously
#: true even with procedure delivery completely broken).
_BUILT_IN_DIRECTIVE_ID = "builtin-baseline-directive"
_BUILT_IN_PROCEDURE_ID = "builtin-baseline-procedure"
_BUILT_IN_GRAPH_YAML = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {{urn: '{_ACTION_URN}', kind: action}}
      - {{urn: 'directive:{_BUILT_IN_DIRECTIVE_ID}', kind: directive}}
      - {{urn: 'procedure:{_BUILT_IN_PROCEDURE_ID}', kind: procedure}}
    edges:
      - {{source: '{_ACTION_URN}', target: 'directive:{_BUILT_IN_DIRECTIVE_ID}', relation: scope}}
      - {{source: '{_ACTION_URN}', target: 'procedure:{_BUILT_IN_PROCEDURE_ID}', relation: scope}}
    """
)

#: A guide-compliant org pack fragment: content lives ONLY under
#: ``drg/fixture.graph.yaml`` (no root-level ``graph.yaml``/``*.graph.yaml``).
#: Declares one tactic and one procedure node, each scoped from the resolved
#: action, so both the ``--json`` tactics assertion and the plain-text
#: procedures assertion have a concrete, non-vacuous target.
_ORG_DRG_TACTIC_ID = "org-drg-tactic-3384"
_ORG_DRG_PROCEDURE_ID = "org-drg-procedure-3384"
_ORG_DRG_FRAGMENT_YAML = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {{urn: 'tactic:{_ORG_DRG_TACTIC_ID}', kind: tactic}}
      - {{urn: 'procedure:{_ORG_DRG_PROCEDURE_ID}', kind: procedure}}
    edges:
      - {{source: '{_ACTION_URN}', target: 'tactic:{_ORG_DRG_TACTIC_ID}', relation: scope}}
      - {{source: '{_ACTION_URN}', target: 'procedure:{_ORG_DRG_PROCEDURE_ID}', relation: scope}}
    """
)

_TYPED_COUNT_KEYS = ("directives", "tactics", "styleguides", "toolguides")


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _graph_from_yaml(text: str) -> DRGGraph:
    """Parse *text* (a ``graph.yaml`` document) into a validated ``DRGGraph``."""
    yaml = YAML(typ="safe")
    return DRGGraph.model_validate(yaml.load(StringIO(text)))


def _write_project_fixture(repo_root: Path) -> None:
    """Write the minimal ``.kittify/charter/`` bootstrap-mode prerequisites."""
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text(_CHARTER_MD, encoding="utf-8")
    (charter_dir / "governance.yaml").write_text(_GOVERNANCE_YAML, encoding="utf-8")


def _write_config(repo_root: Path, *, org_pack_root: Path | None) -> None:
    """Write ``.kittify/config.yaml`` with the mission type activated and,
    when *org_pack_root* is given, that path registered as the sole org pack.
    """
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {"mission_type_activations": [_MISSION_TYPE]}
    if org_pack_root is not None:
        data["doctrine"] = {
            "org": {"packs": [{"name": "guard-fixture-pack", "local_path": str(org_pack_root)}]}
        }
    with (kittify / "config.yaml").open("w", encoding="utf-8") as fh:
        YAML().dump(data, fh)


def _write_org_pack_drg_only(repo_root: Path) -> Path:
    """A guide-compliant org pack: content ONLY at ``<root>/drg/*.graph.yaml``."""
    pack_root = repo_root / "org-packs" / "guard-fixture-pack"
    drg_dir = pack_root / "drg"
    drg_dir.mkdir(parents=True, exist_ok=True)
    (drg_dir / "fixture.graph.yaml").write_text(_ORG_DRG_FRAGMENT_YAML, encoding="utf-8")
    return pack_root


def _write_org_pack_empty(repo_root: Path, *, with_empty_drg_dir: bool) -> Path:
    """An org pack root that exists but carries no loadable graph content.

    Covers both the no-``drg/``-directory-at-all case (``with_empty_drg_dir=
    False``) and the empty-``drg/``-directory case (``with_empty_drg_dir=
    True``) -- US2 AC1+AC2 (T002.5) requires both.
    """
    pack_root = repo_root / "org-packs" / "empty-fixture-pack"
    pack_root.mkdir(parents=True, exist_ok=True)
    if with_empty_drg_dir:
        (pack_root / "drg").mkdir(parents=True, exist_ok=True)
    return pack_root


def _built_in_graph() -> DRGGraph:
    return _graph_from_yaml(_BUILT_IN_GRAPH_YAML)


def _cli_context_json(repo_root: Path) -> dict[str, Any]:
    """Invoke ``charter context --action ... --mission-type ... --json``.

    Patches ``find_repo_root`` onto *repo_root* (mirrors
    ``test_context_include.py``'s ``TestJsonEntryPoint`` pattern) and patches
    ``charter._drg_helpers.load_built_in_graph`` onto the small fixture graph
    above. Asserts a successful ("result": "success") response and returns the
    parsed JSON payload -- callers that need to assert on FAILURE responses
    should not use this helper (see ``_cli_context_json_raw`` below, added by
    T006).
    """
    payload = _cli_context_json_raw(repo_root, json_output=True)
    assert payload["result"] == "success", payload
    assert payload["success"] is True, payload
    return payload


def _cli_context_json_raw(repo_root: Path, *, json_output: bool) -> dict[str, Any]:
    """Invoke ``charter context`` and return the parsed JSON payload, with no
    success/failure assertion -- the raw entry point every other helper in
    this module composes.
    """
    from specify_cli.cli.commands.charter._app import charter_app
    import specify_cli.cli.commands.charter as charter_pkg

    runner = CliRunner()
    args = ["context", "--action", _ACTION, "--mission-type", _MISSION_TYPE, "--no-mark-loaded"]
    if json_output:
        args.append("--json")
    with (
        patch.object(charter_pkg, "find_repo_root", lambda: repo_root),
        patch("charter._drg_helpers.load_built_in_graph", side_effect=_built_in_graph),
    ):
        result = runner.invoke(charter_app, args)
    assert result.output, "CLI produced no output"
    return json.loads(result.output)  # type: ignore[no-any-return]


def _typed_counts(payload: dict[str, Any]) -> dict[str, int]:
    return {key: len(payload[key]) for key in _TYPED_COUNT_KEYS}


def _text_render(repo_root: Path, *, org_root: Path | None) -> str:
    """Direct plain-text render of the same action (no ``--json``).

    Per the spec ruling's binding ``--json``/plain-text split: procedure
    counts are read from this render's Procedures section, never from the
    ``--json`` payload (which carries no ``procedures`` array).
    """
    from charter.context import build_charter_context

    with patch("charter._drg_helpers.load_built_in_graph", side_effect=_built_in_graph):
        result = build_charter_context(
            repo_root,
            action=_ACTION,
            mission_type=_MISSION_TYPE,
            org_root=org_root,
            mark_loaded=False,
        )
    return str(result.text)


def _procedures_section_lines(text: str) -> list[str]:
    """Return the bullet lines under the plain-text render's ``Procedures:``
    heading. Returns ``[]`` when the heading is absent (the bucket was
    empty, so ``_extend_named_artifact_lines`` never emitted the heading at
    all).

    PR-TESTS-001 (R3 confirmed): the raw lines (not just their count) let a
    caller assert POSITIVE MEMBERSHIP of a specific procedure id -- a count
    growing is consistent with "some unrelated procedure appeared", not
    "the one this test cares about did".
    """
    lines = text.splitlines()
    try:
        start = lines.index("  Procedures:")
    except ValueError:
        return []
    section: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("    - "):
            section.append(line)
        else:
            break
    return section


def _procedures_section_count(text: str) -> int:
    """Count the bullet lines under the plain-text render's ``Procedures:``
    heading (see :func:`_procedures_section_lines`)."""
    return len(_procedures_section_lines(text))


# ---------------------------------------------------------------------------
# T002 (IC-01, FR-001/FR-002/FR-005; User Stories 1 & 2)
# ---------------------------------------------------------------------------


class TestDrgOnlyOrgPackGuard:
    def test_drg_only_pack_preserves_or_grows_typed_counts(self, tmp_path: Path) -> None:
        """US1 AC1; FR-001/002/005; SC-001.

        A drg/-only org pack must never *reduce* the resolved action's typed
        doctrine counts below the no-pack baseline -- today's bug (an
        unconditional ``load_graph_or_dir(org_root)`` raising ``DRGLoadError``
        on a directory with no root graph) collapses them to zero instead.
        """
        baseline_repo = tmp_path / "baseline"
        baseline_repo.mkdir()
        _write_project_fixture(baseline_repo)
        _write_config(baseline_repo, org_pack_root=None)
        baseline_payload = _cli_context_json(baseline_repo)
        baseline_counts = _typed_counts(baseline_payload)
        baseline_procedures = _procedures_section_count(
            _text_render(baseline_repo, org_root=None)
        )

        with_pack_repo = tmp_path / "with_pack"
        with_pack_repo.mkdir()
        _write_project_fixture(with_pack_repo)
        pack_root = _write_org_pack_drg_only(with_pack_repo)
        _write_config(with_pack_repo, org_pack_root=pack_root)
        with_pack_payload = _cli_context_json(with_pack_repo)
        with_pack_counts = _typed_counts(with_pack_payload)
        with_pack_procedures = _procedures_section_count(
            _text_render(with_pack_repo, org_root=pack_root)
        )

        for key in _TYPED_COUNT_KEYS:
            assert with_pack_counts[key] >= baseline_counts[key], (
                f"{key}: with-pack count {with_pack_counts[key]} fell below "
                f"the no-pack baseline {baseline_counts[key]}"
            )
        assert with_pack_procedures >= baseline_procedures, (
            f"procedures: with-pack count {with_pack_procedures} fell below "
            f"the no-pack baseline {baseline_procedures}"
        )

    def test_drg_fragment_node_reaches_resolved_bundle(self, tmp_path: Path) -> None:
        """US1 AC2; FR-002; SC-002 -- positive membership, not "no error".

        Covers both the ``--json`` typed-array membership check (tactics)
        and, per the binding SPEC-FRESH4-001 ruling and PR-TESTS-001 (R3
        confirmed), a plain-text-render positive-membership check for the
        drg/-declared PROCEDURE -- the kind issue #3384's own reproduction
        actually zeroed and that no test in this module checked membership
        for before this addition.
        """
        repo = tmp_path / "with_pack"
        repo.mkdir()
        _write_project_fixture(repo)
        pack_root = _write_org_pack_drg_only(repo)
        _write_config(repo, org_pack_root=pack_root)

        payload = _cli_context_json(repo)

        tactic_ids = {t["id"] for t in payload["tactics"]}
        assert _ORG_DRG_TACTIC_ID in tactic_ids, (
            f"drg/-declared tactic {_ORG_DRG_TACTIC_ID!r} did not reach the "
            f"resolved bundle: {tactic_ids}"
        )

        procedure_lines = _procedures_section_lines(_text_render(repo, org_root=pack_root))
        assert any(_ORG_DRG_PROCEDURE_ID in line for line in procedure_lines), (
            f"drg/-declared procedure {_ORG_DRG_PROCEDURE_ID!r} did not reach "
            f"the resolved bundle's plain-text Procedures section: {procedure_lines}"
        )

    def test_empty_org_pack_degrades_to_no_pack_baseline(self, tmp_path: Path) -> None:
        """US2 AC1+AC2; FR-001; SC-003.

        An org pack root that exists but carries no loadable graph content
        (neither at the root nor under ``drg/``) must degrade cleanly to the
        no-pack baseline -- exactly, not merely ">=" -- with no exception.
        Covers both the no-``drg/``-directory-at-all case and the
        empty-``drg/``-directory case.
        """
        baseline_repo = tmp_path / "baseline"
        baseline_repo.mkdir()
        _write_project_fixture(baseline_repo)
        _write_config(baseline_repo, org_pack_root=None)
        baseline_counts = _typed_counts(_cli_context_json(baseline_repo))
        baseline_procedures = _procedures_section_count(
            _text_render(baseline_repo, org_root=None)
        )

        for with_empty_drg_dir in (False, True):
            case_repo = tmp_path / f"empty_pack_drg_{with_empty_drg_dir}"
            case_repo.mkdir()
            _write_project_fixture(case_repo)
            pack_root = _write_org_pack_empty(case_repo, with_empty_drg_dir=with_empty_drg_dir)
            _write_config(case_repo, org_pack_root=pack_root)

            payload = _cli_context_json(case_repo)
            counts = _typed_counts(payload)
            procedures = _procedures_section_count(_text_render(case_repo, org_root=pack_root))

            for key in _TYPED_COUNT_KEYS:
                assert counts[key] == baseline_counts[key], (
                    f"with_empty_drg_dir={with_empty_drg_dir}, {key}: "
                    f"expected exactly the no-pack baseline "
                    f"{baseline_counts[key]}, got {counts[key]}"
                )
            assert procedures == baseline_procedures, (
                f"with_empty_drg_dir={with_empty_drg_dir}, procedures: "
                f"expected exactly the no-pack baseline {baseline_procedures}, "
                f"got {procedures}"
            )


# ---------------------------------------------------------------------------
# T004 (IC-02, FR-003/FR-006; User Story 4)
# ---------------------------------------------------------------------------

_ROOT_AND_DRG_TACTIC_ID = "org-root-tactic-3384"
_ROOT_AND_DRG_DIRECTIVE_ID = "org-drg-directive-3384"
_ROOT_GRAPH_YAML_ROOT_AND_DRG = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {{urn: 'tactic:{_ROOT_AND_DRG_TACTIC_ID}', kind: tactic}}
    edges:
      - {{source: '{_ACTION_URN}', target: 'tactic:{_ROOT_AND_DRG_TACTIC_ID}', relation: scope}}
    """
)
_DRG_GRAPH_YAML_ROOT_AND_DRG = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {{urn: 'directive:{_ROOT_AND_DRG_DIRECTIVE_ID}', kind: directive}}
    edges:
      - {{source: '{_ACTION_URN}', target: 'directive:{_ROOT_AND_DRG_DIRECTIVE_ID}', relation: scope}}
    """
)

#: A duplicated-triple fixture: the root graph and the drg/ fragment each
#: declare the identical ``(source, target, relation)`` edge -- root declares
#: both endpoint nodes; the fragment only repeats the edge (single-file
#: loading never checks dangling references -- only the merged-graph-level
#: ``assert_valid`` does, so this is a legal standalone fragment).
_DUP_EDGE_SOURCE_URN = "directive:org-dup-source-3384"
_DUP_EDGE_TARGET_URN = "directive:org-dup-target-3384"
_ROOT_GRAPH_YAML_DUP_EDGE = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {{urn: '{_DUP_EDGE_SOURCE_URN}', kind: directive}}
      - {{urn: '{_DUP_EDGE_TARGET_URN}', kind: directive}}
    edges:
      - {{source: '{_DUP_EDGE_SOURCE_URN}', target: '{_DUP_EDGE_TARGET_URN}', relation: requires}}
    """
)
_DRG_GRAPH_YAML_DUP_EDGE = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes: []
    edges:
      - {{source: '{_DUP_EDGE_SOURCE_URN}', target: '{_DUP_EDGE_TARGET_URN}', relation: requires}}
    """
)

#: PR-BOUNDARY-001 regression fixture: the root graph declares the identical
#: ``(source, target, relation)`` triple TWICE WITHIN ITSELF (a same-file
#: authoring bug), paired with an unrelated, unconnected drg/ sibling so the
#: dedup step has genuinely cross-source content to distinguish from.
_WITHIN_ROOT_DUP_SOURCE_URN = "directive:org-within-root-dup-source-3384"
_WITHIN_ROOT_DUP_TARGET_URN = "directive:org-within-root-dup-target-3384"
_ROOT_GRAPH_YAML_WITHIN_ROOT_DUP = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {{urn: '{_WITHIN_ROOT_DUP_SOURCE_URN}', kind: directive}}
      - {{urn: '{_WITHIN_ROOT_DUP_TARGET_URN}', kind: directive}}
    edges:
      - {{source: '{_WITHIN_ROOT_DUP_SOURCE_URN}', target: '{_WITHIN_ROOT_DUP_TARGET_URN}', relation: requires}}
      - {{source: '{_WITHIN_ROOT_DUP_SOURCE_URN}', target: '{_WITHIN_ROOT_DUP_TARGET_URN}', relation: requires}}
    """
)
_UNRELATED_DRG_SIBLING_URN = "directive:org-unrelated-drg-sibling-3384"
_DRG_GRAPH_YAML_UNRELATED_SIBLING = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {{urn: '{_UNRELATED_DRG_SIBLING_URN}', kind: directive}}
    edges: []
    """
)

#: PR-TESTS-002 regression fixture: the SAME node URN, declared in both the
#: root graph and the drg/ fragment, with two DIFFERENT ``label`` values --
#: the only fixture shape that can observe which side's label "won" a
#: same-URN conflict (FR-003: drg/ is authoritative).
_LABEL_CONFLICT_URN = "directive:org-label-conflict-3384"
_LABEL_CONFLICT_ROOT_LABEL = "root label"
_LABEL_CONFLICT_DRG_LABEL = "drg label"
_ROOT_GRAPH_YAML_LABEL_CONFLICT = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {{urn: '{_LABEL_CONFLICT_URN}', kind: directive, label: '{_LABEL_CONFLICT_ROOT_LABEL}'}}
    edges: []
    """
)
_DRG_GRAPH_YAML_LABEL_CONFLICT = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {{urn: '{_LABEL_CONFLICT_URN}', kind: directive, label: '{_LABEL_CONFLICT_DRG_LABEL}'}}
    edges: []
    """
)


def _write_org_pack_root_and_drg(
    repo_root: Path, *, root_yaml: str, drg_yaml: str, dir_name: str
) -> Path:
    """An org pack with content at BOTH the root and ``drg/``."""
    pack_root = repo_root / "org-packs" / dir_name
    drg_dir = pack_root / "drg"
    drg_dir.mkdir(parents=True, exist_ok=True)
    (pack_root / "graph.yaml").write_text(root_yaml, encoding="utf-8")
    (drg_dir / "fixture.graph.yaml").write_text(drg_yaml, encoding="utf-8")
    return pack_root


class TestRootAndDrgMerge:
    def test_root_and_drg_both_present_neither_node_dropped(self, tmp_path: Path) -> None:
        """US4 AC1; FR-003/FR-006a; SC-005.

        A root-level graph and a ``drg/`` fragment declaring distinct,
        non-overlapping nodes must both contribute to the resolved bundle --
        two independent positive-membership assertions (guards the
        vacuity-by-empty-set hazard: "no exception while iterating a
        possibly-empty discovered set" would pass vacuously and prove
        nothing).
        """
        repo = tmp_path / "root_and_drg"
        repo.mkdir()
        _write_project_fixture(repo)
        pack_root = _write_org_pack_root_and_drg(
            repo,
            root_yaml=_ROOT_GRAPH_YAML_ROOT_AND_DRG,
            drg_yaml=_DRG_GRAPH_YAML_ROOT_AND_DRG,
            dir_name="root-and-drg-fixture-pack",
        )
        _write_config(repo, org_pack_root=pack_root)

        payload = _cli_context_json(repo)

        tactic_ids = {t["id"] for t in payload["tactics"]}
        directive_ids = {d["id"] for d in payload["directives"]}
        assert _ROOT_AND_DRG_TACTIC_ID in tactic_ids, (
            f"root-declared tactic {_ROOT_AND_DRG_TACTIC_ID!r} was dropped: {tactic_ids}"
        )
        assert _ROOT_AND_DRG_DIRECTIVE_ID in directive_ids, (
            f"drg/-declared directive {_ROOT_AND_DRG_DIRECTIVE_ID!r} was dropped: "
            f"{directive_ids}"
        )

    def test_identical_edge_triple_deduped_to_one_not_dropped(self, tmp_path: Path) -> None:
        """US4 AC2; FR-003/FR-006b; SC-006.

        An identical ``(source, target, relation)`` edge triple declared by
        BOTH the root graph and its ``drg/`` sibling must collapse to exactly
        one retained copy -- not raise (duplicate-edge validation) and not
        silently drop both copies. Calls ``load_validated_graph`` directly
        (not the ``--json`` CLI, which does not expose raw edge triples).
        """
        from charter._drg_helpers import load_validated_graph
        from doctrine.drg.models import Relation

        repo = tmp_path / "dup_edge"
        repo.mkdir()
        pack_root = _write_org_pack_root_and_drg(
            repo,
            root_yaml=_ROOT_GRAPH_YAML_DUP_EDGE,
            drg_yaml=_DRG_GRAPH_YAML_DUP_EDGE,
            dir_name="dup-edge-fixture-pack",
        )

        with patch("charter._drg_helpers.load_built_in_graph", side_effect=_built_in_graph):
            merged = load_validated_graph(repo, org_root=pack_root)

        matching_edges = [
            edge
            for edge in merged.edges
            if edge.source == _DUP_EDGE_SOURCE_URN
            and edge.target == _DUP_EDGE_TARGET_URN
            and edge.relation == Relation.REQUIRES
        ]
        assert len(matching_edges) == 1, (  # golden-count: cardinality-is-contract
            f"expected exactly one retained copy of the duplicated triple, "
            f"found {len(matching_edges)}: {matching_edges}"
        )

    def test_within_root_duplicate_edge_triple_still_raises(self, tmp_path: Path) -> None:
        """PR-BOUNDARY-001 regression (R3 confirmed finding).

        A ``(source, target, relation)`` triple duplicated TWICE WITHIN the
        root graph alone -- not split one-in-root/one-in-drg/ -- is a
        same-file authoring bug unrelated to the cross-source FR-003/IC-02
        dedup this class of fix targets. It must still reach the final
        ``assert_valid`` and raise ``DRGValidationError``, exactly as it did
        before ``_dedup_org_layer_edges`` existed. A dedup step that is not
        scoped to genuinely cross-source duplicates (i.e. one that flags a
        triple purely by ``duplicate_edge_triples`` over the merged graph,
        with no regard for which source each occurrence came from) would
        silently collapse this to one retained edge and swallow the
        authoring error -- the drg/ sibling here carries only unrelated
        content, so nothing about it should influence this outcome.
        """
        from charter._drg_helpers import load_validated_graph
        from doctrine.drg.validator import DRGValidationError

        repo = tmp_path / "within_root_dup"
        repo.mkdir()
        pack_root = _write_org_pack_root_and_drg(
            repo,
            root_yaml=_ROOT_GRAPH_YAML_WITHIN_ROOT_DUP,
            drg_yaml=_DRG_GRAPH_YAML_UNRELATED_SIBLING,
            dir_name="within-root-dup-fixture-pack",
        )

        with (
            patch("charter._drg_helpers.load_built_in_graph", side_effect=_built_in_graph),
            pytest.raises(DRGValidationError),
        ):
            load_validated_graph(repo, org_root=pack_root)

    def test_same_urn_node_label_conflict_drg_is_authoritative(self, tmp_path: Path) -> None:
        """PR-TESTS-002 regression (R3 confirmed finding).

        FR-003/IC-02: on a same-URN node-label conflict between the root
        graph and the drg/ fragment, drg/ is authoritative -- the org-layer
        sub-merge calls ``merge_layers(root_graph, drg_graph)`` (root as the
        ``built_in`` positional argument, drg/ as ``project``), and
        ``merge_layers`` overrides the built-in label with the project
        label on a shared URN. Neither existing ``TestRootAndDrgMerge`` test
        declares the same URN with two different labels in both sources, so
        this is the only assertion pinning that direction -- reversing the
        argument order at ``_drg_helpers.py``'s ``merge_layers(root_graph,
        drg_graph)`` call site (root/drg swapped) would flip this to
        root-authoritative and pass every other test in this module
        untouched.
        """
        from charter._drg_helpers import load_validated_graph

        repo = tmp_path / "label_conflict"
        repo.mkdir()
        pack_root = _write_org_pack_root_and_drg(
            repo,
            root_yaml=_ROOT_GRAPH_YAML_LABEL_CONFLICT,
            drg_yaml=_DRG_GRAPH_YAML_LABEL_CONFLICT,
            dir_name="label-conflict-fixture-pack",
        )

        with patch("charter._drg_helpers.load_built_in_graph", side_effect=_built_in_graph):
            merged = load_validated_graph(repo, org_root=pack_root)

        resolved = next(node for node in merged.nodes if node.urn == _LABEL_CONFLICT_URN)
        assert resolved.label == _LABEL_CONFLICT_DRG_LABEL, (
            f"expected the drg/ fragment's label {_LABEL_CONFLICT_DRG_LABEL!r} "
            f"to win the same-URN conflict (FR-003), got {resolved.label!r}"
        )


# ---------------------------------------------------------------------------
# T006 (IC-03, FR-004; User Story 3 + root-level defect-class broadening)
# ---------------------------------------------------------------------------

#: Invalid YAML syntax (unterminated flow sequence) -- a parser error, not a
#: schema-validation error.
_MALFORMED_YAML_TEXT = "schema_version: '1.0'\nnodes: [unterminated\n"

#: Valid YAML, but schema-invalid: a node missing the required ``kind`` field.
_SCHEMA_INVALID_YAML_TEXT = textwrap.dedent(
    """\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {urn: 'directive:missing-kind-3384'}
    edges: []
    """
)

_VALID_SIBLING_DIRECTIVE_ID = "org-valid-sibling-directive-3384"
_VALID_DRG_SIBLING_YAML = textwrap.dedent(
    f"""\
    schema_version: '1.0'
    generated_at: '2026-08-13T00:00:00Z'
    generated_by: test
    nodes:
      - {{urn: 'directive:{_VALID_SIBLING_DIRECTIVE_ID}', kind: directive}}
    edges:
      - {{source: '{_ACTION_URN}', target: 'directive:{_VALID_SIBLING_DIRECTIVE_ID}', relation: scope}}
    """
)


def _write_org_pack_malformed_drg(repo_root: Path, *, fragment_text: str) -> Path:
    """An org pack with NO root graph and a malformed ``drg/`` fragment."""
    pack_root = repo_root / "org-packs" / "malformed-drg-fixture-pack"
    drg_dir = pack_root / "drg"
    drg_dir.mkdir(parents=True, exist_ok=True)
    (drg_dir / "broken.graph.yaml").write_text(fragment_text, encoding="utf-8")
    return pack_root


def _write_org_pack_malformed_root(repo_root: Path, *, with_valid_drg_sibling: bool) -> Path:
    """An org pack with a malformed root-level ``graph.yaml``.

    ``with_valid_drg_sibling=True`` also writes a valid, loadable
    ``drg/fixture.graph.yaml`` alongside it (the combined case,
    T006.4). ``with_valid_drg_sibling=False`` writes no ``drg/`` directory at
    all -- the standalone case, T006.5, load-bearing per PLAN-FRESH2-003 and
    kept as its own test rather than folded into the combined case.
    """
    pack_root = repo_root / "org-packs" / "malformed-root-fixture-pack"
    pack_root.mkdir(parents=True, exist_ok=True)
    (pack_root / "graph.yaml").write_text(_MALFORMED_YAML_TEXT, encoding="utf-8")
    if with_valid_drg_sibling:
        drg_dir = pack_root / "drg"
        drg_dir.mkdir(parents=True, exist_ok=True)
        (drg_dir / "fixture.graph.yaml").write_text(_VALID_DRG_SIBLING_YAML, encoding="utf-8")
    return pack_root


def _assert_distinguishable_failure(payload: dict[str, Any]) -> None:
    """A malformed-content failure must be a real, reported failure -- never
    ``"result": "success"`` with a silently-zeroed bundle (the shape US2's
    genuinely-empty-pack case produces).
    """
    assert payload["result"] != "success", payload
    assert payload.get("error"), f"expected a non-empty error field, got: {payload}"


class TestMalformedOrgLayerContentVisibility:
    def test_malformed_yaml_drg_fragment_raises_distinguishable_failure(
        self, tmp_path: Path
    ) -> None:
        """US3 AC1; FR-004; SC-007."""
        repo = tmp_path / "malformed_drg_yaml"
        repo.mkdir()
        _write_project_fixture(repo)
        pack_root = _write_org_pack_malformed_drg(repo, fragment_text=_MALFORMED_YAML_TEXT)
        _write_config(repo, org_pack_root=pack_root)

        payload = _cli_context_json_raw(repo, json_output=True)

        _assert_distinguishable_failure(payload)

    def test_schema_invalid_drg_fragment_raises_same_distinguishable_shape(
        self, tmp_path: Path
    ) -> None:
        """US3 AC2; FR-004; SC-007 -- same failure shape, parse-error vs.
        schema-violation cause."""
        repo = tmp_path / "malformed_drg_schema"
        repo.mkdir()
        _write_project_fixture(repo)
        pack_root = _write_org_pack_malformed_drg(repo, fragment_text=_SCHEMA_INVALID_YAML_TEXT)
        _write_config(repo, org_pack_root=pack_root)

        payload = _cli_context_json_raw(repo, json_output=True)

        _assert_distinguishable_failure(payload)

    def test_malformed_root_graph_with_valid_drg_sibling_raises_distinguishable_failure(
        self, tmp_path: Path
    ) -> None:
        """FR-001/FR-004; the plan ruling's defect-class-closure rationale.

        A valid, loadable sibling ``drg/`` fragment must NOT rescue a
        malformed root graph into a silent, zeroed "success" -- it must
        raise the same distinguishable failure shape.
        """
        repo = tmp_path / "malformed_root_with_sibling"
        repo.mkdir()
        _write_project_fixture(repo)
        pack_root = _write_org_pack_malformed_root(repo, with_valid_drg_sibling=True)
        _write_config(repo, org_pack_root=pack_root)

        payload = _cli_context_json_raw(repo, json_output=True)

        _assert_distinguishable_failure(payload)

    def test_malformed_root_graph_no_drg_directory_raises_distinguishable_failure(
        self, tmp_path: Path
    ) -> None:
        """FR-001/FR-004 -- the load-bearing test per PLAN-FRESH2-003.

        Deliberately its OWN test function, distinct from the combined
        malformed-root+valid-drg-sibling case above: this fixture's org pack
        has NO ``drg/`` content whatsoever, so it is the only test that goes
        RED against a conforming-but-incomplete implementation that only
        fires the root-level wrap when ``drg/`` also happens to exist
        alongside it. Do not collapse this into the combined-case test.
        """
        repo = tmp_path / "malformed_root_no_drg"
        repo.mkdir()
        _write_project_fixture(repo)
        pack_root = _write_org_pack_malformed_root(repo, with_valid_drg_sibling=False)
        _write_config(repo, org_pack_root=pack_root)

        payload = _cli_context_json_raw(repo, json_output=True)

        _assert_distinguishable_failure(payload)
