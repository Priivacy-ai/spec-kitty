"""FR-002 (WP03, SPEC-ARCH-002) — ``charter context`` (plain-text AND
``--json``) must resolve the FULL configured org-pack chain, not just pack 1.

Root cause (see this WP's own review finding, SPEC-ARCH-002, and
``spec.md`` User Story 4's "Corrected scope" note): the truncation is not
JSON-only. ``build_charter_context`` already routed through the
self-resolving wrapper ``charter.action_doctrine_bundle._resolve_action_bundle``
— but that wrapper only widens to the full org-pack chain when its caller
passes ``org_root=None``; an *explicit* (already-truncated) ``org_root`` is
honoured verbatim and never widens. ``build_charter_context_json`` had a
SECOND, independent defect on top of this: it called the private
``_load_action_doctrine_bundle`` directly, bypassing ``_resolve_action_bundle``
entirely -- so even a caller passing ``org_root=None`` never widened.

Both halves are required together (T017 stops the CLI-level truncation that
fed an already-narrowed ``org_root`` into both entry points; T018 routes the
JSON path through ``_resolve_action_bundle``, mirroring the plain-text
path). This module proves BOTH are required, empirically, not just that a
plausible-looking fix landed -- see the non-vacuity mutation evidence
recorded in this WP's report.

Fixture shape: a minimal action node lives in an isolated (patched) built-in
graph; each org pack contributes its own self-contained ``*.graph.yaml``
fragment declaring one ``directive`` node reached from the action node via a
depth-1 ``scope`` edge (``doctrine.drg.query.resolve_context``'s step 1 only
walks ``scope`` edges directly off the action URN -- see that function's
docstring), plus a real ``<id>.directive.yaml`` artifact file so the
directive's real content (not just a catalog-miss ID stub) is what's being
proven present, mirroring ``tests/specify_cli/mission_step_contracts/
test_executor.py``'s ``write_org_tier_step_contract_fixture``/
``write_second_org_pack_fixture`` chain-fixture pattern (that module proves
the analogous #3525 DRG-merge fix at the executor seam; this module proves
FR-002's caller-level fix at the ``charter.context`` public API seam).
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from charter.context import build_charter_context, build_charter_context_json
from doctrine.drg.loader import load_graph_or_dir

pytestmark = pytest.mark.fast

_ACTION = "specify"
_MISSION_TYPE = "software-dev"
_ACTION_URN = f"action:{_MISSION_TYPE}/{_ACTION}"

_PACK_A_ID = "ORG_CHAIN_FIXTURE_PACK_A"
_PACK_B_ID = "ORG_CHAIN_FIXTURE_PACK_B"
_PACK_A_URN = f"directive:{_PACK_A_ID}"
_PACK_B_URN = f"directive:{_PACK_B_ID}"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _write_project_fixture(repo_root: Path) -> None:
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text(
        "# Project Charter\n\n## Policy Summary\n\n- Intent: FR-002 org-chain fixture\n",
        encoding="utf-8",
    )
    (charter_dir / "governance.yaml").write_text(
        textwrap.dedent(
            """\
            doctrine:
              template_set: software-dev-default
              selected_paradigms: []
              selected_directives: []
              available_tools: []
            """
        ),
        encoding="utf-8",
    )


def _write_config(repo_root: Path, org_roots: list[Path]) -> None:
    """Register *org_roots* (declaration order) in ``.kittify/config.yaml``.

    ``mission_type_activations`` is provisioned unconditionally --
    ``PackContext.from_config`` is read on every ``build_charter_context``/
    ``build_charter_context_json`` call and must not hard-fail on a
    genuinely absent key (mirrors ``tests/charter/test_context_org_governance
    .py``'s ``_write_config``).
    """
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    lines = ["mission_type_activations:", "  - software-dev"]
    if org_roots:
        lines.append("doctrine:")
        lines.append("  org:")
        lines.append("    packs:")
        for index, root in enumerate(org_roots):
            lines.append(f"      - name: chain-fixture-pack-{index}")
            lines.append(f"        local_path: {root}")
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_org_pack(org_root: Path, *, directive_id: str, directive_urn: str) -> None:
    """One self-contained org pack: a real directive artifact + a DRG
    fragment scoping it directly off the action node (depth-1 ``scope``
    edge -- ``resolve_context`` step 1 is the only step that walks edges
    straight from the action URN itself)."""
    directives_dir = org_root / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    (directives_dir / f"{directive_id.lower()}.directive.yaml").write_text(
        textwrap.dedent(
            f"""\
            schema_version: "1.0"
            id: {directive_id}
            title: "{directive_id} fixture directive"
            intent: "Prove org-chain content (FR-002) reaches charter context."
            enforcement: advisory
            """
        ),
        encoding="utf-8",
    )
    (org_root / f"{directive_id.lower()}.graph.yaml").write_text(
        textwrap.dedent(
            f"""\
            schema_version: "1.0"
            generated_at: "2026-08-17T00:00:00Z"
            generated_by: "test"
            nodes:
              - urn: "{directive_urn}"
                kind: directive
                label: "{directive_id} fixture directive"
            edges:
              - source: "{_ACTION_URN}"
                target: "{directive_urn}"
                relation: scope
            """
        ),
        encoding="utf-8",
    )


def _isolated_built_in_graph(tmp_path: Path):
    """A built-in graph containing ONLY the action node this fixture needs
    -- decoupled from the real, evolving built-in doctrine catalog (mirrors
    ``tests/charter/test_org_pack_chain_drg_merge.py``'s ``_empty_built_in``/
    ``_built_in_from`` pattern, extended with the one action node this
    module's ``resolve_context`` traversal needs a start point for)."""
    root = tmp_path / "isolated-built-in-graph"
    root.mkdir(exist_ok=True)
    (root / "graph.yaml").write_text(
        textwrap.dedent(
            f"""\
            schema_version: "1.0"
            generated_at: "2026-08-17T00:00:00Z"
            generated_by: "test"
            nodes:
              - urn: "{_ACTION_URN}"
                kind: action
                label: "Specify"
            edges: []
            """
        ),
        encoding="utf-8",
    )
    return load_graph_or_dir(root)


def _render_both(repo_root: Path, tmp_path: Path) -> tuple[str, dict[str, object]]:
    """Render both the plain-text and JSON ``charter context`` payloads for
    ``_ACTION``, patched onto the isolated built-in graph, calling
    ``build_charter_context``/``build_charter_context_json`` exactly the way
    the FIXED ``context()`` CLI command now does: ``org_root=None`` (T017),
    letting the charter-layer self-resolution walk the full configured
    chain."""
    mock_built_in = _isolated_built_in_graph(tmp_path)
    with patch(
        "charter._drg_helpers.load_built_in_graph",
        return_value=mock_built_in,
    ):
        text_result = build_charter_context(
            repo_root,
            action=_ACTION,
            depth=2,
            mark_loaded=False,
            org_root=None,
            mission_type=_MISSION_TYPE,
        )
        json_payload = build_charter_context_json(
            repo_root,
            action=_ACTION,
            depth=2,
            org_root=None,
            mission_type=_MISSION_TYPE,
        )
    return str(text_result.text), json_payload


def _directive_ids(json_payload: dict[str, object]) -> set[str]:
    directives = json_payload.get("directives", [])
    assert isinstance(directives, list)
    return {entry["id"] for entry in directives}  # type: ignore[index]


# ---------------------------------------------------------------------------
# T019 -- FR-002 AC2: two-pack chain, pack-2-only content, both paths
# ---------------------------------------------------------------------------


class TestTwoPackChainReachesBothPaths:
    """Red-first (pre-fix): pack B's directive is absent from BOTH the JSON
    ``directives`` array and the plain-text ``Action Doctrine`` stanza --
    the JSON path never even threads a chain (bug #1: ``_load_action_doctrine_bundle``
    called directly, no ``org_roots``), and the plain-text path's already-
    "correct" wrapper (``_resolve_action_bundle``) never widens because the
    CLI truncates ``org_root`` to ``org_roots[0]`` before either call (bug #2,
    the CLI-level truncation this WP also owns). Post-fix: pack B's content
    is present in both.

    Non-vacuity: mutating either T017 (CLI truncation removal, modelled here
    by the ``org_root=None`` call convention in ``_render_both``) or T018
    (the internal ``_resolve_action_bundle`` swap in
    ``build_charter_context_json``) back out independently must turn this RED
    again -- recorded via manual revert-and-rerun in the WP report, per this
    mission's stricter-than-default FR-002 test strategy (both halves proven
    necessary, not just the whole change).
    """

    def test_pack_two_directive_present_in_json_and_text(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _write_project_fixture(repo_root)
        org_root_a = tmp_path / "org-pack-a"
        org_root_b = tmp_path / "org-pack-b"
        _write_org_pack(org_root_a, directive_id=_PACK_A_ID, directive_urn=_PACK_A_URN)
        _write_org_pack(org_root_b, directive_id=_PACK_B_ID, directive_urn=_PACK_B_URN)
        _write_config(repo_root, [org_root_a, org_root_b])

        text, payload = _render_both(repo_root, tmp_path)

        # Pack A (declared first) already worked pre-fix for a single pack --
        # a required companion assertion, not the load-bearing one.
        assert _PACK_A_ID in _directive_ids(payload), (
            "regression: pack A (first-declared) dropped out of the JSON "
            "bundle -- the fix must not break the already-working single-pack case"
        )
        assert _PACK_A_ID in text, (
            "regression: pack A dropped out of the plain-text Action Doctrine stanza"
        )

        # Pack B (second-declared) is the load-bearing assertion: it was
        # UNREACHABLE before this WP's fix at this call site, regardless of
        # which single root the pre-fix code happened to resolve.
        assert _PACK_B_ID in _directive_ids(payload), (
            "pack B (second org pack in the chain) is missing from the JSON "
            "``directives`` array -- build_charter_context_json is still "
            "truncating to a single org root instead of resolving the full "
            "configured chain"
        )
        assert _PACK_B_ID in text, (
            "pack B (second org pack in the chain) is missing from the "
            "plain-text ``Action Doctrine`` stanza -- build_charter_context "
            "is still truncating to a single org root"
        )


# ---------------------------------------------------------------------------
# T020(i) -- FR-002 AC1: single healthy org pack, unchanged (no regression)
# ---------------------------------------------------------------------------


class TestSinglePackRegression:
    def test_single_org_pack_content_present_in_json_and_text(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _write_project_fixture(repo_root)
        org_root_a = tmp_path / "org-pack-a"
        _write_org_pack(org_root_a, directive_id=_PACK_A_ID, directive_urn=_PACK_A_URN)
        _write_config(repo_root, [org_root_a])

        text, payload = _render_both(repo_root, tmp_path)

        assert _PACK_A_ID in _directive_ids(payload)
        assert _PACK_A_ID in text


# ---------------------------------------------------------------------------
# T020(ii) -- FR-002 AC3: no org pack configured, unchanged (no regression)
# ---------------------------------------------------------------------------


class TestNoOrgPackRegression:
    def test_no_org_pack_configured_no_org_content_no_crash(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _write_project_fixture(repo_root)
        _write_config(repo_root, [])

        text, payload = _render_both(repo_root, tmp_path)

        assert _PACK_A_ID not in _directive_ids(payload)
        assert _PACK_B_ID not in _directive_ids(payload)
        assert _PACK_A_ID not in text
        assert _PACK_B_ID not in text
        # Bootstrap mode still renders cleanly -- org-inert is a no-op, not a
        # degraded/erroring render.
        assert "Action Doctrine (specify):" in text


# ---------------------------------------------------------------------------
# T021 -- malformed pack in the chain: unchanged whole-bundle-collapse,
# not this WP's territory (PR #3401) -- must not WORSEN, loud collapse is OK.
# ---------------------------------------------------------------------------


class TestMalformedPackInChainDoesNotWorsen:
    """Per spec.md's "Out of Scope"/C-006: a malformed org pack anywhere in
    the chain collapses the WHOLE action-doctrine bundle (pre-existing
    ``_load_action_doctrine_bundle`` ``except DRGLoadError`` behaviour,
    unchanged by this WP) -- never an uncaught crash to the operator. Before
    this WP's fix, a malformed pack B was simply unreachable (invisible,
    single-root truncation), so this failure mode was structurally
    untestable at this call site; the fix makes it reachable for the first
    time, exhibiting the SAME collapse-not-crash behaviour every other
    ``load_validated_graph`` caller with org roots threaded already has
    (e.g. ``gate_bindings.py``) -- disclosed status quo, not a regression.
    """

    def test_malformed_second_pack_collapses_whole_bundle_without_crashing(
        self, tmp_path: Path
    ) -> None:
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _write_project_fixture(repo_root)
        org_root_a = tmp_path / "org-pack-a"
        _write_org_pack(org_root_a, directive_id=_PACK_A_ID, directive_urn=_PACK_A_URN)

        # Malformed: directory exists on disk but ships no *.graph.yaml
        # fragment anywhere under it (``load_graph_or_dir`` raises
        # ``DRGLoadError`` for this shape -- see
        # ``tests/specify_cli/mission_step_contracts/test_executor.py``'s
        # identically-shaped ``malformed-org-pack-b`` fixture).
        org_root_b = tmp_path / "malformed-org-pack-b"
        (org_root_b / "drg").mkdir(parents=True)
        (org_root_b / "drg" / "fragment.yaml").write_text(
            "kind: directives\n", encoding="utf-8"
        )
        _write_config(repo_root, [org_root_a, org_root_b])

        # Must not raise -- DRGLoadError is caught inside
        # _load_action_doctrine_bundle and logged, never propagated to the
        # operator.
        text, payload = _render_both(repo_root, tmp_path)

        # Whole-bundle collapse: even pack A's (structurally fine, declared
        # first) content is gone too -- this is the documented, unchanged
        # pre-existing behaviour (PR #3401's territory to make per-root
        # instead of whole-bundle), not something this WP is fixing.
        assert _directive_ids(payload) == set()
        assert _PACK_A_ID not in text
        assert _PACK_B_ID not in text
        # Still a clean bootstrap render, not a stack trace.
        assert "Action Doctrine (specify):" in text
